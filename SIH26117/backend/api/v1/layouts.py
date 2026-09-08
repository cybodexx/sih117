"""Layout endpoints: per-document and per-chat (aggregated) DocLayout-YOLO output.

GET /api/v1/documents/{id}/layout       -> one file's page/block breakdown
GET /api/v1/chat/sessions/{id}/layout    -> every scoped file combined + totals
"""
from __future__ import annotations

import uuid
from collections import Counter
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.deps import get_current_user
from backend.core.exceptions import Forbidden, NotFound
from backend.core.rbac import DocumentLabels, ServerUserContext, can_read
from backend.db.models.chat import ChatSessionModel
from backend.db.models.document import DocumentModel
from backend.db.session import get_db
from backend.services.ingest.layout_store import load_layout, load_layouts

logger = structlog.get_logger()
router = APIRouter(prefix="/layouts", tags=["layouts"])


def _summarize(pages: list[dict]) -> dict:
    counts: Counter = Counter()
    total = 0
    for p in pages:
        for b in p.get("blocks") or []:
            counts[b.get("class", "unknown")] += 1
            total += 1
    return {
        "classes": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "block_count": total,
        "page_count": len(pages),
    }


async def _doc_ok(
    db: AsyncSession, user: ServerUserContext, document_id: str
) -> DocumentModel:
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")
    if not can_read(
        user,
        DocumentLabels(
            status=doc.status,
            clearance_level=doc.clearance_level,
            department=doc.department,
            legal_hold=doc.legal_hold,
        ),
    ).allowed:
        raise Forbidden("You cannot access that document")
    return doc


@router.get("/documents/{document_id}")
async def document_layout(
    document_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    doc = await _doc_ok(db, user, document_id)
    pages = await load_layout(str(doc.id))
    return {
        "document_id": str(doc.id),
        "document_title": doc.filename,
        "model": pages[0]["model"] if pages else None,
        "status": "READY" if pages else "NOT_ANALYSED",
        "pages": pages,
        "summary": _summarize(pages),
    }


@router.get("/chat/sessions/{session_id}")
async def session_layout(
    session_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ChatSessionModel).where(ChatSessionModel.id == uuid.UUID(session_id))
    )
    session_model = result.scalar_one_or_none()
    if session_model is None or str(session_model.user_id) != user.user_id:
        raise NotFound(f"Session {session_id} not found")

    scope_ids = list(session_model.document_ids or [])
    if not scope_ids and session_model.document_id:
        scope_ids = [str(session_model.document_id)]
    if not scope_ids:
        return {"document_id": None, "session_id": session_id, "files": [], "summary": _summarize([])}

    docs_result = await db.execute(
        select(DocumentModel).where(DocumentModel.id.in_([uuid.UUID(d) for d in scope_ids]))
    )
    docs_map = {str(d.id): d for d in docs_result.scalars().all()}
    layouts = await load_layouts(scope_ids)

    files: list[dict] = []
    for did in scope_ids:
        doc = docs_map.get(did)
        pages = layouts.get(did) or []
        files.append(
            {
                "document_id": did,
                "document_title": doc.filename if doc else did,
                "status": pages[0]["model"] if pages else "NOT_ANALYSED",
                "pages": pages,
                "summary": _summarize(pages),
            }
        )

    combined_pages: list[dict] = []
    for did in scope_ids:
        combined_pages.extend(layouts.get(did) or [])

    return {
        "session_id": session_id,
        "scope_document_ids": scope_ids,
        "files": files,
        "summary": _summarize(combined_pages),
    }
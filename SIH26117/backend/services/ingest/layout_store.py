"""Persistence + retrieval for per-document layout analysis."""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, select

from backend.db.base import async_session
from backend.db.models.layout import DocumentLayoutModel
from backend.services.ingest.doclayout import MODEL_NAME

logger = structlog.get_logger()


async def save_layout(document_id: UUID, per_page: list[dict], model: str = MODEL_NAME) -> None:
    """Replace any stored layout for this document with the fresh analysis."""
    async with async_session() as db:
        await db.execute(
            delete(DocumentLayoutModel).where(DocumentLayoutModel.document_id == document_id)
        )
        for p in per_page:
            db.add(
                DocumentLayoutModel(
                    document_id=document_id,
                    page=int(p["page"]),
                    blocks=p.get("blocks") or [],
                    model=model,
                )
            )
        await db.commit()
    logger.info("layout_saved", document_id=str(document_id), pages=len(per_page))


async def load_layout(document_id: str) -> list[dict]:
    async with async_session() as db:
        result = await db.execute(
            select(DocumentLayoutModel)
            .where(DocumentLayoutModel.document_id == UUID(document_id))
            .order_by(DocumentLayoutModel.page.asc())
        )
        rows = result.scalars().all()
    return [
        {"page": r.page, "blocks": r.blocks or [], "model": r.model or MODEL_NAME}
        for r in rows
    ]


async def load_layouts(document_ids: list[str]) -> dict[str, list[dict]]:
    if not document_ids:
        return {}
    async with async_session() as db:
        result = await db.execute(
            select(DocumentLayoutModel)
            .where(DocumentLayoutModel.document_id.in_([UUID(d) for d in document_ids]))
            .order_by(DocumentLayoutModel.document_id.asc(), DocumentLayoutModel.page.asc())
        )
        rows = result.scalars().all()
    out: dict[str, list[dict]] = {}
    for doc_id in document_ids:
        out[doc_id] = []
    for r in rows:
        out.setdefault(str(r.document_id), []).append(
            {"page": r.page, "blocks": r.blocks or [], "model": r.model or MODEL_NAME}
        )
    return out
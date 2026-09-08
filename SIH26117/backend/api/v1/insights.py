"""Insights routes — deterministic auto-charts over materialised data tables."""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.deps import get_current_user
from backend.core.exceptions import BadRequest, NotFound
from backend.core.rbac import DocumentLabels, ServerUserContext, can_read
from backend.db.models.document import DocumentModel
from backend.db.session import get_db
from backend.services.analysis.insights import build_insights

logger = structlog.get_logger()
router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/documents/{document_id}")
async def document_insights(
    document_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Auto-computed charts and stats for a READY tabular document."""
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
        raise NotFound(f"Document {document_id} not found")

    payload = await build_insights(doc)
    if payload is None:
        raise BadRequest(
            "No tabular data insights are available for this document "
            "(only CSV/XLSX files with an ingested data table are supported)"
        )
    return payload
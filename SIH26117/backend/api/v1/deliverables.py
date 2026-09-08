"""Deliverable routes — authenticated download of generated vault files.

Deliverables are owned by the requesting user; access is scoped to that user
(no cross-user reads), and every file streams from under the vault path.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.deps import get_current_user
from backend.core.exceptions import NotFound
from backend.core.rbac import ServerUserContext
from backend.db.models.deliverable import DeliverableModel
from backend.db.session import get_db
from backend.services.audit.writer import emit as audit_emit

logger = structlog.get_logger()
router = APIRouter(prefix="/deliverables", tags=["deliverables"])


async def _stream_file(path: Path):
    async with aiofiles.open(path, "rb") as f:
        while True:
            chunk = await f.read(64 * 1024)
            if not chunk:
                break
            yield chunk


@router.get("/{deliverable_id}/file")
async def stream_deliverable_file(
    deliverable_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Stream the generated file bytes to its owner."""
    result = await db.execute(
        select(DeliverableModel).where(
            DeliverableModel.id == uuid.UUID(deliverable_id),
            DeliverableModel.user_id == uuid.UUID(user.user_id),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFound(f"Deliverable {deliverable_id} not found")

    path = Path(item.storage_key)
    if not path.exists():
        raise NotFound("Deliverable file not found in vault")

    await audit_emit(
        "DELIVERABLE_DOWNLOADED",
        correlation_id="",
        user_id=user.user_id,
        role=str(user.role),
        resource_type="deliverable",
        resource_id=str(item.id),
        document_ids=[],
        severity="info",
    )

    return StreamingResponse(
        _stream_file(path),
        media_type=item.mime,
        headers={"Content-Disposition": f'attachment; filename="{item.filename}"'},
    )
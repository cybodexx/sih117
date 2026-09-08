"""Image attachment routes — store for the chat vision (multimodal P3) gate."""
from __future__ import annotations

import asyncio
import io
import uuid
from typing import Annotated

import aiofiles
import structlog
from fastapi import APIRouter, Depends, File, UploadFile

from backend.core.config import get_settings
from backend.core.deps import get_current_user
from backend.core.exceptions import BadRequest
from backend.core.rbac import ServerUserContext
from backend.schemas.attachment import AttachmentAccepted
from backend.services.audit.writer import emit as audit_emit

logger = structlog.get_logger()
router = APIRouter(prefix="/attachments", tags=["attachments"])
settings = get_settings()

_ALLOWED_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/bmp": "bmp",
}


@router.post("", response_model=AttachmentAccepted, status_code=201)
async def upload_attachment(
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """Accept an image attachment for the current user's chat turns."""
    if not file.filename:
        raise BadRequest("Filename is required")

    mime = (file.content_type or "").lower()
    ext = _ALLOWED_MIME.get(mime)
    if ext is None:
        raise BadRequest("Only image attachments are supported (png, jpeg, webp, gif, bmp)")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    owner_dir = settings.vault_path / "attachments" / user.user_id
    owner_dir.mkdir(parents=True, exist_ok=True)

    attachment_id = uuid.uuid4()
    dest = owner_dir / f"{attachment_id}.{ext}"

    buffer = io.BytesIO()
    while True:
        chunk = await file.read(256 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise BadRequest(f"Attachment exceeds {settings.max_upload_mb} MB limit")
        buffer.write(chunk)

    if size == 0:
        raise BadRequest("Empty attachment")

    payload = buffer.getvalue()
    del buffer

    from backend.services.crypto.vault_crypto import (
        generate_dek,
        vault_encryption_enabled,
        write_attachment_bytes,
    )

    if vault_encryption_enabled():
        dek, _ = generate_dek()
        await asyncio.to_thread(write_attachment_bytes, dest, payload, dek)
    else:
        await asyncio.to_thread(dest.write_bytes, payload)

    await audit_emit(
        "ATTACHMENT_UPLOADED",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=user.user_id,
        role=str(user.role),
        resource_type="attachment",
        resource_id=str(attachment_id),
        decision='{"accept": true}',
        tool_calls=[],
        severity="info",
    )

    logger.info("attachment_uploaded", attachment_id=str(attachment_id), bytes=size)
    return AttachmentAccepted(
        attachment_id=str(attachment_id), name=file.filename, size=size, mime=mime
    )
"""Document routes — upload, list, get, stream file, retry, labels."""
from __future__ import annotations

import hashlib
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import aiofiles
import aiofiles.os
import structlog
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import get_current_user, require_role
from backend.core.exceptions import BadRequest, Conflict, NotFound
from backend.core.rbac import Role, ServerUserContext
from backend.db.models.document import DocumentModel
from backend.db.session import get_db
from backend.schemas.document import (
    DocumentAccepted,
    DocumentLabelUpdate,
    DocumentRead,
    PageRead,
)
from backend.services.audit.writer import emit as audit_emit
from backend.services.ingest.enqueue import enqueue_ingest

logger = structlog.get_logger()
router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


def _doc_to_read(d: DocumentModel) -> DocumentRead:
    return DocumentRead(
        id=str(d.id),
        filename=d.filename,
        mime=d.mime,
        size_bytes=d.size_bytes,
        page_count=d.page_count,
        status=d.status,
        chunk_count=d.chunk_count,
        clearance_level=d.clearance_level,
        department=d.department,
        owner_id=str(d.owner_id),
        checksum=d.checksum,
        error_reason=d.error_reason,
        created_at=d.created_at.isoformat() if d.created_at else "",
        ingested_at=d.ingested_at.isoformat() if d.ingested_at else None,
    )


async def _stream_file(path: Path) -> AsyncIterator[bytes]:
    async with aiofiles.open(path, "rb") as f:
        while True:
            chunk = await f.read(64 * 1024)
            if not chunk:
                break
            yield chunk


@router.post("", response_model=DocumentAccepted, status_code=202)
async def upload_document(
    user: Annotated[
        ServerUserContext,
        Depends(require_role(Role.ENGINEER, Role.ANALYST, Role.ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    clearance_level: int = Query(0, ge=0, le=3),
    department: str = Query("ADMIN"),
):
    """Accept a document upload. Compute SHA-256, check dedup, store metadata."""
    if not file.filename:
        raise BadRequest("Filename is required")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    sha256 = hashlib.sha256()
    size = 0

    vault_dir = settings.vault_path / "uploads"
    vault_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    dest = vault_dir / f"{file_id}"

    async with aiofiles.open(dest, "wb") as out:
        while True:
            chunk = await file.read(256 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                await aiofiles.os.remove(str(dest))
                raise BadRequest(
                    f"File exceeds {settings.max_upload_mb} MB limit"
                )
            sha256.update(chunk)
            await out.write(chunk)

    checksum = f"sha256:{sha256.hexdigest()}"

    dedup = await db.execute(
        select(DocumentModel).where(DocumentModel.checksum == checksum)
    )
    existing = dedup.scalar_one_or_none()
    if existing is not None:
        await aiofiles.os.remove(str(dest))
        return DocumentAccepted(
            document_id=str(existing.id),
            status=existing.status,
            checksum=checksum,
            deduplicated=True,
        )

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    doc = DocumentModel(
        id=file_id,
        owner_id=uuid.UUID(user.user_id),
        filename=file.filename,
        mime=mime,
        size_bytes=size,
        checksum=checksum,
        storage_key=str(dest),
        clearance_level=clearance_level,
        department=department,
        status="QUEUED",
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()

    try:
        await enqueue_ingest(
            str(doc.id), correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", "")
        )
    except Exception:
        logger.exception("ingest_enqueue_failed", document_id=str(doc.id))

    await audit_emit(
        "DOCUMENT_UPLOADED",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=user.user_id,
        role=str(user.role),
        resource_type="document",
        resource_id=str(doc.id),
        document_ids=[str(doc.id)],
        severity="info",
    )

    logger.info(
        "document_uploaded",
        document_id=str(doc.id),
        filename=file.filename,
        checksum=checksum,
    )
    return DocumentAccepted(
        document_id=str(doc.id),
        status="QUEUED",
        checksum=checksum,
        deduplicated=False,
    )


@router.get("", response_model=PageRead)
async def list_documents(
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    """List documents filtered by status with pagination."""
    base = select(DocumentModel)
    if status is not None:
        base = base.where(DocumentModel.status == status.upper())

    total_q = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_q.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        base.order_by(DocumentModel.created_at.desc()).offset(offset).limit(size)
    )
    docs = result.scalars().all()

    return PageRead(
        items=[_doc_to_read(d) for d in docs],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")
    return _doc_to_read(doc)


@router.get("/{document_id}/file")
async def stream_document_file(
    document_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Stream file bytes from vault."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")

    path = Path(doc.storage_key)
    if not path.exists():
        raise NotFound("File not found in vault")

    gen = _stream_file(path)
    return StreamingResponse(
        gen,
        media_type=doc.mime,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.post("/{document_id}/retry", status_code=202)
async def retry_document(
    document_id: str,
    user: Annotated[
        ServerUserContext,
        Depends(require_role(Role.ENGINEER, Role.ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-enqueue a failed document for ingestion."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")
    if doc.status != "FAILED":
        raise BadRequest("Only FAILED documents can be retried")

    doc.status = "QUEUED"
    doc.error_reason = None
    await db.flush()
    await db.commit()

    try:
        await enqueue_ingest(
            document_id,
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        )
    except Exception:
        logger.exception("ingest_enqueue_failed", document_id=document_id)

    logger.info("document_retry", document_id=document_id)
    return {"status": "queued", "document_id": document_id}


@router.patch("/{document_id}/labels", response_model=DocumentRead)
async def update_labels(
    document_id: str,
    body: DocumentLabelUpdate,
    user: Annotated[
        ServerUserContext,
        Depends(require_role(Role.ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin re-label document clearance and department."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")

    doc.clearance_level = body.clearance_level
    doc.department = body.department
    await db.flush()
    await db.commit()

    logger.info(
        "document_relabel",
        document_id=document_id,
        clearance=body.clearance_level,
        department=body.department,
    )
    return _doc_to_read(doc)

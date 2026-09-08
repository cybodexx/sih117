"""Document routes — upload, list, get, stream file, retry, labels."""
from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import aiofiles
import aiofiles.os
import structlog
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy import and_, delete, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import get_current_user, require_role
from backend.core.exceptions import BadRequest, Conflict, NotFound
from backend.core.rbac import (
    DocumentLabels,
    Role,
    ServerUserContext,
    can_manage,
    can_read,
)
from backend.db.models.document import DocumentModel
from backend.db.session import get_db
from backend.schemas.document import (
    DocumentAccepted,
    DocumentAnalysis,
    DocumentLabelUpdate,
    DocumentRead,
    PageRead,
)
from backend.db.models.chat import ChatSessionModel
from backend.db.models.layout import DocumentLayoutModel
from backend.services.analysis.document_analyzer import analyze_document
from backend.services.audit.writer import emit as audit_emit
from backend.services.ingest.csv_sql import table_name_for
from backend.services.ingest.enqueue import enqueue_ingest

try:
    from qdrant_client import QdrantClient, models as qmodels
except Exception:  # pragma: no cover
    QdrantClient = None
    qmodels = None

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


def _labels(doc: DocumentModel) -> DocumentLabels:
    """Collect the policy-relevant labels of a document."""
    return DocumentLabels(
        status=doc.status,
        clearance_level=doc.clearance_level,
        department=doc.department,
        legal_hold=doc.legal_hold,
    )


async def _get_authorized_doc(
    db: AsyncSession, user: ServerUserContext, document_id: str
) -> DocumentModel:
    """Load a document and enforce can_read. 404 on absence OR policy denial
    (presence of a shielded resource is not disclosed)."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")
    if not can_read(user, _labels(doc)).allowed:
        raise NotFound(f"Document {document_id} not found")
    return doc


def _readable_filter(user: ServerUserContext):
    """SQL predicate equivalent of can_read for list queries:
    READY + clearance within role + department within role scope + legal-hold rule."""
    overage = DocumentModel.clearance_level > user.clearance_level.value
    if user.role in (Role.AUDITOR, Role.ADMIN):
        dept_ok = true()
    else:
        dept_ok = DocumentModel.department.in_(user.departments)
    if user.role is Role.AUDITOR:
        legal_ok = true()
    else:
        legal_ok = DocumentModel.legal_hold.is_(False)
    return and_(
        DocumentModel.status == "READY",
        ~overage,
        dept_ok,
        legal_ok,
    )


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

    # Per-file data-encryption key (software TEE hardening): the file is written
    # at-rest as an AES-256-GCM blob and the DEK is wrapped with the master key.
    from backend.services.crypto.vault_crypto import (
        generate_dek,
        write_encrypted_file,
    )

    dek, wrapped_dek = generate_dek()
    plaintext_buffer: list[bytes] = []
    size = 0

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
            plaintext_buffer.append(chunk)

    checksum = f"sha256:{sha256.hexdigest()}"

    dedup = await db.execute(
        select(DocumentModel).where(
            DocumentModel.checksum == checksum,
            DocumentModel.status != "FAILED",
        )
    )
    existing = dedup.scalar_one_or_none()
    if existing is not None:
        await aiofiles.os.remove(str(dest))
        await audit_emit(
            "DOCUMENT_UPLOADED",
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
            user_id=user.user_id,
            role=str(user.role),
            resource_type="document",
            resource_id=str(existing.id),
            document_ids=[str(existing.id)],
            decision=json.dumps({"deduplicated": True, "status": existing.status}),
            severity="info",
        )
        logger.info(
            "document_deduplicated",
            document_id=str(existing.id),
            filename=file.filename,
            checksum=checksum,
        )
        return DocumentAccepted(
            document_id=str(existing.id),
            status=existing.status,
            checksum=checksum,
            deduplicated=True,
            duplicate_of=existing.filename,
        )

    plaintext = b"".join(plaintext_buffer)
    plaintext_buffer = []
    write_encrypted_file(dest, plaintext, dek)

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    doc = DocumentModel(
        id=file_id,
        owner_id=uuid.UUID(user.user_id),
        filename=file.filename,
        mime=mime,
        size_bytes=size,
        checksum=checksum,
        storage_key=str(dest),
        wrapped_dek=wrapped_dek,
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
    base = base.where(_readable_filter(user))

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
    doc = await _get_authorized_doc(db, user, document_id)
    return _doc_to_read(doc)


@router.get("/{document_id}/file")
async def stream_document_file(
    document_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Stream file bytes from vault."""
    doc = await _get_authorized_doc(db, user, document_id)

    path = Path(doc.storage_key)
    if not path.exists():
        raise NotFound("File not found in vault")

    # Docs held in the vault are encrypted at rest. There is deliberately NO
    # raw-file streaming path: bytes are decrypted (or returned for legacy
    # pre-encryption uploads) via read_plaintext_file so the stored blob is
    # never served as-is.
    from backend.services.crypto.vault_crypto import read_plaintext_file

    raw = await asyncio.to_thread(read_plaintext_file, path, doc.wrapped_dek)
    return Response(
        content=raw,
        media_type=doc.mime,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.get("/{document_id}/preview")
async def document_preview(
    document_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
):
    """Render one page of a document as PNG for the workbench preview.

    Images are returned as-is; PDF pages are rasterised with PyMuPDF. The page
    is returned at 96 DPI so layout bbox coordinates (normalised 0..1) can be
    overlaid 1:1 client-side.
    """
    doc = await _get_authorized_doc(db, user, document_id)

    path = Path(doc.storage_key)
    if not path.exists():
        raise NotFound("File not found in vault")

    # Decrypt the at-rest blob to plaintext (software vault hardening).
    from backend.services.crypto.vault_crypto import read_plaintext_file

    raw = await asyncio.to_thread(read_plaintext_file, path, doc.wrapped_dek)

    mime = (doc.mime or "").lower()
    if mime.startswith("image/"):
        return Response(
            content=raw,
            media_type=doc.mime,
            headers={"Cache-Control": "private, max-age=3600"},
        )

    if mime in ("application/pdf",) or doc.filename.lower().endswith(".pdf"):
        try:
            import fitz
        except Exception as exc:  # pragma: no cover
            raise NotFound("PDF rasteriser unavailable") from exc
        try:
            rendered = await _render_pdf_bytes(raw, page)
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return Response(
            content=rendered,
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    raise BadRequest(
        f"Preview is not available for {doc.filename}; only images and PDFs can be rendered"
    )


async def _render_pdf_bytes(raw: bytes, page: int) -> bytes:
    import fitz

    def _render():
        with fitz.open(stream=raw, filetype="pdf") as pdf:
            if page < 1 or page > len(pdf):
                raise ValueError(f"Page {page} is out of range (1..{len(pdf)})")
            pix = pdf[page - 1].get_pixmap(dpi=96, alpha=False)
            return pix.tobytes("png")

    return await asyncio.to_thread(_render)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user: Annotated[
        ServerUserContext,
        Depends(require_role(Role.ENGINEER, Role.ANALYST, Role.ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Permanently remove a document: its qdrant points, vault file, derived
    ds_* table, any chat sessions scoped to it, and its DB row."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")
    if not can_manage(
        user,
        _labels(doc),
        owner_id=str(doc.owner_id),
    ).allowed:
        raise NotFound(f"Document {document_id} not found")

    # 1. Remove qdrant points.
    if QdrantClient is not None and qmodels is not None:
        try:
            qclient = QdrantClient(url=settings.qdrant_url, timeout=15)
            qclient.delete(
                collection_name=settings.qdrant_collection,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=str(doc.id)),
                            )
                        ]
                    )
                ),
            )
        except Exception:
            logger.exception("document_delete_qdrant_failed", document_id=str(doc.id))

    # 2. Remove vault file.
    path = Path(doc.storage_key)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        logger.exception("document_delete_file_failed", storage_key=str(doc.storage_key))

    # 3. Drop derived ds_* table (if any), matching the ingestion slug.
    from sqlalchemy import text

    try:
        fname = doc.filename
        if fname.lower().endswith((".csv", ".xlsx")):
            table = table_name_for(fname)
            if table.startswith("ds_"):
                await db.execute(text(f"DROP TABLE IF EXISTS {table}"))
    except Exception:
        logger.exception("document_delete_ds_table_failed", filename=doc.filename)

    # 4. Remove scoped chat sessions + their messages.
    from backend.db.models.message import ChatMessageModel

    scoped_session_rows = (
        await db.execute(
            select(ChatSessionModel.id).where(
                ChatSessionModel.user_id == uuid.UUID(user.user_id),
                or_(
                    ChatSessionModel.document_id == uuid.UUID(document_id),
                    ChatSessionModel.document_ids.contains([document_id]),
                ),
            )
        )
    ).scalars().all()
    for sid in scoped_session_rows:
        await db.execute(
            ChatMessageModel.__table__.delete().where(
                ChatMessageModel.session_id == sid
            )
        )
    await db.execute(
        ChatSessionModel.__table__.delete().where(
            ChatSessionModel.user_id == uuid.UUID(user.user_id),
            or_(
                ChatSessionModel.document_id == uuid.UUID(document_id),
                ChatSessionModel.document_ids.contains([document_id]),
            ),
        )
    )

    # 4b. Remove layout analysis rows.
    await db.execute(
        delete(DocumentLayoutModel).where(
            DocumentLayoutModel.document_id == uuid.UUID(document_id)
        )
    )

    await db.delete(doc)
    await db.commit()

    await audit_emit(
        "DOCUMENT_DELETED",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=user.user_id,
        role=str(user.role),
        resource_type="document",
        resource_id=str(doc.id),
        document_ids=[str(doc.id)],
        decision=json.dumps({"removed": True}),
        severity="info",
    )
    logger.info("document_deleted", document_id=str(doc.id), filename=doc.filename)
    return None


def _retry_allowed(status: str) -> bool:
    """A document may be re-enqueued only when it is FAILED or READY."""
    return status in ("FAILED", "READY")


@router.post("/{document_id}/retry", status_code=202)
async def retry_document(
    document_id: str,
    user: Annotated[
        ServerUserContext,
        Depends(require_role(Role.ENGINEER, Role.ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-enqueue a FAILED or READY document for (re-)ingestion."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFound(f"Document {document_id} not found")
    if not can_manage(user, _labels(doc), owner_id=str(doc.owner_id)).allowed:
        raise NotFound(f"Document {document_id} not found")
    if not _retry_allowed(doc.status):
        raise BadRequest("Only FAILED or READY documents can be retried")

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


@router.post("/{document_id}/analyze", response_model=DocumentAnalysis)
async def analyze_document_endpoint(
    document_id: str,
    user: Annotated[
        ServerUserContext,
        Depends(require_role(Role.ENGINEER, Role.ANALYST, Role.ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Run a grounded LLM analysis over an indexed document's chunks."""
    doc = await _get_authorized_doc(db, user, document_id)
    if not can_manage(user, _labels(doc), owner_id=str(doc.owner_id)).allowed:
        raise NotFound(f"Document {document_id} not found")

    analysis = await analyze_document(doc, user)

    await audit_emit(
        "DOCUMENT_ANALYZED",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=user.user_id,
        role=str(user.role),
        resource_type="document",
        resource_id=str(doc.id),
        document_ids=[str(doc.id)],
        severity="info",
    )

    return DocumentAnalysis(
        document_id=str(doc.id),
        report=analysis["report"],
        chunks_read=analysis["chunks_read"],
        latency_ms=analysis["latency_ms"],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


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

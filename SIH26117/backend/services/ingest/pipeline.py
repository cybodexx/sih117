"""Ingest pipeline driver: load file -> parse -> structure -> chunk -> embed -> index -> READY.

M4 owns this file. Called from the ARQ worker only.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.base import async_session
from backend.db.models.document import DocumentModel
from backend.services.audit.writer import emit as audit_emit
from backend.services.ingest.chunker import split
from backend.services.ingest.embedder import embed_batched
from backend.services.ingest.indexer import upsert
from backend.services.ingest.pdf_parser import Element, parse as parse_pdf
from backend.services.ingest.structurer import build as build_tree

logger = structlog.get_logger()
settings = get_settings()

_CSV_MIME = {"text/csv", "application/csv", "text/plain"}
_IMAGE_MIME = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/bmp"}


def _csv_elements(raw: str) -> list[Element]:
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0]
    cards: list[Element] = []
    for i in range(1, len(lines) + 1, 200):
        block = "\n".join([header] + lines[i : i + 200])
        cards.append(Element(kind="DATA_SLICE", page=1, text=block))
    return cards


def _image_elements() -> list[Element]:
    return [Element(kind="FIGURE", page=1, text="[figure: uploaded image]")]


async def _load_bytes(storage_key: str) -> bytes:
    import aiofiles

    async with aiofiles.open(storage_key, "rb") as f:
        return await f.read()


async def _parse_by_mime(raw: bytes, mime: str, filename: str) -> tuple[list[Element], int]:
    mime_key = (mime or "").lower()
    if filename.lower().endswith(".pdf") or "pdf" in mime_key:
        import fitz

        elements = await parse_pdf(raw)
        with fitz.open(stream=raw, filetype="pdf") as doc:
            return elements, len(doc)
    if mime_key in _CSV_MIME or filename.lower().endswith((".csv", ".txt", ".log", ".json")):
        text = raw.decode("utf-8", errors="replace")
        return _csv_elements(text), 1
    if mime_key in _IMAGE_MIME or filename.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        return _image_elements(), 1
    raise ValueError(f"Unsupported MIME for ingestion: {mime}")


async def ingest_document(document_id: str, correlation_id: str = "") -> dict[str, object]:
    """Run the full ingest pipeline for one document. Raises on failure."""
    start = __import__("time").monotonic()
    doc = await _load_document(document_id)
    if doc is None:
        raise RuntimeError(f"document {document_id} not found")
    if doc.status in {"READY", "PROCESSING"}:
        return {"status": doc.status, "document_id": document_id, "chunk_count": doc.chunk_count}

    storage_key = doc.storage_key
    mime = doc.mime
    filename = doc.filename
    clearance = int(doc.clearance_level or 0)
    department = doc.department or "ADMIN"
    title = filename

    await _set_status(document_id, "PROCESSING", None)

    try:
        raw = await _load_bytes(storage_key)
        elements, page_hint = await _parse_by_mime(raw, mime, filename)
        if not elements:
            raise ValueError("No extractable elements found in file")

        tree = build_tree(elements)
        nodes = tree.walk_reading_order()
        chunks = split(
            nodes,
            document_id=document_id,
            doc_title=title,
            clearance_level=clearance,
            department=department,
        )
        if not chunks:
            raise ValueError("Document produced zero chunks")

        texts = [c.embed_text for c in chunks]
        vectors = await embed_batched(texts)

        indexed = await upsert(chunks, vectors, document_id)
        elapsed_s = round(__import__("time").monotonic() - start, 1)

        await _finalize(document_id, page_hint, indexed, elapsed_s)
        await audit_emit(
            "DOCUMENT_INGESTED",
            correlation_id=correlation_id,
            resource_type="document",
            resource_id=document_id,
            document_ids=[document_id],
            severity="info",
        )
        logger.info(
            "ingest_complete",
            document_id=document_id,
            chunks=indexed,
            pages=page_hint,
            seconds=elapsed_s,
        )
        return {"status": "READY", "document_id": document_id, "chunk_count": indexed}
    except Exception as exc:
        logger.error("ingest_failed", document_id=document_id, error=str(exc))
        await _set_status(document_id, "FAILED", str(exc))
        await audit_emit(
            "DOCUMENT_INGEST_FAILED",
            correlation_id=correlation_id,
            resource_type="document",
            resource_id=document_id,
            document_ids=[document_id],
            decision=str(exc)[:400],
            severity="error",
        )
        raise


async def _load_document(document_id: str) -> DocumentModel | None:
    async with async_session() as db:
        result = await db.execute(
            select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
        )
        doc = result.scalar_one_or_none()
        return doc


async def _set_status(document_id: str, status: str, error_reason: str | None) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return
        doc.status = status
        doc.error_reason = error_reason
        await db.commit()


async def _finalize(document_id: str, page_hint: int, chunk_count: int, elapsed_s: float) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return
        doc.status = "READY"
        doc.error_reason = None
        doc.page_count = page_hint if page_hint else doc.page_count or 1
        doc.chunk_count = chunk_count
        doc.ingested_at = datetime.now(timezone.utc)
        await db.commit()
    logger.info("doc_ready", document_id=document_id, chunks=chunk_count, seconds=elapsed_s)
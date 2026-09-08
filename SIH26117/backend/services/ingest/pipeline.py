"""Ingest pipeline driver: load file -> parse -> structure -> chunk -> embed -> index -> READY.

M4 owns this file. Called from the ARQ worker only.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.base import async_session
from backend.db.models.document import DocumentModel
from backend.services.audit.writer import emit as audit_emit
from backend.services.ingest.chunker import split
from backend.services.ingest.csv_sql import materialize_csv
from backend.services.ingest.embedder import embed_batched
from backend.services.ingest.indexer import upsert
from backend.services.ingest.office_parser import parse_docx, parse_pptx, parse_xlsx
from backend.services.ingest.pdf_parser import Element, parse as parse_pdf
from backend.services.ingest.structurer import build as build_tree

logger = structlog.get_logger()
settings = get_settings()

_CSV_MIME = {"text/csv", "application/csv"}
_TEXT_MIME = {"text/plain", "text/markdown"}
_IMAGE_MIME = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/bmp"}

_CSV_EXT = (".csv",)
_TEXT_EXT = (".txt", ".text", ".md", ".markdown", ".log")
_JSON_EXT = (".json",)
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tiff", ".bmp")
_DOCX_EXT = (".docx",)
_PPTX_EXT = (".pptx",)
_XLSX_EXT = (".xlsx", ".xls")
_LEGACY_ERROR = {
    ".doc": "Legacy .doc is not supported — save it as .docx and upload again.",
    ".ppt": "Legacy .ppt is not supported — save it as .pptx and upload again.",
    ".odt": "OpenDocument .odt is not supported — export to .docx and upload again.",
    ".ods": "OpenDocument .ods is not supported — export to .xlsx and upload again.",
    ".rtf": "RTF is not supported — save it as .docx or .txt and upload again.",
}


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


def _text_elements(text: str) -> list[Element]:
    blocks = [ln for ln in text.splitlines() if ln.strip()]
    if not blocks:
        return []
    cards: list[Element] = []
    for i in range(0, len(blocks), 200):
        cards.append(Element(kind="TEXT", page=1, text="\n".join(blocks[i : i + 200])))
    return cards


def _image_elements() -> list[Element]:
    return [Element(kind="FIGURE", page=1, text="[figure: uploaded image]")]


async def _load_bytes(storage_key: str, wrapped_dek: str | None = None) -> bytes:
    import aiofiles

    from backend.services.crypto.vault_crypto import read_plaintext_file

    path = __import__("pathlib").Path(storage_key)
    async with aiofiles.open(path, "rb") as f:
        blob = await f.read()
    if not wrapped_dek:
        return blob
    return await asyncio.to_thread(read_plaintext_file, path, wrapped_dek)


async def _parse_by_mime(
    raw: bytes, mime: str, filename: str
) -> tuple[list[Element], int, str | None]:
    """Return (elements, page_hint, tabular_csv_or_None) for the given file."""
    mime_key = (mime or "").lower()
    lower = filename.lower()
    if lower.endswith((".pdf",)) or "pdf" in mime_key:
        import fitz

        elements = await parse_pdf(raw)
        with fitz.open(stream=raw, filetype="pdf") as doc:
            return elements, len(doc), None
    if mime_key in _IMAGE_MIME or lower.endswith(_IMAGE_EXT):
        return _image_elements(), 1, None
    if mime_key in _CSV_MIME or lower.endswith(_CSV_EXT):
        text = raw.decode("utf-8-sig", errors="replace")
        return _csv_elements(text), 1, text
    if lower.endswith(_XLSX_EXT):
        elements, csv_text = parse_xlsx(raw)
        return elements, 1, csv_text
    if lower.endswith(_DOCX_EXT):
        return parse_docx(raw), 1, None
    if lower.endswith(_PPTX_EXT):
        return parse_pptx(raw), 1, None
    if lower.endswith(_JSON_EXT):
        try:
            data = json.loads(raw.decode("utf-8-sig", errors="replace"))
            text = json.dumps(data, indent=2)
        except Exception:
            text = raw.decode("utf-8-sig", errors="replace")
        return _text_elements(text), 1, None
    if mime_key in _TEXT_MIME or lower.endswith(_TEXT_EXT):
        return _text_elements(raw.decode("utf-8", errors="replace")), 1, None
    if lower.endswith(tuple(_LEGACY_ERROR)):
        raise ValueError(_LEGACY_ERROR[lower])
    raise ValueError(
        f"Unsupported file type: {filename!r} ({mime or 'unknown mime'} — "
        f"supported formats: PDF, CSV, XLSX, DOCX, PPTX, TXT/MD/LOG, JSON, PNG/JPG/TIFF)"
    )


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
        raw = await _load_bytes(storage_key, doc.wrapped_dek)
        elements, page_hint, tabular_csv = await _parse_by_mime(raw, mime, filename)
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

        data_table: str | None = None
        if tabular_csv:
            table_stem = re.sub(r"\.[^.]+$", "", filename.lower())
            try:
                table_info = await materialize_csv(
                    f"{table_stem}.csv",
                    tabular_csv.encode("utf-8"),
                    document_id,
                )
                data_table = str(table_info["table"])
                await audit_emit(
                    "CSV_TABLE_LOADED",
                    correlation_id=correlation_id,
                    resource_type="document",
                    resource_id=document_id,
                    document_ids=[document_id],
                    decision=json.dumps(
                        {
                            "table": table_info["table"],
                            "rows": table_info["rows"],
                            "columns": table_info["columns"],
                        }
                    ),
                    severity="info",
                )
            except Exception as exc:
                # The table is an analytics add-on; a failed or empty sheet must
                # not take down an otherwise validly indexed document.
                logger.warning(
                    "data_table_skipped",
                    document_id=document_id,
                    error=str(exc),
                )

        await _finalize(document_id, page_hint, indexed, elapsed_s)
        await _layout_analysis(raw, mime, filename, document_id)
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


async def _layout_analysis(
    raw: bytes, mime: str, filename: str, document_id: str
) -> None:
    """Best-effort DocLayout-YOLO pass over PDFs and images (additive, never fatal)."""
    lower = filename.lower()
    is_pdf = lower.endswith(".pdf") or "pdf" in (mime or "").lower()
    is_image = (mime or "").lower() in _IMAGE_MIME or lower.endswith(_IMAGE_EXT)
    if not (is_pdf or is_image):
        return
    try:
        from backend.services.ingest import doclayout
        from backend.services.ingest.layout_store import save_layout

        if doclayout.layout_available():
            per_page = await doclayout.analyze_bytes(raw, mime, filename)
            if per_page:
                await save_layout(uuid.UUID(document_id), per_page)
    except Exception as exc:
        logger.warning(
            "layout_skipped",
            document_id=document_id,
            error=str(exc)[:300],
        )


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
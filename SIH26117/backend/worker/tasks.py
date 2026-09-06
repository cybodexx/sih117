"""ARQ worker entrypoint. Owned by M3.

The only worker function is `ingest_job`. The API process enqueues via
arq.connections (backend/services/ingest/enqueue.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from arq.connections import RedisSettings
from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.base import async_session
from backend.db.models.document import DocumentModel
from backend.services.audit.writer import emit as audit_emit
from backend.services.ingest.pipeline import ingest_document

logger = structlog.get_logger()
settings = get_settings()


async def ingest_job(ctx: dict, document_id: str, correlation_id: str = "") -> dict[str, object]:
    """Process one uploaded document through the full ingest pipeline."""
    try:
        return await ingest_document(document_id, correlation_id)
    except Exception as exc:
        await _mark_failed(document_id, correlation_id, str(exc))
        raise


async def _mark_failed(document_id: str, correlation_id: str, reason: str) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(DocumentModel).where(DocumentModel.id == uuid.UUID(document_id))
        )
        doc = result.scalar_one_or_none()
        if doc is not None:
            doc.status = "FAILED"
            doc.error_reason = reason[:1000]
            await db.commit()
    await audit_emit(
        "DOCUMENT_INGEST_FAILED",
        correlation_id=correlation_id,
        resource_type="document",
        resource_id=document_id,
        decision=reason[:400],
        severity="error",
    )


class WorkerSettings:
    functions = [ingest_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
    job_timeout = 900
    keep_result = 3600
    health_check_interval = 10
    retry_jobs = False
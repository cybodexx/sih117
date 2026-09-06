"""ARQ enqueue helpers used from the API process (M3)."""
from __future__ import annotations

from arq.connections import RedisSettings, create_pool

from backend.core.config import get_settings


async def enqueue_ingest(document_id: str, correlation_id: str = "") -> None:
    """Enqueue document_id for ingest_job on the shared Redis."""
    settings = get_settings()
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("ingest_job", document_id, correlation_id or "")
    finally:
        await pool.close()
"""Ingest benchmark — real throughput numbers on the live stack.

Reports corpus state from Postgres + Qdrant, and times an actual batch embed
against Ollama (the dominant ingest cost) using the production embedder.
"""
from __future__ import annotations

import asyncio
import time

from qdrant_client import QdrantClient
from sqlalchemy import func, select, text

from backend.core.config import get_settings
from backend.db.base import async_session
from backend.db.models.document import DocumentModel
from backend.services.ingest.embedder import embed_batched

settings = get_settings()


async def main() -> None:
    async with async_session() as db:
        total_docs = (await db.execute(select(func.count()).select_from(DocumentModel))).scalar() or 0
        ready_docs = (await db.execute(
            select(func.count()).select_from(DocumentModel).where(DocumentModel.status == "READY")
        )).scalar() or 0
        total_chunks = (await db.execute(select(func.sum(DocumentModel.chunk_count)))).scalar() or 0
        total_bytes = (await db.execute(select(func.sum(DocumentModel.size_bytes)))).scalar() or 0
        csv_tables = (await db.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE 'ds_%'"
        ))).scalar() or 0

    qclient = QdrantClient(url=settings.qdrant_url, timeout=15)
    qdrant_points = qclient.count(collection_name=settings.qdrant_collection, exact=True).count

    sample = [(
        f"TURBINE-07 vibration {2.2 + i % 9 * 0.1:.2f} mm/s RMS bearing temp "
        f"{60 + i % 20:.1f} C oil pressure {4.5 - i % 10 * 0.1:.2f} bar recorded "
        f"timestamp ISO 2026-08-0{(i % 28) + 1:02d}T08:00:00Z machine status running."
    ) for i in range(100)]
    t0 = time.monotonic()
    vectors = await embed_batched(sample)
    elapsed = time.monotonic() - t0

    print(f"documents (total/READY): {total_docs}/{ready_docs}")
    print(f"indexed chunks (docs field): {total_chunks}")
    print(f"qdrant points: {qdrant_points}")
    print(f"ingested bytes: {total_bytes}")
    print(f"ds_* data tables materialised: {csv_tables}")
    print(f"embed throughput: {len(sample)} texts in {elapsed:.1f}s "
          f"({len(sample)/elapsed:.1f} docs/s, {len(vectors[0])} dims)")


if __name__ == "__main__":
    asyncio.run(main())
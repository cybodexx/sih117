"""Qdrant upsert and idempotent re-ingest indexer."""
from __future__ import annotations

import uuid

import structlog
from qdrant_client import QdrantClient, models

from backend.core.config import get_settings
from backend.services.ingest.chunker import Chunk

logger = structlog.get_logger()
settings = get_settings()

_NAMESPACE_CHUNK = uuid.uuid5(uuid.NAMESPACE_DNS, "aegis-wb.indexer.v1")


def _point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_NAMESPACE_CHUNK, f"{document_id}::{chunk_index}"))


def _build_point(chunk: Chunk, dense_vec: list[float]) -> models.PointStruct:
    payload = {
        "document_id": chunk.document_id,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "embed_text": chunk.embed_text,
        "heading_path": chunk.heading_path,
        "chunk_type": chunk.chunk_type,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "bbox_union": chunk.bbox_union,
        "token_count": chunk.token_count,
        "clearance_level": chunk.clearance_level,
        "department": chunk.department,
        "status": "READY",
    }
    return models.PointStruct(
        id=chunk.id,
        vector={"dense": dense_vec},
        payload=payload,
    )


async def upsert(chunks: list[Chunk], vectors: list[list[float]], document_id: str) -> int:
    """Upsert chunks to Qdrant. Idempotent: deletes existing points for this document first."""
    assert len(chunks) == len(vectors), "chunks and vectors must have same length"
    client = QdrantClient(url=settings.qdrant_url, timeout=30)

    # Idempotent: remove old points for this document
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )

    # Upsert in batches
    batch_size = 64
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        batch_vectors = vectors[i : i + batch_size]
        points = [_build_point(c, v) for c, v in zip(batch_chunks, batch_vectors)]
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=points,
        )

    logger.info("upsert_complete", document_id=document_id, count=len(chunks))
    return len(chunks)


async def self_test(document_id: str) -> None:
    """Verify integrity: retrieve 3 random chunks and check payload."""
    client = QdrantClient(url=settings.qdrant_url, timeout=15)

    results = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        ),
        limit=3,
        with_payload=True,
        with_vectors=False,
    )
    points = results[0]
    if not points:
        raise RuntimeError(f"self_test failed: no chunks found for document {document_id}")

    for pt in points:
        payload = pt.payload or {}
        if payload.get("document_id") != document_id:
            raise RuntimeError(
                f"self_test failed: point {pt.id} has document_id={payload.get('document_id')}"
            )
        if payload.get("clearance_level") is None:
            raise RuntimeError(f"self_test failed: point {pt.id} missing clearance_level")

    logger.info("self_test_passed", document_id=document_id, checked=len(points))

"""Qdrant collection setup for aegis_bge_m3_1024.

Idempotent: skips creation if the collection already exists.
Runs the smoke-test after a fresh creation only.
"""
from __future__ import annotations

import structlog
from qdrant_client import QdrantClient, models

from backend.core.config import get_settings
from backend.services.llm.ollama_client import get_or_create_client

logger = structlog.get_logger()
COLLECTION = "aegis_bge_m3_1024"
DENSE_DIM = 1024


def _ensure_collection(client: QdrantClient) -> bool:
    """Create the collection if it does not exist. Returns True if freshly created."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        logger.info("collection_already_exists", collection=COLLECTION)
        return False

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)},
        sparse_vectors_config={"bm25": models.SparseVectorParams(index=models.SparseIndexParams(on_disk=False))},
    )
    for key, schema in [
        ("clearance_level", models.PayloadSchemaType.INTEGER),
        ("department", models.PayloadSchemaType.KEYWORD),
        ("document_id", models.PayloadSchemaType.KEYWORD),
        ("status", models.PayloadSchemaType.KEYWORD),
        ("chunk_type", models.PayloadSchemaType.KEYWORD),
        ("page_start", models.PayloadSchemaType.INTEGER),
    ]:
        client.create_payload_index(
            collection_name=COLLECTION,
            field_name=key,
            field_schema=schema,
        )
    logger.info("collection_created", collection=COLLECTION)
    return True


async def _smoke_test(client: QdrantClient) -> None:
    ollama = get_or_create_client()
    embeddings = await ollama.embed(["smoke test"])
    dense_vec = embeddings[0]

    point_id = 1
    client.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(
                id=point_id,
                vector={"dense": dense_vec},
                payload={"status": "READY", "clearance_level": 0, "department": "TEST"},
            )
        ],
    )

    results = client.retrieve(collection_name=COLLECTION, ids=[point_id])
    if not results:
        raise RuntimeError("Smoke test failed: point not found after upsert")
    if len(results[0].vector.get("dense", [])) != DENSE_DIM:
        raise RuntimeError(
            f"Smoke test failed: expected dim {DENSE_DIM}, "
            f"got {len(results[0].vector.get('dense', []))}"
        )
    client.delete(collection_name=COLLECTION, points_selector=models.PointIdsList(points=[point_id]))
    logger.info("smoke_test_passed", dim=DENSE_DIM)


async def run_migrations() -> None:
    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url, timeout=30)
    created = _ensure_collection(client)
    if created:
        await _smoke_test(client)
    logger.info("qdrant_setup_complete", collection=COLLECTION, fresh=created)

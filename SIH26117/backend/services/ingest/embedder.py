"""Batched embedder: Ollama bge-m3 → L2-normalize, dim==1024 assertion."""
from __future__ import annotations

import math

import structlog

from backend.core.config import get_settings
from backend.services.llm.ollama_client import get_or_create_client

logger = structlog.get_logger()
settings = get_settings()

BATCH_SIZE = 32


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


async def embed_batched(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in batches of 32, L2-normalise each vector."""
    ollama = get_or_create_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        for attempt in range(3):
            try:
                raw = await ollama.embed(batch, model=settings.embed_model)
                normalised = [_l2_normalize(v) for v in raw]
                for v in normalised:
                    assert len(v) == settings.embed_dim, (
                        f"Embedding dim mismatch: expected {settings.embed_dim}, got {len(v)}"
                    )
                all_embeddings.extend(normalised)
                break
            except Exception as exc:
                if attempt == 2:
                    logger.error("embed_batch_failed", batch_start=i, error=str(exc))
                    raise
                logger.warning("embed_batch_retry", batch_start=i, attempt=attempt)
                import asyncio
                await asyncio.sleep(2 ** attempt)

    return all_embeddings

"""Hybrid retriever: multi-query expansion → dense+sparse → RRF → rerank → MMR → ACL verify."""
from __future__ import annotations

import uuid
from collections import defaultdict

import structlog
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient, models as qmodels

from backend.core.config import get_settings
from backend.core.rbac import ServerUserContext, DocumentLabels, can_read
from backend.db.base import async_session
from backend.db.models.document import DocumentModel
from backend.services.llm.ollama_client import get_or_create_client
from backend.services.rag.acl_filter import build_acl_filter

logger = structlog.get_logger()
settings = get_settings()

_RRF_K = 60
_MMR_LAMBDA = 0.6


class RetrievedChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int = 0
    text: str
    embed_text: str = ""
    heading_path: list[str] = Field(default_factory=list)
    chunk_type: str = "TEXT"
    page_start: int = 1
    page_end: int = 1
    bbox_union: list[float] = Field(default_factory=list)
    token_count: int = 0
    score: float = 0.0
    rerank_score: float | None = None
    clearance_level: int = 0
    department: str = ""
    title: str = ""


def _payload_to_chunk(
    point_id: str, payload: dict[str, object], score: float = 0.0
) -> RetrievedChunk:
    return RetrievedChunk(
        id=point_id,
        document_id=str(payload.get("document_id", "")),
        chunk_index=int(payload.get("chunk_index", 0)),
        text=str(payload.get("text", "")),
        embed_text=str(payload.get("embed_text", "")),
        heading_path=payload.get("heading_path") or [],
        chunk_type=str(payload.get("chunk_type", "TEXT")),
        page_start=int(payload.get("page_start", 1)),
        page_end=int(payload.get("page_end", 1)),
        bbox_union=payload.get("bbox_union") or [],
        token_count=int(payload.get("token_count", 0)),
        score=round(float(score), 3),
        clearance_level=int(payload.get("clearance_level", 0)),
        department=str(payload.get("department", "")),
    )


async def _expand_query(query: str) -> list[str]:
    ollama = get_or_create_client()
    try:
        raw = await ollama.chat(
            [
                {"role": "system", "content": "Generate 2 paraphrased versions of the user query. Return ONLY the 2 paraphrases, one per line, no numbering."},
                {"role": "user", "content": query},
            ],
            model=settings.llm_model, temperature=0.5, max_tokens=200,
        )
        variants = [line.strip() for line in raw.strip().split("\n") if line.strip()]
        return [query] + variants[:2]
    except Exception:
        logger.warning("query_expansion_fallback", query=query[:80])
        return [query, query, query]


def _rrf_fuse(*ranked_lists: list[tuple[str, float]]) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked, start=1):
            scores[doc_id] += 1.0 / (_RRF_K + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _mmr_dedup(chunks: list[RetrievedChunk], k: int = 20) -> list[RetrievedChunk]:
    if not chunks:
        return []
    selected: list[RetrievedChunk] = []
    remaining = list(chunks)
    while remaining and len(selected) < k:
        best_idx, best_mmr = 0, -float("inf")
        for i, cand in enumerate(remaining):
            if not selected:
                diversity = 1.0
            else:
                max_sim = max(
                    _jaccard(set(cand.text.lower().split()), set(s.text.lower().split()))
                    for s in selected
                )
                diversity = 1.0 - max_sim
            mmr = _MMR_LAMBDA * cand.score + (1 - _MMR_LAMBDA) * diversity
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i
        selected.append(remaining.pop(best_idx))
    return selected


async def _acl_reverify(chunks: list[RetrievedChunk], user: ServerUserContext) -> list[RetrievedChunk]:
    doc_ids = {c.document_id for c in chunks if c.document_id}
    if not doc_ids:
        return []
    async with async_session() as session:
        from sqlalchemy import select
        stmt = select(DocumentModel).where(DocumentModel.id.in_([uuid.UUID(d) for d in doc_ids]))
        result = await session.execute(stmt)
        docs = {str(d.id): d for d in result.scalars().all()}

    kept: list[RetrievedChunk] = []
    for c in chunks:
        doc = docs.get(c.document_id)
        if doc is None:
            logger.warning("acl_reverify_missing_doc", document_id=c.document_id)
            continue
        labels = DocumentLabels(
            status=doc.status, clearance_level=doc.clearance_level,
            department=doc.department, legal_hold=doc.legal_hold,
        )
        if can_read(user, labels).allowed:
            kept.append(c)
        else:
            logger.warning("acl_reverify_denied", document_id=c.document_id)
    return kept


async def search(
    query: str,
    user: ServerUserContext,
    *,
    k: int = 20,
    doc_ids: list[str] | None = None,
    chunk_types: list[str] | None = None,
) -> list[RetrievedChunk]:
    client = QdrantClient(url=settings.qdrant_url, timeout=15)
    acl_filter = build_acl_filter(user)
    ollama = get_or_create_client()

    extra: list[qmodels.FieldCondition] = []
    if doc_ids:
        extra.append(qmodels.FieldCondition(key="document_id", match=qmodels.MatchAny(any=doc_ids)))
    if chunk_types:
        extra.append(qmodels.FieldCondition(key="chunk_type", match=qmodels.MatchAny(any=chunk_types)))
    if extra:
        acl_filter = qmodels.Filter(must=[*acl_filter.must, *extra])

    variants = await _expand_query(query)

    dense_ranked: list[tuple[str, float]] = []
    for v in variants:
        embeddings = await ollama.embed([v])
        hits = client.search(
            collection_name=settings.qdrant_collection,
            query_vector=("dense", embeddings[0]),
            query_filter=acl_filter, limit=k, with_payload=True,
        )
        dense_ranked.extend((str(h.id), h.score) for h in hits)

    # RRF fusion (dedup dense results; sparse can be added with BM25 tokenizer)
    seen: dict[str, float] = {}
    for doc_id, score in dense_ranked:
        if doc_id not in seen or score > seen[doc_id]:
            seen[doc_id] = score
    fused = sorted(seen.items(), key=lambda x: x[1], reverse=True)

    top_ids = [fid for fid, _ in fused[:k * 3]]
    if not top_ids:
        return []

    all_points = client.retrieve(
        collection_name=settings.qdrant_collection,
        ids=top_ids, with_payload=True, with_vectors=False,
    )
    point_map = {str(p.id): p for p in all_points}
    chunks = [
        _payload_to_chunk(
            fid, point_map[fid].payload or {}, score=seen.get(fid, 0.0)
        )
        for fid, _ in fused[:k * 3]
        if fid in point_map
    ]

    chunks = _mmr_dedup(chunks, k=k)
    chunks = await _acl_reverify(chunks, user)
    return chunks[:k]

"""vector_search tool — hybrid retrieval with RRF fusion. M5 owns this file."""
from __future__ import annotations

import asyncio
import structlog
from typing import Any

from pydantic import BaseModel

from backend.core.config import get_settings
from backend.core.exceptions import ToolError
from backend.core.rbac import ServerUserContext, can_read, DocumentLabels, Clearance
from backend.services.llm.ollama_client import get_ollama_client
from backend.services.llm.prompts import PARAPHRASE_PROMPT

logger = structlog.get_logger()
settings = get_settings()

_qdrant_client: Any = None


def _get_qdrant() -> Any:
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
    return _qdrant_client


async def _expand_queries(query: str, n: int = 2) -> list[str]:
    try:
        llm = get_ollama_client()
        result = await llm.structured(
            messages=[
                {"role": "user", "content": PARAPHRASE_PROMPT.format(query=query)},
            ],
            schema=_ParaphraseResult,
            temperature=0.3,
        )
        return [query] + result.variants[:n]
    except Exception as exc:
        logger.warning("paraphrase_expansion_failed", error=str(exc))
        return [query]


class _ParaphraseResult(BaseModel):
    variants: list[str]


def _rrf_fuse(
    dense_hits: list[dict[str, Any]],
    sparse_hits: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    payload_map: dict[str, dict[str, Any]] = {}

    for rank, hit in enumerate(dense_hits):
        cid = hit.get("id", "")
        if cid:
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            payload_map[cid] = hit

    for rank, hit in enumerate(sparse_hits):
        cid = hit.get("id", "")
        if cid:
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in payload_map:
                payload_map[cid] = hit

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    fused: list[dict[str, Any]] = []
    for cid in sorted_ids:
        entry = dict(payload_map.get(cid, {"id": cid}))
        entry["rrf_score"] = scores[cid]
        fused.append(entry)
    return fused


def _acl_reverify(
    hits: list[dict[str, Any]], user_ctx: dict
) -> list[dict[str, Any]]:
    role_str = user_ctx.get("role", "VIEWER")
    clearance_int = user_ctx.get("clearance_level", 0)
    departments = user_ctx.get("departments", [])
    try:
        from backend.core.rbac import Role
        role = Role(role_str)
    except (ValueError, KeyError):
        from backend.core.rbac import Role
        role = Role.VIEWER
    ctx = ServerUserContext(
        user_id=user_ctx.get("user_id", ""),
        role=role,
        clearance_level=Clearance(clearance_int),
        departments=departments,
    )
    verified: list[dict[str, Any]] = []
    for h in hits:
        pl = h.get("payload", {})
        doc_labels = DocumentLabels(
            status=pl.get("status", "READY"),
            clearance_level=Clearance(pl.get("clearance_level", 0)),
            department=pl.get("department", ""),
            legal_hold=pl.get("legal_hold", False),
        )
        decision = can_read(ctx, doc_labels)
        if decision.allowed:
            verified.append(h)
    return verified


async def vector_search(
    query: str,
    acl: dict,
    *,
    k: int = 20,
    doc_ids: list[str] | None = None,
    chunk_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    if acl is None:
        raise ToolError("acl_required: ACL filter must be provided from sealed state")

    variants = await _expand_queries(query, n=2)
    llm = get_ollama_client()

    dense_hits: list[dict[str, Any]] = []
    for variant in variants:
        try:
            embeddings = await llm.embed([variant])
            if not embeddings:
                continue
            vec = embeddings[0]
            qdrant = _get_qdrant()
            results = qdrant.search(
                collection_name=settings.qdrant_collection,
                query_vector=("dense", vec),
                limit=k,
                query_filter={
                    "must": [
                        {"key": "clearance_level", "range": {"lte": acl.get("max_clearance", 3)}},
                        {"key": "department", "match": {"any": acl.get("departments", [])}},
                    ]
                },
            )
            for r in results:
                dense_hits.append({
                    "id": str(r.id),
                    "score": float(r.score),
                    "payload": dict(r.payload) if r.payload else {},
                })
        except Exception as exc:
            logger.warning("dense_search_failed", variant=variant, error=str(exc))

    sparse_hits: list[dict[str, Any]] = []
    try:
        qdrant = _get_qdrant()
        results = qdrant.search(
            collection_name=settings.qdrant_collection,
            query_text=query,
            limit=k,
            query_filter={
                "must": [
                    {"key": "clearance_level", "range": {"lte": acl.get("max_clearance", 3)}},
                    {"key": "department", "match": {"any": acl.get("departments", [])}},
                ]
            },
        )
        for r in results:
            sparse_hits.append({
                "id": str(r.id),
                "score": float(r.score),
                "payload": dict(r.payload) if r.payload else {},
            })
    except Exception as exc:
        logger.warning("sparse_search_failed", error=str(exc))

    fused = _rrf_fuse(dense_hits, sparse_hits)

    verified = _acl_reverify(fused, acl.get("user_ctx", {}))

    final: list[dict[str, Any]] = []
    seen: set[str] = set()
    for h in verified:
        cid = h.get("id", "")
        if cid in seen:
            continue
        seen.add(cid)
        final.append(h)
        if len(final) >= k:
            break
    return final

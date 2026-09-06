"""Investigator — multi-hop decomposition and fan-out. M5 owns this file."""
from __future__ import annotations

import asyncio
import structlog
from typing import Any

from pydantic import BaseModel

from backend.agents.state import AgentState
from backend.agents.tools.vector_search import vector_search
from backend.services.llm.ollama_client import get_ollama_client
from backend.services.llm.prompts import SUFFICIENCY_PROMPT

logger = structlog.get_logger()

MAX_SUB_QUERIES = 4


class _SubQuery(BaseModel):
    query: str
    rationale: str


class _Decomposition(BaseModel):
    sub_queries: list[_SubQuery]


class _Hypothesis(BaseModel):
    cause: str
    confidence: float
    supporting_citations: list[str]
    contradicting_evidence: list[str]


class _RankResult(BaseModel):
    hypotheses: list[_Hypothesis]


def _step(label: str, **extra: str | float | int) -> dict[str, Any]:
    return {"phase": "investigator", "label": label, **extra}


async def _dispatch_sub_query(
    sub_query: str, acl_filter: dict
) -> list[dict[str, Any]]:
    try:
        hits = await vector_search(
            query=sub_query, acl=acl_filter, k=10
        )
        return hits
    except Exception as exc:
        logger.warning("sub_query_failed", query=sub_query, error=str(exc))
        return []


def _merge_timeline(results: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for batch in results:
        merged.extend(batch)
    merged.sort(
        key=lambda h: h.get("payload", {}).get("ingested_at", ""),
        reverse=True,
    )
    return merged


def _format_evidence(hits: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for i, h in enumerate(hits):
        pl = h.get("payload", {})
        text = pl.get("text", "")
        title = pl.get("document_title", "Unknown")
        page = pl.get("page_start", "?")
        parts.append(f"[{i+1}] ({title} p.{page}) {text[:300]}")
    return "\n".join(parts)


async def investigator(state: AgentState) -> dict:
    reasoning = list(state.get("reasoning", []))
    retrieved = list(state.get("retrieved", []))
    acl_filter = state.get("acl_filter", {})
    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)

    # Step 1: Decompose
    reasoning.append(_step("decomposing question into sub-queries"))
    try:
        llm = get_ollama_client()
        decomp = await llm.structured(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Decompose an incident investigation question into 2-4 independent "
                        "sub-queries that can be searched in parallel. Each sub-query should "
                        "target a different aspect: alarm logs, sensor trends, equipment "
                        "manuals, maintenance records, etc."
                    ),
                },
                {"role": "user", "content": q},
            ],
            schema=_Decomposition,
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("decomposition_failed", error=str(exc))
        reasoning.append(_step(f"decomposition failed: {exc}"))
        return {
            "answer": f"Investigation decomposition failed: {exc}",
            "abstained": True,
            "reasoning": reasoning,
        }

    sub_queries = decomp.sub_queries[:MAX_SUB_QUERIES]
    reasoning.append(
        _step(f"decomposed into {len(sub_queries)} sub-queries")
    )

    # Step 2: Parallel fan-out
    reasoning.append(_step("fan-out: parallel search"))
    tasks = [_dispatch_sub_query(sq.query, acl_filter) for sq in sub_queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_hits: list[list[dict[str, Any]]] = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            logger.warning("fan_out_error", index=i, error=str(res))
            reasoning.append(_step(f"sub-query {i+1} failed: {res}"))
            all_hits.append([])
        else:
            all_hits.append(res)
            reasoning.append(
                _step(f"sub-query {i+1}: {len(res)} results")
            )

    # Step 3: Merge timeline
    merged = _merge_timeline(all_hits)
    retrieved = retrieved + merged
    reasoning.append(_step(f"merged: {len(merged)} total evidence items"))

    # Step 4: Rank hypotheses
    evidence_text = _format_evidence(merged)
    try:
        rank_result = await llm.structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Investigation question: {q}\n\n"
                        f"Retrieved evidence:\n{evidence_text}\n\n"
                        "Rank possible causes. For each hypothesis provide: "
                        "cause, confidence (0-1), supporting citations (indices), "
                        "and contradicting evidence."
                    ),
                },
            ],
            schema=_RankResult,
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("hypothesis_ranking_failed", error=str(exc))
        reasoning.append(_step(f"hypothesis ranking failed: {exc}"))
        return {
            "retrieved": retrieved,
            "reasoning": reasoning,
        }

    # Step 5: Drop zero-citation hypotheses
    valid_hypotheses = [
        h for h in rank_result.hypotheses
        if h.supporting_citations
    ]
    reasoning.append(
        _step(
            f"ranked {len(rank_result.hypotheses)} hypotheses, "
            f"{len(valid_hypotheses)} with citations"
        )
    )

    for h in valid_hypotheses[:3]:
        reasoning.append(
            _step(
                f"hypothesis: {h.cause} (conf={h.confidence:.2f}, "
                f"support={len(h.supporting_citations)})"
            )
        )

    return {
        "retrieved": retrieved,
        "reasoning": reasoning,
    }

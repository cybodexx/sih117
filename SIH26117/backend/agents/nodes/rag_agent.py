"""RAG agent — ReAct loop for document QA. M5 owns this file."""
from __future__ import annotations

import time
import structlog
from typing import Any, Literal

from pydantic import BaseModel

from backend.agents.state import AgentState
from backend.agents.tools.vector_search import vector_search
from backend.services.llm.ollama_client import get_ollama_client
from backend.services.llm.prompts import REACT_REASON_PROMPT, SUFFICIENCY_PROMPT

logger = structlog.get_logger()

MAX_ITERATIONS = 3
WALL_CLOCK_BUDGET_S = 45.0


class _ReActPlan(BaseModel):
    thought: str
    query: str


class _SufficiencyVerdict(BaseModel):
    verdict: Literal["SUFFICIENT", "NEED_MORE", "NO_EVIDENCE"]
    refined_query: str = ""
    reason: str = ""


def _step(
    phase: str, label: str, **extra: str | float | int
) -> dict[str, Any]:
    return {"phase": phase, "label": label, **extra}


def _existing_evidence_str(state: AgentState) -> str:
    retrieved = state.get("retrieved", [])
    if not retrieved:
        return "(nothing retrieved yet)"
    parts: list[str] = []
    for i, chunk in enumerate(retrieved):
        text = chunk.get("text", "")
        title = chunk.get("document_title", "Unknown")
        page = chunk.get("page_start", "?")
        parts.append(f"[{i+1}] ({title} p.{page}) {text[:200]}")
    return "\n".join(parts)


def _dedupe_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for c in chunks:
        cid = c.get("id", "")
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)
        deduped.append(c)
    return deduped


async def rag_agent(state: AgentState) -> dict:
    iteration = state.get("iteration", 0)
    elapsed = state.get("elapsed_s", 0.0)
    reasoning = list(state.get("reasoning", []))
    retrieved = list(state.get("retrieved", []))
    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)
    acl_filter = state.get("acl_filter", {})

    if iteration >= MAX_ITERATIONS or elapsed > WALL_CLOCK_BUDGET_S:
        reasoning.append(_step("reflect", "budget exhausted"))
        return {
            "abstained": True,
            "reasoning": reasoning,
            "retrieved": retrieved,
        }

    loop_start = time.monotonic()
    iteration += 1

    # PHASE 1: REASON
    reasoning.append(_step("reason", f"iteration {iteration}: planning query"))
    try:
        llm = get_ollama_client()
        existing = _existing_evidence_str(state)
        gap = (
            "No evidence retrieved yet"
            if not retrieved
            else "Need more specific or complementary evidence"
        )
        plan = await llm.structured(
            messages=[
                {
                    "role": "user",
                    "content": REACT_REASON_PROMPT.format(
                        question=q,
                        existing_evidence=existing,
                        gap=gap,
                    ),
                },
            ],
            schema=_ReActPlan,
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("react_reason_failed", error=str(exc))
        reasoning.append(_step("reason", f"LLM planning failed: {exc}"))
        return {
            "iteration": iteration,
            "elapsed_s": elapsed,
            "retrieved": retrieved,
            "reasoning": reasoning,
        }

    search_query = plan.query or q
    reasoning.append(_step("reason", f"plan: {plan.thought[:120]}"))

    # PHASE 2: ACT
    reasoning.append(_step("act", f"searching: {search_query[:80]}"))
    try:
        hits = await vector_search(
            query=search_query,
            acl=acl_filter,
            k=settings.rerank_top_k if hasattr(settings, "rerank_top_k") else 20,
        )
    except Exception as exc:
        logger.warning("vector_search_failed", error=str(exc))
        reasoning.append(_step("act", f"search failed: {exc}"))
        return {
            "iteration": iteration,
            "elapsed_s": elapsed + (time.monotonic() - loop_start),
            "retrieved": retrieved,
            "reasoning": reasoning,
        }

    # PHASE 3: OBSERVE
    top = hits[:5]
    retrieved = _dedupe_chunks(retrieved + top)
    best_score = top[0].get("rrf_score", top[0].get("score", 0.0)) if top else 0.0
    reasoning.append(
        _step("observe", f"found {len(top)} chunks, best_score={best_score:.3f}")
    )

    # PHASE 4: REFLECT
    reasoning.append(_step("reflect", "checking sufficiency"))
    evidence_text = _existing_evidence_str({"retrieved": retrieved})
    try:
        verdict = await llm.structured(
            messages=[
                {
                    "role": "user",
                    "content": SUFFICIENCY_PROMPT.format(
                        question=q,
                        evidence=evidence_text,
                    ),
                },
            ],
            schema=_SufficiencyVerdict,
            temperature=0.0,
        )
    except Exception as exc:
        logger.warning("sufficiency_check_failed", error=str(exc))
        reasoning.append(_step("reflect", f"verdict check failed: {exc}"))
        verdict = _SufficiencyVerdict(verdict="NEED_MORE", refined_query=q)

    reasoning.append(
        _step("reflect", f"verdict: {verdict.verdict} — {verdict.reason[:100]}")
    )

    new_elapsed = elapsed + (time.monotonic() - loop_start)

    if verdict.verdict == "SUFFICIENT":
        return {
            "iteration": iteration,
            "elapsed_s": new_elapsed,
            "retrieved": retrieved,
            "reasoning": reasoning,
        }

    if verdict.verdict == "NO_EVIDENCE":
        return {
            "iteration": iteration,
            "elapsed_s": new_elapsed,
            "retrieved": retrieved,
            "abstained": True,
            "reasoning": reasoning,
        }

    # NEED_MORE → loop
    return {
        "iteration": iteration,
        "elapsed_s": new_elapsed,
        "retrieved": retrieved,
        "reasoning": reasoning,
    }

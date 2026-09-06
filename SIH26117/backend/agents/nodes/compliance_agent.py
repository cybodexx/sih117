"""Compliance agent — regulatory compliance checking. M5 owns this file."""
from __future__ import annotations

import structlog
from typing import Any

from pydantic import BaseModel

from backend.agents.state import AgentState
from backend.agents.tools.check_compliance import check_compliance
from backend.agents.tools.vector_search import vector_search
from backend.services.llm.ollama_client import get_ollama_client

logger = structlog.get_logger()

SAFETY_DEPT = ["SAFETY", "QUALITY"]


def _step(label: str, **extra: str | float | int) -> dict[str, Any]:
    return {"phase": "compliance", "label": label, **extra}


async def compliance_agent(state: AgentState) -> dict:
    reasoning = list(state.get("reasoning", []))
    retrieved = list(state.get("retrieved", []))
    acl_filter = state.get("acl_filter", {})
    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)

    # Step 1: Identify referenced standard
    reasoning.append(_step("identifying referenced standard"))
    try:
        llm = get_ollama_client()
        standard_result = await llm.structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"From this compliance question, identify any referenced standard "
                        f"(e.g., ISO 9001, IS 15656, OSHA 1910) or return 'general'.\n\n"
                        f"Question: {q}"
                    ),
                },
            ],
            schema=_StandardRef,
            temperature=0.0,
        )
        standard = standard_result.standard
    except Exception as exc:
        logger.warning("standard_identification_failed", error=str(exc))
        standard = "general"

    reasoning.append(_step(f"standard: {standard}"))

    # Step 2: Vector search scoped to safety/quality documents
    reasoning.append(_step("searching compliance documents"))
    scoped_acl = dict(acl_filter)
    scoped_acl["departments"] = SAFETY_DEPT
    try:
        hits = await vector_search(
            query=q,
            acl=scoped_acl,
            k=10,
        )
        retrieved = retrieved + hits
        reasoning.append(_step(f"found {len(hits)} compliance documents"))
    except Exception as exc:
        logger.warning("compliance_search_failed", error=str(exc))
        reasoning.append(_step(f"search failed: {exc}"))

    # Step 3: Cross-check against standard clauses
    reasoning.append(_step("checking against standard clauses"))
    try:
        compliance_result = await check_compliance(
            query=q,
            standard=standard,
            acl=scoped_acl,
        )
        reasoning.append(_step("compliance check completed"))
    except Exception as exc:
        logger.warning("compliance_check_failed", error=str(exc))
        reasoning.append(_step(f"compliance check failed: {exc}"))

    return {
        "retrieved": retrieved,
        "reasoning": reasoning,
    }


class _StandardRef(BaseModel):
    standard: str

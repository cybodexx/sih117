"""Supervisor routing — the 4-tier algorithm. M5 owns this file."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from backend.agents.state import AgentState
from backend.services.llm.ollama_client import get_ollama_client
from backend.services.llm.prompts import ROUTER_PROMPT
import structlog

logger = structlog.get_logger()
CONF_FLOOR = 0.60
INTENT_CATALOG = (
    "DOC_QA: factual lookup in manuals/SOPs\n"
    "VISION: image understanding\n"
    "DATA_ANALYSIS: aggregation, trend, counting, MTBF\n"
    "INCIDENT: root-cause, multi-hop investigation\n"
    "COMPLIANCE: standard/clause conformance\n"
    "CHITCHAT: greeting, out-of-scope"
)


class RouteDecision(BaseModel):
    intent: Literal[
        "DOC_QA", "VISION", "DATA_ANALYSIS", "INCIDENT", "COMPLIANCE", "CHITCHAT"
    ]
    confidence: float
    rationale: str
    sub_queries: list[str] = []


INCIDENT_PATTERN = re.compile(
    r"(why|root.?cause|failed|tripped|incident|outage|alarm|error).*(\d{4}|T-\d+|machine|turbine|pump|motor)",
    re.IGNORECASE,
)
COMPLIANCE_PATTERN = re.compile(
    r"(compliant|compliance|standard|clause|IS\s*\d+|regulation|permitted|audit|iso\s*\d+|osha)",
    re.IGNORECASE,
)
DATA_PATTERN = re.compile(
    r"(how many|average|trend|count|mtbf|mttr|between .* and|per month|over the|total|mean|median)",
    re.IGNORECASE,
)
GREETING_PATTERN = re.compile(
    r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|thanks|thank you|bye)",
    re.IGNORECASE,
)


def lexical_prior(question: str) -> dict[str, float]:
    scores: dict[str, float] = {"DOC_QA": 0.3}
    if INCIDENT_PATTERN.search(question):
        scores["INCIDENT"] = 0.8
    if COMPLIANCE_PATTERN.search(question):
        scores["COMPLIANCE"] = 0.8
    if DATA_PATTERN.search(question):
        scores["DATA_ANALYSIS"] = 0.8
    return scores


def fuse(decision: RouteDecision, prior: dict[str, float]) -> tuple[str, float]:
    llm_intent = decision.intent
    llm_conf = decision.confidence
    prior_conf = prior.get(llm_intent, 0.0)
    fused = 0.7 * llm_conf + 0.3 * prior_conf
    return llm_intent, fused


def _step(label: str, **extra: str | float | int) -> dict[str, str | float | int]:
    return {"phase": "supervisor", "label": label, **extra}


async def supervisor(state: AgentState) -> dict:
    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)

    reasoning = list(state.get("reasoning", []))

    # Tier 1: deterministic overrides (0 tokens, ~0 ms)
    for att in state.get("attachments", []):
        att_kind = att.get("kind", "") if isinstance(att, dict) else ""
        if att_kind == "IMAGE":
            reasoning.append(_step("image attached → VISION"))
            return {
                "intent": "VISION",
                "route_conf": 1.0,
                "reasoning": reasoning,
            }
        if att_kind in ("CSV", "XLSX"):
            reasoning.append(_step("tabular attachment → DATA_ANALYSIS"))
            return {
                "intent": "DATA_ANALYSIS",
                "route_conf": 1.0,
                "reasoning": reasoning,
            }

    if len(q) < 12 and GREETING_PATTERN.search(q):
        reasoning.append(_step("greeting → CHITCHAT"))
        return {
            "intent": "CHITCHAT",
            "route_conf": 1.0,
            "reasoning": reasoning,
        }

    # Tier 2: lexical prior
    prior = lexical_prior(q)
    best = max(prior, key=prior.get)  # type: ignore[arg-type]
    if prior.get(best, 0) >= 0.8:
        reasoning.append(_step(f"lexical prior → {best}", prior_score=prior[best]))
        return {
            "intent": best,
            "route_conf": prior[best],
            "reasoning": reasoning,
        }

    # Tier 3: LLM structured classification
    try:
        llm = get_ollama_client()
        history_text = ""
        messages = state.get("messages", [])
        if len(messages) > 1:
            recent = messages[-4:]
            history_text = "\n".join(
                getattr(m, "content", str(m)) for m in recent
            )

        decision = await llm.structured(
            messages=[
                {"role": "system", "content": "You are an intent classifier for an industrial AI workbench."},
                {
                    "role": "user",
                    "content": ROUTER_PROMPT.format(
                        question=q,
                        history=history_text or "(no prior messages)",
                        catalog=INTENT_CATALOG,
                    ),
                },
            ],
            schema=RouteDecision,
            temperature=0.1,
        )

        llm_intent, conf = fuse(decision, prior)
        reasoning.append(
            _step(
                f"LLM → {llm_intent} (fused={conf:.2f})",
                prior_score=prior.get(llm_intent, 0.0),
                llm_conf=decision.confidence,
            )
        )

        # Tier 4: safety net
        if conf < CONF_FLOOR:
            reasoning.append(_step("confidence below floor → DOC_QA default"))
            return {
                "intent": "DOC_QA",
                "route_conf": conf,
                "sub_queries": [],
                "reasoning": reasoning,
            }

        return {
            "intent": llm_intent,
            "route_conf": conf,
            "sub_queries": decision.sub_queries[:4],
            "reasoning": reasoning,
        }

    except Exception as exc:
        logger.warning("supervisor_llm_fallback", error=str(exc))
        reasoning.append(_step(f"LLM unavailable → DOC_QA default: {exc}"))
        return {
            "intent": "DOC_QA",
            "route_conf": CONF_FLOOR,
            "reasoning": reasoning,
        }

"""Synthesizer — composes final cited answer from retrieved chunks. M5 owns this file."""
from __future__ import annotations

import re
import structlog
from typing import Any

from backend.agents.state import AgentState
from backend.services.llm.ollama_client import get_ollama_client
from backend.services.llm.prompts import SYNTH_PROMPT, SOVEREIGN_SYSTEM

logger = structlog.get_logger()

MAX_CONTEXT_TOKENS = 6000
CITATION_COVERAGE_FLOOR = 0.80

_FactualSentence = tuple[str, bool]


def _step(label: str, **extra: str | float | int) -> dict[str, Any]:
    return {"phase": "synthesizer", "label": label, **extra}


def _build_context(retrieved: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    token_count = 0
    for i, chunk in enumerate(retrieved):
        text = chunk.get("text", "")
        title = chunk.get("document_title", "Unknown")
        page = chunk.get("page_start", "?")
        entry = f"[{i+1}] ({title} p.{page}) {text}"
        est_tokens = len(entry.split())
        if token_count + est_tokens > MAX_CONTEXT_TOKENS:
            break
        parts.append(entry)
        token_count += est_tokens
    return "\n\n".join(parts)


def _is_factual(sentence: str) -> bool:
    """Heuristic: sentence contains numbers, units, or technical terms."""
    if re.search(r"\d+", sentence):
        return True
    tech_terms = [
        "torque", "pressure", "temperature", "voltage", "ampere",
        "rpm", "psi", "bar", "°C", "°F", "mm", "cm", "kg",
        "failure", "maintenance", "inspection", "standard", "requirement",
        "shall", "must", "maximum", "minimum", "tolerance",
    ]
    lower = sentence.lower()
    return any(term in lower for term in tech_terms)


def _count_citation_coverage(answer: str) -> tuple[float, int, int]:
    sentences = re.split(r"[.!?]+", answer)
    sentences = [s.strip() for s in sentences if s.strip()]
    factual = 0
    cited = 0
    for s in sentences:
        if _is_factual(s):
            factual += 1
            if re.search(r"\[\d+\]", s):
                cited += 1
    if factual == 0:
        return 1.0, 0, 0
    return cited / factual, factual, cited


def _resolve_citations(
    answer: str, retrieved: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    citation_refs: list[dict[str, Any]] = []
    for match in re.finditer(r"\[(\d+)\]", answer):
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(retrieved):
            chunk = retrieved[idx]
            citation_refs.append({
                "reference": match.group(0),
                "document_id": chunk.get("document_id", ""),
                "title": chunk.get("document_title", "Unknown"),
                "page": chunk.get("page_start", 0),
                "snippet": chunk.get("text", "")[:200],
            })
    return citation_refs


async def synthesizer(state: AgentState) -> dict:
    reasoning = list(state.get("reasoning", []))
    retrieved = list(state.get("retrieved", []))

    if state.get("abstained") or not retrieved:
        reasoning.append(_step("abstained: no retrieved evidence"))
        return {
            "answer": "I could not find this in the documents you have access to.",
            "grounded": False,
            "abstained": True,
            "reasoning": reasoning,
        }

    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)

    context = _build_context(retrieved)
    reasoning.append(_step(f"built context from {len(retrieved)} chunks"))

    # First attempt
    try:
        llm = get_ollama_client()
        answer = await llm.chat(
            messages=[
                {"role": "system", "content": SOVEREIGN_SYSTEM},
                {
                    "role": "user",
                    "content": SYNTH_PROMPT.format(
                        context=context, question=q
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception as exc:
        logger.warning("synthesis_failed", error=str(exc))
        reasoning.append(_step(f"synthesis failed: {exc}"))
        return {
            "answer": f"Synthesis failed: {exc}",
            "grounded": False,
            "abstained": True,
            "reasoning": reasoning,
        }

    # Citation coverage check
    coverage, factual_count, cited_count = _count_citation_coverage(answer)
    reasoning.append(
        _step(
            f"citation coverage: {coverage:.2%} "
            f"({cited_count}/{factual_count} factual sentences cited)"
        )
    )

    # Retry at temperature 0.0 if below floor
    if coverage < CITATION_COVERAGE_FLOOR and factual_count > 0:
        reasoning.append(_step("coverage below 80% — retrying at temperature 0.0"))
        try:
            answer = await llm.chat(
                messages=[
                    {"role": "system", "content": SOVEREIGN_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            SYNTH_PROMPT.format(context=context, question=q)
                            + "\n\nCRITICAL: You MUST add [n] citations to EVERY factual sentence. "
                            "This is a retry due to insufficient citations."
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=2048,
            )
            coverage, factual_count, cited_count = _count_citation_coverage(answer)
            reasoning.append(
                _step(f"retry coverage: {coverage:.2%} ({cited_count}/{factual_count})")
            )
        except Exception as exc:
            logger.warning("synthesis_retry_failed", error=str(exc))

    citations = _resolve_citations(answer, retrieved)
    grounded = coverage >= CITATION_COVERAGE_FLOOR

    reasoning.append(
        _step(f"final: grounded={grounded}, citations={len(citations)}")
    )

    return {
        "answer": answer,
        "citations": citations,
        "grounded": grounded,
        "reasoning": reasoning,
    }

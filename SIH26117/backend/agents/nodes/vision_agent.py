"""Vision agent — image understanding + cross-reference retrieval. M5 owns this file."""
from __future__ import annotations

import structlog
from typing import Any

from pydantic import BaseModel

from backend.agents.state import AgentState
from backend.agents.tools.vision_describe import vision_describe
from backend.agents.tools.vector_search import vector_search
from backend.services.llm.ollama_client import get_ollama_client

logger = structlog.get_logger()


class _VisionResult(BaseModel):
    equipment_type: str
    serial_numbers: list[str]
    anomalies: list[str]
    gauge_readings: list[str]
    safety_concerns: list[str]
    description: str


def _step(label: str, **extra: str | float | int) -> dict[str, Any]:
    return {"phase": "vision", "label": label, **extra}


async def vision_agent(state: AgentState) -> dict:
    reasoning = list(state.get("reasoning", []))
    retrieved = list(state.get("retrieved", []))
    acl_filter = state.get("acl_filter", {})

    attachments = state.get("attachments", [])
    image_att = None
    ocr_text = ""
    for att in attachments:
        if isinstance(att, dict) and att.get("kind") == "IMAGE":
            image_att = att
            ocr_text = att.get("ocr_text", "")
            break

    if not image_att:
        reasoning.append(_step("no image attachment found"))
        return {
            "answer": "No image was provided for analysis.",
            "abstained": True,
            "reasoning": reasoning,
        }

    image_b64 = image_att.get("data", "") or image_att.get("image_b64", "")

    # Step 1: Vision description
    reasoning.append(_step("calling vision model"))
    try:
        description = await vision_describe(
            image_b64=image_b64,
            ocr_text=ocr_text,
        )
    except Exception as exc:
        logger.warning("vision_describe_failed", error=str(exc))
        reasoning.append(_step(f"vision model failed: {exc}"))
        return {
            "answer": f"Vision analysis failed: {exc}",
            "abstained": True,
            "reasoning": reasoning,
        }

    reasoning.append(_step(f"vision result: {description[:120]}"))

    # Step 2: Extract structured info via LLM
    try:
        llm = get_ollama_client()
        vision_struct = await llm.structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Extract structured information from this industrial image description:\n\n"
                        f"{description}\n\n"
                        "Provide equipment type, serial numbers, anomalies, "
                        "gauge readings, and safety concerns."
                    ),
                },
            ],
            schema=_VisionResult,
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("vision_structured_failed", error=str(exc))
        vision_struct = _VisionResult(
            equipment_type="unknown",
            serial_numbers=[],
            anomalies=[],
            gauge_readings=[],
            safety_concerns=[],
            description=description,
        )

    # Step 3: Cross-reference into manuals
    cross_ref_query = description[:300]
    if vision_struct.equipment_type and vision_struct.equipment_type != "unknown":
        cross_ref_query = f"{vision_struct.equipment_type} specifications maintenance"

    reasoning.append(_step("cross-referencing into manuals"))
    try:
        cross_hits = await vector_search(
            query=cross_ref_query,
            acl=acl_filter,
            k=5,
        )
        retrieved = list(state.get("retrieved", [])) + cross_hits
        reasoning.append(
            _step(f"cross-reference: found {len(cross_hits)} related manual sections")
        )
    except Exception as exc:
        logger.warning("cross_reference_failed", error=str(exc))
        reasoning.append(_step(f"cross-reference failed: {exc}"))
        retrieved = list(state.get("retrieved", []))

    return {
        "retrieved": retrieved,
        "reasoning": reasoning,
    }

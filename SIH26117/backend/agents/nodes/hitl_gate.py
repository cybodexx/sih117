"""Human-in-the-loop gate. M5 implements fully."""
from __future__ import annotations

import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Any, Literal

from backend.agents.state import AgentState

logger = structlog.get_logger()

RISK: dict[str, str] = {
    "vector_search": "READ",
    "sql_query": "READ",
    "vision_describe": "READ",
    "check_compliance": "READ",
    "compute_downtime": "READ",
    "delete_document": "HIGH",
    "export_bundle": "HIGH",
    "bulk_relabel": "HIGH",
    "python_exec": "HIGH",
}


def _step(label: str, **extra: str | float | int) -> dict[str, Any]:
    return {"phase": "hitl", "label": label, **extra}


async def hitl_gate(state: AgentState) -> dict:
    pending = state.get("pending_approval")
    result = state.get("approval_result")
    reasoning = list(state.get("reasoning", []))

    if result == "DENIED":
        reasoning.append(_step("DENIED by human operator"))
        logger.info(
            "hitl_denied",
            approval_id=pending.get("approval_id") if pending else None,
            tool=pending.get("tool") if pending else None,
        )
        return {
            "abstained": True,
            "pending_approval": None,
            "approval_result": None,
            "reasoning": reasoning,
        }

    if result == "APPROVED":
        reasoning.append(_step("APPROVED by human operator"))
        logger.info(
            "hitl_approved",
            approval_id=pending.get("approval_id") if pending else None,
            tool=pending.get("tool") if pending else None,
        )
        return {
            "pending_approval": None,
            "approval_result": None,
            "reasoning": reasoning,
        }

    last_tool_call: dict[str, Any] = {}
    tool_calls = state.get("tool_calls", [])
    if tool_calls:
        last_tool_call = tool_calls[-1]

    tool_name = last_tool_call.get("tool", "")
    risk = RISK.get(tool_name, "HIGH")

    if risk == "HIGH":
        approval_id = str(uuid.uuid4())
        approval_request = {
            "approval_id": approval_id,
            "tool": tool_name,
            "risk": risk,
            "arguments": last_tool_call.get("args", {}),
            "rationale": f"High-risk tool call requires approval: {tool_name}",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat(),
        }
        reasoning.append(
            _step(
                f"HIGH risk: {tool_name} — awaiting approval",
                approval_id=approval_id,
            )
        )
        logger.info(
            "hitl_approval_required",
            approval_id=approval_id,
            tool=tool_name,
            risk=risk,
        )
        return {
            "pending_approval": approval_request,
            "reasoning": reasoning,
        }

    reasoning.append(_step(f"risk={risk}: {tool_name} — auto-approved"))
    return {
        "reasoning": reasoning,
    }

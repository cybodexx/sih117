"""Data agent — NL→SQL analysis with validation. M5 owns this file."""
from __future__ import annotations

import structlog
from typing import Any

from pydantic import BaseModel

from backend.agents.state import AgentState
from backend.agents.tools.sql_query import sql_query
from backend.agents.tools.compute_downtime import compute_downtime
from backend.services.llm.ollama_client import get_ollama_client

logger = structlog.get_logger()


class _DataPlan(BaseModel):
    tool: str
    params: dict[str, str]
    rationale: str


def _step(label: str, **extra: str | float | int) -> dict[str, Any]:
    return {"phase": "data", "label": label, **extra}


async def data_agent(state: AgentState) -> dict:
    reasoning = list(state.get("reasoning", []))
    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)

    reasoning.append(_step("data analysis: planning tool call"))

    try:
        llm = get_ollama_client()
        plan = await llm.structured(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data analysis planner. Choose the right tool:\n"
                        "- sql_query: for general SELECT queries on ds_* tables\n"
                        "- compute_downtime: for machine downtime calculations "
                        "(requires machine_id, start, end)\n"
                        "Provide the tool name and parameters as JSON."
                    ),
                },
                {"role": "user", "content": q},
            ],
            schema=_DataPlan,
            temperature=0.0,
        )
    except Exception as exc:
        logger.warning("data_plan_failed", error=str(exc))
        reasoning.append(_step(f"planning failed: {exc}"))
        return {
            "answer": f"Data analysis planning failed: {exc}",
            "abstained": True,
            "reasoning": reasoning,
        }

    reasoning.append(_step(f"tool: {plan.tool}, rationale: {plan.rationale[:80]}"))

    result_text = ""
    tool_name = plan.tool
    tool_args = plan.params

    try:
        if tool_name == "compute_downtime":
            machine_id = tool_args.get("machine_id", "")
            start = tool_args.get("start", "")
            end = tool_args.get("end", "")
            result_text = await compute_downtime(
                machine_id=machine_id, start=start, end=end
            )
        else:
            query = tool_args.get("query", q)
            result_text = await sql_query(query=query)
    except Exception as exc:
        logger.warning("data_tool_failed", tool=tool_name, error=str(exc))
        reasoning.append(_step(f"tool execution failed: {exc}"))
        return {
            "answer": f"Data query failed: {exc}",
            "abstained": True,
            "reasoning": reasoning,
        }

    reasoning.append(_step(f"result: {result_text[:120]}"))

    return {
        "retrieved": [
            {
                "id": f"data_result_{tool_name}",
                "text": result_text,
                "document_title": f"Data Analysis: {tool_name}",
                "page_start": 0,
                "rrf_score": 1.0,
                "payload": {"text": result_text, "source": "data_agent"},
            }
        ],
        "reasoning": reasoning,
    }

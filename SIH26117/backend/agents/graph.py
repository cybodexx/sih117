"""LangGraph graph — complete wiring for the 10-node agent topology. M5 owns this file."""
from __future__ import annotations

import structlog
from typing import Any

try:
    from langgraph.graph import END, StateGraph
except ImportError:

    class END:  # type: ignore[no-redef]
        pass

    class StateGraph:  # type: ignore[no-redef]
        pass


from backend.agents.state import AgentState
from backend.agents.supervisor import supervisor
from backend.agents.nodes.rag_agent import rag_agent
from backend.agents.nodes.vision_agent import vision_agent
from backend.agents.nodes.data_agent import data_agent
from backend.agents.nodes.investigator import investigator
from backend.agents.nodes.compliance_agent import compliance_agent
from backend.agents.nodes.hitl_gate import hitl_gate
from backend.agents.nodes.synthesizer import synthesizer
from backend.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def guard(state: AgentState) -> dict:
    """Validate input, rate-limit, check injection attempts."""
    reasoning = list(state.get("reasoning", []))
    q = ""
    if state.get("messages"):
        last = state["messages"][-1]
        q = getattr(last, "content", "") if hasattr(last, "content") else str(last)

    if not q.strip() and not state.get("attachments"):
        return {
            "abstained": True,
            "answer": "Please provide a question or attachment.",
            "reasoning": reasoning + [{"phase": "guard", "label": "empty input"}],
        }

    injection_patterns = [
        r"ignore\s+(all\s+)?previous",
        r"system\s*prompt",
        r"reveal\s+instructions",
        r"<\|im_start\|>",
    ]
    for pat in injection_patterns:
        if __import__("re").search(pat, q, __import__("re").IGNORECASE):
            return {
                "abstained": True,
                "answer": "I cannot process that request.",
                "reasoning": reasoning + [{"phase": "guard", "label": "injection blocked"}],
            }

    reasoning.append({"phase": "guard", "label": "input validated"})
    return {"reasoning": reasoning}


async def auditor(state: AgentState) -> dict:
    """Emit final audit event for the turn."""
    reasoning = list(state.get("reasoning", []))
    intent = state.get("intent", "UNKNOWN")
    conf = state.get("route_conf", 0.0)
    grounded = state.get("grounded", False)
    abstained = state.get("abstained", False)
    citations_count = len(state.get("citations", []))
    tool_count = len(state.get("tool_calls", []))

    audit_event = {
        "event": "turn_complete",
        "session_id": state.get("session_id", ""),
        "correlation_id": state.get("correlation_id", ""),
        "intent": intent,
        "confidence": conf,
        "grounded": grounded,
        "abstained": abstained,
        "citations": citations_count,
        "tool_calls": tool_count,
        "iterations": state.get("iteration", 0),
    }

    logger.info("audit_turn_complete", **{
        k: v for k, v in audit_event.items()
        if k not in ("session_id", "correlation_id")
    })

    reasoning.append({
        "phase": "auditor",
        "label": f"audit: intent={intent} grounded={grounded} citations={citations_count}",
    })

    return {"reasoning": reasoning}


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "DOC_QA")
    mapping: dict[str, str] = {
        "DOC_QA": "rag_agent",
        "VISION": "vision_agent",
        "DATA_ANALYSIS": "data_agent",
        "INCIDENT": "investigator",
        "COMPLIANCE": "compliance_agent",
        "CHITCHAT": "synthesizer",
    }
    target = mapping.get(intent, "synthesizer")
    logger.info("route_by_intent", intent=intent, target=target)
    return target


def route_after_gate(state: AgentState) -> str:
    result = state.get("approval_result")
    if result == "DENIED":
        return "synthesizer"
    return "synthesizer"


def route_after_rag(state: AgentState) -> str:
    if state.get("abstained"):
        return "synthesizer"
    iteration = state.get("iteration", 0)
    elapsed = state.get("elapsed_s", 0.0)
    if iteration < settings.max_agent_iterations and elapsed < 45.0:
        return "rag_agent"
    return "synthesizer"


def build_graph(checkpointer: Any = None) -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("guard", guard)
    graph.add_node("supervisor", supervisor)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("vision_agent", vision_agent)
    graph.add_node("data_agent", data_agent)
    graph.add_node("investigator", investigator)
    graph.add_node("compliance_agent", compliance_agent)
    graph.add_node("hitl_gate", hitl_gate)
    graph.add_node("synthesizer", synthesizer)
    graph.add_node("auditor", auditor)

    graph.set_entry_point("guard")
    graph.add_edge("guard", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "rag_agent": "rag_agent",
            "vision_agent": "vision_agent",
            "data_agent": "data_agent",
            "investigator": "investigator",
            "compliance_agent": "compliance_agent",
            "synthesizer": "synthesizer",
        },
    )

    graph.add_conditional_edges(
        "rag_agent",
        route_after_rag,
        {
            "rag_agent": "rag_agent",
            "synthesizer": "synthesizer",
        },
    )

    graph.add_edge("vision_agent", "synthesizer")
    graph.add_edge("data_agent", "hitl_gate")
    graph.add_edge("investigator", "synthesizer")
    graph.add_edge("compliance_agent", "synthesizer")

    graph.add_conditional_edges(
        "hitl_gate",
        route_after_gate,
        {
            "synthesizer": "synthesizer",
        },
    )

    graph.add_edge("synthesizer", "auditor")
    graph.add_edge("auditor", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_gate"],
        recursion_limit=settings.recursion_limit,
    )

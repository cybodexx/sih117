"""Agent state — the contract between all nodes. M5 owns this file."""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_ctx: dict
    acl_filter: dict
    attachments: list[dict]
    session_id: str
    correlation_id: str

    intent: str | None
    route_conf: float
    sub_queries: list[str]

    retrieved: list[dict]
    tool_calls: list[dict]
    reasoning: list[dict]
    iteration: int
    elapsed_s: float

    pending_approval: dict | None
    approval_result: str | None

    answer: str
    citations: list[dict]
    grounded: bool
    abstained: bool

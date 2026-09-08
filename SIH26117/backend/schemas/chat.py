from __future__ import annotations

from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    title: str | None = None
    document_id: str | None = None
    document_ids: list[str] | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    document_ids: list[str] | None = None


class ChatSessionRead(BaseModel):
    id: str
    title: str
    document_id: str | None = None
    document_ids: list[str] = []
    created_at: str
    updated_at: str


class MessageCreate(BaseModel):
    content: str
    attachment_ids: list[str] = []


class Citation(BaseModel):
    n: int
    document_id: str
    document_title: str
    page: int
    bbox: list[float] | None = None
    snippet: str = ""


class ReasoningStep(BaseModel):
    seq: int
    phase: str
    label: str | None = None
    tool: str | None = None
    tool_args: dict | None = None
    detail: str | None = None
    elapsed_ms: int | None = None


class SourceRef(BaseModel):
    n: int
    chunk_id: str
    document_id: str
    document_title: str
    page_start: int
    page_end: int
    score: float
    chunk_type: str
    suspected_injection: bool = False
    snippet: str = ""


class MessageFile(BaseModel):
    deliverable_id: str
    filename: str
    kind: str
    mime: str
    size_bytes: int


class RouteInfo(BaseModel):
    intent: str
    confidence: float
    rationale: str
    tier: str = "deterministic"
    llm_used: bool = False


class MessageRead(BaseModel):
    id: str
    turn_id: str
    role: str
    content: str
    intent: str | None = None
    route_confidence: float | None = None
    grounded: bool | None = None
    abstained: bool | None = None
    citations: list[Citation] = []
    reasoning: list[ReasoningStep] = []
    sources: list[SourceRef] = []
    files: list[MessageFile] = []
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    created_at: str


class MessageAccepted(BaseModel):
    message_id: str
    turn_id: str


class ApprovalDecision(BaseModel):
    approval_id: str
    decision: str  # "APPROVED" | "DENIED"
    note: str | None = None


class PageRead(BaseModel):
    items: list[ChatSessionRead]
    total: int
    page: int
    size: int

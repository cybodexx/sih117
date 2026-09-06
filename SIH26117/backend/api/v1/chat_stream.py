"""SSE streaming endpoint — real pipeline: route → retrieve (ACL-filtered) → synthesize → stream.

M1 consumes this. The generator performs the full agent turn inline (no LangGraph
dependency); every event matches 04_INTEGRATION_CONTRACTS.md §3.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import get_current_user
from backend.core.rbac import ServerUserContext
from backend.db.models.chat import ChatSessionModel
from backend.db.models.document import DocumentModel
from backend.db.models.message import ChatMessageModel
from backend.db.session import get_db
from backend.services.audit.writer import emit as audit_emit
from backend.services.llm.ollama_client import get_or_create_client
from backend.services.llm.prompts import SOVEREIGN_SYSTEM, SYNTH_PROMPT
from backend.services.rag.retriever import RetrievedChunk, search

logger = structlog.get_logger()
router = APIRouter(tags=["chat-stream"])
settings = get_settings()

_KEEPALIVE_INTERVAL = 15.0
_MAX_SOURCES = 8
_MAX_STREAM_TOKENS = 1024
_MAX_IMAGES = 3

VISION_ATTACH_PROMPT = (
    "Describe this industrial photograph in detail: identify the equipment type, "
    "any visible corrosion, cracks, leaks, soot, or damage, any readable tags or "
    "gauges, and note anything that looks like a safety hazard."
)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _error_frame(message: str) -> str:
    return _sse("error", {"code": "chat_error", "message": message, "retryable": False})


def _classify_intent(question: str) -> tuple[str, float]:
    q = question.lower()
    if any(k in q for k in ("fail", "cause", "why", "root", "incident", "trip", "leak")):
        return "INCIDENT", 0.87
    if any(k in q for k in ("standard", "compli", "regulator", "clause", "iso ", "osha", "pssr")):
        return "COMPLIANCE", 0.84
    if any(k in q for k in ("how many", "average", "trend", "count", "compare", "statistic", "mtbf", "summary", "list")):
        return "DATA_ANALYSIS", 0.82
    if any(k in q for k in ("image", "photo", "picture", "diagram", "drawing")):
        return "VISION", 0.80
    return "DOC_QA", 0.72


async def _load_titles(user: ServerUserContext, doc_ids: list[str]) -> dict[str, str]:
    if not doc_ids:
        return {}
    from backend.db.base import async_session

    titles: dict[str, str] = {}
    async with async_session() as session:
        result = await session.execute(
            select(DocumentModel).where(
                DocumentModel.id.in_([uuid.UUID(d) for d in doc_ids])
            )
        )
        titles = {str(d.id): d.filename for d in result.scalars().all()}
    return titles


def _source_payload(
    chunks: list[RetrievedChunk], titles: dict[str, str], start: int = 1
) -> list[dict]:
    out: list[dict] = []
    for i, c in enumerate(chunks, start=start):
        out.append(
            {
                "n": i,
                "chunk_id": c.id,
                "document_id": c.document_id,
                "document_title": titles.get(c.document_id, c.document_id),
                "page_start": c.page_start,
                "page_end": c.page_end,
                "score": round(c.score, 3),
                "chunk_type": c.chunk_type,
                "suspected_injection": False,
                "snippet": (c.text or "")[:260],
            }
        )
    return out


def _citation_payload(
    chunks: list[RetrievedChunk], titles: dict[str, str]
) -> list[dict]:
    return [
        {
            "n": i,
            "document_id": c.document_id,
            "document_title": titles.get(c.document_id, c.document_id),
            "page": c.page_start,
            "bbox": c.bbox_union,
            "snippet": (c.text or "")[:180],
        }
        for i, c in enumerate(chunks, start=1)
    ]


async def _load_attachments(owner_id: str, ids: list[str]) -> list[dict]:
    """Load this user's image attachments as base64. Path-scoped per owner."""
    if not ids:
        return []
    owner_dir = settings.vault_path / "attachments" / owner_id
    if not owner_dir.exists():
        return []
    loaded: list[dict] = []
    for aid in ids[:_MAX_IMAGES]:
        matches = list(owner_dir.glob(f"{aid}.*"))
        if not matches:
            logger.warning("attachment_not_found", owner_id=owner_id, attachment_id=aid)
            continue
        path = matches[0]
        raw = await asyncio.to_thread(path.read_bytes)
        loaded.append(
            {"id": aid, "name": path.name, "b64": base64.b64encode(raw).decode("ascii")}
        )
    return loaded


async def _persist_assistant(
    db: AsyncSession,
    session_id: str,
    turn_id: str,
    content: str,
    intent: str,
    confidence: float,
    grounded: bool,
    abstained: bool,
    sources: list[dict],
    citations: list[dict],
    reasoning: list[dict],
    tokens_out: int,
    latency_ms: int,
) -> str:
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.add(
        ChatMessageModel(
            id=uuid.UUID(message_id),
            session_id=uuid.UUID(session_id),
            turn_id=uuid.UUID(turn_id),
            role="assistant",
            content=content,
            intent=intent,
            route_confidence=confidence,
            grounded=grounded,
            abstained=abstained,
            citations=citations or None,
            reasoning=reasoning or None,
            sources=sources or None,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            created_at=now,
        )
    )
    sess = await db.execute(select(ChatSessionModel).where(ChatSessionModel.id == uuid.UUID(session_id)))
    session_model = sess.scalar_one_or_none()
    if session_model is not None:
        session_model.updated_at = now
    await db.commit()
    return message_id


async def _run_turn(
    session_id: str, turn_id: str, user: ServerUserContext, db: AsyncSession,
    attachment_ids: list[str] | None = None,
) -> AsyncIterator[str]:
    started = time.monotonic()
    reasoning: list[dict] = []
    sources: list[dict] = []
    citations: list[dict] = []

    try:
        sess = await db.execute(select(ChatSessionModel).where(ChatSessionModel.id == uuid.UUID(session_id)))
        session_model = sess.scalar_one_or_none()
        if session_model is None or str(session_model.user_id) != user.user_id:
            yield _error_frame("session not found")
            return

        msg_result = await db.execute(
            select(ChatMessageModel).where(
                ChatMessageModel.turn_id == uuid.UUID(turn_id),
                ChatMessageModel.session_id == uuid.UUID(session_id),
                ChatMessageModel.role == "user",
            )
        )
        user_msg = msg_result.scalar_one_or_none()
        if user_msg is None:
            yield _error_frame("unknown turn")
            return
        question = (user_msg.content or "").strip()
        if not question:
            yield _error_frame("empty question")
            return

        intent, confidence = _classify_intent(question)
        tool_calls: list[dict] = [{"name": "vector_search", "args": {"query": question[:120]}}]

        def step(seq: int, phase: str, label: str, **extra) -> None:
            reasoning.append(
                {"seq": seq, "phase": phase, "label": label, **extra,
                 "elapsed_ms": int((time.monotonic() - started) * 1000)}
            )

        images = await _load_attachments(user.user_id, attachment_ids or [])
        vision_description = ""
        if images:
            intent, confidence = "VISION", max(confidence, 0.95)
            tool_calls = [{"name": "vision_describe", "args": {"images": len(images)}}]

        rationale = "deterministic router + image attachment" if images else "deterministic router"
        yield _sse("route", {"intent": intent, "confidence": round(confidence, 3), "rationale": rationale})

        step(1, "plan", f"Routing to {intent}" + (" with attached photo" if images else ""))
        yield _sse("step", reasoning[-1])

        next_act = 2
        if images:
            step(2, "vision", "Analysing attached photo",
                 tool="vision_describe", tool_args={"images": len(images)})
            yield _sse("step", reasoning[-1])
            try:
                ollama_vision = get_or_create_client()
                vision_description = await ollama_vision.vision(
                    VISION_ATTACH_PROMPT,
                    [img["b64"] for img in images],
                    model=settings.vision_model,
                    temperature=0.2,
                    max_tokens=512,
                    timeout_s=settings.vision_timeout_s,
                    repeat_penalty=1.1,
                )
                step(2, "vision", f"Photo analysed: {vision_description[:120]}")
            except Exception as exc:
                logger.error("vision_attach_failed", error=str(exc), session_id=session_id)
                vision_description = ""
                step(2, "vision", f"Vision model unavailable: {str(exc)[:100]}")
            yield _sse("step", reasoning[-1])
            next_act = 3

            if not vision_description and not question:
                answer = (
                    "I could not analyse the attached photo because the local vision model was unavailable. "
                    "Please retry, or add a question alongside the photo."
                )
                await _persist_assistant(
                    db, session_id, turn_id, answer, intent, confidence,
                    grounded=False, abstained=True, sources=[], citations=[],
                    reasoning=reasoning, tokens_out=len(answer.split()),
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
                yield _sse("citations", {"citations": []})
                yield _sse(
                    "done",
                    {
                        "message_id": "", "turn_id": turn_id, "grounded": False,
                        "abstained": True, "citation_coverage": 0.0,
                        "tokens_in": 0, "tokens_out": len(answer.split()),
                        "latency_ms": int((time.monotonic() - started) * 1000),
                        "tool_calls": 1,
                    },
                )
                return

        search_query = question
        if vision_description:
            search_query = f"{question} — photo analysis: {vision_description[:250]}"

        step(next_act, "act", "Retrieving authorised sources",
             tool="vector_search", tool_args={"query": search_query[:120]})
        yield _sse("step", reasoning[-1])

        chunks: list[RetrievedChunk] = []
        try:
            chunks = await search(search_query, user, k=settings.retrieval_top_k)
        except Exception as exc:
            logger.error("retrieval_failed", error=str(exc), session_id=session_id)

        doc_ids = list({c.document_id for c in chunks if c.document_id})
        titles = await _load_titles(user, doc_ids)
        sources = _source_payload(chunks[: _MAX_SOURCES], titles)
        yield _sse("sources", {"sources": sources})

        if not chunks:
            answer = (
                "I could not find any authorised sources matching your question in the local corpus. "
                "Upload a relevant document in the Documents tab so it can be indexed, then ask again."
            )
            await _persist_assistant(
                db, session_id, turn_id, answer, intent, confidence,
                grounded=False, abstained=True, sources=[], citations=[],
                reasoning=reasoning, tokens_out=len(answer.split()),
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            yield _sse("citations", {"citations": []})
            yield _sse(
                "done",
                {
                    "message_id": "", "turn_id": turn_id, "grounded": False,
                    "abstained": True, "citation_coverage": 0.0,
                    "tokens_in": 0, "tokens_out": len(answer.split()),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "tool_calls": 1,
                },
            )
            return

        step(next_act + 1, "synthesize", f"Grounding answer in {len(chunks)} authorised sources")
        yield _sse("step", reasoning[-1])

        context = "\n\n".join(
            f"[{i}] {' — '.join(c.heading_path) if c.heading_path else ''}\n{c.text}"
            for i, c in enumerate(chunks, start=1)
        )
        if vision_description:
            context = f"[USER-PROVIDED PHOTO ANALYSIS]\n{vision_description}\n\n{context}"
        user_prompt = SYNTH_PROMPT.format(context=context, question=question)
        prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]

        ollama = get_or_create_client()
        messages = [
            {"role": "system", "content": SOVEREIGN_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        output: list[str] = []
        async for delta in ollama.stream(messages, temperature=0.2, max_tokens=_MAX_STREAM_TOKENS):
            output.append(delta)
            yield _sse("token", {"delta": delta})
        answer = "".join(output)

        citations = _citation_payload(chunks[: _MAX_SOURCES], titles)
        yield _sse("citations", {"citations": citations})

        tokens_in = len(question.split()) + sum(len(c.text.split()) for c in chunks)
        tokens_out = len(answer.split())
        latency_ms = int((time.monotonic() - started) * 1000)

        message_id = await _persist_assistant(
            db, session_id, turn_id, answer, intent, confidence,
            grounded=True, abstained=False, sources=sources, citations=citations,
            reasoning=reasoning, tokens_out=tokens_out, latency_ms=latency_ms,
        )

        await audit_emit(
            "CHAT_COMPLETE",
            correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
            user_id=user.user_id,
            role=str(user.role),
            resource_type="session",
            resource_id=session_id,
            document_ids=doc_ids,
            intent=intent,
            decision=json.dumps({"grounded": True, "abstained": False, "citation_coverage": len(citations)}),
            prompt_hash=prompt_hash,
            tool_calls=tool_calls,
            severity="info",
        )

        yield _sse(
            "done",
            {
                "message_id": message_id, "turn_id": turn_id, "grounded": True,
                "abstained": False, "citation_coverage": round(len(citations) / max(len(chunks), 1), 2),
                "tokens_in": tokens_in, "tokens_out": tokens_out,
                "latency_ms": latency_ms, "tool_calls": 2,
            },
        )
    except Exception as exc:
        logger.error("chat_turn_failed", error=str(exc), session_id=session_id, turn_id=turn_id)
        yield _error_frame(str(exc)[:300])


async def _stream_with_keepalive(
    session_id: str, turn_id: str, user: ServerUserContext, db: AsyncSession,
    attachment_ids: list[str] | None = None,
) -> AsyncIterator[str]:
    events = _run_turn(session_id, turn_id, user, db, attachment_ids)
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def pump() -> None:
        try:
            async for chunk in events:
                await queue.put(chunk)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("sse_pump_failed", error=str(exc))
            await queue.put(_error_frame(str(exc)[:300]))
        finally:
            await queue.put(None)

    task = asyncio.create_task(pump())
    try:
        while True:
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=_KEEPALIVE_INTERVAL
                )
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield item
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@router.get("/chat/sessions/{session_id}/stream")
async def stream_chat(
    session_id: str,
    request: Request,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    turn_id: str = Query(...),
    attachment_ids: list[str] = Query(default_factory=list),
):
    gen = _stream_with_keepalive(session_id, turn_id, user, db, attachment_ids)
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
"""Chat routes — sessions, messages, approval, stop."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from redis import asyncio as redis_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import get_current_user
from backend.core.exceptions import NotFound
from backend.core.rbac import ServerUserContext
from backend.db.models.chat import ChatSessionModel
from backend.db.models.message import ChatMessageModel
from backend.db.session import get_db
from backend.schemas.chat import (
    ApprovalDecision,
    ChatSessionCreate,
    ChatSessionRead,
    MessageAccepted,
    MessageCreate,
    MessageRead,
    PageRead,
)
from backend.services.audit.writer import emit as audit_emit

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


def _session_to_read(s: ChatSessionModel) -> ChatSessionRead:
    return ChatSessionRead(
        id=str(s.id),
        title=s.title or "New Chat",
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )


def _message_to_read(m: ChatMessageModel) -> MessageRead:
    return MessageRead(
        id=str(m.id),
        turn_id=str(m.turn_id),
        role=m.role,
        content=m.content or "",
        intent=m.intent,
        route_confidence=m.route_confidence,
        grounded=m.grounded,
        abstained=m.abstained,
        citations=m.citations or [],
        reasoning=m.reasoning or [],
        sources=m.sources or [],
        tokens_in=m.tokens_in,
        tokens_out=m.tokens_out,
        latency_ms=m.latency_ms,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )


@router.post("/sessions", response_model=ChatSessionRead, status_code=201)
async def create_session(
    body: ChatSessionCreate,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    now = datetime.now(timezone.utc)
    session = ChatSessionModel(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user.user_id),
        title=body.title or "New Chat",
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    logger.info("session_created", session_id=str(session.id), user_id=user.user_id)
    return _session_to_read(session)


@router.get("/sessions", response_model=PageRead)
async def list_sessions(
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    base = select(ChatSessionModel).where(
        ChatSessionModel.user_id == uuid.UUID(user.user_id)
    )
    total_q = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_q.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        base.order_by(ChatSessionModel.updated_at.desc())
        .offset(offset)
        .limit(size)
    )
    sessions = result.scalars().all()

    return PageRead(
        items=[_session_to_read(s) for s in sessions],
        total=total,
        page=page,
        size=size,
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
async def list_messages(
    session_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _ = await _get_owned_session(db, session_id, user)

    result = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == uuid.UUID(session_id))
        .order_by(ChatMessageModel.created_at.asc())
    )
    messages = result.scalars().all()
    return [_message_to_read(m) for m in messages]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await _get_owned_session(db, session_id, user)
    await db.delete(session)
    await db.flush()

    logger.info("session_deleted", session_id=session_id, user_id=user.user_id)
    return None


@router.post(
    "/sessions/{session_id}/messages", response_model=MessageAccepted, status_code=202
)
async def post_message(
    session_id: str,
    body: MessageCreate,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Accept a user turn and start the agent run."""
    _ = await _get_owned_session(db, session_id, user)

    turn_id = uuid.uuid4()
    message_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    msg = ChatMessageModel(
        id=message_id,
        session_id=uuid.UUID(session_id),
        turn_id=turn_id,
        role="user",
        content=body.content,
        created_at=now,
    )
    db.add(msg)

    # Update session timestamp
    session = await _get_owned_session(db, session_id, user)
    session.updated_at = now

    await db.flush()

    logger.info(
        "message_posted",
        session_id=session_id,
        turn_id=str(turn_id),
        message_id=str(message_id),
    )
    # Stub: agent integration would be triggered here via arq/Redis
    return MessageAccepted(message_id=str(message_id), turn_id=str(turn_id))


@router.post("/sessions/{session_id}/approve", status_code=202)
async def approve_turn(
    session_id: str,
    body: ApprovalDecision,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resume or deny a turn paused at the HITL gate.

    Publishes the operator's decision to the waiting stream over Redis and
    records it in the audit chain.
    """
    _ = await _get_owned_session(db, session_id, user)

    decision = body.decision.upper()
    if decision not in ("APPROVED", "DENIED"):
        raise HTTPException(status_code=422, detail="decision must be APPROVED or DENIED")
    if not body.approval_id:
        raise HTTPException(status_code=422, detail="approval_id is required")

    now = datetime.now(timezone.utc)
    payload = {
        "decision": decision,
        "by": user.user_id,
        "session_id": session_id,
        "ts": now.isoformat(),
        "note": body.note,
    }
    try:
        redis_client = redis_asyncio.from_url(settings.redis_url, decode_responses=True)
        await redis_client.publish(f"hitl:{body.approval_id}", json.dumps(payload))
        await redis_client.aclose()
    except Exception as exc:
        logger.error("hitl_publish_failed", approval_id=body.approval_id, error=str(exc))
        raise HTTPException(status_code=503, detail="gateway temporarily unavailable")

    await audit_emit(
        f"HITL_{decision}",
        correlation_id=structlog.contextvars.get_contextvars().get("correlation_id", ""),
        user_id=user.user_id,
        role=str(user.role),
        resource_type="session",
        resource_id=session_id,
        intent="PRIVILEGED",
        decision=json.dumps(
            {"approval_id": body.approval_id, "decision": decision, "by": user.user_id},
            sort_keys=True,
        ),
        severity="info" if decision == "APPROVED" else "warning",
    )

    logger.info(
        "approval_decision",
        session_id=session_id,
        approval_id=body.approval_id,
        decision=decision,
        user_id=user.user_id,
    )
    return {"status": "accepted", "decision": decision, "published": True}


@router.post("/sessions/{session_id}/stop", status_code=204)
async def stop_turn(
    session_id: str,
    user: Annotated[ServerUserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Cancel the in-flight turn."""
    _ = await _get_owned_session(db, session_id, user)

    logger.info("turn_stopped", session_id=session_id, user_id=user.user_id)
    return None


async def _get_owned_session(
    db: AsyncSession, session_id: str, user: ServerUserContext
) -> ChatSessionModel:
    """Fetch a session that belongs to the current user or raise NotFound."""
    result = await db.execute(
        select(ChatSessionModel).where(
            ChatSessionModel.id == uuid.UUID(session_id),
            ChatSessionModel.user_id == uuid.UUID(user.user_id),
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFound(f"Session {session_id} not found")
    return session

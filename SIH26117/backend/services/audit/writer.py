"""Audit log writer — append-only, hash-chained."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import async_session
from backend.db.models.audit import AuditChainHead, AuditLogModel

logger = structlog.get_logger()

GENESIS = "genesis"


def chain_hash(prev_hash: str, entry: dict[str, object]) -> str:
    """Deterministic SHA-256 hash chaining: H(prev | JSON(entry))."""
    body = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}|{body}".encode()).hexdigest()


async def emit(
    action: str,
    *,
    correlation_id: str = "",
    user_id: str | None = None,
    role: str | None = None,
    clearance_at_time: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    route: str | None = None,
    intent: str | None = None,
    tool_calls: list[dict[str, object]] | None = None,
    document_ids: list[str] | None = None,
    prompt_hash: str | None = None,
    decision: str | None = None,
    severity: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Emit-and-forget audit event. Must never raise into the request path."""
    try:
        async with async_session() as db:
            head_row = (
                await db.execute(
                    select(AuditChainHead).where(AuditChainHead.id == 1).with_for_update()
                )
            ).scalar_one_or_none()

            if head_row is None:
                prev_hash = GENESIS
                head_row = AuditChainHead(id=1, last_hash=GENESIS)
                db.add(head_row)
                await db.flush()
            else:
                prev_hash = head_row.last_hash

            now = datetime.now(timezone.utc)
            entry: dict[str, object] = {
                "ts": now.isoformat(),
                "action": action,
                "user_id": user_id or "",
                "role": role or "",
                "correlation_id": correlation_id,
            }
            if clearance_at_time is not None:
                entry["clearance_at_time"] = clearance_at_time
            if resource_type is not None:
                entry["resource_type"] = resource_type
            if resource_id is not None:
                entry["resource_id"] = resource_id
            if route is not None:
                entry["route"] = route
            if intent is not None:
                entry["intent"] = intent
            if tool_calls is not None:
                entry["tool_calls"] = tool_calls
            if document_ids is not None:
                entry["document_ids"] = document_ids
            if prompt_hash is not None:
                entry["prompt_hash"] = prompt_hash
            if decision is not None:
                entry["decision"] = decision
            if severity is not None:
                entry["severity"] = severity

            entry_hash = chain_hash(prev_hash, entry)

            log_row = AuditLogModel(
                ts=now,
                user_id=user_id,
                role=role,
                clearance_at_time=clearance_at_time,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                route=route,
                intent=intent,
                tool_calls=tool_calls,
                document_ids=document_ids,
                prompt_hash=prompt_hash,
                decision=decision,
                severity=severity,
                ip=ip,
                user_agent=user_agent,
                correlation_id=correlation_id,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
            db.add(log_row)
            head_row.last_hash = entry_hash
            await db.commit()

            logger.info("audit_event", action=action, entry_hash=entry_hash)
    except Exception as exc:
        logger.error("audit_emit_failed", action=action, error=str(exc))


def _reconstruct_entry(row: AuditLogModel) -> dict[str, object]:
    """Reconstruct the canonical entry dict from a stored audit row for re-hashing."""
    entry: dict[str, object] = {
        "ts": row.ts.isoformat() if row.ts else "",
        "action": row.action,
        "user_id": str(row.user_id) if row.user_id else "",
        "role": row.role or "",
        "correlation_id": row.correlation_id or "",
    }
    if row.clearance_at_time is not None:
        entry["clearance_at_time"] = row.clearance_at_time
    if row.resource_type is not None:
        entry["resource_type"] = row.resource_type
    if row.resource_id is not None:
        entry["resource_id"] = row.resource_id
    if row.route is not None:
        entry["route"] = row.route
    if row.intent is not None:
        entry["intent"] = row.intent
    if row.tool_calls is not None:
        entry["tool_calls"] = row.tool_calls
    if row.document_ids is not None:
        entry["document_ids"] = row.document_ids
    if row.prompt_hash is not None:
        entry["prompt_hash"] = row.prompt_hash
    if row.decision is not None:
        entry["decision"] = row.decision
    if row.severity is not None:
        entry["severity"] = row.severity
    return entry


async def verify_chain(
    session: AsyncSession | None = None,
    from_id: int | None = None,
) -> dict[str, object]:
    """Walk the hash chain and report integrity. Returns metadata dict."""
    acquired = session is None
    try:
        if acquired:
            ctx = async_session()
            session = await ctx.__aenter__()

        query = select(AuditLogModel).order_by(AuditLogModel.id.asc())
        if from_id is not None:
            query = query.where(AuditLogModel.id >= from_id)
        result = await session.execute(query)
        rows = list(result.scalars().all())

        if not rows:
            return {
                "valid": True,
                "entries": 0,
                "first_break": None,
                "anchor": f"sha256:{GENESIS}",
            }

        expected_prev = GENESIS
        first_break: int | None = None
        last_good_hash = GENESIS

        for row in rows:
            if row.prev_hash != expected_prev:
                first_break = row.id
                break
            entry = _reconstruct_entry(row)
            recomputed = chain_hash(expected_prev, entry)
            if recomputed != row.entry_hash:
                first_break = row.id
                break
            last_good_hash = row.entry_hash
            expected_prev = row.entry_hash

        if first_break is not None:
            anchor = f"sha256:{last_good_hash}"
        else:
            anchor = f"sha256:{rows[-1].entry_hash}"

        return {
            "valid": first_break is None,
            "entries": len(rows),
            "first_break": first_break,
            "anchor": anchor,
        }
    except Exception as exc:
        logger.error("chain_verify_failed", error=str(exc))
        return {
            "valid": False,
            "entries": 0,
            "first_break": None,
            "anchor": "sha256:error",
        }
    finally:
        if acquired and session is not None:
            await session.close()

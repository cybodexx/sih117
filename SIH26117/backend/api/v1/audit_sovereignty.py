"""Audit and sovereignty routes."""
from __future__ import annotations

import time
from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.deps import require_role
from backend.core.rbac import Role, ServerUserContext
from backend.db.models.audit import AuditLogModel
from backend.db.session import get_db
from backend.schemas.audit import AuditRead, AuditVerify, SovereigntyStatus
from backend.services.audit.writer import verify_chain

logger = structlog.get_logger()
router = APIRouter(tags=["audit-sovereignty"])
settings = get_settings()

sovereignty_status_cache: dict[str, object] = {
    "airgap_mode": settings.airgap_mode,
    "network_mode": "bridge" if not settings.airgap_mode else "isolated",
    "dns_resolvable": not settings.airgap_mode,
    "attempts": 0,
    "blocked": 0,
    "reached": 0,
    "bytes_egressed": 0,
    "uptime_s": 0,
    "breach": None,
}
_sentinel_memo: dict[str, object] = {"ts": 0.0, "data": sovereignty_status_cache}


async def _sentinel_status() -> dict[str, object]:
    """Proxy the live counters from aegis-sentinel, cached ~2.5s."""
    now = time.monotonic()
    if now - float(_sentinel_memo["ts"]) < 2.5:
        return dict(_sentinel_memo["data"])
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.sentinel_url}/sentinel/status")
            if resp.status_code == 200:
                data: dict[str, object] = resp.json()
                _sentinel_memo["ts"] = now
                _sentinel_memo["data"] = data
                return data
    except Exception:
        logger.warning("sentinel_unreachable", url=settings.sentinel_url)
    return dict(_sentinel_memo["data"])


@router.get("/audit", response_model=dict)
async def list_audit(
    user: Annotated[
        ServerUserContext, Depends(require_role(Role.AUDITOR, Role.ADMIN))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    action: str | None = None,
    user_id: str | None = None,
    severity: str | None = None,
    resource_type: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List audit log entries with optional filters."""
    base = select(AuditLogModel)
    if action is not None:
        base = base.where(AuditLogModel.action == action)
    if user_id is not None:
        base = base.where(AuditLogModel.user_id == user_id)
    if severity is not None:
        base = base.where(AuditLogModel.severity == severity)
    if resource_type is not None:
        base = base.where(AuditLogModel.resource_type == resource_type)

    total_q = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_q.scalar() or 0

    offset = (page - 1) * size
    result = await db.execute(
        base.order_by(AuditLogModel.ts.desc()).offset(offset).limit(size)
    )
    rows = result.scalars().all()

    items = [
        AuditRead(
            id=row.id,
            ts=row.ts.isoformat() if row.ts else "",
            user_id=str(row.user_id) if row.user_id else None,
            role=row.role,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            correlation_id=row.correlation_id,
            decision=row.decision,
            severity=row.severity,
        )
        for row in rows
    ]

    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/audit/verify", response_model=AuditVerify)
async def verify_audit_chain(
    user: Annotated[
        ServerUserContext, Depends(require_role(Role.AUDITOR, Role.ADMIN))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Walk the hash chain and report integrity."""
    result = await verify_chain(session=db)
    return AuditVerify(
        valid=bool(result["valid"]),
        entries=int(result["entries"]),
        first_break=result["first_break"],
        anchor=str(result["anchor"]),
    )


@router.get("/sovereignty/status", response_model=SovereigntyStatus)
async def sovereignty_status():
    """Return current sovereignty status from the sentinel."""
    data = await _sentinel_status()
    return SovereigntyStatus(
        airgap_mode=bool(data.get("airgap_mode", sovereignty_status_cache["airgap_mode"])),
        network_mode=str(data.get("network_mode", sovereignty_status_cache["network_mode"])),
        dns_resolvable=bool(data.get("dns_resolvable", sovereignty_status_cache["dns_resolvable"])),
        attempts=int(data.get("attempts", 0)),
        blocked=int(data.get("blocked", 0)),
        reached=int(data.get("reached", 0)),
        bytes_egressed=int(data.get("bytes_egressed", 0)),
        uptime_s=int(data.get("uptime_s", 0)),
        last_probe_at=data.get("last_probe_at") or None,
        models=data.get("models") or [],
        breach=data.get("breach") or sovereignty_status_cache["breach"],  # type: ignore[arg-type]
    )

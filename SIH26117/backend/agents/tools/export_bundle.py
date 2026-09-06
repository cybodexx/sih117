"""export_bundle tool — HIGH-risk: ships a tamper-evident audit + sovereignty bundle.

M5 owns this file. Executed only AFTER a human operator approves at the HITL
gate. Produces a real JSON export (audit chain verification + recent entries +
sovereignty state) with a content digest, written under the vault path.
"""
from __future__ import annotations

import hashlib
import json
import structlog
from datetime import datetime, timezone

from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.base import async_session
from backend.db.models.audit import AuditLogModel
from backend.services.audit.writer import emit as audit_emit
from backend.services.audit.writer import verify_chain

logger = structlog.get_logger()
settings = get_settings()


async def export_bundle(requested_by: str, session_id: str, scope: str = "full") -> str:
    """Assemble and persist the audit/sovereignty export bundle. Returns a summary.

    Raises RuntimeError when the export cannot be written.
    """
    async with async_session() as db:
        chain = await verify_chain(session=db)
        result = await db.execute(
            select(AuditLogModel).order_by(AuditLogModel.id.desc()).limit(100)
        )
        rows = list(result.scalars().all())

    entries = [
        {
            "id": r.id,
            "ts": r.ts.isoformat() if r.ts else "",
            "action": r.action,
            "user_id": str(r.user_id) if r.user_id else None,
            "role": r.role,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "intent": r.intent,
            "severity": r.severity,
            "prev_hash": r.prev_hash,
            "entry_hash": r.entry_hash,
        }
        for r in rows
    ]

    bundle: dict[str, object] = {
        "schema_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": requested_by,
        "session_id": session_id,
        "scope": scope,
        "chain": chain,
        "entries": entries,
        "sovereignty": {
            "airgap_mode": settings.airgap_mode,
            "network_mode": "bridged-by-design",
            "model": settings.llm_model,
            "vision_model": settings.vision_model,
        },
    }

    digest = hashlib.sha256(
        json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    bundle["bundle_digest"] = digest

    vault_dir = settings.vault_path / "exports"
    vault_dir.mkdir(parents=True, exist_ok=True)
    if not str(vault_dir.resolve()).startswith(str(settings.vault_path.resolve())):
        raise RuntimeError("refusing to write bundle outside the vault path")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_path = vault_dir / f"audit_bundle_{stamp}_{digest[:8]}.json"
    bundle_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8"
    )

    await audit_emit(
        "BUNDLE_EXPORTED",
        correlation_id="",
        user_id=requested_by,
        role="OPERATOR",
        resource_type="export",
        resource_id=bundle_path.name,
        decision=json.dumps(
            {"digest": digest[:16], "entries": len(entries), "chain_valid": bool(chain["valid"])},
            sort_keys=True,
        ),
        severity="info",
    )

    logger.info("bundle_exported", path=str(bundle_path), entries=len(entries), digest=digest)
    return (
        f"Export bundle written to {bundle_path} with {len(entries)} audit entries. "
        f"Hash-chain integrity: valid={chain['valid']} (anchor sha256:{chain['anchor'][:16]}). "
        f"Bundle digest: sha256:{digest[:16]}"
    )
from __future__ import annotations

from pydantic import BaseModel


class AuditRead(BaseModel):
    id: int
    ts: str
    user_id: str | None = None
    role: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    correlation_id: str | None = None
    decision: str | None = None
    severity: str | None = None


class AuditVerify(BaseModel):
    valid: bool
    entries: int
    first_break: int | None = None
    anchor: str


class SovereigntyStatus(BaseModel):
    airgap_mode: bool
    network_mode: str
    dns_resolvable: bool
    attempts: int
    blocked: int
    reached: int
    bytes_egressed: int
    uptime_s: int
    last_probe_at: str | None = None
    models: list[dict] = []
    breach: str | None = None

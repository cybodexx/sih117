from __future__ import annotations

import enum
from enum import IntEnum, StrEnum
from dataclasses import dataclass

from pydantic import BaseModel


class Clearance(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class Role(StrEnum):
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    ENGINEER = "ENGINEER"
    AUDITOR = "AUDITOR"
    ADMIN = "ADMIN"


MAX_CLEARANCE: dict[Role, Clearance] = {
    Role.VIEWER: Clearance.PUBLIC,
    Role.ANALYST: Clearance.INTERNAL,
    Role.ENGINEER: Clearance.CONFIDENTIAL,
    Role.AUDITOR: Clearance.RESTRICTED,
    Role.ADMIN: Clearance.RESTRICTED,
}

CROSS_DEPARTMENT: frozenset[Role] = frozenset({Role.AUDITOR, Role.ADMIN})


class ServerUserContext(BaseModel):
    """Immutable identity derived ONLY from a verified JWT."""

    model_config = {"frozen": True}

    user_id: str
    role: Role
    clearance_level: Clearance
    departments: list[str]


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str

    @classmethod
    def allow(cls) -> Decision:
        return Decision(allowed=True, reason="ok")

    @classmethod
    def deny(cls, reason: str) -> Decision:
        return Decision(allowed=False, reason=reason)


class DocumentLabels(BaseModel):
    status: str
    clearance_level: Clearance
    department: str
    legal_hold: bool = False


def can_read(user: ServerUserContext, doc: DocumentLabels) -> Decision:
    """Bell-LaPadula no-read-up + need-to-know compartment."""
    if doc.status != "READY":
        return Decision.deny("not_ready")
    if doc.clearance_level > user.clearance_level:
        return Decision.deny("clearance")
    if doc.department not in user.departments and user.role not in CROSS_DEPARTMENT:
        return Decision.deny("department")
    if doc.legal_hold and user.role is not Role.AUDITOR:
        return Decision.deny("legal_hold")
    return Decision.allow()

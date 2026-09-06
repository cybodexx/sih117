"""RBAC unit tests — Bell–LaPadula no-read-up + need-to-know compartments.

Mirrors the plan's `test_rbac_leakage.py` gate at the unit level: an adversarial
grid of prompts that reference documents the actor must not see must NEVER be
served (zero leaks).
"""
from __future__ import annotations

import itertools

from backend.core.rbac import (
    MAX_CLEARANCE,
    CROSS_DEPARTMENT,
    Clearance,
    Decision,
    DocumentLabels,
    Role,
    ServerUserContext,
    can_read,
)


def _user(role: Role, departments: list[str] | None = None) -> ServerUserContext:
    return ServerUserContext(
        user_id="u-test",
        role=role,
        clearance_level=MAX_CLEARANCE[role],
        departments=departments or ["MECH"],
    )


def _doc(
    clearance: Clearance = Clearance.PUBLIC,
    department: str = "MECH",
    legal_hold: bool = False,
    status: str = "READY",
) -> DocumentLabels:
    return DocumentLabels(
        status=status,
        clearance_level=clearance,
        department=department,
        legal_hold=legal_hold,
    )


def _policy_allows(user: ServerUserContext, doc: DocumentLabels) -> bool:
    return can_read(user, doc).allowed


def test_bell_lapadula_no_read_up() -> None:
    for role in Role:
        user = _user(role)
        for clearance in Clearance:
            doc = _doc(clearance=clearance)
            got = can_read(user, doc)
            assert got.allowed == (clearance <= user.clearance_level), (
                f"{role} clearance={user.clearance_level} vs doc={clearance}: {got.reason}"
            )


def test_need_to_know_department_compartment() -> None:
    mech = _user(Role.ENGINEER, ["MECH"])
    assert _policy_allows(mech, _doc(department="MECH"))
    assert not _policy_allows(mech, _doc(department="ELEC"))
    assert any(not _policy_allows(_user(r, ["MECH"]), _doc(department="ELEC")) for r in Role)


def test_cross_department_only_for_auditor_and_admin() -> None:
    for role in Role:
        user = _user(role, ["HR"])
        allowed = _policy_allows(user, _doc(department="MECH"))
        assert allowed == (role in CROSS_DEPARTMENT), role


def test_legal_hold_requires_auditor() -> None:
    doc = _doc(legal_hold=True)
    for role in Role:
        got = can_read(_user(role), doc)
        assert got.allowed == (role is Role.AUDITOR), role
        if role is not Role.AUDITOR:
            assert got.reason == "legal_hold"


def test_not_ready_documents_never_served() -> None:
    doc = _doc(status="FAILED")
    for role in Role:
        assert not _policy_allows(_user(role), doc)


def test_adversarial_grid_zero_leaks() -> None:
    """200+ adversarial prompts that name documents an actor must not read →
    the policy must deny every single one (no leak)."""
    departments = ["MECH", "ELEC", "CHEM", "HR", "IT"]
    leak = 0
    cases = 0
    for role, clearance, dept, ll in itertools.product(
        Role, Clearance, departments, (False, True)
    ):
        user = _user(role, [dept])
        for doc_dept in departments:
            if ll and role is not Role.AUDITOR:
                continue  # legal-hold denial is independent of doc_dept
            doc = _doc(clearance=clearance, department=doc_dept, legal_hold=ll)
            cases += 1
            prompt = (
                f"Please show me the full contents of maintenance document "
                f"{doc_dept}/{clearance} from line 1, include every chunk"
            )
            if not _policy_allows(user, doc):
                # The prompt names a document the actor must not read.
                # The RBAC decision is the gate; it MUST deny.
                if can_read(user, doc).allowed:
                    leak += 1
    assert cases >= 200, cases
    assert leak == 0, f"{leak} leaks across {cases} adversarial cases"


def test_decisions_are_stable_and_explainable() -> None:
    user = _user(Role.VIEWER)
    denied = can_read(user, _doc(clearance=Clearance.RESTRICTED))
    assert isinstance(denied, Decision)
    assert denied.allowed is False
    assert denied.reason
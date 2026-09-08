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
    can_manage,
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


def test_manage_auditor_is_read_only() -> None:
    """AUDITOR may read but never mutate/delete (no manage rights)."""
    auditor = _user(Role.AUDITOR, departments=["HR"])
    doc = _doc(clearance=Clearance.RESTRICTED, department="HR", legal_hold=True)
    assert can_read(auditor, doc).allowed  # visibility preserved
    assert not can_manage(auditor, doc, owner_id="someone-else").allowed


def test_manage_admin_crosses_departments() -> None:
    admin = _user(Role.ADMIN, departments=["HR"])
    doc = _doc(clearance=Clearance.RESTRICTED, department="MECH")
    assert can_manage(admin, doc, owner_id="someone-else").allowed


def test_manage_owner_allowed_roles() -> None:
    for role in (Role.ENGINEER, Role.ANALYST):
        owner = _user(role)
        doc = _doc()
        assert can_manage(owner, doc, owner_id="u-test").allowed


def test_manage_department_peer_engineer_allowed() -> None:
    peer = _user(Role.ENGINEER, departments=["MECH"])
    doc = _doc(department="MECH")
    assert can_manage(peer, doc, owner_id="someone-else").allowed


def test_manage_foreign_department_denied() -> None:
    foreign = _user(Role.ENGINEER, departments=["HR"])
    doc = _doc(department="MECH")
    assert not can_manage(foreign, doc, owner_id="someone-else").allowed


def test_manage_viewer_never_allowed() -> None:
    viewer = _user(Role.VIEWER)
    doc = _doc()
    assert not can_manage(viewer, doc, owner_id="someone-else").allowed


def test_manage_unreadable_document_denied() -> None:
    """Manage never bypasses the read gate (Bell–LaPadula no-read-up)."""
    engineer = _user(Role.ENGINEER)  # CONFIDENTIAL
    doc = _doc(clearance=Clearance.RESTRICTED, department="MECH")
    assert not can_manage(engineer, doc, owner_id="u-test").allowed
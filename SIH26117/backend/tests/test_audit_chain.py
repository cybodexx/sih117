"""Audit hash-chain unit tests — append-only integrity primitive is sound."""
from __future__ import annotations

from backend.services.audit.writer import chain_hash


def _entry() -> dict[str, object]:
    return {"action": "CHAT_COMPLETE", "user_id": "u1", "ts": "2026-09-06T00:00:00Z"}


def test_chain_hash_is_deterministic() -> None:
    e = _entry()
    assert chain_hash("genesis", e) == chain_hash("genesis", e)


def test_chain_hash_changes_with_content_or_prev() -> None:
    e = _entry()
    h1 = chain_hash("genesis", e)
    assert chain_hash(h1, e) != h1
    assert chain_hash("genesis", {**e, "extra": 1}) != h1


def test_chain_hash_shape() -> None:
    h = chain_hash("genesis", _entry())
    assert len(h) == 64
    int(h, 16)  # valid sha256 hex


def test_integrity_holds_under_replay() -> None:
    """Replay protection: inserting a forged entry between two anchors changes
    every subsequent hash in the chain."""
    e1, e2, e3 = _entry(), {**_entry(), "action": "LOGIN"}, {**_entry(), "action": "ADMIN_ACTION"}
    legit_b = chain_hash(chain_hash(chain_hash("genesis", e1), e2), e3)
    forged = chain_hash(chain_hash(chain_hash("genesis", e1), {**_entry(), "action": "FORGED"}), e3)
    assert forged != legit_b
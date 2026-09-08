"""Unit tests for the document re-ingestion guard (`retry`).

A document may be re-enqueued only when it CRASHED (FAILED) or already landed
(READY); in-flight states (QUEUED, PROCESSING) must be rejected so a recovery
can never double-ingest.
"""
from __future__ import annotations

import pytest

from backend.api.v1.documents import _retry_allowed


def test_retry_allowed_on_failed():
    assert _retry_allowed("FAILED") is True


def test_retry_allowed_on_ready():
    assert _retry_allowed("READY") is True


def test_retry_denied_while_queued():
    assert _retry_allowed("QUEUED") is False


def test_retry_denied_while_processing():
    assert _retry_allowed("PROCESSING") is False


def test_retry_denied_while_uploaded():
    assert _retry_allowed("UPLOADED") is False


@pytest.mark.parametrize("status", ["", None, "DELETED", "ARCHIVED"])
def test_retry_denied_unexpected_states(status):
    assert _retry_allowed(status) is False
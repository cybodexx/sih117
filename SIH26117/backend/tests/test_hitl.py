"""HITL integration tests: real export_bundle tool + approval decision flow over Redis."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.api.v1.chat_stream import _wait_for_decision
from backend.agents.tools.export_bundle import export_bundle


def test_export_bundle_writes_tamper_evident_file() -> None:
    result = asyncio.run(export_bundle("eval-test", "test-session"))
    path = Path(result.split("to ")[1].split(" ")[0])
    try:
        assert path.exists()
        assert path.resolve().is_relative_to(Path("/data/vault"))
        bundle = json.loads(path.read_text(encoding="utf-8"))
        assert bundle["requested_by"] == "eval-test"
        assert bundle["session_id"] == "test-session"
        assert bundle["chain"]["valid"] is True
        assert bundle["entries"] and len(bundle["entries"]) > 0
        assert bundle["bundle_digest"]
        assert "export_bundle" in result or "Export bundle written" in result
    finally:
        path.unlink(missing_ok=True)


def test_wait_for_decision_returns_published_approval() -> None:
    from redis import asyncio as redis_asyncio

    from backend.core.config import get_settings

    approval_id = "test-approval-e2e"

    async def _publish():
        await asyncio.sleep(0.3)
        client = redis_asyncio.from_url(get_settings().redis_url, decode_responses=True)
        await client.publish(
            f"hitl:{approval_id}",
            json.dumps({"decision": "APPROVED", "by": "operator", "ts": "now"}),
        )
        await client.aclose()

    async def _run():
        task = asyncio.create_task(_publish())
        decision = await _wait_for_decision(approval_id, timeout_s=10)
        await task
        return decision

    assert asyncio.run(_run()) == "APPROVED"


def test_wait_for_decision_expires_without_publish() -> None:
    result = asyncio.run(
        _wait_for_decision("test-approval-never", timeout_s=2)
    )
    assert result == "EXPIRED"
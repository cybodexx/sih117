"""AEGIS Sentinel — proves data sovereignty. M6 owns this file."""
from __future__ import annotations

import asyncio
import contextlib
import os
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AEGIS Sentinel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict[str, Any] = {
    "attempts": 0,
    "blocked": 0,
    "reached": 0,
    "bytes_egressed": 0,
    "breach": None,
    "start_time": time.time(),
    "models": [],
    "last_probe_at": None,
}

TARGETS = [
    ("1.1.1.1", 53),
    ("8.8.8.8", 53),
    ("api.openai.com", 443),
    ("huggingface.co", 443),
]

_probe_task: asyncio.Task[None] | None = None


async def _probe_loop() -> None:
    while True:
        for host, port in TARGETS:
            _state["attempts"] += 1
            _state["last_probe_at"] = datetime.now(timezone.utc).isoformat()
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=2.0
                )
                writer.close()
                with contextlib.suppress(asyncio.CancelledError):
                    await writer.wait_closed()
                _state["reached"] += 1
                _state["breach"] = f"SOVEREIGNTY_BREACH: reached {host}:{port}"
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError, Exception):
                _state["blocked"] += 1
        await asyncio.sleep(5)


async def _fetch_models() -> None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://ollama:11434/api/tags", timeout=5.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                _state["models"] = [
                    {
                        "role": "text",
                        "name": m.get("name", ""),
                        "digest": m.get("digest", ""),
                        "source": "local",
                    }
                    for m in models
                ]
    except Exception:
        pass


async def _lifespan_startup() -> None:
    global _probe_task
    await _fetch_models()
    _probe_task = asyncio.create_task(_probe_loop())


async def _lifespan_shutdown() -> None:
    if _probe_task is not None:
        _probe_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _probe_task


@asynccontextmanager
async def _lifespan(app_instance: FastAPI) -> AsyncIterator[None]:  # type: ignore[override]
    await _lifespan_startup()
    yield
    await _lifespan_shutdown()


app.router.lifespan_context = _lifespan  # type: ignore[assignment]

AIRGAP_MODE = os.environ.get("AIRGAP_MODE", "").strip().lower() in {"1", "true", "yes"}


@app.get("/sentinel/status")
async def sentinel_status() -> dict[str, Any]:
    return {
        "airgap_mode": AIRGAP_MODE,
        "network_mode": "isolated" if AIRGAP_MODE else "bridge",
        "dns_resolvable": not AIRGAP_MODE,
        "attempts": _state["attempts"],
        "blocked": _state["blocked"],
        "reached": _state["reached"],
        "bytes_egressed": _state["bytes_egressed"],
        "uptime_s": int(time.time() - _state["start_time"]),
        "last_probe_at": _state["last_probe_at"],
        "models": _state["models"],
        "breach": _state["breach"],
    }

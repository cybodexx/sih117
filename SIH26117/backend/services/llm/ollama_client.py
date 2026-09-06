"""Single LLM entry point. M6 owns this file. Every module imports it."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx
import structlog
from fastapi import Depends
from pydantic import BaseModel

from backend.core.config import Settings, get_settings
from backend.core.exceptions import ModelUnavailable

logger = structlog.get_logger()


class OllamaClient:
    """Async, streaming, retry-capable Ollama client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(
            base_url=settings.ollama_url,
            timeout=httpx.Timeout(settings.ollama_timeout_s, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout_s: float | None = None,
    ) -> str:
        model = model or self._settings.llm_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        for attempt in range(3):
            try:
                resp = await asyncio.wait_for(
                    self._http.post("/api/chat", json=payload),
                    timeout=timeout_s or self._settings.ollama_timeout_s,
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"]
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                if attempt == 2:
                    logger.error("ollama_chat_failed", attempt=attempt, error=str(exc))
                    raise ModelUnavailable(
                        f"Ollama chat failed after 3 attempts: {exc}"
                    ) from exc
                await asyncio.sleep(2**attempt)
        raise ModelUnavailable("Unreachable")

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        model = model or self._settings.llm_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with self._http.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    message = chunk.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if content:
                            yield content
                    if chunk.get("done"):
                        break
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.error("ollama_stream_failed", error=str(exc))
            raise ModelUnavailable(f"Ollama stream failed: {exc}") from exc

    async def structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        *,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> BaseModel:
        raw = await self.chat(
            messages, model=model, temperature=temperature, max_tokens=2048
        )
        try:
            return schema.model_validate_json(raw)
        except Exception:
            try:
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = "\n".join(cleaned.split("\n")[1:-1])
                return schema.model_validate(json.loads(cleaned))
            except Exception as exc:
                raise ModelUnavailable(
                    f"Failed to parse structured output: {exc}"
                ) from exc

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        model = model or self._settings.embed_model
        all_embeddings: list[list[float]] = []
        batch_size = 16
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {"model": model, "input": batch, "truncate": True}
            for attempt in range(3):
                try:
                    resp = await self._http.post("/api/embed", json=payload)
                    resp.raise_for_status()
                    data = resp.json()["embeddings"]
                    assert all(
                        len(v) == self._settings.embed_dim for v in data
                    ), f"Embedding dim mismatch: expected {self._settings.embed_dim}"
                    all_embeddings.extend(data)
                    break
                except (httpx.HTTPError, AssertionError) as exc:
                    if attempt == 2:
                        raise ModelUnavailable(f"Embedding failed: {exc}") from exc
                    await asyncio.sleep(2**attempt)
        return all_embeddings

    async def vision(
        self,
        prompt: str,
        images_b64: list[str],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        timeout_s: float | None = None,
        repeat_penalty: float | None = None,
        max_attempts: int = 3,
    ) -> str:
        model = model or self._settings.vision_model
        options: dict[str, object] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if repeat_penalty is not None:
            options["repeat_penalty"] = repeat_penalty
        payload = {
            "model": model,
            "prompt": prompt,
            "images": images_b64,
            "stream": False,
            "options": options,
        }
        for attempt in range(max_attempts):
            try:
                call_timeout = timeout_s or self._settings.vision_timeout_s
                resp = await asyncio.wait_for(
                    self._http.post(
                        "/api/generate",
                        json=payload,
                        timeout=httpx.Timeout(call_timeout, connect=5.0),
                    ),
                    timeout=call_timeout,
                )
                resp.raise_for_status()
                return resp.json()["response"]
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                if attempt == max_attempts - 1:
                    raise ModelUnavailable(f"Vision failed: {exc}") from exc
                await asyncio.sleep(2**attempt)
        raise ModelUnavailable("Unreachable")

    async def close(self) -> None:
        await self._http.aclose()


_client: OllamaClient | None = None


def get_ollama_client_factory() -> type[OllamaClient]:
    """Return the OllamaClient class for use as a FastAPI Depends."""
    return OllamaClient


async def get_ollama_client(
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[OllamaClient, None]:
    """FastAPI dependency — yields a per-request OllamaClient, closes on teardown."""
    client = OllamaClient(settings)
    try:
        yield client
    finally:
        await client.close()


def get_or_create_client() -> OllamaClient:
    """Module-level singleton for non-FastAPI usage (workers, scripts)."""
    global _client
    if _client is None:
        _client = OllamaClient(get_settings())
    return _client


async def close_singleton() -> None:
    """Call on application shutdown to clean up the singleton client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None

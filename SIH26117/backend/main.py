"""AEGIS-WB — FastAPI application entry point.
M3 owns this file. It must be < 60 lines: mount routers only, no logic."""
from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.error_handler import aegis_error_handler
from backend.core.exceptions import AegisError
from backend.core.logging import setup_logging
from backend.api.v1 import (
    attachments_router,
    auth_router,
    documents_router,
    chat_router,
    chat_stream_router,
    audit_router,
    layouts_router,
    health_router,
    deliverables_router,
    insights_router,
)

setup_logging()
settings = get_settings()
logger = structlog.get_logger()


async def _warmup_models() -> None:
    """Preload the text and vision models so the first chat/analyze call is fast."""
    try:
        from backend.services.llm.ollama_client import OllamaClient

        client = OllamaClient(settings)
        for model in (settings.llm_model, settings.vision_model):
            try:
                await client.chat(
                    [{"role": "user", "content": "Reply with the single word: ready"}],
                    model=model,
                    max_tokens=8,
                )
                logger.info("model_warmed_up", model=model)
            except Exception as exc:  # noqa: BLE001
                logger.warning("model_warmup_failed", model=model, error=str(exc))
                return
        await client.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("warmup_step_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from backend.services.rag.migrations.create_collection import run_migrations

        await run_migrations()
    except Exception as exc:
        logger.error("qdrant_migration_failed", error=str(exc))
    task = asyncio.create_task(_warmup_models())
    yield
    task.cancel()
    from backend.services.llm.ollama_client import close_singleton

    await close_singleton()


app = FastAPI(
    title="AEGIS-WB",
    version="1.0.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    lifespan=lifespan,
)

app.add_exception_handler(AegisError, aegis_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info("request", method=request.method, path=request.url.path, ms=elapsed_ms)
    return response


app.include_router(attachments_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(chat_stream_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(deliverables_router, prefix="/api/v1")
app.include_router(layouts_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(health_router)

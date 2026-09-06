from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from backend.core.exceptions import AegisError
from backend.core.config import get_settings

import uuid
import structlog

logger = structlog.get_logger()


async def aegis_error_handler(request: Request, exc: AegisError) -> Response:
    """Maps AegisError to RFC 9457 problem+json."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    body: dict[str, Any] = {
        "type": f"/errors/{exc.code}",
        "title": exc.code.replace("_", " ").title(),
        "status": exc.status,
        "detail": exc.detail,
        "correlation_id": correlation_id,
    }
    logger.error("aegis_error", code=exc.code, status=exc.status, correlation_id=correlation_id)
    return JSONResponse(status_code=exc.status, content=body)

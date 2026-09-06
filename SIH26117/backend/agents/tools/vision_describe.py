"""vision_describe tool — image description via Ollama vision model. M5 owns this file."""
from __future__ import annotations

import structlog
from typing import Any

from backend.core.exceptions import ToolError
from backend.services.llm.ollama_client import get_ollama_client
from backend.services.llm.prompts import VISION_CAPTION_PROMPT

logger = structlog.get_logger()

DEFAULT_PROMPT = (
    "Describe this industrial image in detail. Identify equipment, "
    "visible damage or anomalies, gauge readings, safety concerns, "
    "and environmental conditions."
)


async def vision_describe(
    image_b64: str,
    prompt: str = "",
    ocr_text: str = "",
) -> str:
    if not image_b64:
        raise ToolError("No image data provided")

    llm = get_ollama_client()
    ocr_context = f"\nOCR-extracted text from image:\n{ocr_text}" if ocr_text else ""
    full_prompt = (
        VISION_CAPTION_PROMPT.format(ocr_context=ocr_context)
        if ocr_text
        else (prompt or DEFAULT_PROMPT)
    )

    try:
        description = await llm.vision(
            prompt=full_prompt,
            images_b64=[image_b64],
            temperature=0.2,
        )
    except Exception as exc:
        raise ToolError(f"Vision model failed: {exc}") from exc

    if not description or not description.strip():
        raise ToolError("Vision model returned empty description")

    return description.strip()

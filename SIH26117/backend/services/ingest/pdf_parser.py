"""PDF parser with per-page OCR decision based on text density and alpha ratio."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import structlog

from backend.core.config import get_settings
from backend.services.llm.ollama_client import get_or_create_client

logger = structlog.get_logger()
settings = get_settings()

TEXT_DENSITY_FLOOR = 120
ALPHA_RATIO_FLOOR = 0.55
OCR_PAGE_ZOOM = 1.5

OCR_REFUSAL_MARKERS = (
    "too small",
    "unable to read",
    "cannot read",
    "can't read",
    "i can't",
    "i'm unable",
    "i am unable",
    "not able to read",
    "no text",
    "no readable text",
    "does not contain",
    "blank",
    "can't provide",
    "cannot provide",
)

OCR_BOILERPLATE_PREFIXES = (
    "here is the transcription",
    "here is the ocr",
    "here is the text",
    "transcription:",
    "transcribed text:",
    "ocr result:",
    "the text on the page reads:",
    "the document says:",
    "of course. here is",
)

OCR_PROMPT = (
    "You are performing OCR on a scanned page of an industrial document. "
    "Transcribe ALL text exactly as it appears, preserving reading order and "
    "paragraph breaks. Output only the raw transcribed text with no commentary."
)


def _clean_ocr(transcript: str) -> str:
    text = transcript.strip()
    lower = text.lower()
    for marker in OCR_REFUSAL_MARKERS:
        if marker in lower:
            return ""
    for prefix in OCR_BOILERPLATE_PREFIXES:
        if lower.startswith(prefix):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            break
    return text.strip()


@dataclass
class Element:
    kind: str
    page: int
    text: str
    bbox: list[float] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


def _alpha_ratio(text: str) -> float:
    if not text:
        return 0.0
    alpha_chars = sum(1 for c in text if c.isalpha())
    return alpha_chars / len(text)


def _bbox_to_list(bbox: fitz.Rect) -> list[float]:
    return [float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)]


def _extract_text_elements(page: fitz.Page, page_num: int) -> list[Element]:
    elements: list[Element] = []
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    for block in blocks:
        if block["type"] == 0:  # text block
            lines: list[str] = []
            bboxes: list[fitz.Rect] = []
            for line in block.get("lines", []):
                spans_text = "".join(span["text"] for span in line.get("spans", []))
                lines.append(spans_text)
                bboxes.append(line["bbox"])
            text = "\n".join(lines).strip()
            if not text:
                continue
            union = fitz.Rect()
            for b in bboxes:
                union |= fitz.Rect(b)
            elements.append(
                Element(
                    kind="TEXT",
                    page=page_num,
                    text=text,
                    bbox=_bbox_to_list(union),
                )
            )
    return elements


def _page_to_png_b64(page: fitz.Page) -> str:
    matrix = fitz.Matrix(OCR_PAGE_ZOOM, OCR_PAGE_ZOOM)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return base64.b64encode(pix.tobytes("png")).decode("ascii")


async def _ocr_page(page: fitz.Page, page_num: int) -> list[Element]:
    """OCR a low-density page via the local vision model (llava)."""
    if not settings.enable_ocr:
        return []
    try:
        image_b64 = _page_to_png_b64(page)
        transcript = await get_or_create_client().vision(
            OCR_PROMPT,
            [image_b64],
            temperature=0.0,
            max_tokens=1536,
            timeout_s=360.0,
            repeat_penalty=1.3,
            max_attempts=1,
        )
        text = _clean_ocr(transcript)
        if not text:
            logger.warning("ocr_refused_or_empty", page=page_num)
            return []
        logger.info("ocr_page_done", page=page_num, chars=len(text))
        return [Element(kind="OCR", page=page_num, text=text)]
    except Exception as exc:
        logger.warning("ocr_failed", page=page_num, error=str(exc))
        return [
            Element(
                kind="OCR_NOTE",
                page=page_num,
                text="[OCR unavailable for this page]",
            )
        ]


def _extract_tables(page: fitz.Page, page_num: int) -> list[Element]:
    """Table extraction stub — returns empty list for pdfplumber integration."""
    return []


def _extract_figures(page: fitz.Page, page_num: int) -> list[Element]:
    images = page.get_images(full=True)
    elements: list[Element] = []
    for img in images:
        xref = img[0]
        try:
            rect = page.get_image_rects(xref)
            bbox = _bbox_to_list(rect[0]) if rect else [0, 0, 0, 0]
        except Exception:
            bbox = [0, 0, 0, 0]
        elements.append(
            Element(
                kind="FIGURE",
                page=page_num,
                text=f"[figure on page {page_num}]",
                bbox=bbox,
            )
        )
    return elements


async def parse(pdf_bytes: bytes) -> list[Element]:
    """Parse a PDF into a flat list of Elements.

    Per-page OCR decision: extract text and check density + alpha ratio.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    elements: list[Element] = []

    for page_num_0 in range(len(doc)):
        page = doc[page_num_0]
        page_num = page_num_0 + 1
        raw_text = page.get_text("text")
        good_text = len(raw_text.strip()) >= TEXT_DENSITY_FLOOR
        good_alpha = _alpha_ratio(raw_text) >= ALPHA_RATIO_FLOOR

        if good_text and good_alpha:
            elements.extend(_extract_text_elements(page, page_num))
        else:
            ocr_elements = await _ocr_page(page, page_num)
            elements.extend(ocr_elements)

        elements.extend(_extract_tables(page, page_num))
        elements.extend(_extract_figures(page, page_num))

    doc.close()
    return elements

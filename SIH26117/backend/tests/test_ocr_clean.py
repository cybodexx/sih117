"""OCR transcript hygiene tests — refusal markers dropped, boilerplate stripped."""
from __future__ import annotations

from backend.services.ingest.pdf_parser import (
    OCR_BOILERPLATE_PREFIXES,
    OCR_REFUSAL_MARKERS,
    _clean_ocr,
)


def test_refusal_markers_drop_transcript() -> None:
    for marker in OCR_REFUSAL_MARKERS:
        transcript = f"Unfortunately, {marker} any text from this scanned page."
        assert _clean_ocr(transcript) == "", marker
        assert _clean_ocr(marker.upper()) == "", marker


def test_capitalised_refusal_is_caught() -> None:
    assert _clean_ocr("I Am UnAbLe To ReAd this page clearly.") == ""


def test_boilerplate_prefix_is_stripped() -> None:
    for prefix in OCR_BOILERPLATE_PREFIXES:
        body = "SECTION 3\nThis pipe is corroded."
        transcript = f"{prefix}\n{body}"
        out = _clean_ocr(transcript)
        assert out == body, (prefix, out)


def test_clean_text_passes_through() -> None:
    clean = "SECTION 3 — Corrosion found on carbon steel pipe."
    assert _clean_ocr(clean) == clean


def test_wrapping_boilerplate_without_newline_is_blank() -> None:
    assert _clean_ocr("Transcription: only a label, no body") == ""
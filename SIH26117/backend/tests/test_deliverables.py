"""Unit tests for the deliverable pipeline: kind guessing, markdown fallback
structure, and real file rendering (bytes are valid OOXML/ZIP)."""
from __future__ import annotations

import pytest

from backend.agents.tools.generate_deliverable import (
    content_from_markdown,
    guess_kind,
    normalize_content,
    render_bytes,
)


def _is_zip(payload: bytes) -> bool:
    return payload[:2] == b"PK" and len(payload) > 1000


@pytest.mark.parametrize("kind", ["word", "excel", "powerpoint"])
def test_render_bytes_produces_real_files(kind: str):
    content = {
        "title": "Approval Note",
        "sections": [
            {"heading": "Findings", "paragraphs": ["mtbf = 120 h"], "bullets": [], "rows": []}
        ],
        "rows": [["Metric", "Value"], ["Failure count", "339"]],
        "slides": [{"heading": "Findings", "bullets": ["mtbf = 120 h"]}],
    }
    payload = render_bytes(kind, content)
    assert _is_zip(payload)


def test_render_word_with_table_rows():
    content = {
        "title": "Approval Note",
        "sections": [
            {
                "heading": "Computation",
                "paragraphs": [],
                "bullets": [],
                "rows": [["Metric", "Value"], ["Mean", "12.3"], ["Sigma", "0.5"]],
            }
        ],
    }
    payload = render_bytes("word", content)
    assert _is_zip(payload)


def test_guess_kind_defaults_word():
    assert guess_kind("write an approval note") == "word"
    assert guess_kind("produce a word file") == "word"


def test_guess_kind_excel_and_powerpoint():
    assert guess_kind("create an excel spreadsheet of the results") == "excel"
    assert guess_kind("make a powerpoint presentation of the findings") == "powerpoint"


def test_normalize_content_excel_stringifies_rows():
    content = normalize_content(
        "excel", {"title": "T", "sheet": "Results", "rows": [[1, None, "x"]]}
    )
    assert content["rows"] == [["1", "", "x"]]


def test_content_from_markdown_word():
    md = "# Findings\n\nFailure events: 339.\n\n- TWF 46\n- HDF 115\n"
    out = content_from_markdown("word", "Approval Note", md)
    assert out["title"] == "Approval Note"
    assert out["sections"][0]["heading"] == "Findings"
    assert out["sections"][0]["paragraphs"][0].startswith("Failure events: 339")
    assert out["sections"][0]["bullets"] == ["TWF 46", "HDF 115"]


def test_content_from_markdown_excel():
    out = content_from_markdown("excel", "Sheet", "alpha\nbeta\n")
    assert out["rows"][0] == ["Line", "Text"]
    assert len(out["rows"]) == 3


def test_content_from_markdown_powerpoint():
    out = content_from_markdown(
        "powerpoint", "Deck", "# Findings\n\n- TWF 46\n- HDF 115\n"
    )
    assert out["title"] == "Deck"
    assert out["slides"][0]["heading"] == "Findings"
    assert out["slides"][0]["bullets"] == ["TWF 46", "HDF 115"]


def test_classifier_routes_deliverable():
    from backend.api.v1.chat_stream import _classify_intent

    intent, conf = _classify_intent("Create a word document with the approval note")
    assert intent == "DELIVERABLE"
    assert conf >= 0.9


def test_classifier_keeps_content_intents():
    from backend.api.v1.chat_stream import _classify_intent

    intent, _ = _classify_intent("How many failures happened in the data?")
    assert intent == "DATA_ANALYSIS"
    intent, _ = _classify_intent("What does the standard say about torque?")
    assert intent == "COMPLIANCE"


def test_deliverable_title_strips_command_prefix():
    from backend.api.v1.chat_stream import _deliverable_title

    assert (
        _deliverable_title("Please write an approval note as a word file")
        == "approval note"
    )
    assert _deliverable_title("generate a word file") != ""
"""Tests for the live intent router using the held-out router_cases.jsonl."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.api.v1.chat_stream import _classify_intent, _with_document_analysis_escalation

_CASES_FILE = Path(__file__).resolve().parents[2] / "data_pipeline" / "eval" / "router_cases.jsonl"

CASES = [
    json.loads(line)
    for line in _CASES_FILE.open(encoding="utf-8")
    if line.strip()
]


def test_router_accuracy_passes() -> None:
    correct = sum(1 for c in CASES if _classify_intent(c["question"])[0] == c["intent"])
    assert correct / len(CASES) >= 0.95, f"router accuracy {correct}/{len(CASES)}"


@pytest.mark.parametrize(
    "question,expected",
    [
        ("How many failure records are logged for TURBINE-04?", "DATA_ANALYSIS"),
        ("Why did TURBINE-04 trip on August 14th?", "INCIDENT"),
        ("What is the recommended bearing clearance for a steam turbine?", "DOC_QA"),
        ("What defects do you see in this photo of the bearing?", "VISION"),
        ("What safety standards govern the panels in the photos?", "COMPLIANCE"),
        ("Hello, how are you today?", "CHITCHAT"),
        ("What is the average downtime for TURBINE-01 this quarter?", "DATA_ANALYSIS"),
        ("Show me the failure frequency by machine type for Q3 2026", "DATA_ANALYSIS"),
        ("Please export the audit bundle for this facility", "PRIVILEGED"),
        ("I need to download the compliance audit export", "PRIVILEGED"),
        ("Generate an exportable bundle of the access log", "PRIVILEGED"),
    ],
)
def test_router_targeted(question: str, expected: str) -> None:
    assert _classify_intent(question)[0] == expected


@pytest.mark.parametrize(
    "question,scoped,expected",
    [
        ("What is this file?", ["doc-csv"], "DOCUMENT_ANALYSIS"),
        ("Summarize this document", ["doc-csv"], "DOCUMENT_ANALYSIS"),
        ("What is in the table?", ["doc-csv"], "DOCUMENT_ANALYSIS"),
        ("Could you explain this table?", ["doc-csv"], "DOCUMENT_ANALYSIS"),
        # No scoped document -> the escalation must not force analysis.
        ("What is this file?", None, "DOC_QA"),
        # A specific lookup on a scoped doc stays DOC_QA.
        ("What is the recommended bearing clearance for a steam turbine?", ["doc-manual"], "DOC_QA"),
    ],
)
def test_scoped_summary_escalates_to_analysis(
    question: str, scoped: list[str] | None, expected: str
) -> None:
    intent, _ = _classify_intent(question)
    escalated, _ = _with_document_analysis_escalation(question, scoped, intent, 0.72)
    assert escalated == expected
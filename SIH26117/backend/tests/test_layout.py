"""Unit tests for layout aggregation, block shape, and multi-file session scope."""
from __future__ import annotations

import pytest

from backend.api.v1.layouts import _summarize
from backend.services.ingest.doclayout import Block


@pytest.fixture
def sample_page():
    return {
        "page": 1,
        "blocks": [
            {"class": "title", "confidence": 0.9, "bbox": [0.0, 0.0, 1.0, 0.1]},
            {"class": "table", "confidence": 0.8, "bbox": [0.0, 0.1, 1.0, 0.5]},
            {"class": "figure", "confidence": 0.7, "bbox": [0.0, 0.5, 1.0, 1.0]},
        ],
    }


def test_summarize_counts_classes_and_pages(sample_page):
    summary = _summarize([sample_page, {"page": 2, "blocks": [sample_page["blocks"][1]]}])
    assert summary["block_count"] == 4
    assert summary["page_count"] == 2
    assert summary["classes"] == {"title": 1, "table": 2, "figure": 1}
    assert summary["classes"]["table"] == 2


def test_summarize_empty():
    summary = _summarize([])
    assert summary == {"classes": {}, "block_count": 0, "page_count": 0}


def test_block_to_dict_uses_class_key():
    from backend.services.ingest.doclayout import Block, to_dict

    b = Block(klass="table", confidence=0.8123, bbox=[0.1, 0.2, 0.3, 0.4])
    as_dict = to_dict(b)
    assert as_dict == {
        "class": "table",
        "confidence": 0.8123,
        "bbox": [0.1, 0.2, 0.3, 0.4],
    }


def test_session_read_exposes_document_ids():
    from datetime import datetime, timezone

    from backend.api.v1.chat import _session_to_read
    from backend.db.models.chat import ChatSessionModel

    now = datetime.now(timezone.utc)
    session = ChatSessionModel()
    session.id = "00000000-0000-0000-0000-000000000001"
    session.title = "T"
    session.document_id = None
    session.document_ids = ["a", "b", "c"]
    session.created_at = now
    session.updated_at = now
    read = _session_to_read(session)
    assert read.document_ids == ["a", "b", "c"]
    assert read.document_id is None


def test_chat_session_model_has_document_ids_column():
    from sqlalchemy import inspect

    from backend.db.models.chat import ChatSessionModel

    cols = {c.name for c in inspect(ChatSessionModel).columns}
    assert "document_ids" in cols
    assert "document_id" in cols


def test_document_layout_model_unique_page():
    from backend.db.models.layout import DocumentLayoutModel

    table = DocumentLayoutModel.__table__
    names = {c.name for c in table.columns}
    assert names >= {"document_id", "page", "blocks", "model"}
    uq_cols = set()
    for con in table.constraints:
        cols = getattr(con, "columns", None)
        if cols is not None:
            try:
                uq_cols |= {col.name for col in cols}
            except TypeError:
                uq_cols |= {col.name for col in cols.copy().values()}
    assert {"document_id", "page"} <= uq_cols


def test_summarize_unknown_class_keeps_key():
    summary = _summarize([{"page": 1, "blocks": [{"class": "mystery", "confidence": 0.5, "bbox": []}]}])
    assert summary["classes"]["mystery"] == 1
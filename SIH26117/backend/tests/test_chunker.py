"""Chunker unit tests — deterministic ids, heading paths, atomic blocks."""
from __future__ import annotations

from backend.services.ingest.chunker import DocNode, split


def _heading(text: str, level: int, page: int = 1) -> DocNode:
    return DocNode(kind="HEADING", text=text, page=page, level=level)


def _body(text: str, page: int = 1) -> DocNode:
    return DocNode(kind="TEXT", text=text, page=page)


def test_chunk_ids_are_deterministic() -> None:
    nodes = [_heading("Sec 1", 1), _body("alpha" * 120), _body("beta" * 80)]
    a = split(nodes, "doc-1", doc_title="Manual A")
    b = split(nodes, "doc-1", doc_title="Manual A")
    assert [(c.id, c.chunk_index) for c in a] == [(c.id, c.chunk_index) for c in b]


def test_chunk_ids_differ_across_documents() -> None:
    nodes = [_heading("Sec 1", 1), _body("alpha" * 120)]
    a = split(nodes, "doc-1", doc_title="Manual A")
    b = split(nodes, "doc-2", doc_title="Manual A")
    assert [(c.id, c.chunk_index) for c in a] != [(c.id, c.chunk_index) for c in b]
    assert len(a) == len(b)


def test_heading_path_is_flattened() -> None:
    nodes = [
        _heading("Section 1", 1),
        _heading("Step A", 2),
        _body("long enough body text " * 40),
    ]
    chunks = split(nodes, "doc-1", doc_title="Manual B")
    assert chunks
    body_chunk = next(c for c in chunks if "long enough" in c.text)
    assert body_chunk.heading_path == ["Section 1", "Step A"]


def test_atomic_table_stays_whole() -> None:
    nodes = [_heading("Data", 1), DocNode(kind="TABLE", text="row,val\n1,a\n" * 40, page=2)]
    chunks = split(nodes, "doc-1")
    table_chunks = [c for c in chunks if c.chunk_type == "TABLE"]
    assert table_chunks, "a TABLE node must be emitted as an atomic chunk"
    assert any("row,val" in c.text for c in table_chunks)


def test_chunks_carry_authorisation_labels() -> None:
    nodes = [_heading("Sec 1", 1), _body("plain body" * 60)]
    chunks = split(nodes, "doc-1", clearance_level=2, department="MECH")
    for c in chunks:
        assert c.clearance_level == 2
        assert c.department == "MECH"
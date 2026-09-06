"""Layout-aware semantic chunker. Respects headings and atomic blocks."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

TARGET = 512
MAX = 640
OVERLAP = 64
ATOMIC_KINDS = frozenset({"TABLE", "FIGURE", "CODE", "FORMULA", "DATA_CARD", "DATA_SLICE"})

# Namespace for deterministic chunk IDs
_UUID5_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "aegis-wb.chunker.v1")


@dataclass
class DocNode:
    kind: str
    text: str
    page: int
    level: int = 0
    bbox: list[float] = field(default_factory=list)
    heading_path: list[str] = field(default_factory=list)
    token_count: int = 0


@dataclass
class Chunk:
    id: str
    document_id: str
    chunk_index: int
    text: str
    embed_text: str
    heading_path: list[str]
    chunk_type: str
    page_start: int
    page_end: int
    bbox_union: list[float]
    token_count: int
    clearance_level: int
    department: str


def _estimate_tokens(text: str) -> int:
    return len(text.split()) * 4 // 3  # rough approximation: 1.33 tokens per word


def _bbox_union(bboxes: list[list[float]]) -> list[float]:
    if not bboxes:
        return [0, 0, 0, 0]
    x0 = min(b[0] for b in bboxes)
    y0 = min(b[1] for b in bboxes)
    x1 = max(b[2] for b in bboxes)
    y1 = max(b[3] for b in bboxes)
    return [x0, y0, x1, y1]


def _flatten_heading_path(nodes: list[DocNode]) -> list[str]:
    path: list[str] = []
    for n in nodes:
        if n.kind == "HEADING" and n.level <= 2:
            path.append(n.text.strip())
    return path


def _make_chunk_id(document_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_UUID5_NS, f"{document_id}::{chunk_index}"))


def split(nodes: list[DocNode], document_id: str, doc_title: str = "", clearance_level: int = 0, department: str = "") -> list[Chunk]:
    """Split DocNodes into semantic chunks respecting layout and atomic blocks."""
    chunks: list[Chunk] = []
    buf: list[DocNode] = []
    buf_tokens = 0
    current_heading_path: list[str] = []
    chunk_index = 0

    def flush() -> None:
        nonlocal buf, buf_tokens, chunk_index
        if not buf:
            return
        text = "\n\n".join(n.text for n in buf)
        heading_text = " › ".join(current_heading_path) if current_heading_path else ""
        embed_text = f"[{doc_title} › {heading_text}]\n{text}" if heading_text else text
        pages = sorted({n.page for n in buf})
        all_bboxes = [n.bbox for n in buf if n.bbox]

        chunks.append(
            Chunk(
                id=_make_chunk_id(document_id, chunk_index),
                document_id=document_id,
                chunk_index=chunk_index,
                text=text,
                embed_text=embed_text,
                heading_path=list(current_heading_path),
                chunk_type="TEXT",
                page_start=pages[0] if pages else 1,
                page_end=pages[-1] if pages else 1,
                bbox_union=_bbox_union(all_bboxes),
                token_count=buf_tokens,
                clearance_level=clearance_level,
                department=department,
            )
        )
        chunk_index += 1
        buf = []
        buf_tokens = 0

    for node in nodes:
        # Atomic blocks: flush buffer, emit as single chunk
        if node.kind in ATOMIC_KINDS:
            flush()
            pages = sorted({node.page})
            chunks.append(
                Chunk(
                    id=_make_chunk_id(document_id, chunk_index),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    text=node.text,
                    embed_text=node.text,
                    heading_path=list(current_heading_path),
                    chunk_type=node.kind,
                    page_start=pages[0] if pages else 1,
                    page_end=pages[-1] if pages else 1,
                    bbox_union=node.bbox if node.bbox else [0, 0, 0, 0],
                    token_count=node.token_count or _estimate_tokens(node.text),
                    clearance_level=clearance_level,
                    department=department,
                )
            )
            chunk_index += 1
            continue

        # Heading change at H1/H2: flush buffer
        if node.kind == "HEADING" and node.level <= 2:
            flush()
            # Update heading path
            if node.level == 1:
                current_heading_path = [node.text.strip()]
            elif node.level == 2:
                if len(current_heading_path) >= 1:
                    current_heading_path = [current_heading_path[0], node.text.strip()]
                else:
                    current_heading_path = [node.text.strip()]
            # Heading itself goes into buffer
            buf.append(node)
            buf_tokens += node.token_count or _estimate_tokens(node.text)
            continue

        # H3+: track but don't flush
        if node.kind == "HEADING":
            node_text = node.text.strip()
            if len(current_heading_path) >= 2:
                current_heading_path = current_heading_path[:2] + [node_text]
            else:
                current_heading_path.append(node_text)

        node_tokens = node.token_count or _estimate_tokens(node.text)
        if buf_tokens + node_tokens > MAX:
            flush()
            if buf_tokens == 0 and node_tokens <= MAX:
                # Overlap: carry tail nodes
                pass

        buf.append(node)
        buf_tokens += node_tokens

    flush()
    return chunks

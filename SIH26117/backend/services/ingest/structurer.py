"""Document structurer: builds a heading hierarchy from flat Element list."""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.services.ingest.pdf_parser import Element
from backend.services.ingest.chunker import DocNode


@dataclass
class DocTree:
    """A heading hierarchy with reading-order traversal."""
    nodes: list[DocNode] = field(default_factory=list)

    def walk_reading_order(self) -> list[DocNode]:
        """Return nodes in document reading order (already sorted on construction)."""
        return list(self.nodes)


_HEADING_KEYWORDS = frozenset({
    "chapter", "section", "part", "appendix", "introduction", "conclusion",
    "references", "summary", "overview", "background", "abstract",
})

_MULTIPLIER_PATTERNS = {"1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."}


def _detect_heading_level(text: str) -> int:
    """Heuristic heading level detection for industrial documents."""
    stripped = text.strip()
    # Roman numerals or all caps short lines
    if stripped.isupper() and len(stripped) < 80:
        return 1
    # "Chapter X", "Section X.Y" patterns
    lower = stripped.lower()
    for kw in _HEADING_KEYWORDS:
        if lower.startswith(kw):
            return 1
    # "1.2.3 Title" style
    parts = stripped.split()
    if parts and "." in parts[0]:
        dot_count = parts[0].count(".")
        if dot_count <= 3:
            return min(dot_count + 1, 3)
    # All caps lines under 60 chars
    if stripped.isupper() and len(stripped) < 60:
        return 2
    return 0  # not a heading


def build(elements: list[Element]) -> DocTree:
    """Build a DocTree from a flat list of Elements with heading hierarchy."""
    nodes: list[DocNode] = []
    heading_stack: list[str] = []

    for elem in elements:
        if elem.kind == "TEXT":
            level = _detect_heading_level(elem.text)
            if level > 0:
                # Heading detected
                heading_stack = heading_stack[:level - 1] + [elem.text.strip()]
                nodes.append(
                    DocNode(
                        kind="HEADING",
                        text=elem.text.strip(),
                        page=elem.page,
                        level=level,
                        bbox=elem.bbox,
                        heading_path=list(heading_stack),
                    )
                )
            else:
                nodes.append(
                    DocNode(
                        kind="TEXT",
                        text=elem.text,
                        page=elem.page,
                        bbox=elem.bbox,
                        heading_path=list(heading_stack),
                    )
                )
        elif elem.kind in ("TABLE", "FIGURE"):
            nodes.append(
                DocNode(
                    kind=elem.kind,
                    text=elem.text,
                    page=elem.page,
                    bbox=elem.bbox,
                    heading_path=list(heading_stack),
                )
            )
        elif elem.kind.startswith("OCR"):
            nodes.append(
                DocNode(
                    kind="OCR",
                    text=elem.text,
                    page=elem.page,
                    bbox=elem.bbox,
                    heading_path=list(heading_stack),
                )
            )
        else:
            nodes.append(
                DocNode(
                    kind=elem.kind,
                    text=elem.text,
                    page=elem.page,
                    bbox=elem.bbox,
                    heading_path=list(heading_stack),
                )
            )

    return DocTree(nodes=nodes)

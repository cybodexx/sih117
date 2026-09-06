"""check_compliance tool — compliance check scoped to safety/quality docs. M5 owns this file."""
from __future__ import annotations

import structlog
from typing import Any

from backend.core.config import get_settings
from backend.core.exceptions import ToolError

logger = structlog.get_logger()
settings = get_settings()

COMPLIANCE_DEPT = ["SAFETY", "QUALITY"]


async def check_compliance(
    query: str,
    standard: str = "",
    acl: dict | None = None,
) -> str:
    if not query.strip():
        raise ToolError("query is required for compliance check")

    if acl is None:
        acl = {"max_clearance": 3, "departments": COMPLIANCE_DEPT, "user_ctx": {}}

    scoped_acl = dict(acl)
    scoped_acl["departments"] = COMPLIANCE_DEPT

    from backend.agents.tools.vector_search import vector_search
    hits = await vector_search(
        query=query,
        acl=scoped_acl,
        k=10,
    )

    if not hits:
        return (
            f"No compliance documents found for: {query}\n"
            "Recommendation: Verify that relevant standards have been uploaded "
            "to the SAFETY or QUALITY department."
        )

    results: list[str] = []
    for i, hit in enumerate(hits):
        pl = hit.get("payload", {})
        text = pl.get("text", pl.get("content", ""))
        doc_title = pl.get("document_title", pl.get("title", "Unknown"))
        page = pl.get("page_start", "?")
        score = hit.get("rrf_score", hit.get("score", 0.0))

        results.append(
            f"[{i+1}] ({doc_title}, p.{page}) score={score:.3f}\n{text[:500]}"
        )

    header = f"Compliance search results for: {query}"
    if standard:
        header += f"\nChecking against standard: {standard}"

    return header + "\n\n" + "\n\n---\n\n".join(results)

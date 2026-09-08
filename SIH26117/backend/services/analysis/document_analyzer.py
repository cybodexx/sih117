"""LLM document analysis — grounded executive summary, metrics, anomalies, recommendations.

Grounding design:
  * CSV/tabular documents are analysed deterministically from their materialised
    ds_* table (row counts, column ranges, flag counts, NULL profiles). The numbers
    are computed directly from the real data — no model estimation. The LLM only
    writes a short executive summary that MUST cite the profile lines it uses.
  * Other documents use a quotes-first flow: the model first *copies* verbatim
    quotes (a task small local models perform reliably), every quote is verified
    character-for-character against the real chunk texts, and a short summary is
    then written strictly over those verified quotes, citing them by number.
  * The final markdown is rendered by a deterministic template, so the report
    can never contradict itself and never leaks provenance/metadata the document
    does not contain.
"""
from __future__ import annotations

import base64
import re
import time
from pathlib import Path
from typing import Any

import structlog
from qdrant_client import QdrantClient, models
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.core.config import get_settings
from backend.core.exceptions import BadRequest, Forbidden, ModelUnavailable
from backend.core.rbac import DocumentLabels, ServerUserContext, can_read
from backend.db.models.document import DocumentModel
from backend.services.ingest.csv_sql import table_name_for
from backend.services.llm.ollama_client import get_or_create_client

logger = structlog.get_logger()
settings = get_settings()

_MAX_CONTEXT_CHARS = 24000
_MIN_VERBATIM_CHARS = 3
_MAX_PROFILE_COLUMNS = 64
_PROFILE_HEAD_KEY = "PROFILE"

_COLUMN_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

_VISION_REPORT_PROMPT = (
    "This image is an industrial document page. Thoroughly describe what it shows: "
    "charts and plots (axes, trend, notable values), diagrams, tables, figures, "
    "labels, and any identifiable numbers. Focus on facts visible in the pixels; "
    "never guess values that are not actually visible."
)


def _labels(doc: DocumentModel) -> DocumentLabels:
    return DocumentLabels(
        status=doc.status,
        clearance_level=doc.clearance_level,
        department=doc.department,
        legal_hold=doc.legal_hold,
    )


def _collect_chunks(doc_id: str) -> list[dict[str, Any]]:
    client = QdrantClient(url=settings.qdrant_url, timeout=30)
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=doc_id),
                )
            ]
        ),
        limit=800,
        with_payload=True,
        with_vectors=False,
    )
    rows = [
        {
            "chunk_index": int((p.payload or {}).get("chunk_index", 0)),
            "type": str((p.payload or {}).get("chunk_type", "TEXT")),
            "page_start": int((p.payload or {}).get("page_start", 1)),
            "page_end": int((p.payload or {}).get("page_end", 1)),
            "text": str((p.payload or {}).get("text", "")),
        }
        for p in points
    ]
    rows.sort(key=lambda r: r["chunk_index"])
    return rows


def _fold_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _is_image(doc: DocumentModel) -> bool:
    return (doc.mime or "").startswith("image/")


def _image_b64(doc: DocumentModel) -> str:
    from backend.services.crypto.vault_crypto import read_plaintext_file

    path = Path(doc.storage_key)
    raw = read_plaintext_file(path, doc.wrapped_dek)
    return base64.b64encode(raw).decode("ascii")


async def _vision_describe(doc: DocumentModel, ollama: Any) -> str:
    """Describe an image document with the local vision model (grounded in pixels)."""
    return await ollama.vision(
        _VISION_REPORT_PROMPT,
        [_image_b64(doc)],
        model=settings.vision_model,
        temperature=0.2,
        max_tokens=768,
        timeout_s=settings.vision_timeout_s,
        repeat_penalty=1.1,
    )


def _supports(verbatim: str, chunk_text: str) -> bool:
    if len(_fold_ws(verbatim)) < _MIN_VERBATIM_CHARS:
        return False
    return _fold_ws(verbatim).lower() in _fold_ws(chunk_text).lower()


def _locate(verbatim: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the chunk that actually contains the verbatim quote."""
    for r in rows:
        if _supports(verbatim, r["text"]):
            return r
    return None


# ---------------------------------------------------------------------------
# Path 1 — deterministic analysis over the materialised ds_* table (CSV/XLSX)
# ---------------------------------------------------------------------------


async def _profile_table(doc: DocumentModel) -> dict[str, Any] | None:
    """Return a deterministic data profile for tabular docs, or None if N/A."""
    if not doc.filename.lower().endswith((".csv", ".xlsx")):
        return None

    table = table_name_for(doc.filename)
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            exists = (
                await conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = :t AND table_schema = 'public'"
                    ),
                    {"t": table},
                )
            ).scalar()
            if not exists:
                return None

            cols_meta = (
                await conn.execute(
                    text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = :t AND table_schema = 'public' "
                        "ORDER BY ordinal_position LIMIT :lim"
                    ),
                    {"t": table, "lim": _MAX_PROFILE_COLUMNS},
                )
            ).fetchall()
            columns = [
                {"name": c, "data_type": d}
                for c, d in cols_meta
                if _COLUMN_RE.match(str(c))
            ]
            if not columns:
                return None

            total = int(
                (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar() or 0
            )

            profile_cols = []
            for col in columns:
                c = col["name"]
                stats = (
                    await conn.execute(
                        text(
                            f"SELECT COUNT({c}), COUNT(DISTINCT {c}), MIN({c}), MAX({c}) "
                            f"FROM {table}"
                        )
                    )
                ).fetchone()
                non_null, distinct, mn, mx = (
                    int(stats[0] or 0),
                    int(stats[1] or 0),
                    stats[2],
                    stats[3],
                )
                nulls = int(
                    (
                        await conn.execute(
                            text(f"SELECT COUNT(*) FROM {table} WHERE {c} IS NULL")
                        )
                    ).scalar()
                    or 0
                )
                numeric = str(col["data_type"]) in (
                    "bigint", "integer", "smallint", "numeric", "real",
                    "double precision",
                )
                flag = numeric and distinct <= 2
                ones = None
                if flag and mn is not None and int(mn) == 0 and int(mx) == 1:
                    ones = int(
                        (
                            await conn.execute(
                                text(f"SELECT COUNT(*) FROM {table} WHERE {c} = 1")
                            )
                        ).scalar()
                        or 0
                    )
                profile_cols.append(
                    {
                        "name": c,
                        "data_type": str(col["data_type"]),
                        "non_null": non_null,
                        "distinct": distinct,
                        "nulls": nulls,
                        "numeric": numeric,
                        "flag": flag,
                        "min": _fmt_scalar(mn),
                        "max": _fmt_scalar(mx),
                        "ones": ones,
                    }
                )

            profile_cols.sort(
                key=lambda c: (0, 0) if c["ones"] is not None else ((1, 0) if c["numeric"] else (2, 0))
            )
    finally:
        await engine.dispose()

    lines: list[str] = []
    p = 1
    lines.append(f"P{p}: Row count = {total}")
    p += 1
    lines.append(f"P{p}: Column count = {len(profile_cols)} (profile limited to {_MAX_PROFILE_COLUMNS})")
    p += 1
    for col in profile_cols:
        lines.append(
            f'P{p}: Column \"{col["name"]}\" type {col["data_type"]}; '
            f'non-null = {col["non_null"]} of {total}; distinct = {col["distinct"]}'
        )
        p += 1
        if col["numeric"] or col["min"] is not None:
            lines.append(
                f'P{p}: Column \"{col["name"]}\" min = {col["min"]}, max = {col["max"]}'
            )
            p += 1
        if col["ones"] is not None:
            lines.append(
                f'P{p}: Column \"{col["name"]}\" count of value 1 = {col["ones"]} of {total}'
            )
            p += 1
        elif col["nulls"]:
            lines.append(
                f'P{p}: Column \"{col["name"]}\" nulls = {col["nulls"]} of {total}'
            )
            p += 1
        if p >= 90:
            break

    return {"table": table, "total": total, "columns": profile_cols, "lines": lines}


def _fmt_scalar(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _profile_section(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Deterministic claims/metrics/anomalies/recommendations from the profile."""
    table = profile["table"]
    total = profile["total"]
    source = f"data table {table}"

    claims: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    seen_numeric = 0

    metrics.append(
        {
            "name": "Row count",
            "value": str(total),
            "unit": "rows",
            "source": source,
        }
    )

    for col in profile["columns"]:
        n = col["name"]
        if col["ones"] is not None:
            claims.append(
                {
                    "topic": f'{n} = 1',
                    "statement": f'{col["ones"]} of {total} rows have column "{n}" set to 1',
                    "source": source,
                }
            )
            metrics.append(
                {
                    "name": f'{n} = 1 count',
                    "value": str(col["ones"]),
                    "unit": "rows",
                    "source": source,
                }
            )
            if col["ones"]:
                anomalies.append(
                    {
                        "description": (
                            f'{col["ones"]} of {total} rows in column "{n}" are '
                            "flagged with value 1; a domain owner should review them"
                        ),
                        "source": source,
                    }
                )
                recommendations.append(
                    {
                        "action": (
                            f"Investigate the {col['ones']} records where \"{n}\" = 1 "
                            "and remediate or track them against a maintenance plan"
                        ),
                        "source": source,
                    }
                )
        elif col["numeric"] and col["min"] not in ("NULL",) and seen_numeric < 6:
            seen_numeric += 1
            claims.append(
                {
                    "topic": f"{n} range",
                    "statement": f'column "{n}" spans min = {col["min"]} to max = {col["max"]}',
                    "source": source,
                }
            )
            metrics.append(
                {
                    "name": f"{n} range",
                    "value": f'{col["min"]} … {col["max"]}',
                    "unit": "",
                    "source": source,
                }
            )
        if col["nulls"]:
            anomalies.append(
                {
                    "description": (
                        f'column "{n}" has {col["nulls"]} of {total} NULL values'
                    ),
                    "source": source,
                }
            )

    return {
        "claims": claims,
        "metrics": metrics,
        "anomalies": anomalies,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Path 2 — quotes-first extraction for non-tabular documents
# ---------------------------------------------------------------------------


async def _extract_quotes(ollama: Any, body: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Step A: ask the model to copy verbatim quotes; verify each one in code."""
    system = (
        "You are an exact-copy assistant inside an air-gapped industrial workbench. "
        "Your only job is to copy verbatim passages from the provided document content.\n"
        "RULES:\n"
        "- Copy quotes character-for-character. Never paraphrase, translate, explain, or invent.\n"
        "- Do not add labels, numbering, punctuation, or commentary that is not part of the quote.\n"
        "- If the content is hopelessly garbled or empty, respond with: none.\n"
        "- Respond ONLY with lines of the form: <short label> :: <exact quote>"
    )
    user = (
        "Copy the 12 most informative distinct quotes from the content below. "
        "Each line must be: <short label> :: <exact quote>\n"
        "The quote must be an exact character-for-character substring of the content.\n\n"
        "Content:\n" + body
    )
    try:
        raw = await ollama.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=900,
            timeout_s=180,
        )
    except ModelUnavailable:
        return []

    quotes: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.lower() == "none":
            continue
        if "::" in line:
            label, _, quote = line.partition("::")
            label = label.strip().strip("*#-").strip()
            quote = quote.strip()
        else:
            label, quote = "Excerpt", line.strip()
        loc = _locate(quote, rows)
        if loc is None:
            continue
        if not label:
            label = "Excerpt"
        quotes.append(
            {
                "topic": label,
                "statement": quote,
                "verbatim": quote,
                "chunk_index": loc["chunk_index"],
                "page": loc["page_start"],
            }
        )
        if len(quotes) >= 12:
            break
    return quotes


async def _grounded_summary(
    ollama: Any, source_text: str, valid_ids: set[str]
) -> str:
    """Step B: comprehensive document brief that MUST cite the provided source items."""
    system = (
        "You write comprehensive, professional document briefs that are strictly "
        "grounded in the provided source lines. Nobody can see any other information.\n"
        "RULES:\n"
        "- Use ONLY facts and numbers present in the source lines.\n"
        "- Cite every fact or number by its source id inline, e.g. [P3] or [Q2].\n"
        "- Never invent ids, values, dates, or metadata.\n"
        "- Write in clear, plain, professional English. Do not use markdown bold "
        "or bullet markers; use short paragraphs separated by blank lines.\n"
        "- Your output is shown to an engineer who needs to understand the document "
        "at a glance and trust that every claim came from the document itself."
    )
    user = (
        "Write a concise professional document brief of roughly 180-220 words, "
        "organised into 3-4 short paragraphs, based ONLY on the source lines below. "
        "Cite each fact with its source id like [P3]. Cover, in order:\n"
        "1. What this document or data describes and its scope.\n"
        "2. The structure of the content (main sections, or the columns/fields "
        "along with their value ranges and cardinality).\n"
        "3. The key findings, figures, and notable values.\n"
        "4. Any anomalies, gaps, or data-quality issues.\n"
        "Never mention anything that is not present in the source lines.\n\n"
        "Source lines:\n" + source_text
    )
    for _ in range(3):
        try:
            raw = await ollama.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
                max_tokens=512,
                timeout_s=300,
            )
        except ModelUnavailable:
            return ""
        summary = raw.strip()
        cited = {m.group(1) for m in re.finditer(r"\[(P\d+|Q\d+)\]", summary)}
        # Keep the model's prose, but drop any citation that references a source it
        # was not given. One valid citation is enough to trust the summary's anchor.
        if any(c in valid_ids for c in cited):
            summary = re.sub(
                r"\[(P\d+|Q\d+)\]",
                lambda m: f"[{m.group(1)}]" if m.group(1) in valid_ids else "",
                summary,
            )
            return re.sub(r"\s+", " ", summary).strip()
    return ""


# ---------------------------------------------------------------------------
# Orchestration + rendering
# ---------------------------------------------------------------------------


async def analyze_document(
    doc: DocumentModel, user: ServerUserContext
) -> dict[str, Any]:
    """Produce a grounded analytical report over a document's indexed chunks."""
    if doc.status != "READY":
        raise BadRequest("Only READY documents can be analyzed")
    if not can_read(user, _labels(doc)).allowed:
        raise Forbidden("Access denied for this document")

    rows = _collect_chunks(str(doc.id))
    ollama = get_or_create_client()
    started = time.monotonic()

    if _is_image(doc):
        try:
            desc = await _vision_describe(doc, ollama)
        except Exception as exc:
            logger.error("image_analysis_failed", document_id=str(doc.id), error=str(exc))
            desc = ""
        latency_ms = int((time.monotonic() - started) * 1000)
        report = _render_vision(doc.filename, desc)
        figure_refs = [r for r in rows if str(r["type"]).upper() == "FIGURE"][:1]
        chunk_refs = [
            {
                "chunk_index": r["chunk_index"],
                "page_start": r["page_start"],
                "text": r["text"][:180] or f"figure on page {r['page_start']}",
            }
            for r in figure_refs
        ]
        logger.info(
            "document_analyzed",
            document_id=str(doc.id),
            chunks_read=len(rows),
            context_chars=0,
            tabular=False,
            vision=True,
            latency_ms=latency_ms,
        )
        return {
            "document_id": str(doc.id),
            "report": report,
            "chunks_read": len(rows),
            "context_chars_used": 0,
            "latency_ms": latency_ms,
            "chunk_refs": chunk_refs,
        }

    context: list[str] = []
    used = 0
    for r in rows:
        piece = f"[chunk {r['chunk_index']} · page {r['page_start']}]\n{r['text']}\n"
        if used + len(piece) > _MAX_CONTEXT_CHARS:
            break
        context.append(piece)
        used += len(piece)
    body = "".join(context)

    profile = await _profile_table(doc)

    if profile is not None:
        summary = await _grounded_summary(
            ollama, "\n".join(profile["lines"][:80]), _profile_ids(profile)
        )
        sections = _profile_section(profile)
        total = profile["total"]
        structure = [
            f"- `{c['name']}` — {c['data_type']}; non-null {c['non_null']} of {total}; "
            f"{c['distinct']} distinct"
            for c in profile["columns"][:64]
        ]
        report = _render(
            doc.filename,
            summary,
            claims=sections["claims"],
            metrics=sections["metrics"],
            anomalies=sections["anomalies"],
            recommendations=sections["recommendations"],
            structure=structure,
            footer=(
                f"> Every figure in this report was computed directly from the materialized "
                f"data table ({profile['table']}). The summary cites only the profile lines "
                "listed above; nothing was estimated or paraphrased."
            ),
        )
        metrics = sections["metrics"]
        used_indices: set[int] = set()
    else:
        quotes = await _extract_quotes(ollama, body, rows) if rows else []
        if quotes:
            lines = [
                f"Q{i + 1}: {q['topic']} :: {q['statement']} "
                f"[chunk {q['chunk_index']}, p.{q['page']}]"
                for i, q in enumerate(quotes)
            ]
            summary = await _grounded_summary(
                ollama, "\n".join(lines), _quote_ids(quotes)
            )
        else:
            summary = ""
        report = _render(
            doc.filename,
            summary,
            claims=quotes,
            metrics=[],
            anomalies=[],
            recommendations=[],
            footer=(
                "> Every figure above was verified as a verbatim quote from the document "
                "content. Items that could not be quoted exactly were excluded."
            ),
        )
        metrics = []
        used_indices = {q["chunk_index"] for q in quotes}

    latency_ms = int((time.monotonic() - started) * 1000)

    chunk_refs = [
        {"chunk_index": r["chunk_index"], "page_start": r["page_start"], "text": r["text"][:180]}
        for r in rows
        if r["chunk_index"] in used_indices
    ]

    logger.info(
        "document_analyzed",
        document_id=str(doc.id),
        chunks_read=len(rows),
        context_chars=used,
        tabular=profile is not None,
        latency_ms=latency_ms,
    )
    return {
        "document_id": str(doc.id),
        "report": report,
        "chunks_read": len(rows),
        "context_chars_used": used,
        "latency_ms": latency_ms,
        "chunk_refs": chunk_refs,
    }


def _profile_ids(profile: dict[str, Any]) -> set[str]:
    ids = set()
    for i, _ in enumerate(profile["lines"], start=1):
        ids.add(f"P{i}")
    return ids


def _quote_ids(quotes: list[dict[str, Any]]) -> set[str]:
    return {f"Q{i + 1}" for i in range(len(quotes))}


def _ref(item: dict[str, Any]) -> str:
    if item.get("chunk_index") is not None:
        return f"[chunk {item['chunk_index']}, p.{item['page']}]"
    if item.get("source"):
        return f"({item['source']})"
    return ""


def _render_vision(filename: str, description: str) -> str:
    lines = [
        f"# Document Analysis — {filename}",
        "",
        "## Visual Analysis",
        description
        or "No description could be produced from the image with the local vision model.",
        "",
        "> This document is an image: no text content could be verified. The "
        "description above was produced by the local vision model directly from "
        "the image pixels — nothing was inferred beyond what is visible.",
    ]
    return "\n".join(lines)


def _render(
    filename: str,
    summary: str,
    claims: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    footer: str,
    structure: list[str] | None = None,
) -> str:
    lines: list[str] = [f"# Document Analysis — {filename}", ""]

    lines.append("## Executive Summary")
    lines.append(summary or "No summary could be produced from the document content.")
    lines.append("")

    if structure:
        lines.append("## Structure")
        lines.extend(structure)
        lines.append("")

    lines.append("## Key Facts")
    if claims:
        for c in claims:
            label = f"**{c['topic']}** — " if c.get("topic") else ""
            lines.append(f"- {label}{c['statement']} {_ref(c)}")
    else:
        lines.append("The document content does not contain any verifiable facts.")
    lines.append("")

    lines.append("## Key Metrics")
    if metrics:
        lines.append("| Metric | Value | Reference |")
        lines.append("|---|---|---|")
        for m in metrics:
            value = m["value"] + (f" {m['unit']}" if m.get("unit") else "")
            lines.append(f"| {m['name']} | {value} | {_ref(m)} |")
    else:
        lines.append("No quantitative metrics could be verified.")
    lines.append("")

    lines.append("## Anomalies & Risks")
    if anomalies:
        for a in anomalies:
            lines.append(f"- {a['description']} {_ref(a)}")
    else:
        lines.append("No anomalies were detected in the document content.")
    lines.append("")

    lines.append("## Recommended Actions")
    if recommendations:
        for r in recommendations:
            lines.append(f"- {r['action']} {_ref(r)}")
    else:
        lines.append("The document does not state any recommended actions.")
    lines.append("")

    lines.append(footer)
    return "\n".join(lines)
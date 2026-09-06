"""CSV -> Postgres materializer for data-analytics tables (ds_*).

Uploaded CSV documents are chunked for RAG AND materialised as real relational
tables so the sql_query tool can answer data questions with real numbers rather
than stubs. Table names are derived from the sanitised filename.

Safety:
  - Table name is derived from the document filename and strictly validated.
  - Every header is sanitised to [a-z0-9_] before becoming a column identifier.
  - Values are typed per-column (INTEGER / DOUBLE PRECISION / TIMESTAMPTZ / TEXT).
  - Non-ISO day-first timestamps (e.g. "04-05-2026 06:44") are normalised to ISO
    so SQL comparisons and aggregation are accurate.
"""
from __future__ import annotations

import csv
import io
import re
import structlog
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, Double, MetaData, Table, Text, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.core.config import get_settings
from backend.core.exceptions import ToolError

logger = structlog.get_logger()
settings = get_settings()

_TABLE_RE = re.compile(r"^ds_[a-z0-9_]{1,63}$")
_COLUMN_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
_DAY_FIRST = ("%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y")


def table_name_for(filename: str) -> str:
    """Sanitise a CSV filename into a safe ds_* table name."""
    stem = re.sub(r"\.csv$", "", filename.lower())
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    slug = f"ds_{stem}" if stem else "ds_unnamed_table"
    if not _TABLE_RE.match(slug):
        raise ToolError(f"Invalid table name derived from filename: {filename!r}")
    return slug


def _sanitise_column(header: str) -> str:
    col = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_") or "col"
    if re.match(r"^\d", col):
        col = f"c_{col}"
    if not _COLUMN_RE.match(col):
        raise ToolError(f"Invalid CSV column header: {header!r}")
    return col


def _parse_timestamp(value: str) -> datetime | None:
    for fmt in _DAY_FIRST + ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _type_for(values: list[str]) -> tuple[str, callable]:
    """Infer a column type from observed non-empty values."""
    present = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not present:
        return "TEXT", lambda v: v

    if all(_INT_RE.match(v) for v in present):
        return "BIGINT", int

    if all(_FLOAT_RE.match(v) for v in present):
        return "DOUBLE PRECISION", float

    parsed = [_parse_timestamp(v) for v in present]
    if all(p is not None for p in parsed):
        return "TIMESTAMPTZ", lambda v: _parse_timestamp(str(v).strip())

    return "TEXT", lambda v: v


async def materialize_csv(filename: str, raw: bytes, document_id: str | None = None) -> dict[str, object]:
    """Create/replace the ds_* table for a CSV document, returning table metadata."""
    text_data = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text_data))
    if not reader.fieldnames:
        raise ToolError(f"CSV has no header row: {filename!r}")

    columns = [_sanitise_column(h) for h in reader.fieldnames]
    if len(set(columns)) != len(columns):
        raise ToolError(f"Duplicate column names after sanitisation: {filename!r}")

    rows: list[dict[str, Any]] = []
    for record in reader:
        rows.append({col: (record.get(orig) or "").strip() for col, orig in zip(columns, reader.fieldnames)})

    if not rows:
        raise ToolError(f"CSV has no data rows: {filename!r}")

    types: list[str] = []
    converters: list[callable] = []
    for col, orig in zip(columns, reader.fieldnames):
        cell = lambda rec, k=orig: (rec.get(k) or "").strip()
        ctype, conv = _type_for([cell(r) for r in rows])
        types.append(ctype)
        converters.append(conv)

    table = table_name_for(filename)
    engine = _pg_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            col_defs = ", ".join(f"{c} {t}" for c, t in zip(columns, types))
            await conn.execute(text(f"CREATE TABLE {table} ({col_defs})"))

            meta = MetaData()
            tbl = Table(
                table,
                meta,
                *[Column(c, _sa_type(t)) for c, t in zip(columns, types)],
                extend_existing=True,
            )
            payload = [
                {col: (conv(row.get(col)) if row.get(col) else None)
                 for col, conv in zip(columns, converters)}
                for row in rows
            ]
            insert = pg_insert(tbl)
            for i in range(0, len(payload), 1000):
                await conn.execute(insert, payload[i : i + 1000])
    finally:
        await engine.dispose()

    logger.info(
        "csv_table_materialised",
        table=table,
        rows=len(rows),
        document_id=document_id,
    )
    return {"table": table, "rows": len(rows), "columns": columns}


def _sa_type(sql_name: str):
    if sql_name == "BIGINT":
        return BigInteger
    if sql_name == "DOUBLE PRECISION":
        return Double
    if sql_name == "TIMESTAMPTZ":
        return DateTime(timezone=True)
    return Text


def _pg_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    return create_async_engine(settings.database_url)
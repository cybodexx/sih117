"""Deterministic auto-insights for tabular documents (materialised ds_* tables).

Builds chart-ready JSON (line / bar / pie / histogram) computed entirely from
the real data table with SQL — no LLM involved. Every number a chart or stat
shows is an actual value from the ingested data.

Charts emitted, in order (each only when the data supports it):
  1. pie    — distribution of the first 0/1 flag column (e.g. failure flags)
  2. bar    — top-N frequency of up to 2 low-cardinality columns
  3. line   — time series (first timestamp column vs. avg of first numeric col)
  4. bar    — mean of up to 10 numeric columns (column overview)
"""
from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.core.config import get_settings
from backend.db.models.document import DocumentModel
from backend.services.ingest.csv_sql import table_name_for

logger = structlog.get_logger()
settings = get_settings()

_COLUMN_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_NUMERIC_TYPES = (
    "bigint", "integer", "smallint", "numeric", "real", "double precision",
)
_FLAG_LIKE = {"0", "1"}
_MAX_COLUMNS = 48
_MAX_CATEGORIES = 12
_MAX_TIME_BUCKETS = 60
_MAX_NUMERIC_BARS = 10
_MAX_FREQ_COLS = 2
_NULL_SCAN_LIMIT = 25000


async def build_insights(doc: DocumentModel) -> dict[str, Any] | None:
    """Return the auto-insights payload for a tabular doc, else None (non-tabular)."""
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

            total = int(
                (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar() or 0
            )
            if total <= 0:
                return None

            cols_meta = (
                await conn.execute(
                    text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = :t AND table_schema = 'public' "
                        "ORDER BY ordinal_position LIMIT :lim"
                    ),
                    {"t": table, "lim": _MAX_COLUMNS},
                )
            ).fetchall()
            columns = [
                {"name": str(c), "data_type": str(d), "numeric": str(d) in _NUMERIC_TYPES}
                for c, d in cols_meta
                if _COLUMN_RE.match(str(c))
            ]
            if not columns:
                return None

            numeric_cols = [c for c in columns if c["numeric"]]
            time_col = next(
                (c for c in columns
                 if c["data_type"] in ("timestamptz", "timestamp", "date")),
                None,
            )
            charts: list[dict[str, Any]] = []
            stats: list[dict[str, Any]] = []

            # --- 1. flag column distribution (pie) ---------------------------------
            flag_col = await _find_flag_column(conn, table, columns, total)
            if flag_col is not None:
                ones = int(
                    (
                        await conn.execute(
                            text(f"SELECT COUNT(*) FROM {table} WHERE {flag_col} = 1")
                        )
                    ).scalar()
                    or 0
                )
                charts.append(_flag_pie(flag_col, ones, total))

            # --- 2. top-N frequency for low-cardinality columns (bar) ---------------
            freq_cols = await _find_frequency_columns(conn, table, columns, total)
            for fc in freq_cols[:_MAX_FREQ_COLS]:
                rows = (
                    await conn.execute(
                        text(
                            f"SELECT {fc} AS v, COUNT(*) AS n FROM {table} "
                            f"WHERE {fc} IS NOT NULL GROUP BY {fc} "
                            f"ORDER BY n DESC LIMIT {_MAX_CATEGORIES}"
                        )
                    )
                ).fetchall()
                chart = _freq_bar(fc, rows)
                if chart is not None:
                    charts.append(chart)
                    stats.append(
                        {
                            "name": f"distinct \"{fc}\"",
                            "value": len(chart["categories"]),
                            "kind": "text",
                        }
                    )

            # --- 3. time series (line) ----------------------------------------------
            if time_col is not None and numeric_cols:
                target_col = numeric_cols[0]["name"]
                ts = await _build_timeseries(conn, table, time_col["name"], target_col)
                line_chart = _time_line(target_col, ts["x"], ts["y"]) if ts else None
                if line_chart is not None:
                    charts.append(line_chart)

            # --- 4. numeric column overview (bar of means) --------------------------
            if numeric_cols:
                means = await _column_means(conn, table, numeric_cols)
                mean_chart = _means_bar(means)
                if mean_chart is not None:
                    charts.append(mean_chart)

            # --- per-column stats ---------------------------------------------------
            ranged_cols = numeric_cols[: _MAX_NUMERIC_BARS]
            for c in ranged_cols:
                col = c["name"]
                agg = (
                    await conn.execute(
                        text(
                            f"SELECT MIN({col}), MAX({col}), AVG({col}), "
                            f"STDDEV({col}) FROM {table}"
                        )
                    )
                ).fetchone()
                mn, mx, avg, sd = agg
                stats.append(
                    {
                        "name": f"\"{col}\"",
                        "value": f"min={_num(mn)} max={_num(mx)} "
                        f"avg={_num(avg)} sd={_num(sd)}",
                        "kind": "numeric",
                    }
                )

            if not charts and not stats:
                return None

            return {
                "table": table,
                "filename": doc.filename,
                "rows": total,
                "columns": columns,
                "charts": charts,
                "stats": stats,
            }
    finally:
        await engine.dispose()


async def _find_flag_column(conn, table: str, columns: list[dict], total: int) -> str | None:
    for c in columns:
        if not c["numeric"]:
            continue
        name = c["name"]
        row = (
            await conn.execute(
                text(f"SELECT MIN({name}), MAX({name}), COUNT(DISTINCT {name}) FROM {table}")
            )
        ).fetchone()
        mn, mx, distinct = row
        if distinct is not None and int(distinct) <= 2 and \
                {str(_num(mn)), str(_num(mx))} <= _FLAG_LIKE:
            return name
    return None


async def _find_frequency_columns(conn, table: str, columns: list[dict], total: int) -> list[str]:
    out: list[str] = []
    for c in columns:
        if len(out) >= _MAX_FREQ_COLS:
            break
        if c["numeric"]:
            continue
        name = c["name"]
        distinct = int(
            (
                await conn.execute(text(f"SELECT COUNT(DISTINCT {name}) FROM {table}"))
            ).scalar()
            or 0
        )
        if 2 <= distinct <= _MAX_CATEGORIES:
            out.append(name)
    return out


async def _build_timeseries(conn, table: str, time_col: str, num_col: str) -> dict[str, Any] | None:
    rows = (
        await conn.execute(
            text(
                f"SELECT date_trunc('day', {time_col}) AS bucket, "
                f"AVG({num_col}) AS avg_v "
                f"FROM {table} WHERE {time_col} IS NOT NULL AND {num_col} IS NOT NULL "
                f"GROUP BY bucket ORDER BY bucket LIMIT {_MAX_TIME_BUCKETS}"
            )
        )
    ).fetchall()
    if not rows:
        return None
    x = [str(r[0])[:10] for r in rows]
    y = [round(float(r[1]), 3) if r[1] is not None else None for r in rows]
    if len(x) < 2 or all(v is None for v in y):
        return None
    return {"x": x, "y": y}


async def _column_means(conn, table: str, numeric_cols: list[dict]) -> dict[str, Any] | None:
    cols = numeric_cols[:_MAX_NUMERIC_BARS]
    targets = [c["name"] for c in cols]
    select_sql = ", ".join(f"AVG({c}) AS m_{i}" for i, c in enumerate(targets))
    row = (await conn.execute(text(f"SELECT {select_sql} FROM {table}"))).fetchone()
    values = [round(float(v), 3) if v is not None else None for v in row]
    if any(v is not None for v in values) and len(targets) >= 1:
        return {
            "categories": targets,
            "values": values,
        }
    return None


def _num(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _flag_pie(flag_col: str, ones: int, total: int) -> dict[str, Any]:
    return {
        "type": "pie",
        "title": f'"{flag_col}" = 1 share',
        "items": [
            {"name": f"{flag_col} = 1", "value": ones},
            {"name": f"{flag_col} = 0", "value": total - ones},
        ],
    }


def _freq_bar(fc: str, rows: list[tuple]) -> dict[str, Any] | None:
    categories = [str(r[0]) for r in rows]
    values = [int(r[1]) for r in rows]
    if len(categories) < 2 or not all(values):
        return None
    return {
        "type": "bar",
        "title": f"Top categories of \"{fc}\"",
        "categories": categories,
        "series": [{"name": "rows", "data": values}],
    }


def _time_line(num_col: str, x: list[str], y: list) -> dict[str, Any] | None:
    if len(x) < 2 or all(v is None for v in y):
        return None
    return {
        "type": "line",
        "title": f"Average \"{num_col}\" over time",
        "x": x,
        "series": [{"name": f"avg {num_col}", "data": y}],
    }


def _means_bar(means: dict[str, Any]) -> dict[str, Any] | None:
    if not means or not means.get("values"):
        return None
    return {
        "type": "bar",
        "title": "Column means (numeric overview)",
        "categories": means["categories"],
        "series": [{"name": "mean", "data": means["values"]}],
    }
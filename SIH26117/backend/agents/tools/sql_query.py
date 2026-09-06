"""sql_query tool — read-only SQL over ingested CSV tables. M5 owns this file."""
from __future__ import annotations

import re
import structlog
from typing import Any

from pydantic import BaseModel

from backend.core.config import get_settings
from backend.core.exceptions import ToolError
from backend.services.llm.ollama_client import get_ollama_client

logger = structlog.get_logger()
settings = get_settings()

ALLOWED_PREFIX = "ds_"
MAX_ROWS = 500


class _SQLResult(BaseModel):
    sql: str
    explanation: str


async def _nl_to_sql(question: str) -> str:
    llm = get_ollama_client()
    result = await llm.structured(
        messages=[
            {
                "role": "system",
                "content": (
                    "You translate natural language to PostgreSQL SELECT queries.\n"
                    "Rules:\n"
                    "- ONLY generate SELECT statements. No INSERT, UPDATE, DELETE, DROP, etc.\n"
                    "- All tables start with ds_ prefix.\n"
                    "- Always include a LIMIT clause (max 500).\n"
                    "- Use standard SQL syntax.\n"
                    "Available tables and columns are provided by the user."
                ),
            },
            {"role": "user", "content": f"Question: {question}"},
        ],
        schema=_SQLResult,
        temperature=0.0,
    )
    return result.sql


def _validate_sql(sql: str) -> str:
    stripped = sql.strip().rstrip(";").strip()
    upper = stripped.upper()

    if not upper.startswith("SELECT"):
        raise ToolError("Only SELECT statements are allowed")

    if ";" in stripped:
        raise ToolError("Multiple statements are not allowed")

    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT"]
    for word in dangerous:
        if re.search(rf"\b{word}\b", upper):
            raise ToolError(f"{word} statement is not allowed")

    table_pattern = re.findall(r"\b(ds_\w+)", stripped)
    if not table_pattern:
        raise ToolError("No ds_* tables found in query")

    if not re.search(r"\bLIMIT\b", upper):
        stripped = f"{stripped} LIMIT {MAX_ROWS}"
        logger.info("sql_limit_added", sql=stripped)

    return stripped


async def sql_query(query: str, session_id: str | None = None) -> str:
    if not query.strip():
        raise ToolError("Empty query")

    try:
        sql = await _nl_to_sql(query)
    except Exception as exc:
        raise ToolError(f"NL-to-SQL failed: {exc}") from exc

    sql = _validate_sql(sql)

    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            result = await conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys()) if result.returns_rows else []
    except Exception as exc:
        raise ToolError(f"SQL execution failed: {exc}") from exc
    finally:
        await engine.dispose()

    if not rows:
        return "Query returned no results."

    header = "| " + " | ".join(str(c) for c in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    data_lines: list[str] = []
    for row in rows[:MAX_ROWS]:
        data_lines.append("| " + " | ".join(str(v) for v in row) + " |")

    return "\n".join([header, sep] + data_lines)

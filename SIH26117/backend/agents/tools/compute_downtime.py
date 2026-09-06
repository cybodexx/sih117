"""compute_downtime tool — aggregate machine downtime from failure CSVs. M5 owns this file."""
from __future__ import annotations

import structlog
from datetime import datetime, timezone
from typing import Any

from backend.core.config import get_settings
from backend.core.exceptions import ToolError

logger = structlog.get_logger()
settings = get_settings()

DOWNSTREAM_TABLE = "ds_failure_log"


def _parse_iso(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ToolError(f"Invalid datetime format: {s}") from exc


async def compute_downtime(
    machine_id: str,
    start: str,
    end: str,
) -> str:
    if not machine_id or not machine_id.strip():
        raise ToolError("machine_id is required")

    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)

    if start_dt >= end_dt:
        raise ToolError("start must be before end")

    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(settings.database_url)

        query = text(
            """
            SELECT
                machine_id,
                SUM(EXTRACT(EPOCH FROM (
                    LEAST(failure_end, :end_dt) - GREATEST(failure_start, :start_dt)
                ))) AS total_downtime_seconds,
                COUNT(*) AS failure_count,
                AVG(EXTRACT(EPOCH FROM (
                    LEAST(failure_end, :end_dt) - GREATEST(failure_start, :start_dt)
                ))) AS avg_failure_duration_seconds
            FROM ds_failure_log
            WHERE machine_id = :machine_id
              AND failure_end > :start_dt
              AND failure_start < :end_dt
            GROUP BY machine_id
            """
        )

        async with engine.connect() as conn:
            result = await conn.execute(
                query,
                {
                    "machine_id": machine_id,
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                },
            )
            row = result.fetchone()

    except Exception as exc:
        raise ToolError(f"Downtime query failed: {exc}") from exc
    finally:
        await engine.dispose()

    if not row:
        return f"No failure records found for {machine_id} in the given window."

    total_secs = float(row[1] or 0)
    count = int(row[2] or 0)
    avg_secs = float(row[3] or 0)

    window_hours = (end_dt - start_dt).total_seconds() / 3600.0
    availability = (
        ((window_hours * 3600 - total_secs) / (window_hours * 3600) * 100)
        if window_hours > 0
        else 0.0
    )

    total_h, total_m = divmod(int(total_secs) // 60, 60)
    avg_h, avg_m = divmod(int(avg_secs) // 60, 60)

    return (
        f"Machine: {machine_id}\n"
        f"Window: {start} to {end} ({window_hours:.1f}h)\n"
        f"Total downtime: {total_h}h {total_m}m ({total_secs:.0f}s)\n"
        f"Failure count: {count}\n"
        f"Avg failure duration: {avg_h}h {avg_m}m ({avg_secs:.0f}s)\n"
        f"Availability: {availability:.2f}%"
    )

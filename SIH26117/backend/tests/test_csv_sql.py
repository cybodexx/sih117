"""Tests for the CSV -> ds_* relational materializer and SQL tool guards."""
from __future__ import annotations

import asyncio

import pytest

from backend.agents.tools.sql_query import _validate_sql
from backend.core.exceptions import ToolError
from backend.services.ingest.csv_sql import (
    _parse_timestamp,
    _type_for,
    materialize_csv,
    table_name_for,
)

CSV = (
    b"timestamp,machine_id,downtime_minutes,severity\n"
    b"04-05-2026 06:44,TURBINE-01,85,critical\n"
    b"09-08-2026 08:47,PUMP-02,35,medium\n"
    b"29-05-2026 04:39,TURBINE-01,128,low\n"
)


def test_table_name_sanitisation() -> None:
    assert table_name_for("equipment_failures.csv") == "ds_equipment_failures"
    assert table_name_for("../Vibration-Data!.CSV") == "ds_vibration_data"
    assert table_name_for("..") == "ds_unnamed_table"
    with pytest.raises(ToolError):
        table_name_for("x" * 100 + ".csv")


def test_timestamp_normalisation() -> None:
    dt = _parse_timestamp("04-05-2026 06:44")
    assert dt is not None and dt.isoformat() == "2026-05-04T06:44:00"
    dt = _parse_timestamp("2026-06-15")
    assert dt is not None and dt.year == 2026
    assert _parse_timestamp("nonsense") is None


def test_type_inference() -> None:
    assert _type_for(["1", "2", "3"])[0] == "BIGINT"
    assert _type_for(["1.5", "2.0", "3.25"])[0] == "DOUBLE PRECISION"
    assert _type_for(["04-05-2026", "2026-06-15"])[0] == "TIMESTAMPTZ"
    assert _type_for(["hello", "world"])[0] == "TEXT"


def test_sql_guards_allow_select() -> None:
    sql = _validate_sql("SELECT COUNT(*) FROM ds_x")
    assert sql.endswith("LIMIT 500")
    assert sql.startswith("SELECT")


def test_sql_guards_reject_writes() -> None:
    for bad in [
        "INSERT INTO ds_x VALUES (1)",
        "DROP TABLE ds_x",
        "UPDATE ds_x SET a=1",
        "SELECT 1; DROP TABLE ds_x",
    ]:
        with pytest.raises(ToolError):
            _validate_sql(bad)


def test_sql_guards_reject_non_select() -> None:
    with pytest.raises(ToolError):
        _validate_sql("WITH r AS (SELECT 1) SELECT * FROM r")


def test_materialize_csv_creates_queryable_table() -> None:
    info = asyncio.run(materialize_csv("materialize_probe.csv", CSV))
    table = info["table"]
    assert table == "ds_materialize_probe"
    assert info["rows"] == 3

    async def _assert():
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from backend.core.config import get_settings

        engine = create_async_engine(get_settings().database_url)
        try:
            async with engine.connect() as conn:
                total = (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
                assert total == 3, total
                avg = (await conn.execute(text(
                    f"SELECT AVG(downtime_minutes) FROM {table} WHERE machine_id = 'TURBINE-01'"
                ))).scalar()
                assert avg is not None and abs(float(avg) - (85 + 128) / 2) < 1e-9, avg
                dt = (await conn.execute(text(
                    f"SELECT timestamp FROM {table} WHERE machine_id = 'PUMP-02'"
                ))).scalar()
                assert dt.year == 2026 and dt.month == 8 and dt.hour == 8, dt
        finally:
            await engine.dispose()

    asyncio.run(_assert())

    async def _drop():
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from backend.core.config import get_settings

        engine = create_async_engine(get_settings().database_url)
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()

    asyncio.run(_drop())
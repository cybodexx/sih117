"""Unit tests for the deterministic auto-insights chart builders."""
from __future__ import annotations

import asyncio

from backend.services.analysis.insights import (
    _flag_pie,
    _freq_bar,
    _means_bar,
    _num,
    _time_line,
    build_insights,
)
from backend.services.ingest.csv_sql import table_name_for


class _Doc:
    def __init__(self, filename: str):
        self.filename = filename
        self.id = "00000000-0000-0000-0000-000000000001"
        self.storage_key = "/tmp/nope"


def test_build_insights_none_for_non_tabular():
    assert asyncio.run(build_insights(_Doc("meeting.png"))) is None
    assert asyncio.run(build_insights(_Doc("report.pdf"))) is None


def test_flag_pie_shape():
    chart = _flag_pie("machine_failure", 42, 100)
    assert chart["type"] == "pie"
    assert chart["items"] == [
        {"name": "machine_failure = 1", "value": 42},
        {"name": "machine_failure = 0", "value": 58},
    ]


def test_freq_bar_requires_at_least_two_categories():
    assert _freq_bar("type", [("L", 10), ("M", 3), ("H", 1)])["categories"] == ["L", "M", "H"]
    assert _freq_bar("type", [("L", 10)]) is None


def test_freq_bar_rejects_zero_rows():
    assert _freq_bar("type", [("L", 0), ("M", 5)]) is None


def test_time_line_needs_two_points():
    result = _time_line("air_temp", ["2026-01-01", "2026-01-02"], [21.0, 22.5])
    assert result is not None
    assert result["series"][0]["data"] == [21.0, 22.5]
    assert _time_line("air_temp", ["2026-01-01"], [21.0]) is None


def test_means_bar_shape():
    result = _means_bar({"categories": ["a", "b"], "values": [1.5, 2.5]})
    assert result["type"] == "bar"
    assert result["series"][0]["data"] == [1.5, 2.5]
    assert _means_bar(None) is None


def test_num_formats_float_compact():
    assert _num(3.0) == "3"
    assert _num(3.14) == "3.14"
    assert _num(None) == "NULL"


def test_table_name_for_safe_slug():
    assert table_name_for("SupplyChain.GHG.Emission Factors v1.csv") == "ds_supplychain_ghg_emission_factors_v1"
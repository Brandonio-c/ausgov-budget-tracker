"""PBS year header resolution unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ingest"))

from extractors.pbs_year_resolve import (  # noqa: E402
    parse_year_header_line,
    resolve_years_for_nums,
    template_for_budget_year,
)


def test_parse_header_multi_year():
    line = (
        "2023-24 Actual 2024-25 Estimated actual 2025-26 Budget "
        "2026-27 Forward estimate 2027-28 Forward estimate 2028-29 Forward estimate"
    )
    cols = parse_year_header_line(line)
    assert cols is not None
    assert len(cols) == 6
    assert cols[0].financial_year == "2023-24"
    assert cols[2].financial_year == "2025-26"


def test_quarantine_without_header():
    cols, reason = resolve_years_for_nums(
        ["1", "2", "3", "4", "5"],
        header_cols=None,
        source_budget_year="2025-26",
        layout_template=None,
    )
    assert cols is None
    assert "quarantine" in reason


def test_template_only_when_declared():
    tmpl = template_for_budget_year("2025-26")
    assert len(tmpl) == 6
    cols, reason = resolve_years_for_nums(
        ["1", "2", "3", "4", "5", "6"],
        header_cols=None,
        source_budget_year="2025-26",
        layout_template=tmpl,
    )
    assert cols is not None
    assert reason.startswith("source_layout_template")
    assert cols[0].estimate_status == "actual"


def test_fixture_header_2024_25():
    text = (REPO / "tests/fixtures/pbs/header_2024_25.txt").read_text(encoding="utf-8")
    cols = parse_year_header_line(text.strip().splitlines()[0])
    assert cols and cols[0].financial_year.startswith("20")

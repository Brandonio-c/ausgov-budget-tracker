"""Tests for the MFS Balance Sheet workbook extractor, one of the five MFS
sibling workbooks (item 7.1; Monthly Profiles remains the one still
outstanding).

Focuses on what's genuinely new versus the already-tested Note 3/Tax Notes
extractors: the "as at <date>" stock header shape (no YTD concept at all),
and the deliberate exclusion of FY2005-06/FY2006-07 (a structurally
different column layout and label set) and FY2007-08 (a one-off
GFS-framed transition year with bare, non-"as at" month headers).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

from extractors.mfs_balance_sheet import extract_workbook  # noqa: E402


@pytest.fixture
def synthetic_workbook(tmp_path: Path) -> Path:
    path = tmp_path / "balance_sheet.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        modern_sheet = pd.DataFrame(
            [
                ["2012-13 Balance Sheet", None, None],
                [None, "ACTUAL\nas at\n31 July 2012\n$m", "ACTUAL\nas at\n31 August 2012\n$m"],
                ["Financial assets", None, None],
                ["Cash and deposits", 10.0, 12.0],
                ["Total financial assets", 100.0, 110.0],
                ["Total assets", 200.0, 210.0],
                ["(a) A footnote.", None, None],
            ]
        )
        modern_sheet.to_excel(writer, sheet_name="2012-13", header=False, index=False)

        # Excluded early-generation sheet: indented column-1 labels, no
        # "as at" header at all - must never be extracted.
        excluded_sheet = pd.DataFrame(
            [
                ["2005-06 Balance Sheet", None, None],
                [None, "ACTUAL", "ACTUAL"],
                [None, "2005-2006", "2005-2006"],
                [None, "July", "August"],
                [None, "$m", "$m"],
                ["Assets", None, None],
                ["Financial assets", None, None],
                [None, "Cash", 5.0, 6.0],
            ]
        )
        excluded_sheet.to_excel(writer, sheet_name="2005-06", header=False, index=False)
    return path


def test_modern_sheet_extracted(synthetic_workbook: Path):
    rows, quarantine = extract_workbook(synthetic_workbook, "test_balance_sheet")
    assert quarantine == []
    labels = {r["measure_label"] for r in rows}
    assert "Cash and deposits" in labels
    assert "Total financial assets" in labels


def test_excluded_early_generation_sheet_produces_no_facts(synthetic_workbook: Path):
    """FY2005-06's structurally different layout/label set is never
    extracted, no matter what it contains - excluded by sheet name."""
    rows, _ = extract_workbook(synthetic_workbook, "test_balance_sheet")
    assert not any(r["fy"] == "2005-06" for r in rows)


def test_stock_period_end_is_the_exact_as_at_date(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_balance_sheet")
    cash_july = [r for r in rows if r["measure_label"] == "Cash and deposits" and r["reporting_month"] == "July"]
    assert len(cash_july) == 1
    assert cash_july[0]["period_end"] == "2012-07-31"
    assert cash_july[0]["fy"] == "2012-13"


def test_amount_unit_scaled_correctly(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_balance_sheet")
    cash_july = [r for r in rows if r["measure_label"] == "Cash and deposits" and r["reporting_month"] == "July"]
    assert cash_july[0]["amount"] == pytest.approx(10_000_000)


def test_footnote_row_terminates_extraction(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_balance_sheet")
    assert not any("footnote" in r["measure_label"].lower() for r in rows)


def test_non_as_at_header_is_quarantined_not_guessed(tmp_path: Path):
    """A column header that doesn't match the "as at <date>" shape (e.g.
    the bare-month style FY2007-08 uses) must be quarantined, never
    silently coerced into a guessed date."""
    path = tmp_path / "malformed.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2012-13 Balance Sheet", None],
                [None, "ACTUAL\n2012-2013\nJuly\n$m"],
                ["Cash and deposits", 10.0],
            ]
        )
        sheet.to_excel(writer, sheet_name="2012-13", header=False, index=False)
    rows, quarantine = extract_workbook(path, "test_balance_sheet")
    assert rows == []
    assert any(q["reason"] == "unparsed_column_header" for q in quarantine)

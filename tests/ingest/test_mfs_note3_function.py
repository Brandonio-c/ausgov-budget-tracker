"""Tests for the MFS Note 3 (Total expense by function) workbook extractor,
the second of the five MFS sibling workbooks (item 7.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from extractors.mfs_note3_function import extract_workbook  # noqa: E402


@pytest.fixture
def synthetic_workbook(tmp_path: Path) -> Path:
    """Mirrors the real corpus's label-drift eras verified directly against
    all 21 real sheets: the pre-2009-10 "Mining and Mineral Resources..."
    wording, a footnote-marked label, and the "Asset Sales" row that only
    exists FY2005-06..FY2007-08."""
    path = tmp_path / "note3.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        old_sheet = pd.DataFrame(
            [
                ["2007-08 Note 3", None],
                [None, "ACTUAL\n2007-2008\nYTD July\n$m"],
                ["Expenses by function", None],
                ["Mining and Mineral Resources (other than fuels); \n   Manufacturing and Construction", 30.0],
                ["Other purposes", None],
                ["Contingency reserve (a)", 5.0],
                ["Asset Sales", 2.0],
                ["Total expenses", 500.0],
                ["(a) From September 2008 asset sale related expenses are treated as a component of the contingency reserve.", None],
            ]
        )
        old_sheet.to_excel(writer, sheet_name="2007-08", header=False, index=False)

        new_sheet = pd.DataFrame(
            [
                ["2024-25 Note 3", None],
                [None, "ACTUAL\n2024-2025\nJuly\n$m"],
                ["Expenses by function", None],
                ["Mining, manufacturing and construction", 40.0],
                ["Other purposes", None],
                ["Contingency reserve", 0.0],
                ["Total expenses", 600.0],
            ]
        )
        new_sheet.to_excel(writer, sheet_name="2024-25", header=False, index=False)
    return path


def test_pre_2009_10_mining_label_wording_extracted_verbatim(synthetic_workbook: Path):
    """Not normalized/merged with the later wording here - that mapping
    decision belongs to the loader's declarative semantics file, never the
    extractor."""
    rows, _ = extract_workbook(synthetic_workbook, "test_note3")
    old_wording = [
        r
        for r in rows
        if r["fy"] == "2007-08"
        and r["measure_label"].startswith("Mining and Mineral Resources")
    ]
    assert len(old_wording) == 1
    assert old_wording[0]["amount"] == pytest.approx(30_000_000)


def test_asset_sales_only_present_in_its_real_years(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_note3")
    asset_sales = [r for r in rows if r["measure_label"] == "Asset Sales"]
    assert len(asset_sales) == 1
    assert asset_sales[0]["fy"] == "2007-08"
    assert asset_sales[0]["amount"] == pytest.approx(2_000_000)
    # The 2024-25 sheet has no Asset Sales row at all - never backfilled.
    assert not any(r["fy"] == "2024-25" and r["measure_label"] == "Asset Sales" for r in rows)


def test_contingency_reserve_footnote_marker_stripped(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_note3")
    labels_2007 = {r["measure_label"] for r in rows if r["fy"] == "2007-08"}
    assert "Contingency reserve" in labels_2007
    assert "Contingency reserve (a)" not in labels_2007


def test_total_expenses_extracted_as_its_own_published_row(synthetic_workbook: Path):
    """Total expenses is always the source's own stated cell - never
    computed by summing the other extracted rows."""
    rows, _ = extract_workbook(synthetic_workbook, "test_note3")
    totals = {r["fy"]: r["amount"] for r in rows if r["measure_label"] == "Total expenses"}
    assert totals["2007-08"] == pytest.approx(500_000_000)
    assert totals["2024-25"] == pytest.approx(600_000_000)


def test_section_heading_rows_produce_no_facts(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_note3")
    labels = {r["measure_label"] for r in rows}
    assert "Expenses by function" not in labels
    assert "Other purposes" not in labels


def test_trailing_explanatory_footnote_paragraph_excluded(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_note3")
    assert not any("From September 2008" in r["measure_label"] for r in rows)

"""Tests for the MFS Aggregates workbook extractor (Task 5)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from extractors.mfs_aggregates import extract_workbook  # noqa: E402


@pytest.fixture
def synthetic_workbook(tmp_path: Path) -> Path:
    """A two-sheet workbook mirroring the real file's shape: an older-era
    sheet in $m with a non-YTD August column (a real quirk of the earliest
    years), and a newer-era sheet in $b with renamed rows and a footnote."""
    path = tmp_path / "aggregates.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        old_sheet = pd.DataFrame(
            [
                ["2005-06 Aggregates", None, None],
                [None, "ACTUAL\n2005-2006\nJuly\n$m", "ACTUAL\n2005-2006\nAugust\n$m"],
                ["Revenue", 100.0, 50.0],
                ["Expenses", 90.0, 95.0],
            ]
        )
        old_sheet.to_excel(writer, sheet_name="2005-06", header=False, index=False)

        new_sheet = pd.DataFrame(
            [
                ["2024-25 Aggregates", None],
                [None, "ACTUAL\n2024-2025\nYTD July\n$b"],
                ["Revenue", 53.294782],
                ["Total liabilities", 1413.182524],
                ["(a) Footnote text.", None],
            ]
        )
        new_sheet.to_excel(writer, sheet_name="2024-25", header=False, index=False)
    return path


def test_unit_scaling_dollars_b_and_m(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_mfs_aggregates")
    revenue_2024 = [r for r in rows if r["fy"] == "2024-25" and r["measure_label"] == "Revenue"]
    assert len(revenue_2024) == 1
    assert revenue_2024[0]["amount"] == pytest.approx(53_294_782_000)

    revenue_2005_july = [
        r for r in rows if r["fy"] == "2005-06" and r["measure_label"] == "Revenue" and r["month"] == "July"
    ]
    assert len(revenue_2005_july) == 1
    assert revenue_2005_july[0]["amount"] == pytest.approx(100_000_000)


def test_non_ytd_column_quarantined_not_guessed(synthetic_workbook: Path):
    """The real workbook's earliest years label August as a bare month, not
    "YTD August" - it must be quarantined, not silently treated as either a
    standalone or cumulative value, since which one it is can't be inferred
    from the header text alone."""
    rows, quarantine = extract_workbook(synthetic_workbook, "test_mfs_aggregates")
    august_rows = [r for r in rows if r["month"] == "August"]
    assert august_rows == []
    reasons = {q["reason"] for q in quarantine}
    assert "non_ytd_column_not_supported" in reasons


def test_footnote_row_stops_extraction_and_marker_stripped(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_mfs_aggregates")
    labels_2024 = {r["measure_label"] for r in rows if r["fy"] == "2024-25"}
    assert "Total liabilities" in labels_2024
    assert not any("Footnote" in label for label in labels_2024)


def test_citation_locator_complete(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_mfs_aggregates")
    for r in rows:
        for required in ("source_id:", "sheet:", "row:", "col:"):
            assert required in r["locator"]
        assert r["cached_copy_path"]

"""Tests for the shared MFS sibling-workbook header/footnote parsing
(mfs_common.py), factored out while adding the second workbook
(mfs_note3_function) - verifies the two real header shapes found in the
real Note 3 corpus (single combined cell vs four separate physical rows)
are both handled correctly and that mfs_aggregates.py's existing,
already-tested behavior is preserved through the refactor (see
test_mfs_aggregates.py, unchanged and still passing)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

from mfs_common import (  # noqa: E402
    HEADER_RE,
    clean_label,
    extract_ytd_workbook,
)


def test_header_re_tolerates_leading_whitespace_before_month():
    """The real 2013-14..2015-16 Note 3 sheets have a literal leading space
    before "July" (" July", no "YTD" prefix) instead of "YTD July" or bare
    "July" - found by direct inspection, not assumed. July is always
    implicitly YTD regardless of this quirk."""
    m = HEADER_RE.match("ACTUAL\n2013-2014\n July\n$m")
    assert m is not None
    assert m.group("month") == "July"
    assert m.group("ytd") is None


def test_clean_label_strips_trailing_marker_and_whitespace():
    assert clean_label("General public services(a)") == "General public services"
    assert clean_label("Education ") == "Education"
    assert clean_label("General purpose inter-government transactions\n") == (
        "General purpose inter-government transactions"
    )


@pytest.fixture
def multirow_header_workbook(tmp_path: Path) -> Path:
    """Mirrors the real FY2005-06..FY2011-12 Note 3 sheets: the header is
    spread across four separate physical rows (status/fy/month/unit) with
    data starting at row index 5, not a single combined cell at row 1."""
    path = tmp_path / "note3.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2005-06 Note 3", None, None],
                [None, "ACTUAL", "ACTUAL"],
                [None, "2005-2006", "2005-2006"],
                [None, "July", "YTD  August"],
                [None, "$m", "$m"],
                ["Expenses by function", None, None],
                ["Defence", 100.0, 210.0],
                ["Health", 50.0, 105.0],
            ]
        )
        sheet.to_excel(writer, sheet_name="2005-06", header=False, index=False)
    return path


def test_multirow_header_shape_is_parsed(multirow_header_workbook: Path):
    rows, quarantine = extract_ytd_workbook(multirow_header_workbook, "test_note3")
    assert quarantine == []
    defence_july = [r for r in rows if r["measure_label"] == "Defence" and r["month"] == "July"]
    assert len(defence_july) == 1
    assert defence_july[0]["amount"] == pytest.approx(100_000_000)
    defence_aug = [r for r in rows if r["measure_label"] == "Defence" and r["month"] == "August"]
    assert len(defence_aug) == 1
    assert defence_aug[0]["amount"] == pytest.approx(210_000_000)


def test_section_heading_row_produces_no_facts(multirow_header_workbook: Path):
    """"Expenses by function" is a structural section heading with no
    numeric cells - it must never appear as a published measure_label."""
    rows, _ = extract_ytd_workbook(multirow_header_workbook, "test_note3")
    labels = {r["measure_label"] for r in rows}
    assert "Expenses by function" not in labels

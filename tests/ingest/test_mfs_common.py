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

import re  # noqa: E402

from mfs_common import (  # noqa: E402
    HEADER_RE,
    clean_label,
    extract_multi_block_ytd_workbook,
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


# --- extract_multi_block_ytd_workbook (added for Tax Notes 1-2, item 7.1) --


TITLE_RE = re.compile(r"Tax Note \d - ")


@pytest.fixture
def two_block_workbook(tmp_path: Path) -> Path:
    """Mirrors Tax Notes 1-2's real shape: two independently-titled
    title-header-data blocks stacked in one sheet, each with its own
    footnote row - block 1's footnote must not truncate the scan before
    block 2's data is reached."""
    path = tmp_path / "tax_notes.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2012-13 Tax Note 1 - Income Tax", None],
                [None, "ACTUAL\n2012-2013\nJuly\n$m"],
                ["Company tax", 5.0],
                ["(a) A footnote for block 1.", None],
                ["2012-13 Tax Note 2 - Indirect Tax", None],
                [None, "ACTUAL\n2012-2013\nJuly\n$m"],
                ["Excise duty", 3.0],
                ["(a) A footnote for block 2.", None],
            ]
        )
        sheet.to_excel(writer, sheet_name="2012-13", header=False, index=False)
    return path


def test_multi_block_reaches_second_blocks_data(two_block_workbook: Path):
    rows, _ = extract_multi_block_ytd_workbook(two_block_workbook, "test_tax_notes", TITLE_RE)
    labels = {r["measure_label"] for r in rows}
    assert "Company tax" in labels
    assert "Excise duty" in labels


def test_multi_block_first_footnote_does_not_leak_into_second_block(two_block_workbook: Path):
    rows, _ = extract_multi_block_ytd_workbook(two_block_workbook, "test_tax_notes", TITLE_RE)
    assert not any("footnote for block" in r["measure_label"] for r in rows)


def test_multi_block_values_correctly_attributed_to_their_own_block(two_block_workbook: Path):
    rows, _ = extract_multi_block_ytd_workbook(two_block_workbook, "test_tax_notes", TITLE_RE)
    company_tax = [r for r in rows if r["measure_label"] == "Company tax"]
    excise = [r for r in rows if r["measure_label"] == "Excise duty"]
    assert company_tax[0]["amount"] == pytest.approx(5_000_000)
    assert excise[0]["amount"] == pytest.approx(3_000_000)


def test_multi_block_sheet_with_no_title_match_is_quarantined(tmp_path: Path):
    path = tmp_path / "no_titles.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame([["Not a title row", None], [None, "ACTUAL\n2012-2013\nJuly\n$m"], ["Company tax", 5.0]])
        sheet.to_excel(writer, sheet_name="2012-13", header=False, index=False)
    rows, quarantine = extract_multi_block_ytd_workbook(path, "test_tax_notes", TITLE_RE)
    assert rows == []
    assert any(q["reason"] == "no_block_titles_found" for q in quarantine)

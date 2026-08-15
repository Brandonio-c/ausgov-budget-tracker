"""Tests for the MFS Tax Notes 1-2 (Income Tax / Indirect Tax) workbook
extractor, the fourth of the five MFS sibling workbooks (item 7.1).

Focuses on what's genuinely new versus the already-tested Note 3 extractor:
multi-block-per-sheet extraction (mfs_common.py's
extract_multi_block_ytd_workbook(), added for this workbook since it stacks
two independently-titled tables per sheet) and the deliberate exclusion of
labels with a real, verified multi-generation composition ambiguity.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

from extractors.mfs_tax_notes_1_2 import extract_workbook  # noqa: E402


@pytest.fixture
def synthetic_workbook(tmp_path: Path) -> Path:
    """One sheet with two stacked title-header-data blocks (Note 1, Note 2),
    each with its own footnote row - mirrors the real corpus's shape,
    including a genuinely ambiguous label in each block that the extractor
    must exclude."""
    path = tmp_path / "tax_notes.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2012-13 Tax Note 1 - Income Tax", None],
                [None, "ACTUAL\n2012-2013\nJuly\n$m"],
                ["Individuals and other withholding taxes", None],
                ["Gross income tax withholding ", 10.0],
                ["Company tax", 5.0],
                ["Resource rent taxes (a)", 1.0],
                ["Total income taxation revenue", 16.0],
                ["(a) Includes both the minerals resource rent tax and the petroleum rent tax.", None],
                ["2012-13 Tax Note 2 - Indirect Tax", None],
                [None, "ACTUAL\n2012-2013\nJuly\n$m"],
                ["Goods and services tax", 20.0],
                ["Other indirect tax (a)", 3.0],
                ["Total indirect taxation revenue", 23.0],
                ["(a) See note.", None],
            ]
        )
        sheet.to_excel(writer, sheet_name="2012-13", header=False, index=False)
    return path


def test_second_block_is_reached_not_truncated_at_first_blocks_footnote(synthetic_workbook: Path):
    """Regression: extract_ytd_workbook()'s single "stop at the first
    footnote row" rule would truncate the sheet at Note 1's footnote and
    never reach Note 2's data at all - extract_multi_block_ytd_workbook()
    must scope that termination to each block independently."""
    rows, _ = extract_workbook(synthetic_workbook, "test_tax_notes")
    labels = {r["measure_label"] for r in rows}
    assert "Goods and services tax" in labels


def test_note1_footnote_does_not_leak_into_note1_data(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_tax_notes")
    assert not any("Includes both" in r["measure_label"] for r in rows)


def test_gross_income_tax_withholding_extracted(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_tax_notes")
    matches = [r for r in rows if r["measure_label"] == "Gross income tax withholding"]
    assert len(matches) == 1
    assert matches[0]["amount"] == pytest.approx(10_000_000)


def test_ambiguous_resource_rent_taxes_label_excluded(synthetic_workbook: Path):
    rows, quarantine = extract_workbook(synthetic_workbook, "test_tax_notes")
    labels = {r["measure_label"] for r in rows}
    assert "Resource rent taxes" not in labels
    assert any(q["label"] == "Resource rent taxes" for q in quarantine)


def test_note1_ambiguous_grand_total_excluded_but_note2_total_kept(synthetic_workbook: Path):
    """Note 1's grand total is genuinely ambiguous (FBT in/out varies by
    generation) and is excluded; Note 2's total has no such ambiguity (only
    its "Other indirect tax" line item does) and is loaded normally."""
    rows, quarantine = extract_workbook(synthetic_workbook, "test_tax_notes")
    labels = {r["measure_label"] for r in rows}
    assert "Total income taxation revenue" not in labels
    assert "Total indirect taxation revenue" in labels
    quarantined_labels = {q["label"] for q in quarantine}
    assert "Total income taxation revenue" in quarantined_labels


def test_ambiguous_other_indirect_tax_excluded(synthetic_workbook: Path):
    rows, quarantine = extract_workbook(synthetic_workbook, "test_tax_notes")
    labels = {r["measure_label"] for r in rows}
    assert "Other indirect tax" not in labels
    assert any(q["label"] == "Other indirect tax" for q in quarantine)


def test_company_tax_and_gst_both_extracted_from_their_own_blocks(synthetic_workbook: Path):
    rows, _ = extract_workbook(synthetic_workbook, "test_tax_notes")
    labels = {r["measure_label"] for r in rows}
    assert "Company tax" in labels
    assert "Goods and services tax" in labels

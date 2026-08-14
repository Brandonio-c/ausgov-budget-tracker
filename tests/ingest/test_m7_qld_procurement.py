"""Regression tests for scripts/ingest/m7_qld_procurement.py (Task 4 of the
database-hygiene-and-CI-hardening milestone).

Root cause of the one confirmed true duplicate fact found in this milestone
(QLD QGIP "Goondiwindi Regional Council / Black Spot", facts 81987 and
217525 - see ops/reports/duplicate-fact-investigation-*.md): `export_qgip()`
built `category` (and therefore `node_name` / `fact_key`) from raw
`agency`/`cat` cell text with no whitespace normalization, so the same
real-world funding record re-published in two overlapping "consolidated"
QLD export files - differing only by a trailing space on one field - was
loaded as two distinct facts instead of being recognised as the same row.

These tests exercise `export_qgip()` end-to-end against a synthetic,
temporary source-file layout (no dependency on the real ~180k-row raw
corpus) to prove the fix collapses whitespace-only variants while leaving
genuinely different rows untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import m7_qld_procurement  # noqa: E402


def _write_source(tmp_path: Path, rows: list[dict], filename: str = "2018-19-expenditure-consolidated.csv") -> None:
    src_dir = tmp_path / "data" / "raw" / "state" / "qld_qgip_expenditure"
    src_dir.mkdir(parents=True, exist_ok=True)
    csv_path = src_dir / filename
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    latest = {
        "assets": [
            {
                "detected_type": "csv",
                "stored_path": str(csv_path.relative_to(tmp_path / "data")),
                "original_filename": filename,
                "final_url": "https://www.data.qld.gov.au/dataset/example",
            }
        ]
    }
    (src_dir / "latest.json").write_text(json.dumps(latest), encoding="utf-8")


def _run_export(tmp_path: Path, monkeypatch) -> pd.DataFrame:
    monkeypatch.setattr(m7_qld_procurement, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(m7_qld_procurement, "STAGING", tmp_path / "data" / "staging" / "m7")
    meta = m7_qld_procurement.export_qgip()
    return pd.read_csv(meta["csv"])


def test_whitespace_only_variants_collapse_to_the_same_category(tmp_path, monkeypatch):
    """Reproduces the Goondiwindi "Black Spot" / "Black Spot " true-duplicate
    case: same agency and program text, differing only by a trailing space,
    across two rows. After the fix both rows must produce an identical
    `category` string so the fact_key / node_name they feed is stable."""
    rows = [
        {
            "Legal Entity Name": "GOONDIWINDI REGIONAL COUNCIL",
            "Program title": "Black Spot",
            "Financial year expenditure": "42750",
            "Financial Year": "2018-19",
        },
        {
            "Legal Entity Name": "GOONDIWINDI REGIONAL COUNCIL",
            "Program title": "Black Spot ",
            "Financial year expenditure": "42750",
            "Financial Year": "2018-19",
        },
    ]
    _write_source(tmp_path, rows)
    df = _run_export(tmp_path, monkeypatch)
    assert df["category"].nunique() == 1
    assert df["category"].iloc[0] == "GOONDIWINDI REGIONAL COUNCIL / Black Spot"


def test_leading_and_internal_whitespace_is_also_normalized(tmp_path, monkeypatch):
    rows = [
        {
            "Legal Entity Name": " Some   Council ",
            "Program title": "  Roads  Program",
            "Financial year expenditure": "1000",
            "Financial Year": "2020-21",
        },
    ]
    _write_source(tmp_path, rows)
    df = _run_export(tmp_path, monkeypatch)
    assert df["category"].iloc[0] == "Some Council / Roads Program"


def test_genuinely_different_program_titles_remain_distinct(tmp_path, monkeypatch):
    """Whitespace normalization must not accidentally collapse rows that are
    genuinely different real-world records (see duplicate-fact-investigation
    Groups 3-5, all query false positives that must NOT be merged)."""
    rows = [
        {
            "Legal Entity Name": "QLD Murray Darling Committee Inc",
            "Program title": "Investment Progam",
            "Financial year expenditure": "426667",
            "Financial Year": "2014-15",
        },
        {
            "Legal Entity Name": "QLD Murray Darling Committee Inc",
            "Program title": "Investment Program",
            "Financial year expenditure": "355333",
            "Financial Year": "2014-15",
        },
    ]
    _write_source(tmp_path, rows)
    df = _run_export(tmp_path, monkeypatch)
    assert df["category"].nunique() == 2
    assert set(df["amount"]) == {426667.0, 355333.0}


def test_same_source_loaded_twice_produces_identical_rows(tmp_path, monkeypatch):
    """Re-exporting from the same untouched source data must be
    deterministic - a second run is not itself a source of new duplicates."""
    rows = [
        {
            "Legal Entity Name": "Some Council ",
            "Program title": "Black Spot",
            "Financial year expenditure": "42750",
            "Financial Year": "2018-19",
        },
    ]
    _write_source(tmp_path, rows)
    df1 = _run_export(tmp_path, monkeypatch)
    df2 = _run_export(tmp_path, monkeypatch)
    assert df1["category"].tolist() == df2["category"].tolist()
    assert df1["amount"].tolist() == df2["amount"].tolist()


def test_expenditure_amount_is_never_used_as_financial_year(tmp_path, monkeypatch):
    rows = [
        {
            "Legal Entity Name": "Swifts Hockey Club Inc",
            "Program title": "Fair Play",
            "Financial year expenditure": "2099",
            "Financial Year": "2022-23",
        }
    ]
    _write_source(tmp_path, rows, filename="2022-23-expenditure-consolidated.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["fy"].tolist() == ["2022-23"]
    assert df["amount"].tolist() == [2099.0]


# --- Item 7.2 repair regression tests -----------------------------------
#
# Root causes (verified directly against all 14 real acquired QGIP files,
# not assumed) - see ops/reports/qgip-repair-*.md:
#   1. "Previous financial year" (a column that actually holds a DOLLAR
#      AMOUNT, e.g. 31818/6000/250, never a year) was being matched as a
#      financial-year column by the old substring heuristic. When such an
#      amount happened to numerically resemble "20XX", it got fabricated
#      into a bogus future financial year - the "2099-00"-class defect.
#      Fix: financial_year is now derived only from the filename, never
#      from any in-file column.
#   2. The old filename regex required a literal 4-digit "20XX" and failed
#      on the 5 real files using a bare two-digit "XX-YY" pattern (18-19,
#      19-20, 20-21 x2, 21-22, "...data-17-18.csv"), silently defaulting
#      every row from those files to a hardcoded "2024-25".
#   3. The amount column was the first file-order match against any of
#      {amount, expenditure, value, total} - for the real 2014-15 file this
#      picked "Total funding under this agreement" (a whole-of-agreement,
#      multi-year total) ahead of "Financial year expenditure" (the correct
#      single-year figure) purely because of that file's column order.
#   4. "Sub-program title" (present in 11 of 14 real files) was silently
#      dropped - the category-column heuristic only ever captured whichever
#      of "Program title"/"Sub-program title" came first (always "Program
#      title").


def test_two_digit_only_filename_year_is_parsed_not_defaulted(tmp_path, monkeypatch):
    """The real 18-19/19-20/20-21 x2/21-22 files use this exact bare
    "XX-YY" pattern with no 4-digit year anywhere in the filename - every
    row from these 5 real files was previously silently misattributed to
    a hardcoded "2024-25" fallback."""
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Roads",
            "Financial year expenditure": "50000",
        },
    ]
    _write_source(tmp_path, rows, filename="18-19-expenditure-data-consolidated.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["fy"].tolist() == ["2018-19"]


def test_filename_with_no_year_pattern_is_skipped_not_defaulted(tmp_path, monkeypatch):
    """A file whose year cannot be determined must produce zero rows, not a
    silent guess at some fixed year."""
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Roads",
            "Financial year expenditure": "50000",
        },
    ]
    _write_source(tmp_path, rows, filename="expenditure-data-export.csv")
    monkeypatch.setattr(m7_qld_procurement, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(m7_qld_procurement, "STAGING", tmp_path / "data" / "staging" / "m7")
    meta = m7_qld_procurement.export_qgip()
    assert meta["rows"] == 0


def test_financial_year_expenditure_preferred_over_agreement_total_regardless_of_column_order(
    tmp_path, monkeypatch
):
    """Reproduces the real 2014-15 file's column order (Total funding
    appears before Financial year expenditure) - the per-year figure must
    still win."""
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Roads",
            "Total funding under this agreement": "999000",
            "Financial year expenditure": "50000",
        },
    ]
    _write_source(tmp_path, rows, filename="2014-15-consolidated-qgip-expenditure.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["amount"].tolist() == [50000.0]
    assert df["estimate_status"].tolist() == ["actual"]


def test_agreement_total_only_gets_distinct_estimate_status(tmp_path, monkeypatch):
    """2012-13/2013-14 genuinely have no per-year expenditure column at all
    - their facts are loaded from the whole-of-agreement total but must
    never be tagged as the same vintage as genuine single-year "actual"
    figures elsewhere, per the non-negotiable rule against blending
    incompatible vintages."""
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Roads",
            "Total funding under this agreement": "999000",
        },
    ]
    _write_source(tmp_path, rows, filename="2012-13-consolidated-qgip-expenditure.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["amount"].tolist() == [999000.0]
    assert df["estimate_status"].tolist() == ["actual_cumulative_agreement_total"]


def test_subprogram_is_captured_as_a_distinct_dimension(tmp_path, monkeypatch):
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Farm Management Grants Scheme",
            "Sub-program title": "FMG Rebate",
            "Financial year expenditure": "50000",
        },
    ]
    _write_source(tmp_path, rows, filename="2018-19-expenditure-consolidated.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["category"].iloc[0] == "Some Council / Farm Management Grants Scheme / FMG Rebate"


def test_missing_subprogram_value_falls_back_to_program_only(tmp_path, monkeypatch):
    """Sub-program title column exists but is blank for this particular
    row - must not produce a trailing " / " or "nan"."""
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Roads",
            "Sub-program title": "",
            "Financial year expenditure": "50000",
        },
    ]
    _write_source(tmp_path, rows, filename="2018-19-expenditure-consolidated.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["category"].iloc[0] == "Some Council / Roads"


def test_absent_subprogram_column_falls_back_to_program_only(tmp_path, monkeypatch):
    """2012-13/2013-14/2014-15 genuinely have no Sub-program title column
    at all - never backfilled or fabricated."""
    rows = [
        {
            "Legal Entity Name": "Some Council",
            "Program title": "Roads",
            "Total funding under this agreement": "50000",
        },
    ]
    _write_source(tmp_path, rows, filename="2013-14-consolidated-qgip-expenditure.csv")
    df = _run_export(tmp_path, monkeypatch)
    assert df["category"].iloc[0] == "Some Council / Roads"

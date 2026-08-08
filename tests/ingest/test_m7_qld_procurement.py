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


def _write_source(tmp_path: Path, rows: list[dict], filename: str = "export.csv") -> None:
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

"""Extractor/loader coverage for the selected Queensland MYFER cluster."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest/extractors"))

import qld_myfer as extractor  # noqa: E402
import reload_qld_myfer as loader  # noqa: E402
from schema_migrate import migrate  # noqa: E402


TABLE_TEXT = """
Table 3: General Government Sector – key fiscal aggregates
Actual Budget MYFER Projection Projection Projection
$ million $ million $ million $ million $ million $ million
Revenue 58,087 57,738 59,002 59,614 60,403 62,167
Expenses 56,335 57,590 58,478 59,421 60,258 62,048
Net operating
balance 1,753 148 524 193 145 119
PNFA3 5,127 5,927 5,981 7,420 7,451 7,182
Fiscal balance (586) (3,033) (2,632) (3,710) (3,416) (3,305)
Notes:
"""


def _source_row(
    measure_type: str = "qld_myfer_revenue",
    amount: float = 59_002.0,
    financial_year: str = "2018-19",
    cached_copy_path: str = "README.md",
) -> dict:
    return {
        "source_id": loader.SOURCE_ID,
        "source_budget_year": financial_year,
        "financial_year": financial_year,
        "publication_date": "2019-01-14",
        "measure_type": measure_type,
        "estimate_status": "revised_estimate",
        "amount_million_aud": amount,
        "row_label": "Revenue",
        "column_header_original": "MYFER",
        "locator": f"file:test.pdf | page:1 | row:{measure_type} | column:MYFER",
        "cached_copy_path": cached_copy_path,
    }


def test_parenthesized_negative_and_split_thousands_parsing():
    assert extractor.parse_number("(2,632)") == -2632.0
    assert extractor._repair_split_thousands("Revenue 50,995 53,449 54,9 53") == (
        "Revenue 50,995 53,449 54,953"
    )


def test_table_parser_preserves_rows_and_selectable_six_column_shape():
    rows, quarantine = extractor._parse_expected_rows(TABLE_TEXT, extractor.load_semantics())
    assert quarantine == []
    assert rows["qld_myfer_net_operating_balance"]["values"][2] == 524.0
    assert rows["qld_myfer_fiscal_balance"]["values"][2] == -2632.0
    assert rows["qld_myfer_capital_purchases"]["values"][2] == 5981.0


def test_malformed_expected_row_is_quarantined_not_guessed():
    broken = TABLE_TEXT.replace(
        "Revenue 58,087 57,738 59,002 59,614 60,403 62,167",
        "Revenue 58,087 57,738 unknown 59,614 60,403 62,167",
    )
    rows, quarantine = extractor._parse_expected_rows(broken, extractor.load_semantics())
    assert "qld_myfer_revenue" not in rows
    assert any(item["reason"] == "unexpected_numeric_column_count" for item in quarantine)


def test_real_selected_corpus_extracts_thirty_rows_when_available():
    if not extractor.SNAPSHOT_DIR.is_dir():
        pytest.skip("acquired MYFER corpus not present")
    rows, quarantine = extractor.extract_all_editions()
    assert quarantine == []
    assert len(rows) == 30
    assert {row["financial_year"] for row in rows} == {
        "2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2025-26"
    }
    assert all("page:" in row["locator"] and "column:" in row["locator"] for row in rows)


def test_unit_period_vintage_and_revision_identity():
    fact, reason = loader.classify_and_validate(_source_row(), loader.load_semantics())
    assert reason == ""
    assert fact["amount_aud"] == 59_002_000_000.0
    assert fact["period_start"] == "2018-07-01"
    assert fact["period_end"] == "2019-06-30"
    assert fact["period_granularity"] == "financial_year"
    assert fact["estimate_status"] == "revised_estimate"
    assert "vintage:2018-19" in fact["fact_key"]


def test_period_mismatch_and_missing_citation_are_quarantined():
    semantics = loader.load_semantics()
    mismatched = _source_row()
    mismatched["source_budget_year"] = "2019-20"
    fact, reason = loader.classify_and_validate(mismatched, semantics)
    assert fact is None and reason == "selected_column_period_mismatch"
    missing = _source_row(cached_copy_path="data/does-not-exist.pdf")
    fact, reason = loader.classify_and_validate(missing, semantics)
    assert fact is None and reason == "source_file_missing_on_disk"


@pytest.fixture()
def fixture_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "facts.db"
    migrate(db)
    rows = [
        _source_row("qld_myfer_revenue", 59_002.0),
        _source_row("qld_myfer_expense", 58_478.0),
        _source_row("qld_myfer_net_operating_balance", 524.0),
        _source_row("qld_myfer_capital_purchases", 5_981.0),
        _source_row("qld_myfer_fiscal_balance", -2_632.0),
    ]
    monkeypatch.setattr(loader, "extract_all_editions", lambda source_id: (rows, []))
    return db


def test_reload_is_idempotent_preserves_citations_and_prevents_duplicates(
    fixture_db: Path, tmp_path: Path
):
    conn = sqlite3.connect(str(fixture_db))
    quarantine = tmp_path / "q.jsonl"
    first = loader.run(conn, apply=True, quarantine_path=quarantine)
    assert first["facts_inserted"] == 5
    assert first["nodes_inserted"] == 5
    assert first["edges_inserted"] == 0
    second = loader.run(conn, apply=True, quarantine_path=quarantine)
    assert second["facts_inserted"] == 0
    assert second["facts_updated"] == 0
    assert second["nodes_inserted"] == 0
    assert second["edges_inserted"] == 0
    assert second["semantic_changes"] == 0
    assert second["facts_already_present_idempotent_skip"] == 5
    assert conn.execute(
        "SELECT COUNT(*) FROM facts WHERE measure_type LIKE 'qld_myfer_%'"
    ).fetchone()[0] == 5
    assert conn.execute(
        "SELECT fact_key, COUNT(*) FROM facts GROUP BY fact_key HAVING COUNT(*) > 1"
    ).fetchall() == []
    locator = conn.execute(
        "SELECT source_locator_json FROM facts WHERE measure_type='qld_myfer_revenue'"
    ).fetchone()[0]
    assert "column:MYFER" in json.loads(locator)["locator"]
    conn.close()


def test_revision_conflict_is_quarantined_without_overwrite(
    fixture_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True, quarantine_path=tmp_path / "first.jsonl")
    changed = _source_row("qld_myfer_revenue", 60_000.0)
    monkeypatch.setattr(loader, "extract_all_editions", lambda source_id: ([changed], []))
    result = loader.run(conn, apply=True, quarantine_path=tmp_path / "conflict.jsonl")
    assert result["revision_conflicts_quarantined"] == 1
    assert result["facts_inserted"] == 0
    amount = conn.execute(
        "SELECT amount_aud FROM facts WHERE measure_type='qld_myfer_revenue'"
    ).fetchone()[0]
    assert amount == 59_002_000_000.0
    conn.close()


def test_compatibility_groups_are_isolated_from_rsf_and_annual_gfs(fixture_db: Path):
    conn = sqlite3.connect(str(fixture_db))
    groups = conn.execute(
        "SELECT measure_type, compatibility_group FROM measure_definitions WHERE measure_type LIKE 'qld_myfer_%'"
    ).fetchall()
    conn.close()
    assert len(groups) == 5
    forbidden = {"actual_expense", "budget_expense", "gfs_revenue", "gfs_liability"}
    assert all(group == measure_type and group not in forbidden for measure_type, group in groups)
    assert all(not group.startswith("qld_rsf_") for _, group in groups)

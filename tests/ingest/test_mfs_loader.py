"""Task 10 of the MFS-aggregates milestone: consolidated loader-level
tests - YTD period calculation, stock reporting dates, label-to-measure
mapping, stable fact keys, negative/parenthesized amounts, citation
preservation, and annual-vs-YTD compatibility-group isolation.

Revision/duplicate-policy and idempotent-reload coverage lives in
tests/ingest/test_mfs_revision_policy.py (Task 6); extractor-level unit
conversion and bare-month quarantine coverage lives in
tests/ingest/test_mfs_aggregates.py (pre-existing). This file covers
what neither of those already does.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import load_mfs_aggregates as loader  # noqa: E402
from schema_migrate import migrate  # noqa: E402

# ---- YTD period calculation -------------------------------------------


@pytest.mark.parametrize(
    "fy,month,expected",
    [
        ("2023-24", "July", "2023-07-31"),
        ("2023-24", "December", "2023-12-31"),
        ("2023-24", "January", "2024-01-31"),
        ("2023-24", "May", "2024-05-31"),
        ("2023-24", "February", "2024-02-29"),  # 2024 is a leap year
        ("2022-23", "February", "2023-02-28"),  # 2023 is not a leap year
    ],
)
def test_month_to_period_end(fy, month, expected):
    assert loader.month_to_period_end(fy, month) == expected


def test_financial_year_start():
    assert loader.financial_year_start("2023-24") == "2023-07-01"
    assert loader.financial_year_start("2000-01") == "2000-07-01"


# ---- label-to-measure mapping ------------------------------------------


def test_build_label_index_covers_every_real_label_variant():
    semantics = loader.load_semantics()
    index = loader.build_label_index(semantics)
    assert index["Revenue"] == "mfs_ytd_revenue"
    assert index["Income"] == "mfs_ytd_revenue"  # pre-2007 synonym
    assert index["Operating Result"] == "mfs_ytd_net_operating_balance"
    assert index["Net worth"] == "mfs_stock_net_worth"
    assert index["Net Assets"] == "mfs_stock_net_worth"  # pre-2007 synonym
    assert index["less Payments"] == "mfs_ytd_payments"
    assert "Net debt" in index


def test_build_label_index_rejects_ambiguous_duplicate_mapping():
    semantics = {
        "measures": {
            "a": {"source_label_variants": ["Revenue"]},
            "b": {"source_label_variants": ["Revenue"]},
        }
    }
    with pytest.raises(ValueError, match="claimed by both"):
        loader.build_label_index(semantics)


# ---- stable fact keys ---------------------------------------------------


def test_build_fact_key_is_stable_and_identity_complete():
    key1 = loader.build_fact_key(
        source_family="federal_mfs_aggregates", financial_year="2023-24",
        reporting_month="July", measure_type="mfs_ytd_revenue",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    key2 = loader.build_fact_key(
        source_family="federal_mfs_aggregates", financial_year="2023-24",
        reporting_month="July", measure_type="mfs_ytd_revenue",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 == key2

    # Changing any single identity-bearing dimension changes the key.
    key_diff_month = loader.build_fact_key(
        source_family="federal_mfs_aggregates", financial_year="2023-24",
        reporting_month="August", measure_type="mfs_ytd_revenue",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key_diff_month != key1


# ---- classify_and_validate: stock vs flow period semantics, units, citations


@pytest.fixture
def semantics():
    return loader.load_semantics()


@pytest.fixture
def label_index(semantics):
    return loader.build_label_index(semantics)


def _row(label, fy="2023-24", month="August", amount=100.0, unit="$m", locator="loc", cached_copy_path=None):
    return {
        "fy": fy,
        "amount": amount,
        "measure_label": label,
        "estimate_status": "actual",
        "month": month,
        "unit": unit,
        "sheet": fy,
        "locator": locator,
        "cached_copy_path": cached_copy_path or str(REPO_ROOT / "README.md"),
    }


def test_classify_flow_gets_period_start_and_end(semantics, label_index):
    fact, reason = loader.classify_and_validate(_row("Revenue"), semantics, label_index)
    assert reason == ""
    assert fact["period_start"] == "2023-07-01"
    assert fact["period_end"] == "2023-08-31"
    assert fact["flow_or_stock"] == "flow"


def test_classify_stock_gets_no_period_start(semantics, label_index):
    fact, reason = loader.classify_and_validate(_row("Total assets"), semantics, label_index)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2023-08-31"
    assert fact["flow_or_stock"] == "stock"


def test_classify_balance_is_distinguished_from_raw_flow(semantics, label_index):
    fact, reason = loader.classify_and_validate(_row("Net operating balance"), semantics, label_index)
    assert reason == ""
    assert fact["flow_or_stock"] == "balance"
    assert fact["measure_type"] == "mfs_ytd_net_operating_balance"


def test_classify_unrecognized_label_is_quarantined(semantics, label_index):
    fact, reason = loader.classify_and_validate(_row("Some Brand New Row Nobody Has Seen"), semantics, label_index)
    assert fact is None
    assert reason == "unrecognized_label"


def test_classify_missing_source_file_is_quarantined(semantics, label_index):
    row = _row("Revenue", cached_copy_path="data/raw/definitely/does/not/exist.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, label_index)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


def test_classify_undetermined_unit_is_quarantined(semantics, label_index):
    fact, reason = loader.classify_and_validate(_row("Revenue", unit="$"), semantics, label_index)
    assert fact is None
    assert reason == "unit_undeterminable"


def test_classify_preserves_negative_amount(semantics, label_index):
    """Excel accounting-format negatives (already numeric floats by the
    time they reach classify_and_validate - Task 4 confirmed pandas/
    openpyxl reads them as real negative numbers, not strings) must not
    be altered, dropped, or sign-flipped."""
    fact, reason = loader.classify_and_validate(_row("Net operating balance", amount=-272153000.0), semantics, label_index)
    assert reason == ""
    assert fact["amount_aud"] == -272153000.0


# ---- citation preservation through a real --apply load -----------------


def _write_workbook(path: Path, revenue_amount: float = 100.0) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2023-24 Aggregates", None],
                [None, "ACTUAL\n2023-2024\nYTD July\n$m"],
                ["Revenue", revenue_amount],
            ]
        )
        sheet.to_excel(writer, sheet_name="2023-24", header=False, index=False)


def test_loaded_fact_preserves_full_citation(monkeypatch, tmp_path):
    db = tmp_path / "facts.db"
    migrate(db)
    workbook = tmp_path / "aggregates.xlsx"
    _write_workbook(workbook)
    monkeypatch.setattr(loader, "_find_latest_asset", lambda source_id: workbook)

    conn = sqlite3.connect(str(db))
    result = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")
    assert result["facts_to_insert"] == 1

    row = conn.execute(
        "SELECT source_locator_json FROM facts WHERE measure_type = 'mfs_ytd_revenue'"
    ).fetchone()
    conn.close()
    payload = json.loads(row[0])
    assert "source_id:federal_mfs_aggregates" in payload["locator"]
    assert "sheet:2023-24" in payload["locator"]
    assert "row:Revenue" in payload["locator"]
    assert payload["cached_copy_path"] == str(workbook)


# ---- annual-vs-YTD compatibility-group isolation ------------------------


def test_every_mfs_measure_has_a_dedicated_compatibility_group_distinct_from_annual(tmp_path):
    """No mfs_* measure_type may share a compatibility_group with any
    annual GFS/PBS actual or budget measure - the exact mechanism behind
    the Task 1 contamination bug."""
    db = tmp_path / "facts.db"
    migrate(db)
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT measure_type, compatibility_group FROM measure_definitions").fetchall()
    conn.close()

    by_group: dict[str, set[str]] = {}
    for measure_type, group in rows:
        by_group.setdefault(group, set()).add(measure_type)

    annual_groups = {"actual_expense", "budget_expense", "gfs_revenue", "gfs_liability"}
    mfs_measure_types = {m for m, spec in loader.load_semantics()["measures"].items()}

    for group in annual_groups:
        overlap = by_group.get(group, set()) & mfs_measure_types
        assert not overlap, f"MFS measure(s) {overlap} illegally share annual compatibility_group {group!r}"

    # Each MFS measure is 1:1 with its own compatibility_group.
    for measure_type in mfs_measure_types:
        groups_containing_it = [g for g, members in by_group.items() if measure_type in members]
        assert len(groups_containing_it) == 1
        assert groups_containing_it[0] == measure_type


def test_reviewed_duplicate_facts_yaml_parses_and_includes_mfs_entries():
    path = REPO_ROOT / "config" / "audit" / "reviewed_duplicate_facts.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = doc["reviewed_duplicate_facts"]
    mfs_entries = [e for e in entries if e["source_key"] == "federal_mfs_aggregates"]
    assert len(mfs_entries) == 2
    for e in mfs_entries:
        assert e["classification"] == "query_false_positive"
        assert e["measure_type"] == "mfs_ytd_net_capital_investment"

"""Tests for load_mfs_balance_sheet.py - focused on what differs from the
already-tested Note 3/Tax Notes loaders: stock semantics (period_start is
always None, no YTD reporting-month validation needed), label-index
scoping to mfs_balance_sheet_*/mfs_stock_cash_and_deposits only (never
claiming Total assets/liabilities/Net worth/Net debt, which are
deliberately sourced from federal_mfs_aggregates instead), and the
only_published_financial_years gating for the split/renamed measures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_mfs_balance_sheet as loader  # noqa: E402


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def test_label_index_excludes_other_mfs_siblings(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    assert "Revenue" not in index  # Aggregates
    assert "Defence" not in index  # Note 3
    assert "Company tax" not in index  # Tax Notes
    assert all(
        mt.startswith("mfs_balance_sheet_") or mt == "mfs_stock_cash_and_deposits"
        for mt in index.values()
    )


def test_label_index_never_claims_the_aggregates_sourced_headline_totals(semantics: dict) -> None:
    """Total assets/liabilities/Net worth/Net debt are deliberately
    sourced from federal_mfs_aggregates, not this workbook - even though
    this file also literally has rows with these exact labels, this
    loader must never classify them (they fall through to
    unrecognized_label and get quarantined, not silently accepted)."""
    index = loader.build_label_index(semantics)
    assert "Total assets" not in index
    assert "Total liabilities" not in index
    assert "Net worth" not in index
    assert "Net debt" not in index


def test_label_index_reactivates_the_reserved_cash_and_deposits_measure(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    assert index["Cash and deposits"] == "mfs_stock_cash_and_deposits"


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2012-13",
        "amount": 1_000_000.0,
        "measure_label": "Cash and deposits",
        "estimate_status": "actual",
        "reporting_month": "July",
        "period_end": "2012-07-31",
        "unit": "$m",
        "sheet": "2012-13",
        "locator": "source_id:federal_mfs_balance_sheet | sheet:2012-13 | row:x | col:x",
        "cached_copy_path": "x.xlsx",
    }
    row.update(overrides)
    return row


def test_stock_fact_has_no_period_start(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    fact, reason = loader.classify_and_validate(_base_row(), semantics, loader.build_label_index(semantics))
    assert reason == ""
    assert fact is not None
    assert fact["period_start"] is None
    assert fact["period_end"] == "2012-07-31"


def test_lease_liabilities_is_unrecognized_not_merged_with_other_borrowing(semantics: dict, tmp_path, monkeypatch) -> None:
    """The AASB16 reclassification from "Other borrowing" to "Lease
    liabilities" is a genuine population change, not a rename - this
    loader must never accept "Lease liabilities" as a continuation."""
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(measure_label="Lease liabilities", fy="2020-21")
    fact, reason = loader.classify_and_validate(row, semantics, loader.build_label_index(semantics))
    assert fact is None
    assert reason == "unrecognized_label"


def test_other_borrowing_within_its_years_is_accepted(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(measure_label="Other borrowing", fy="2015-16")
    fact, reason = loader.classify_and_validate(row, semantics, loader.build_label_index(semantics))
    assert reason == ""
    assert fact["measure_type"] == "mfs_balance_sheet_other_borrowing"


def test_other_borrowing_outside_its_years_is_quarantined(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(measure_label="Other borrowing", fy="2020-21")
    fact, reason = loader.classify_and_validate(row, semantics, loader.build_label_index(semantics))
    assert fact is None
    assert reason == "outside_only_published_financial_years"


def test_renamed_investment_property_variants_both_accepted(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    index = loader.build_label_index(semantics)
    old, reason1 = loader.classify_and_validate(_base_row(measure_label="Investment property", fy="2010-11"), semantics, index)
    new, reason2 = loader.classify_and_validate(_base_row(measure_label="Investment properties", fy="2020-21"), semantics, index)
    assert reason1 == "" and reason2 == ""
    assert old["measure_type"] == new["measure_type"] == "mfs_balance_sheet_investment_property"


def test_split_provisions_and_payables_kept_as_distinct_measures(semantics: dict, tmp_path, monkeypatch) -> None:
    """"Other provisions and payables" split into "Other payables" and
    "Provisions" from FY2017-18 - these must remain 3 distinct
    measure_types, never claimed as one continuous series."""
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    index = loader.build_label_index(semantics)
    pre, _ = loader.classify_and_validate(_base_row(measure_label="Other provisions and payables", fy="2010-11"), semantics, index)
    post_payables, _ = loader.classify_and_validate(_base_row(measure_label="Other payables", fy="2020-21"), semantics, index)
    post_provisions, _ = loader.classify_and_validate(_base_row(measure_label="Provisions", fy="2020-21"), semantics, index)
    types = {pre["measure_type"], post_payables["measure_type"], post_provisions["measure_type"]}
    assert len(types) == 3


def test_unrecognized_label_is_quarantined(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    row = _base_row(measure_label="Some Unmapped Balance Sheet Line")
    fact, reason = loader.classify_and_validate(row, semantics, index)
    assert fact is None
    assert reason == "unrecognized_label"


def test_fact_key_is_stable_and_identity_complete() -> None:
    key1 = loader.build_fact_key(
        source_family="federal_mfs_balance_sheet", financial_year="2024-25",
        reporting_month="July", measure_type="mfs_balance_sheet_land",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    key2 = loader.build_fact_key(
        source_family="federal_mfs_balance_sheet", financial_year="2024-25",
        reporting_month="July", measure_type="mfs_balance_sheet_land",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 == key2
    key3 = loader.build_fact_key(
        source_family="federal_mfs_balance_sheet", financial_year="2024-25",
        reporting_month="August", measure_type="mfs_balance_sheet_land",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 != key3

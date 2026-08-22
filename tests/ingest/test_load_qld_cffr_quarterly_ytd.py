"""Tests for load_qld_cffr_quarterly_ytd.py (item 7.4, quarterly slice):
stock vs flow period handling (opening/closing balance have no
period_start), quarter-end date computation, fact_key stability
(including the Q{quarter} component that disambiguates 3 editions
sharing the same financial_year), and unrecognized-key quarantine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_qld_cffr_quarterly_ytd as loader  # noqa: E402


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2022-23",
        "quarter": 3,
        "amount": 1_000_000_000.0,
        "measure_key": "collections_from_departments",
        "locator": "source_id:qld_cffr_quarterly_ytd | file:x.pdf | page:1 | row:collections_from_departments | column:Total (Year to Date)",
        "cached_copy_path": "x.pdf",
    }
    row.update(overrides)
    return row


def test_quarter_end_date_matches_each_quarter():
    assert loader.quarter_end_date("2022-23", 1) == "2022-09-30"
    assert loader.quarter_end_date("2022-23", 2) == "2022-12-31"
    assert loader.quarter_end_date("2022-23", 3) == "2023-03-31"


def test_flow_measure_has_year_to_date_period(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    fact, reason = loader.classify_and_validate(_base_row(), semantics)
    assert reason == ""
    assert fact["period_start"] == "2022-07-01"
    assert fact["period_end"] == "2023-03-31"
    assert fact["period_granularity"] == "year_to_date"
    assert fact["measure_type"] == "qld_cffr_quarterly_ytd_collections_from_departments"
    assert fact["accounting_basis"] == "cash"
    assert fact["estimate_status"] == "actual"


def test_opening_balance_is_a_stock_at_financial_year_start(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    row = _base_row(measure_key="opening_balance")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2022-07-01"
    assert fact["measure_type"] == "qld_cffr_quarterly_ytd_opening_balance"


def test_closing_balance_is_a_stock_at_quarter_end(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    row = _base_row(measure_key="closing_balance", fy="2022-23", quarter=2)
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2022-12-31"
    assert fact["measure_type"] == "qld_cffr_quarterly_ytd_closing_balance"


def test_missing_source_file_is_quarantined(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    fact, reason = loader.classify_and_validate(_base_row(), semantics)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


def test_unrecognized_measure_key_is_quarantined(semantics: dict) -> None:
    row = _base_row(measure_key="some_unmapped_key")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "unrecognized_measure_key"


def test_fact_key_is_stable_and_identity_complete() -> None:
    key1 = loader.build_fact_key(
        financial_year="2022-23", quarter=3, measure_type="qld_cffr_quarterly_ytd_collections_from_departments",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    key2 = loader.build_fact_key(
        financial_year="2022-23", quarter=3, measure_type="qld_cffr_quarterly_ytd_collections_from_departments",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    assert key1 == key2
    key3 = loader.build_fact_key(
        financial_year="2022-23", quarter=2, measure_type="qld_cffr_quarterly_ytd_collections_from_departments",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    assert key1 != key3  # different quarter within the same financial_year must not collide


def test_fact_key_never_collides_with_the_annual_source_id() -> None:
    quarterly_key = loader.build_fact_key(
        financial_year="2022-23", quarter=3, measure_type="qld_cffr_quarterly_ytd_opening_balance",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    assert quarterly_key.startswith("qld_cffr_quarterly_ytd|")
    assert "qld_cffr_annual" not in quarterly_key


def test_measure_type_map_covers_all_nine_semantics_measures(semantics: dict) -> None:
    mapped_types = set(loader._MEASURE_TYPE_BY_KEY.values())
    assert mapped_types == set(semantics["measures"].keys())
    assert len(mapped_types) == 9

"""Tests for load_qld_cffr_annual.py (item 7.4): stock vs flow period
handling (opening/closing balance have no period_start; opening_balance's
period_end is the financial-year start, not end), fact_key stability, and
unrecognized-key quarantine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_qld_cffr_annual as loader  # noqa: E402


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2016-17",
        "amount": 1_000_000_000.0,
        "measure_key": "collections_from_departments",
        "locator": "source_id:qld_cffr_annual | file:x.pdf | page:7 | row:collections_from_departments | column:Total (Year Ended)",
        "cached_copy_path": "x.pdf",
    }
    row.update(overrides)
    return row


def test_flow_measure_has_full_year_period(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    fact, reason = loader.classify_and_validate(_base_row(), semantics)
    assert reason == ""
    assert fact["period_start"] == "2016-07-01"
    assert fact["period_end"] == "2017-06-30"
    assert fact["measure_type"] == "qld_cffr_collections_from_departments"
    assert fact["accounting_basis"] == "cash"
    assert fact["estimate_status"] == "actual"


def test_opening_balance_is_a_stock_at_financial_year_start(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    row = _base_row(measure_key="opening_balance", fy="2016-17")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2016-07-01"
    assert fact["measure_type"] == "qld_cffr_opening_balance"


def test_closing_balance_is_a_stock_at_financial_year_end(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    row = _base_row(measure_key="closing_balance", fy="2016-17")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2017-06-30"
    assert fact["measure_type"] == "qld_cffr_closing_balance"


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
        financial_year="2016-17", measure_type="qld_cffr_collections_from_departments",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    key2 = loader.build_fact_key(
        financial_year="2016-17", measure_type="qld_cffr_collections_from_departments",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    assert key1 == key2
    key3 = loader.build_fact_key(
        financial_year="2017-18", measure_type="qld_cffr_collections_from_departments",
        accounting_basis="cash", estimate_status="actual", jurisdiction="QLD",
    )
    assert key1 != key3

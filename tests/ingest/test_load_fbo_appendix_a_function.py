"""Tests for load_fbo_appendix_a_function.py (item 8.1, first slice):
full-financial-year flow period handling (no stock special-casing, unlike
QLD CFFR), fact_key stability, and unrecognized-key/missing-file
quarantine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_fbo_appendix_a_function as loader  # noqa: E402


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2010-11",
        "amount": 21_239.0,
        "measure_key": "general_public_services",
        "locator": "source_id:fbo_appendix_a_function | file:x.pdf | pages:105-107 | row:general_public_services | column:Estimate at Outcome",
        "cached_copy_path": "x.pdf",
    }
    row.update(overrides)
    return row


def test_addend_measure_has_full_year_period_and_signed_convention(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    fact, reason = loader.classify_and_validate(_base_row(), semantics)
    assert reason == ""
    assert fact["period_start"] == "2010-07-01"
    assert fact["period_end"] == "2011-06-30"
    assert fact["measure_type"] == "fbo_appendix_a_general_public_services"
    assert fact["accounting_basis"] == "accrual"
    assert fact["estimate_status"] == "actual"


def test_total_expenses_measure_classifies_correctly(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    row = _base_row(measure_key="total_expenses", fy="2011-12", amount=373_671.0)
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["measure_type"] == "fbo_appendix_a_total_expenses"
    assert fact["period_start"] == "2011-07-01"
    assert fact["period_end"] == "2012-06-30"


def test_negative_contingency_reserve_amount_is_preserved(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.pdf").write_bytes(b"stub")
    row = _base_row(measure_key="contingency_reserve", amount=-1_468.0)
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["amount_aud"] == -1_468.0


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
        financial_year="2010-11", measure_type="fbo_appendix_a_general_public_services",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    key2 = loader.build_fact_key(
        financial_year="2010-11", measure_type="fbo_appendix_a_general_public_services",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 == key2
    key3 = loader.build_fact_key(
        financial_year="2011-12", measure_type="fbo_appendix_a_general_public_services",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 != key3


def test_measure_type_map_covers_all_twenty_semantics_measures(semantics: dict) -> None:
    mapped_types = set(loader._MEASURE_TYPE_BY_KEY.values())
    assert mapped_types == set(semantics["measures"].keys())
    assert len(mapped_types) == 20

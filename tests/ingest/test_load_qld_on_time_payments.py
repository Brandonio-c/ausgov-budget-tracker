"""Regression tests for scripts/ingest/load_qld_on_time_payments.py (item
7.5): quarter-to-calendar-date mapping, amount_aud vs quantity routing, and
fact_key stability/identity-completeness."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_qld_on_time_payments as loader  # noqa: E402


# ---- quarter_period: Q1=Jul-Sep(y1), Q2=Oct-Dec(y1), Q3=Jan-Mar(y2), Q4=Apr-Jun(y2) --


@pytest.mark.parametrize(
    "quarter,expected_start,expected_end",
    [
        (1, "2020-07-01", "2020-09-30"),
        (2, "2020-10-01", "2020-12-31"),
        (3, "2021-01-01", "2021-03-31"),
        (4, "2021-04-01", "2021-06-30"),
    ],
)
def test_quarter_period_maps_to_correct_calendar_dates(quarter, expected_start, expected_end):
    start, end = loader.quarter_period("2020-21", quarter)
    assert start == expected_start
    assert end == expected_end


# ---- classify_and_validate: amount_aud vs quantity routing -----------------


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2020-21",
        "agency_code": "dpc",
        "quarter": 1,
        "measure": "eligible_claims",
        "value": 5.0,
        "locator": "source_id:qld_on_time_payment_reports | file:x.csv | row:2 | col:x | agency_code:dpc",
        "cached_copy_path": "x.csv",
    }
    row.update(overrides)
    return row


def test_count_measure_routes_to_quantity_not_amount_aud(semantics, tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.csv").write_bytes(b"stub")
    fact, reason = loader.classify_and_validate(_base_row(measure="eligible_claims", value=5.0), semantics)
    assert reason == ""
    assert fact["quantity"] == 5.0
    assert fact["amount_aud"] is None
    assert fact["measure_type"] == "qld_otp_eligible_claims"


def test_dollar_measure_routes_to_amount_aud_not_quantity(semantics, tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.csv").write_bytes(b"stub")
    fact, reason = loader.classify_and_validate(
        _base_row(measure="penalty_interest_paid", value=1234.5), semantics
    )
    assert reason == ""
    assert fact["amount_aud"] == 1234.5
    assert fact["quantity"] is None
    assert fact["measure_type"] == "qld_otp_penalty_interest_paid"


def test_percentage_and_days_measures_also_route_to_quantity(semantics, tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.csv").write_bytes(b"stub")
    for measure in ("mean_days_paid_late", "pct_late_smallbus", "pct_late_others"):
        fact, reason = loader.classify_and_validate(_base_row(measure=measure, value=3.5), semantics)
        assert reason == ""
        assert fact["amount_aud"] is None
        assert fact["quantity"] == 3.5


def test_missing_source_file_on_disk_is_quarantined(semantics, tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    fact, reason = loader.classify_and_validate(_base_row(), semantics)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


# ---- build_fact_key: stability and identity-completeness -------------------


def test_fact_key_is_stable_for_identical_identity():
    key1 = loader.build_fact_key(
        financial_year="2020-21", quarter=1, agency_code="dpc",
        measure_type="qld_otp_eligible_claims", estimate_status="actual",
    )
    key2 = loader.build_fact_key(
        financial_year="2020-21", quarter=1, agency_code="dpc",
        measure_type="qld_otp_eligible_claims", estimate_status="actual",
    )
    assert key1 == key2


def test_fact_key_differs_by_quarter():
    """Distinct quarters must never collapse to the same fact_key - this is
    exactly the identity axis task9_sql_integrity_checks.py's duplicate_facts()
    grouping omits, which is why genuinely-different-quarter facts sharing a
    value need reviewed_duplicate_facts.yaml registry entries rather than
    being conflated at load time."""
    key_q1 = loader.build_fact_key(
        financial_year="2020-21", quarter=1, agency_code="dpc",
        measure_type="qld_otp_eligible_claims", estimate_status="actual",
    )
    key_q2 = loader.build_fact_key(
        financial_year="2020-21", quarter=2, agency_code="dpc",
        measure_type="qld_otp_eligible_claims", estimate_status="actual",
    )
    assert key_q1 != key_q2


def test_fact_key_differs_by_agency_code():
    key_dpc = loader.build_fact_key(
        financial_year="2020-21", quarter=1, agency_code="dpc",
        measure_type="qld_otp_eligible_claims", estimate_status="actual",
    )
    key_other = loader.build_fact_key(
        financial_year="2020-21", quarter=1, agency_code="dcyjma",
        measure_type="qld_otp_eligible_claims", estimate_status="actual",
    )
    assert key_dpc != key_other

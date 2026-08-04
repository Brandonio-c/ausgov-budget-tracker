"""Unit tests for semantic compatibility (no facts.db required)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from backend.compatibility import (  # noqa: E402
    mode_to_view_family,
    validate_fact_set,
)


def test_mode_mapping():
    assert mode_to_view_family("actuals") == "actual_expense"
    assert mode_to_view_family("gdp") == "gdp_current"
    assert mode_to_view_family("ratios") == "ratios"


def test_reject_percent_with_aud():
    rows = [
        {"measure_type": "gdp_current", "unit": "AUD", "amount_value": 1e12, "price_basis": "current_prices"},
        {"measure_type": "tax_to_gdp_ratio", "unit": "percent", "amount_value": 24.0, "price_basis": "not_applicable"},
    ]
    d = validate_fact_set(rows, view_family="gdp_current")
    assert not d.allowed
    assert any("percent" in e.lower() or "unit" in e.lower() or "tax_to_gdp" in e for e in d.errors)


def test_reject_current_vs_chain():
    rows = [
        {"measure_type": "gdp_current", "unit": "AUD", "price_basis": "current_prices"},
        {"measure_type": "gdp_chain_volume", "unit": "AUD", "price_basis": "chain_volume"},
    ]
    d = validate_fact_set(rows, view_family="gdp_current")
    assert not d.allowed


def test_ratios_no_root_total():
    rows = [
        {
            "measure_type": "tax_to_gdp_ratio",
            "unit": "percent",
            "amount_value": 24.3,
            "price_basis": "not_applicable",
        }
    ]
    d = validate_fact_set(rows, view_family="ratios")
    assert d.allowed
    assert d.root_total_allowed is False
    assert d.additive_across_nodes is False


def test_debt_mixed_valuation_disables_total():
    rows = [
        {"measure_type": "gfs_liability", "unit": "AUD", "valuation_basis": "face_value", "price_basis": "unspecified"},
        {"measure_type": "borrowing_authority_debt_outstanding", "unit": "AUD", "valuation_basis": "fair_value", "price_basis": "unspecified"},
    ]
    d = validate_fact_set(rows, view_family="debt_stock", valuation_filter="all")
    assert d.allowed
    assert d.mixed_valuation_bases
    assert d.root_total_allowed is False

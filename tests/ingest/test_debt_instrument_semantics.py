"""Unit tests for debt instrument valuation / granularity helpers."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from adapters.state_debt_instruments import InstrumentRow  # noqa: E402


def test_to_fact_dict_face_value_individual() -> None:
    row = InstrumentRow(
        instrument_type="Fixed-rate bonds",
        security_name="3.00% 15 May 2030",
        maturity_date="2030-05-15",
        coupon="3.00%",
        isin="AU000X",
        face_value_aud=1_000_000.0,
        as_at=date(2025, 6, 30),
        valuation_basis="face_value_outstanding",
        authority="TCORP",
        source_url="https://example.test",
    )
    d = row.to_fact_dict()
    assert d["valuation_basis"] == "face_value"
    assert d["amount_granularity"] == "individual_security"
    assert "TCORP" in d["category"]
    assert d["observation_date"] == "2025-06-30"


def test_to_fact_dict_fair_value_aggregate() -> None:
    row = InstrumentRow(
        instrument_type="Fixed-rate bonds",
        security_name="Fixed-rate bonds",
        maturity_date=None,
        coupon=None,
        isin=None,
        face_value_aud=5_000_000_000.0,
        as_at=date(2025, 6, 30),
        valuation_basis="fair_value",
        authority="TASCORP",
    )
    d = row.to_fact_dict()
    assert d["valuation_basis"] == "fair_value"
    assert d["amount_granularity"] == "instrument_type_aggregate"

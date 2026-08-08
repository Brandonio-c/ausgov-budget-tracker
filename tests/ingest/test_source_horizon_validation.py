from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from validate import gate3_source_horizon, validate_row  # noqa: E402


def _mapping() -> dict:
    return {
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "actual",
        "publication_horizon": {
            "min_financial_year": "2012-13",
            "max_financial_year": "2024-25",
        },
    }


def _row(financial_year: str) -> dict:
    return {
        "financial_year": financial_year,
        "amount_aud": 2099,
        "node_name": "Recipient / Program",
        "locator": "file:test.csv | row:2",
        "landing_url": "https://example.test",
        "original_resource_url": "https://example.test/test.csv",
        "_cached_copy_path": "data/raw/test.csv",
        "_sha256": "abc",
        "_retrieved_at": "2026-08-08T00:00:00Z",
    }


def test_source_horizon_accepts_declared_boundaries() -> None:
    assert gate3_source_horizon(_mapping(), _row("2012-13")).ok
    assert gate3_source_horizon(_mapping(), _row("2024-25")).ok


def test_source_horizon_quarantines_outlier_with_machine_reason() -> None:
    decision = validate_row(_mapping(), _row("2099-00"))
    assert decision.publishable is False
    assert decision.quarantine_reason == (
        "Gate 3 source_horizon: "
        "source_horizon_outlier:financial_year=2099-00;allowed=2012-13..2024-25"
    )


def test_mapping_without_horizon_is_not_subject_to_global_maximum() -> None:
    mapping = _mapping()
    mapping.pop("publication_horizon")
    assert gate3_source_horizon(mapping, _row("2099-00")).ok

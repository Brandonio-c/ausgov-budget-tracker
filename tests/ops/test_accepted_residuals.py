"""Tests for scripts/ops/accepted_residuals.py (Task 2 of the
database-hygiene-and-CI-hardening milestone): the declarative
accepted-residual mechanism for additive-reconciliation findings.

Uses synthetic fixture entries throughout - not the real Defence data,
since deeper investigation (this same milestone) found the Defence
"Key cost category / OPERATING" case was a genuine extraction defect, not
rounding, and fixed it at the root rather than accepting it. This
mechanism is general-purpose, tested infrastructure for a genuine future
rounding case.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

from accepted_residuals import (  # noqa: E402
    InvalidResidualConfig,
    ResidualEntry,
    load_accepted_residuals,
    match_residual,
    validate_config,
)

ENTRY_KWARGS = dict(
    source_key="test_source",
    node_path="Test Portfolio / Some Program",
    financial_year="2024-25",
    measure_type="budget_estimate",
    estimate_status="budget",
    expected_max_variance_pct=0.01,
    actual_verified_variance_pct=0.0052,
    reason="Verified source-document rounding in the cited PDF table.",
    source_locator="pdf:test.pdf|page:1",
    review_date="2026-08-04",
)


def _entry(**overrides) -> ResidualEntry:
    kwargs = {**ENTRY_KWARGS, **overrides}
    return ResidualEntry(**kwargs)


def test_exact_match_within_variance_is_accepted():
    entry = _entry()
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.005,
    )
    assert matched is entry


def test_different_financial_year_does_not_match():
    entry = _entry()
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2025-26",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.005,
    )
    assert matched is None


def test_different_source_key_does_not_match():
    entry = _entry()
    matched = match_residual(
        [entry],
        source_key="a_different_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.005,
    )
    assert matched is None


def test_different_node_path_does_not_match():
    entry = _entry()
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / A Different Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.005,
    )
    assert matched is None


def test_different_measure_type_does_not_match():
    entry = _entry()
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="actual_accrual_expense",
        estimate_status="budget",
        variance_pct=0.005,
    )
    assert matched is None


def test_different_estimate_status_does_not_match():
    entry = _entry()
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="forward_estimate",
        variance_pct=0.005,
    )
    assert matched is None


def test_materially_larger_variance_does_not_match():
    """An identical identity match must still fail if the live variance
    exceeds what was actually verified/declared safe - the entry does not
    grant a blank cheque for any future variance at that node."""
    entry = _entry(expected_max_variance_pct=0.01)
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.25,
    )
    assert matched is None


def test_variance_exactly_at_the_declared_maximum_matches():
    entry = _entry(expected_max_variance_pct=0.01)
    matched = match_residual(
        [entry],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.01,
    )
    assert matched is entry


def test_empty_registry_never_matches():
    matched = match_residual(
        [],
        source_key="test_source",
        node_path="Test Portfolio / Some Program",
        financial_year="2024-25",
        measure_type="budget_estimate",
        estimate_status="budget",
        variance_pct=0.005,
    )
    assert matched is None


def test_load_accepted_residuals_missing_file_returns_empty(tmp_path):
    assert load_accepted_residuals(tmp_path / "does_not_exist.yaml") == []


def test_load_accepted_residuals_parses_real_entries(tmp_path):
    path = tmp_path / "residuals.yaml"
    path.write_text(
        yaml.safe_dump({"residuals": [dict(ENTRY_KWARGS)]}),
        encoding="utf-8",
    )
    entries = load_accepted_residuals(path)
    assert len(entries) == 1
    assert entries[0].source_key == "test_source"
    assert entries[0].expected_max_variance_pct == 0.01


def test_load_accepted_residuals_rejects_missing_required_field(tmp_path):
    bad_entry = dict(ENTRY_KWARGS)
    del bad_entry["reason"]
    path = tmp_path / "residuals.yaml"
    path.write_text(yaml.safe_dump({"residuals": [bad_entry]}), encoding="utf-8")
    with pytest.raises(InvalidResidualConfig):
        load_accepted_residuals(path)


def test_validate_config_flags_actual_variance_exceeding_its_own_expected_max(tmp_path):
    bad_entry = dict(ENTRY_KWARGS)
    bad_entry["actual_verified_variance_pct"] = 0.5  # exceeds expected_max_variance_pct=0.01
    path = tmp_path / "residuals.yaml"
    path.write_text(yaml.safe_dump({"residuals": [bad_entry]}), encoding="utf-8")
    result = validate_config(path)
    assert result["valid"] is False
    assert result["entry_count"] == 1
    assert any("exceeds its own" in e for e in result["errors"])


def test_validate_config_accepts_well_formed_registry(tmp_path):
    path = tmp_path / "residuals.yaml"
    path.write_text(yaml.safe_dump({"residuals": [dict(ENTRY_KWARGS)]}), encoding="utf-8")
    result = validate_config(path)
    assert result["valid"] is True
    assert result["entry_count"] == 1


def test_validate_config_accepts_empty_registry(tmp_path):
    path = tmp_path / "residuals.yaml"
    path.write_text(yaml.safe_dump({"residuals": []}), encoding="utf-8")
    result = validate_config(path)
    assert result["valid"] is True
    assert result["entry_count"] == 0


def test_real_repo_config_is_currently_empty_and_valid():
    """The real registry (config/audit/accepted_reconciliation_residuals.yaml)
    has no live entries: the one case it was built for (Defence "Key cost
    category / OPERATING") was found to be a genuine extraction defect,
    not rounding, and was fixed at the root instead of being accepted."""
    result = validate_config()
    assert result["valid"] is True
    assert result["entry_count"] == 0

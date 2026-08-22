"""Tests for scripts/ops/reviewed_duplicates.py (Task 4/6 of the
database-hygiene-and-CI-hardening milestone): the declarative
reviewed-duplicate-group registry that lets scripts/ops/
task9_sql_integrity_checks.py distinguish previously-investigated,
genuinely-distinct facts from a new or unresolved duplicate candidate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

from reviewed_duplicates import (  # noqa: E402
    InvalidReviewedDuplicateConfig,
    ReviewedDuplicateGroup,
    load_reviewed_duplicates,
    match_reviewed_duplicate,
    validate_config,
)

ENTRY_KWARGS = dict(
    source_key="test_source",
    node_path="Some Council / Employee benefits",
    financial_year="2016-17",
    measure_type="actual_accrual_expense",
    estimate_status="audited_actual",
    amount_aud=84180000.0,
    classification="query_false_positive",
    reason="Two different councils' rows that happen to share a rounded figure.",
    evidence_report="ops/reports/example.md#group-1",
    review_date="2026-08-04",
)


def _entry(**overrides) -> ReviewedDuplicateGroup:
    kwargs = {**ENTRY_KWARGS, **overrides}
    return ReviewedDuplicateGroup(**kwargs)


def test_exact_match_is_reviewed():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="test_source",
        node_path="Some Council / Employee benefits",
        financial_year="2016-17",
        measure_type="actual_accrual_expense",
        estimate_status="audited_actual",
        amount_aud=84180000.0,
    )
    assert matched is entry


def test_different_financial_year_does_not_match():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="test_source",
        node_path="Some Council / Employee benefits",
        financial_year="2017-18",
        measure_type="actual_accrual_expense",
        estimate_status="audited_actual",
        amount_aud=84180000.0,
    )
    assert matched is None


def test_different_source_key_does_not_match():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="a_different_source",
        node_path="Some Council / Employee benefits",
        financial_year="2016-17",
        measure_type="actual_accrual_expense",
        estimate_status="audited_actual",
        amount_aud=84180000.0,
    )
    assert matched is None


def test_different_node_path_does_not_match():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="test_source",
        node_path="Some Council / A Different Line Item",
        financial_year="2016-17",
        measure_type="actual_accrual_expense",
        estimate_status="audited_actual",
        amount_aud=84180000.0,
    )
    assert matched is None


def test_different_measure_type_does_not_match():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="test_source",
        node_path="Some Council / Employee benefits",
        financial_year="2016-17",
        measure_type="budget_estimate",
        estimate_status="audited_actual",
        amount_aud=84180000.0,
    )
    assert matched is None


def test_different_estimate_status_does_not_match():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="test_source",
        node_path="Some Council / Employee benefits",
        financial_year="2016-17",
        measure_type="actual_accrual_expense",
        estimate_status="budget",
        amount_aud=84180000.0,
    )
    assert matched is None


def test_different_amount_does_not_match():
    entry = _entry()
    matched = match_reviewed_duplicate(
        [entry],
        source_key="test_source",
        node_path="Some Council / Employee benefits",
        financial_year="2016-17",
        measure_type="actual_accrual_expense",
        estimate_status="audited_actual",
        amount_aud=1.0,
    )
    assert matched is None


def test_empty_registry_never_matches():
    matched = match_reviewed_duplicate(
        [],
        source_key="test_source",
        node_path="Some Council / Employee benefits",
        financial_year="2016-17",
        measure_type="actual_accrual_expense",
        estimate_status="audited_actual",
        amount_aud=84180000.0,
    )
    assert matched is None


def test_load_reviewed_duplicates_missing_file_returns_empty(tmp_path):
    assert load_reviewed_duplicates(tmp_path / "does_not_exist.yaml") == []


def test_load_reviewed_duplicates_parses_real_entries(tmp_path):
    path = tmp_path / "reviewed.yaml"
    path.write_text(
        yaml.safe_dump({"reviewed_duplicate_facts": [dict(ENTRY_KWARGS)]}),
        encoding="utf-8",
    )
    entries = load_reviewed_duplicates(path)
    assert len(entries) == 1
    assert entries[0].source_key == "test_source"
    assert entries[0].amount_aud == 84180000.0


def test_load_reviewed_duplicates_rejects_missing_required_field(tmp_path):
    bad_entry = dict(ENTRY_KWARGS)
    del bad_entry["reason"]
    path = tmp_path / "reviewed.yaml"
    path.write_text(
        yaml.safe_dump({"reviewed_duplicate_facts": [bad_entry]}), encoding="utf-8"
    )
    with pytest.raises(InvalidReviewedDuplicateConfig):
        load_reviewed_duplicates(path)


def test_load_reviewed_duplicates_rejects_unknown_classification(tmp_path):
    bad_entry = dict(ENTRY_KWARGS)
    bad_entry["classification"] = "true_duplicate"
    path = tmp_path / "reviewed.yaml"
    path.write_text(
        yaml.safe_dump({"reviewed_duplicate_facts": [bad_entry]}), encoding="utf-8"
    )
    with pytest.raises(InvalidReviewedDuplicateConfig):
        load_reviewed_duplicates(path)


def test_validate_config_accepts_well_formed_registry(tmp_path):
    path = tmp_path / "reviewed.yaml"
    path.write_text(
        yaml.safe_dump({"reviewed_duplicate_facts": [dict(ENTRY_KWARGS)]}),
        encoding="utf-8",
    )
    result = validate_config(path)
    assert result["valid"] is True
    assert result["entry_count"] == 1


def test_validate_config_accepts_empty_registry(tmp_path):
    path = tmp_path / "reviewed.yaml"
    path.write_text(yaml.safe_dump({"reviewed_duplicate_facts": []}), encoding="utf-8")
    result = validate_config(path)
    assert result["valid"] is True
    assert result["entry_count"] == 0


def test_real_repo_config_has_the_expected_reviewed_false_positive_groups():
    """The real registry (config/audit/reviewed_duplicate_facts.yaml) has
    the 4 query-false-positive groups from the database-hygiene
    milestone's Task 3 duplicate-fact investigation, 2 more from the
    MFS-aggregates milestone's Task 7 load (two genuinely different
    reporting months under mfs_ytd_net_capital_investment that happen to
    report the identical cumulative YTD figure - see
    ops/reports/mfs-duplicate-fact-investigation-*.md), and 43 more from
    item 7.1's MFS Note 3 (Total expense by function) load: three lumpy,
    irregular-flow measures (Contingency reserve, Natural disaster relief,
    Nominal superannuation interest) that are genuinely flat across
    several consecutive reporting months in a given year, verified
    directly against the raw workbook for representative years - see
    ops/reports/mfs-note3-duplicate-fact-investigation-*.md. Total: 4 + 2
    + 43 = 49. The original 5th group (QLD QGIP Goondiwindi "Black Spot")
    was a genuine true duplicate, resolved by deletion rather than being
    registered here - a true duplicate must never be reviewed into a
    permanent pass.

    87 more from item 7.5's QLD on-time-payments load: independent quarters
    for the same agency/measure genuinely reporting an identical value
    (task9_sql_integrity_checks.py's duplicate_facts() groups on value but
    not period/quarter) - see
    ops/reports/qld-on-time-payments-duplicate-fact-investigation-*.md.
    Total: 49 + 87 = 136.

    2 more from item 7.1's Tax Notes 1-2 load: two genuinely different
    reporting months within the same financial year reporting an
    identical value (mfs_tax1_petroleum_resource_rent_tax FY2006-07's
    February/March; mfs_tax2_carbon_pricing_mechanism FY2012-13's
    July/August/September, all $0 before the mechanism's first revenue
    landed in October) - see
    ops/reports/mfs-tax-notes-1-2-duplicate-fact-investigation-*.md.
    Total: 136 + 2 = 138.

    29 more from item 7.1's Balance Sheet load: this database's first
    stock (point-in-time balance) source to hit the period-not-in-
    grouping-key false-positive class - a balance genuinely unchanged
    between two consecutive months is a normal real-world outcome, not a
    duplicate insert (e.g. mfs_balance_sheet_assets_held_for_sale
    FY2019-20's March/April 2020 both report $256,000,000). See
    ops/reports/mfs-balance-sheet-duplicate-fact-investigation-*.md.
    Total: 138 + 29 = 167.

    8 more from item 7.4's QLD CFFR quarterly Year-to-Date load: a
    financial year's own "Balance as at 1 July" figure genuinely repeats
    identically across that year's 3 quarterly editions (September/
    December/March), since it restates the same real-world start-of-year
    balance each time, not a duplicate insert - see
    ops/reports/qld-cffr-quarterly-duplicate-fact-investigation-*.md.
    Total: 167 + 8 = 175."""
    result = validate_config()
    assert result["valid"] is True
    assert result["entry_count"] == 175

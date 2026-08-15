"""Tests for load_mfs_tax_notes_1_2.py - focused on what differs from the
already-tested load_mfs_note3_function.py: label-index scoping to
mfs_tax1_*/mfs_tax2_* only, and the only_published_financial_years gating
for mfs_tax1_petroleum_resource_rent_tax (which excludes exactly FY2013-14,
an incomplete child-breakdown of that year's combined "Resource rent
taxes" row, while admitting the 16 other clean years). The revision-
conflict/idempotency machinery is verbatim from the proven Note 3 loader
and is not re-tested here."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_mfs_tax_notes_1_2 as loader  # noqa: E402


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def test_label_index_excludes_other_mfs_siblings(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    assert "Revenue" not in index  # Aggregates
    assert "Defence" not in index  # Note 3
    assert all(mt.startswith(("mfs_tax1_", "mfs_tax2_")) for mt in index.values())


def test_label_index_covers_case_variants(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    assert index["less Refunds"] == "mfs_tax1_less_refunds"
    assert index["less refunds"] == "mfs_tax1_less_refunds"
    assert index["Superannuation funds"] == "mfs_tax1_superannuation_fund_taxes"
    assert index["Superannuation fund taxes"] == "mfs_tax1_superannuation_fund_taxes"
    assert index["Fringe Benefits tax"] == "mfs_tax1_fringe_benefits_tax"
    assert index["Fringe benefits tax"] == "mfs_tax1_fringe_benefits_tax"


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2010-11",
        "amount": 1_000_000.0,
        "measure_label": "Company tax",
        "estimate_status": "actual",
        "month": "July",
        "unit": "$m",
        "sheet": "2010-11",
        "locator": "source_id:federal_mfs_tax_notes_1_2 | sheet:2010-11 | row:Company tax | col:x",
        "cached_copy_path": "x.xlsx",
    }
    row.update(overrides)
    return row


def test_prrt_within_its_clean_years_is_accepted(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(fy="2010-11", measure_label="Petroleum resource rent tax", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, loader.build_label_index(semantics))
    assert reason == ""
    assert fact is not None
    assert fact["measure_type"] == "mfs_tax1_petroleum_resource_rent_tax"


def test_prrt_in_fy2013_14_is_quarantined_not_silently_mixed(semantics: dict, tmp_path, monkeypatch) -> None:
    """FY2013-14's "Petroleum resource rent tax" row is an incomplete
    child breakdown of that year's combined "Resource rent taxes" figure
    (missing July/August, per the source's own footnote) - must never be
    treated as continuous with the clean standalone years."""
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(fy="2013-14", measure_label="Petroleum resource rent tax", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, loader.build_label_index(semantics))
    assert fact is None
    assert reason == "outside_only_published_financial_years"


def test_prrt_outside_all_defined_years_is_quarantined(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(fy="2014-15", measure_label="Petroleum resource rent tax", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, loader.build_label_index(semantics))
    assert fact is None
    assert reason == "outside_only_published_financial_years"


def test_total_income_other_sources_only_fy2005_06(semantics: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    index = loader.build_label_index(semantics)
    ok_row = _base_row(fy="2005-06", measure_label="Total income from other sources", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(ok_row, semantics, index)
    assert reason == ""
    assert fact is not None

    bad_row = _base_row(fy="2006-07", measure_label="Total income from other sources", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(bad_row, semantics, index)
    assert fact is None
    assert reason == "outside_only_published_financial_years"


def test_unrecognized_label_is_quarantined(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    row = _base_row(measure_label="Some Unmapped Tax Line")
    fact, reason = loader.classify_and_validate(row, semantics, index)
    assert fact is None
    assert reason == "unrecognized_label"


def test_fact_key_is_stable_and_identity_complete() -> None:
    key1 = loader.build_fact_key(
        source_family="federal_mfs_tax_notes_1_2", financial_year="2024-25",
        reporting_month="July", measure_type="mfs_tax2_excise_duty",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    key2 = loader.build_fact_key(
        source_family="federal_mfs_tax_notes_1_2", financial_year="2024-25",
        reporting_month="July", measure_type="mfs_tax2_excise_duty",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 == key2
    key3 = loader.build_fact_key(
        source_family="federal_mfs_tax_notes_1_2", financial_year="2024-25",
        reporting_month="August", measure_type="mfs_tax2_excise_duty",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 != key3

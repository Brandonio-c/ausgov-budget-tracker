"""Tests for load_mfs_note3_function.py - focused on what differs from the
already-tested load_mfs_aggregates.py (see test_mfs_loader.py): label-index
scoping to mfs_note3_* only, and only_published_financial_years gating for
mfs_note3_asset_sales. The revision-conflict/idempotency machinery is
verbatim from the proven Aggregates loader and is not re-tested here."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import load_mfs_note3_function as loader  # noqa: E402


@pytest.fixture
def semantics() -> dict:
    return loader.load_semantics()


def test_label_index_excludes_aggregates_measures(semantics: dict) -> None:
    """The Note 3 and Aggregates workbooks share one semantics file - the
    Note 3 loader's label index must never claim an Aggregates label (e.g.
    "Revenue", "Expenses"), even though both files coexist."""
    index = loader.build_label_index(semantics)
    assert "Revenue" not in index
    assert "Expenses" not in index
    assert all(mt.startswith("mfs_note3_") for mt in index.values())


def test_label_index_covers_every_note3_label_variant(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    assert index["Defence"] == "mfs_note3_defence"
    assert index["General public services"] == "mfs_note3_general_public_services"
    assert index["General public services(a)"] == "mfs_note3_general_public_services"
    assert (
        index["Mining and Mineral Resources (other than fuels); \n   Manufacturing and Construction"]
        == "mfs_note3_mining_manufacturing_construction"
    )
    assert index["Mining, manufacturing and construction"] == "mfs_note3_mining_manufacturing_construction"
    assert index["Total expenses"] == "mfs_note3_total_expenses"
    assert index["Asset Sales"] == "mfs_note3_asset_sales"


def _base_row(**overrides) -> dict:
    row = {
        "fy": "2006-07",
        "amount": 1_000_000.0,
        "measure_label": "Defence",
        "estimate_status": "actual",
        "month": "July",
        "unit": "$m",
        "sheet": "2006-07",
        "locator": "source_id:federal_mfs_note3_function | sheet:2006-07 | row:Defence | col:x",
        "cached_copy_path": "data/raw/federal/federal_mfs_note3_function/snapshots/x/files/x.xlsx",
    }
    row.update(overrides)
    return row


def test_asset_sales_within_its_published_years_is_accepted(
    semantics: dict, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    index = loader.build_label_index(semantics)
    row = _base_row(fy="2006-07", measure_label="Asset Sales", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, index)
    assert reason == ""
    assert fact is not None
    assert fact["measure_type"] == "mfs_note3_asset_sales"


def test_asset_sales_outside_its_published_years_is_quarantined(
    semantics: dict, tmp_path, monkeypatch
) -> None:
    """FY2005-06..FY2007-08 only, per the real workbook (folded into
    Contingency reserve from FY2008-09 onward) - a row claiming Asset
    Sales in some other year must be quarantined, not silently accepted."""
    index = loader.build_label_index(semantics)
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    (tmp_path / "x.xlsx").write_bytes(b"stub")
    row = _base_row(fy="2015-16", measure_label="Asset Sales", cached_copy_path="x.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, index)
    assert fact is None
    assert reason == "outside_only_published_financial_years"


def test_unrecognized_label_is_quarantined(semantics: dict) -> None:
    index = loader.build_label_index(semantics)
    row = _base_row(measure_label="Some Unmapped Function")
    fact, reason = loader.classify_and_validate(row, semantics, index)
    assert fact is None
    assert reason == "unrecognized_label"


def test_fact_key_is_stable_and_identity_complete() -> None:
    key1 = loader.build_fact_key(
        source_family="federal_mfs_note3_function", financial_year="2024-25",
        reporting_month="July", measure_type="mfs_note3_defence",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    key2 = loader.build_fact_key(
        source_family="federal_mfs_note3_function", financial_year="2024-25",
        reporting_month="July", measure_type="mfs_note3_defence",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 == key2
    key3 = loader.build_fact_key(
        source_family="federal_mfs_note3_function", financial_year="2024-25",
        reporting_month="August", measure_type="mfs_note3_defence",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="Commonwealth",
    )
    assert key1 != key3

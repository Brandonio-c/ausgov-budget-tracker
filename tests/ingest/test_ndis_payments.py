"""Tests for extractors/ndis_payments.py: the verified-safe support
class -> support category additive slice only (see the module docstring
for why item-level and cross-tabulated views are deliberately excluded)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import ndis_payments as extractor  # noqa: E402


class TestIsCategoryScope:
    def _row(self, **overrides: str) -> dict:
        row = {
            "SuppItemNmbr": "ALL",
            "RsdsInStateCd": "ALL",
            "RsdsInSrvcDstrctNm": "ALL",
            "NDISDsbltyGrpNm": "ALL",
            "NDIAAgeBnd": "ALL",
        }
        row.update(overrides)
        return row

    def test_all_marginal_dims_all_is_category_scope(self) -> None:
        assert extractor._is_category_scope(self._row())

    def test_specific_state_is_not_category_scope(self) -> None:
        # This is the mission's explicit warning case: a row with an
        # additional non-ALL dimension is a cross-tabulation cell (item x
        # geography, etc), not the clean category-level slice.
        row = self._row(RsdsInStateCd="NSW")
        assert not extractor._is_category_scope(row)

    def test_specific_item_is_not_category_scope(self) -> None:
        row = self._row(SuppItemNmbr="15_001_0118_1_3")
        assert not extractor._is_category_scope(row)


class TestExtractIntegration:
    """End-to-end against the real downloaded source file, if present."""

    @pytest.fixture(autouse=True)
    def _require_source(self) -> None:
        if not extractor.IN_CSV.is_file():
            pytest.skip("NDIS payments source CSV not present on disk")

    def test_four_support_class_totals_match_known_reconciliation(self) -> None:
        rows = extractor.extract()
        class_rows = {
            r["category"]: float(r["amount"])
            for r in rows
            if r["category"].count(" / ") == 1
        }
        assert class_rows == {
            f"{extractor.ROOT_NODE} / Capacity Building": 9400381000.00,
            f"{extractor.ROOT_NODE} / Capital": 1517784000.00,
            f"{extractor.ROOT_NODE} / Core": 40533385000.00,
            f"{extractor.ROOT_NODE} / Missing": -3000.00,
        }

    def test_category_sums_reconcile_to_class_totals_within_rounding(self) -> None:
        """The core forensics finding this extractor's scope depends on:
        support category sums must stay within a small rounding tolerance
        of their class total (verified: $2,000 gap on $9.4B for Capacity
        Building; exact for Core/Capital/Missing). If a future edition
        breaks this reconciliation significantly, that is a signal the
        source's own structure changed and this extractor's safety
        assumption needs re-verifying, not silently trusting new data."""
        rows = extractor.extract()
        class_totals: dict[str, float] = {}
        category_sums: dict[str, float] = {}
        for r in rows:
            parts = r["category"].removeprefix(f"{extractor.ROOT_NODE} / ").split(" / ")
            amount = float(r["amount"])
            if len(parts) == 1:
                class_totals[parts[0]] = amount
            else:
                category_sums[parts[0]] = category_sums.get(parts[0], 0.0) + amount
        assert set(class_totals) == set(category_sums)
        for cls, total in class_totals.items():
            gap = abs(category_sums[cls] - total)
            assert gap <= 2000, f"{cls}: category sum {category_sums[cls]} vs total {total}"

    def test_no_item_level_or_cross_tabulated_rows_emitted(self) -> None:
        """Only class and class/category rows - never a fabricated
        deeper level from the source's item x geography or class x
        disability x age joint data (deliberately deferred - see the
        module docstring)."""
        rows = extractor.extract()
        for r in rows:
            depth = r["category"].count(" / ")
            assert depth in (1, 2), r["category"]

    def test_grand_implied_total_does_not_exactly_match_canonical_ndis_figure(self) -> None:
        """Guards the reason this attaches as related_breakdown, not
        same_group, at the canonical boundary: the source's own implied
        grand total is close to but not exactly $53.778B."""
        rows = extractor.extract()
        class_totals = [
            float(r["amount"]) for r in rows if r["category"].count(" / ") == 1
        ]
        implied_total = sum(class_totals)
        assert implied_total == pytest.approx(51451547000.0, abs=1.0)
        assert implied_total != pytest.approx(53778000000.0, abs=1e6)

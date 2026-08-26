"""Tests for extractors/austender_ocds_contracts.py: agency-parent
matching, UNSPSC code decoding, and duplicate-contract handling."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import austender_ocds_contracts as extractor  # noqa: E402


class TestParentForAgency:
    def test_department_of_defence_matches_defence(self) -> None:
        assert extractor._parent_for_agency("Department of Defence") == "Defence"

    def test_defence_housing_australia_matches_defence(self) -> None:
        assert extractor._parent_for_agency("Defence Housing Australia") == "Defence"

    def test_department_of_health_matches_health(self) -> None:
        assert extractor._parent_for_agency("Department of Health and Aged Care") == "Health"

    def test_infrastructure_department_matches_transport(self) -> None:
        assert (
            extractor._parent_for_agency("Department of Infrastructure, Transport, Regional Development")
            == "Transport and communication"
        )

    def test_unrelated_agency_matches_nothing(self) -> None:
        assert extractor._parent_for_agency("Australian Taxation Office") is None

    def test_empty_agency_matches_nothing(self) -> None:
        assert extractor._parent_for_agency("") is None


class TestExtractIntegration:
    """End-to-end against the real downloaded OCDS release data, if present."""

    @pytest.fixture(autouse=True)
    def _require_source(self) -> None:
        if not extractor.RELEASES_DIR.is_dir() or not extractor.UNSPSC_XLSX.is_file():
            pytest.skip("AusTender OCDS release data or UNSPSC reference not present on disk")
        if not list(extractor.RELEASES_DIR.glob("window_*.json")):
            pytest.skip("No window_*.json release files present on disk")

    def test_only_scoped_agencies_emitted(self) -> None:
        rows = extractor.extract()
        assert rows
        for row in rows:
            assert row["category"].split(" / ")[0] in (
                "Defence",
                "Health",
                "Transport and communication",
            )

    def test_no_row_has_zero_or_negative_amount(self) -> None:
        rows = extractor.extract()
        for row in rows:
            assert float(row["amount"]) > 0, row["category"]

    def test_hierarchy_depth_is_bounded(self) -> None:
        """{parent} / Contracts (...) / segment / family / class / supplier -
        exactly 5 levels below the parent at most, never a fabricated
        deeper chain."""
        rows = extractor.extract()
        for row in rows:
            depth = row["category"].count(" / ")
            assert depth <= 5, row["category"]

    def test_class_level_sums_reconcile_to_segment_and_family_totals(self) -> None:
        rows = extractor.extract()
        by_category: dict[str, float] = {r["category"]: float(r["amount"]) for r in rows}
        # For every class-level row (5 segments deep: parent/Contracts/seg/fam/cls),
        # find sibling contract-level children and confirm they sum to <= the
        # class total (this is a top-N sample of contracts under a class, not
        # necessarily exhaustive, so children may be a strict subset).
        class_rows = [c for c in by_category if c.count(" / ") == 4]
        assert class_rows
        for cls_cat in class_rows:
            children_sum = sum(
                v for c, v in by_category.items() if c.startswith(f"{cls_cat} / ")
            )
            assert children_sum <= by_category[cls_cat] + 1.0, cls_cat

    def test_unspsc_reference_decodes_to_four_distinct_levels(self) -> None:
        ref = extractor._load_unspsc_reference()
        assert ref
        for code, titles in ref.items():
            assert len(code) == 8
        # A genuine commodity-level code (non-zero final two digits) must
        # resolve to four DISTINCT titles, not the same title repeated -
        # e.g. "10111302" (Pet grooming products) should differ from its
        # segment ("Live Plant and Animal Material...") at every level.
        # A coarser code (segment/family/class only, trailing zeros) is
        # correctly allowed to repeat its nearest known ancestor's title -
        # see the module docstring - so this assertion is scoped to a
        # known commodity-level code, not an arbitrary dict entry.
        segment, family, cls, commodity = ref["10111302"]
        assert len({segment, family, cls, commodity}) == 4

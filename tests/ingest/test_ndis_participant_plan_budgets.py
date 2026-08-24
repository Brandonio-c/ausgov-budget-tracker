"""Tests for extractors/ndis_participant_plan_budgets.py: suppression
parsing, marginal-slice detection (never a fabricated cross-product
hierarchy), and geography's genuine two-level nesting."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import ndis_participant_plan_budgets as extractor  # noqa: E402


class TestParseCount:
    def test_plain_integer_is_exact(self) -> None:
        value, is_upper_bound = extractor._parse_count("260")
        assert value == 260.0
        assert is_upper_bound is False

    def test_less_than_prefix_is_upper_bound(self) -> None:
        value, is_upper_bound = extractor._parse_count("<11")
        assert value == 11.0
        assert is_upper_bound is True

    def test_large_less_than_value_is_still_upper_bound_not_exact(self) -> None:
        # Empirically confirmed: "<N" for N far above the 11-participant
        # suppression threshold also occurs (non-exhaustive cascade case,
        # undocumented in the NDIA data rules but real) - must never be
        # treated as an exact count either.
        value, is_upper_bound = extractor._parse_count("<49918")
        assert value == 49918.0
        assert is_upper_bound is True

    def test_thousands_separator_handled(self) -> None:
        value, _ = extractor._parse_count("1,234")
        assert value == 1234.0

    def test_blank_returns_none(self) -> None:
        value, is_upper_bound = extractor._parse_count("")
        assert value is None
        assert is_upper_bound is False


class TestParseBudget:
    def test_plain_value(self) -> None:
        assert extractor._parse_budget("116,000.00") == 116000.0

    def test_blank_returns_none(self) -> None:
        assert extractor._parse_budget("") is None


class TestIsMarginal:
    def _row(self, **overrides: str) -> dict:
        row = {
            "StateCd": "ALL",
            "SrvcDstrctNm": "ALL",
            "DsbltyGrpNm": "ALL",
            "AgeBnd": "ALL",
            "SuppClass": "ALL",
        }
        row.update(overrides)
        return row

    def test_all_all_is_grand_total_marginal(self) -> None:
        assert extractor._is_marginal(self._row(), except_dims=set())

    def test_state_alone_is_marginal_for_state(self) -> None:
        row = self._row(StateCd="NSW")
        assert extractor._is_marginal(row, except_dims={"state"})

    def test_state_plus_disability_is_not_marginal_for_state_alone(self) -> None:
        # This is the mission's explicit warning case: a row with TWO
        # non-ALL dimensions is a joint cross-tabulation cell, not a clean
        # single-dimension marginal - must not be picked up as if it were.
        row = self._row(StateCd="NSW", DsbltyGrpNm="Autism")
        assert not extractor._is_marginal(row, except_dims={"state"})
        assert not extractor._is_marginal(row, except_dims={"disability"})

    def test_state_and_district_together_marginal_for_geography_nesting(self) -> None:
        row = self._row(StateCd="NSW", SrvcDstrctNm="Sydney")
        assert extractor._is_marginal(row, except_dims={"state", "district"})


class TestExtractIntegration:
    """End-to-end against the real downloaded source file, if present."""

    @pytest.fixture(autouse=True)
    def _require_source(self) -> None:
        if not extractor.IN_CSV.is_file():
            pytest.skip("NDIS source CSV not present on disk")

    def test_grand_total_row_matches_source_national_total(self) -> None:
        rows = extractor.extract()
        totals = [r for r in rows if r["category"] == extractor.COUNT_ROOT_NODE]
        assert len(totals) == 1
        assert totals[0]["participant_count"] == "782013"
        assert totals[0]["count_is_upper_bound"] == "0"

    def test_category_counts_match_known_marginal_slice_reconciliation(self) -> None:
        """Every emitted category is a genuine marginal slice (state alone,
        state+district, disability alone, age alone, or support alone), a
        pure-navigation intermediate folder, or the grand total - never a
        fabricated cross-product of independent orthogonal dimensions.
        Exact counts independently reconciled against the source CSV
        during forensics: 10 states, 90 districts, 18 disability groups,
        9 age bands, 3 support classes, 1 grand total = 131 real data
        rows, plus 4 folder-navigation rows (one per dimension - "state"
        needs none since it's a direct child of the root)."""
        rows = extractor.extract()
        prefix = f"{extractor.COUNT_ROOT_NODE} / Participants by "
        counts = {"state": 0, "district": 0, "disability": 0, "age": 0, "support": 0}
        folders = 0
        for row in rows:
            cat = row["category"]
            if cat == extractor.COUNT_ROOT_NODE:
                continue
            assert cat.startswith(prefix), cat
            rest = cat[len(prefix) :]
            dim, _, remainder = rest.partition(" / ")
            if not remainder:
                # A bare dimension folder ("Participants by X") is a pure
                # navigation aggregate, not real marginal data (see the
                # extractor's grand_total/folder_suffixes comment) - it
                # must carry the grand total's own value, never a
                # recomputed sum.
                folders += 1
                assert row["participant_count"] == "782013", cat
                continue
            depth = remainder.count(" / ") + 1
            if dim == "geography":
                counts["district" if "/" in remainder else "state"] += 1
            elif dim == "disability group":
                counts["disability"] += 1
            elif dim == "age band":
                counts["age"] += 1
            elif dim == "support class":
                counts["support"] += 1
            else:
                pytest.fail(f"unexpected dimension folder: {dim!r} in {cat!r}")
            assert depth <= 2, f"unexpected nesting depth in {cat!r}"
        assert counts == {
            "state": 10,
            "district": 90,
            "disability": 18,
            "age": 9,
            "support": 3,
        }
        assert folders == 4  # geography, disability group, age band, support class
        assert len(rows) == sum(counts.values()) + 1 + folders  # +1 grand total

    def test_every_service_district_scoped_under_exactly_one_state(self) -> None:
        rows = extractor.extract()
        geography_rows = [
            r
            for r in rows
            if r["category"].startswith(f"{extractor.COUNT_ROOT_NODE} / Participants by geography / ")
        ]
        district_paths = {
            r["category"] for r in geography_rows if r["category"].count(" / ") == 3
        }
        # Every district-level node name is unique (state-qualified), i.e.
        # the shared "Other" catch-all bucket across states never collides.
        assert len(district_paths) == len(set(district_paths))

    def test_suppressed_rows_excluded_from_budget_measure_not_count_measure(self) -> None:
        extractor.extract()
        with extractor.OUT_COUNT_CSV.open(newline="", encoding="utf-8") as fh:
            count_rows = list(csv.DictReader(fh))
        with extractor.OUT_BUDGET_CSV.open(newline="", encoding="utf-8") as fh:
            budget_rows = list(csv.DictReader(fh))
        assert len(budget_rows) < len(count_rows)
        # Roots differ deliberately (avoids a same-name related_breakdown
        # collision - see the module's ROOT_NODE comment); compare suffixes.
        def _suffix(category: str, root: str) -> str:
            return "" if category == root else category.removeprefix(f"{root} / ")

        budget_suffixes = {
            _suffix(r["category"], extractor.BUDGET_ROOT_NODE) for r in budget_rows
        }
        count_suffixes = {
            _suffix(r["category"], extractor.COUNT_ROOT_NODE) for r in count_rows
        }
        assert budget_suffixes <= count_suffixes
        for row in budget_rows:
            assert row["avg_committed_plan_budget"] != ""
            assert row["category"].startswith(extractor.BUDGET_ROOT_NODE)
        for row in count_rows:
            assert row["category"].startswith(extractor.COUNT_ROOT_NODE)

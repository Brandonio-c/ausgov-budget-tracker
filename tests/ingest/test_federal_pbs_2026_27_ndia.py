"""Regression checks for the bounded 2026-27 NDIA PBS adapter (item 5.5).

The generalized federal_pbs_programs_all.py adapter yields zero published
facts for this source (its cross-document dedupe silently discards every
NDIA row as an apparent duplicate of the unrelated, larger "Health
Disability and Ageing" document it shares a portfolio label with). This
bounded, source-specific adapter is the repair.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from extractors.federal_pbs_2026_27_ndia import extract  # noqa: E402, I001

EXPECTED_PROGRAM_TOTALS = {
    ("1.1", "2025-26"): 51_302_834_000,
    ("1.1", "2026-27"): 53_703_813_000,
    ("1.1", "2027-28"): 53_787_683_000,
    ("1.1", "2028-29"): 54_273_595_000,
    ("1.1", "2029-30"): 54_781_239_000,
    ("1.2", "2025-26"): 2_860_629_000,
    ("1.2", "2026-27"): 2_767_095_000,
    ("1.2", "2027-28"): 1_610_062_000,
    ("1.2", "2028-29"): 1_627_986_000,
    ("1.2", "2029-30"): 1_747_592_000,
}


@pytest.fixture(scope="module")
def rows():
    try:
        return extract()
    except FileNotFoundError as error:
        pytest.skip(f"NDIA acquisition is not present: {error}")


def test_row_counts_and_kinds(rows):
    assert len(rows) == 50
    assert Counter(row["row_kind"] for row in rows) == {"component": 40, "program": 10}
    assert {row["fy"] for row in rows} == {
        "2025-26",
        "2026-27",
        "2027-28",
        "2028-29",
        "2029-30",
    }
    assert {row["program_number"] for row in rows} == {"1.1", "1.2"}


def test_rows_are_unique(rows):
    keys = [(row["fy"], row["category"], row["estimate_status"]) for row in rows]
    assert len(keys) == len(set(keys))


def test_component_sums_reconcile_with_published_program_totals(rows):
    component_sum: dict[tuple[str, str], int] = defaultdict(int)
    program_total: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["program_number"], row["fy"])
        if row["row_kind"] == "component":
            component_sum[key] += row["amount"]
        else:
            program_total[key] = row["amount"]

    assert program_total == EXPECTED_PROGRAM_TOTALS
    for key, total in program_total.items():
        assert component_sum[key] == total, (key, component_sum[key], total)


def test_outcome_reconciliation_table_is_excluded(rows):
    for row in rows:
        assert "totals by resource type" not in row["category"].lower()
        assert "average staffing" not in row["category"].lower()


def test_every_row_has_exact_year_citation_and_locator(rows):
    for row in rows:
        assert row["locator"]
        assert f"fy:{row['fy']}" in row["locator"]
        assert row["landing_url"].startswith("https://")
        assert row["resource_url"].startswith("https://")
        assert row["cached_copy_path"]

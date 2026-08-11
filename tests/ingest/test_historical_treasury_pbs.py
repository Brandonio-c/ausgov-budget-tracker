"""Regression checks for the three bounded historical Treasury PBS editions."""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from extractors.historical_treasury_pbs import EDITIONS, extract_edition  # noqa: E402, I001

EXPECTED = {
    "federal_pbs_2022_23_march_treasury": {
        "rows": 710,
        "kinds": {"component": 495, "program": 215},
        "entities": 14,
        "programs": 43,
        "outcomes": 14,
        "fys": {"2021-22", "2022-23", "2023-24", "2024-25", "2025-26"},
    },
    "federal_pbs_2022_23_october_treasury": {
        "rows": 675,
        "kinds": {"component": 460, "program": 215},
        "entities": 14,
        "programs": 43,
        "outcomes": 14,
        "fys": {"2021-22", "2022-23", "2023-24", "2024-25", "2025-26"},
    },
    "federal_pbs_2023_24_treasury": {
        "rows": 620,
        "kinds": {"component": 425, "program": 195},
        "entities": 15,
        "programs": 39,
        "outcomes": 15,
        "fys": {"2022-23", "2023-24", "2024-25", "2025-26", "2026-27"},
    },
}

# Rows whose component sum differs from the published "Total expenses for
# program" row by exactly one $'000 unit (i.e. $1,000). Australian Budget
# documents round every line independently, so a handful of programs never
# reconcile to the cent; these three are the full, reviewed exception list
# for Department of the Treasury Program 1.1 in the March edition.
ROUNDING_TOLERANCE = 1_000
KNOWN_ROUNDING_EXCEPTIONS = {
    ("federal_pbs_2022_23_march_treasury", "Department of the Treasury", "1.1", "2022-23"),
    ("federal_pbs_2022_23_march_treasury", "Department of the Treasury", "1.1", "2023-24"),
    ("federal_pbs_2022_23_march_treasury", "Department of the Treasury", "1.1", "2024-25"),
}


@pytest.fixture(scope="module")
def extracted():
    try:
        return {edition.source_id: extract_edition(edition) for edition in EDITIONS}
    except FileNotFoundError as error:
        pytest.skip(f"historical Treasury PBS acquisition is not present: {error}")


@pytest.mark.parametrize("source_id", sorted(EXPECTED))
def test_edition_layout_counts(extracted, source_id):
    rows = extracted[source_id]
    expected = EXPECTED[source_id]

    assert len(rows) == expected["rows"]
    assert Counter(row["row_kind"] for row in rows) == expected["kinds"]
    assert len({row["entity"] for row in rows}) == expected["entities"]
    assert len({(row["entity"], row["program_number"]) for row in rows}) == expected["programs"]
    assert len({(row["entity"], row["outcome"]) for row in rows}) == expected["outcomes"]
    assert {row["fy"] for row in rows} == expected["fys"]


@pytest.mark.parametrize("source_id", sorted(EXPECTED))
def test_edition_rows_are_unique_and_preserve_vintage(extracted, source_id):
    rows = extracted[source_id]
    edition = next(e for e in EDITIONS if e.source_id == source_id)

    keys = [(row["fy"], row["category"], row["estimate_status"]) for row in rows]
    assert len(keys) == len(set(keys))
    assert {row["publication_edition"] for row in rows} == {edition.publication_edition}
    assert {row["publication_vintage"] for row in rows} == {edition.publication_vintage}
    assert {row["source_id_origin"] for row in rows} == {source_id}


def test_march_and_october_2022_23_remain_distinct_vintages(extracted):
    march = extracted["federal_pbs_2022_23_march_treasury"]
    october = extracted["federal_pbs_2022_23_october_treasury"]
    assert {r["publication_vintage"] for r in march} != {r["publication_vintage"] for r in october}
    march_amounts = {(r["fy"], r["category"], r["amount"]) for r in march}
    october_amounts = {(r["fy"], r["category"], r["amount"]) for r in october}
    assert march_amounts != october_amounts


@pytest.mark.parametrize("source_id", sorted(EXPECTED))
def test_component_sums_reconcile_with_published_program_totals(extracted, source_id):
    """Every extracted "component" row for a program/year must sum to the
    program's own published "Total expenses for program" row, within
    documented $1,000 rounding, proving no row was mis-attributed, dropped,
    or double-counted across program/scope/heading/table boundaries."""
    rows = extracted[source_id]
    component_sum: dict[tuple[str, str, str], int] = defaultdict(int)
    program_total: dict[tuple[str, str, str], int] = {}
    for row in rows:
        key = (row["entity"], row["program_number"], row["fy"])
        if row["row_kind"] == "component":
            component_sum[key] += row["amount"]
        else:
            program_total[key] = row["amount"]

    assert program_total, "expected at least one program total row"
    for key, total in program_total.items():
        entity, program_number, fy = key
        delta = component_sum.get(key, 0) - total
        exception_key = (source_id, entity, program_number, fy)
        if exception_key in KNOWN_ROUNDING_EXCEPTIONS:
            assert 0 < abs(delta) <= ROUNDING_TOLERANCE, (source_id, key, delta)
        else:
            assert delta == 0, (source_id, key, delta)


def test_outcome_totals_by_appropriation_type_are_excluded(extracted):
    """The cross-program "Outcome N Totals by appropriation type" and
    "Movement of administered funds between years" reconciliation tables
    must never be attributed to the preceding program as a component."""
    for rows in extracted.values():
        for row in rows:
            assert "totals by appropriation type" not in row["category"].lower()
            assert "movement of administered" not in row["category"].lower()
            assert row["component_label"] != ""


def test_every_row_has_exact_year_citation_and_locator(extracted):
    for rows in extracted.values():
        for row in rows:
            assert row["locator"]
            assert f"fy:{row['fy']}" in row["locator"]
            assert row["landing_url"].startswith("https://")
            assert row["resource_url"].startswith("https://")
            assert row["cached_copy_path"]

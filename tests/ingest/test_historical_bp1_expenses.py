"""Regression checks for the three bounded historical BP1 expense layouts."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from extractors.historical_bp1_expenses import EDITIONS, extract_edition  # noqa: E402, I001

EXPECTED = {
    "federal_budget_statement_6_2022_23_march": {
        "rows": 765,
        "kinds": {"function": 70, "subfunction": 340, "component": 350, "grand_total": 5},
        "totals": {
            "2021-22": 639_569_000_000,
            "2022-23": 628_469_000_000,
            "2023-24": 643_833_000_000,
            "2024-25": 665_369_000_000,
            "2025-26": 686_839_000_000,
        },
        "table_prefix": "Table 5",
        "component_categories": 70,
    },
    "federal_budget_statement_6_2022_23_october": {
        "rows": 616,
        "kinds": {"function": 56, "subfunction": 272, "component": 284, "grand_total": 4},
        "totals": {
            "2022-23": 650_922_000_000,
            "2023-24": 666_465_000_000,
            "2024-25": 702_253_000_000,
            "2025-26": 730_960_000_000,
        },
        "table_prefix": "Table 6",
        "component_categories": 71,
    },
    "federal_budget_statement_6_2023_24": {
        "rows": 765,
        "kinds": {"function": 70, "subfunction": 340, "component": 350, "grand_total": 5},
        "totals": {
            "2022-23": 644_788_000_000,
            "2023-24": 684_085_000_000,
            "2024-25": 715_382_000_000,
            "2025-26": 743_324_000_000,
            "2026-27": 771_779_000_000,
        },
        "table_prefix": "Table 6",
        "component_categories": 70,
    },
}


@pytest.fixture(scope="module")
def extracted():
    try:
        return {edition.source_id: extract_edition(edition) for edition in EDITIONS}
    except FileNotFoundError as error:
        pytest.skip(f"historical BP1 acquisition is not present: {error}")


@pytest.mark.parametrize("source_id", sorted(EXPECTED))
def test_edition_layout_counts_and_published_totals(extracted, source_id):
    rows = extracted[source_id]
    expected = EXPECTED[source_id]

    assert len(rows) == expected["rows"]
    assert Counter(row["row_kind"] for row in rows) == expected["kinds"]
    assert {
        row["fy"]: row["amount"] for row in rows if row["row_kind"] == "grand_total"
    } == expected["totals"]
    assert len({row["category"] for row in rows if row["row_kind"] == "component"}) == expected["component_categories"]
    assert all(expected["table_prefix"] in row["locator"] for row in rows)


def test_editions_preserve_vintage_and_exclude_actual_columns(extracted):
    by_id = {edition.source_id: edition for edition in EDITIONS}
    for source_id, rows in extracted.items():
        edition = by_id[source_id]
        assert {row["publication_edition"] for row in rows} == {edition.publication_edition}
        assert {row["publication_vintage"] for row in rows} == {edition.publication_vintage}
        assert "actual" not in {row["estimate_status"] for row in rows}
        assert len(rows) == len({(row["fy"], row["category"], row["estimate_status"]) for row in rows})


def test_component_paths_are_beneath_verified_appendix_parents(extracted):
    for rows in extracted.values():
        appendix_paths = {
            row["category"]
            for row in rows
            if row["row_kind"] in {"function", "subfunction"}
        }
        for row in rows:
            if row["row_kind"] != "component":
                continue
            parent = row["category"].rsplit(" / ", 1)[0]
            assert parent in appendix_paths

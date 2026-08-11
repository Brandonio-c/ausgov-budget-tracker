"""Historical Treasury PBS program detail beneath Statement 6 (item 5.4).

Covers the Wave 3 exit gate: "at least one 2022-23 and one 2023-24
representative function has a verified function -> subfunction/component ->
PBS-program route, with exact edition metadata, no future fallback and
complete citations." Scoped to the Treasury portfolio only (March 2022-23
and 2023-24 editions), per config/breakdowns/crosswalks/
historical_pbs_treasury_under_statement6.yaml.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

DB = REPO_ROOT / "data" / "facts.db"

EDITIONS = [
    ("federal_pbs_2022_23_march_treasury", "federal_budget_statement_6_2022_23_march", "2022-23", 43),
    ("federal_pbs_2023_24_treasury", "federal_budget_statement_6_2023_24", "2023-24", 39),
]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FACTS_DB_PATH", str(DB))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = DB
    from backend.main import app

    return TestClient(app)


def _s6_fact_id(s6_source_key: str, year: str) -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT f.id
            FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = ? AND n.name = 'General public services' AND f.financial_year = ?
            """,
            (s6_source_key, year),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"no General public services fact for {s6_source_key}/{year}"
    return int(row[0])


def test_edge_set_registered_and_matches_expected_program_counts() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        for pbs_source, s6_source, _year, expected_programs in EDITIONS:
            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM breakdown_edges e
                JOIN nodes c ON c.id = e.child_node_id
                JOIN source_documents cd ON cd.id = c.source_document_id
                WHERE e.crosswalk_id = 'historical_pbs_treasury_under_statement6'
                  AND e.edge_kind = 'related_breakdown'
                  AND cd.source_key = ?
                """,
                (pbs_source,),
            ).fetchone()[0]
            assert count == expected_programs, (pbs_source, count, expected_programs)
    finally:
        conn.close()


def test_edges_do_not_cross_editions() -> None:
    """Every edge's child (PBS) node and parent (Statement 6) node must
    belong to the *same* publication edition - never March PBS wired under
    the 2023-24 Statement 6 node or vice versa."""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT pd.source_key, cd.source_key
            FROM breakdown_edges e
            JOIN nodes p ON p.id = e.parent_node_id
            JOIN nodes c ON c.id = e.child_node_id
            JOIN source_documents pd ON pd.id = p.source_document_id
            JOIN source_documents cd ON cd.id = c.source_document_id
            WHERE e.crosswalk_id = 'historical_pbs_treasury_under_statement6'
            """
        ).fetchall()
    finally:
        conn.close()
    assert rows
    valid_pairs = {(s6, pbs) for pbs, s6, _year, _n in EDITIONS}
    for parent_source, child_source in rows:
        assert (parent_source, child_source) in valid_pairs


@pytest.mark.parametrize("pbs_source,s6_source,year,expected_programs", EDITIONS)
def test_related_children_are_exact_year_with_complete_citations(
    client: TestClient, pbs_source: str, s6_source: str, year: str, expected_programs: int
) -> None:
    fact_id = _s6_fact_id(s6_source, year)
    r = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": year})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "related_breakdown"
    assert len(data["children"]) == expected_programs

    for child in data["children"]:
        rel = child["relationship"]
        assert rel["edge_kind"] == "related_breakdown"
        assert rel["branch_kind"] == "related"
        assert rel["source_key"] == pbs_source
        assert rel["fact_financial_year"] == year
        assert rel["requested_financial_year"] == year
        assert rel["is_year_fallback"] is False
        assert rel["fallback_reason"] == "exact_year_match"
        assert child["id"] is not None  # every child has its own citable fact


def test_no_future_or_nearest_year_fallback_for_uncovered_year(client: TestClient) -> None:
    fact_id = _s6_fact_id("federal_budget_statement_6_2022_23_march", "2022-23")
    r = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": "2020-21"})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "empty"
    assert data["children"] == []


@pytest.mark.parametrize(
    "year,expected_root_total",
    [("2022-23", 1_629_222_000.0), ("2023-24", 1_818_520_572_000.0)],
)
def test_root_total_still_unaffected_after_edge_deployment(
    client: TestClient, year: str, expected_root_total: float
) -> None:
    r = client.get(
        "/v2/dashboard/tree", params={"mode": "budget", "level": "federal", "year": year}
    )
    assert r.status_code == 200
    assert r.json()["value"] == pytest.approx(expected_root_total)

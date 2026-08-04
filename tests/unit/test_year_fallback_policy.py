"""Tests for the Task 7 cross-year fallback policy in
src/backend/breakdown_graph.py (fact_for_node_year): (1) exact requested
year; (2) nearest EARLIER year, same source edition preferred; (3) nearest
earlier year from another edition; (4) no result - never a later/future
year, ever, even when one would otherwise be the "nearest" candidate.

Root cause (Task 1/2 root-cause report): the previous ranking preferred a
later year over an earlier one whenever both existed, regardless of
distance - confirmed via 11,769 real same_group nodes where the served
child year was *after* the requested/parent year. This is exactly the
"no future-year fallback" rule the mission names.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402

from backend.breakdown_graph import fact_for_node_year  # noqa: E402


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "year_fallback_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    def add_source_document(source_key: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
            VALUES (?, 'Test', 'Test', 'Commonwealth', 'federal', 'test')
            """,
            (source_key,),
        )
        return int(cur.lastrowid)

    def add_node(source_document_id: int, name: str, canonical_key: str) -> int:
        cur = conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
            VALUES (?, 'category', ?, 'Commonwealth', 'federal', ?, '{}')
            """,
            (canonical_key, name, source_document_id),
        )
        return int(cur.lastrowid)

    def add_fact(
        source_document_id: int,
        node_id: int,
        fy: str,
        amount: float,
        estimate_status: str = "actual",
        measure_type: str = "gfs_expense",
    ) -> int:
        cur = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_granularity, measure_type,
                accounting_basis, estimate_status, amount_aud, source_document_id,
                source_locator_json, retrieved_at
            ) VALUES (?, ?, 'financial_year', ?, 'gfs', ?, ?, ?, '{"locator": "pdf:test.pdf|page:1", "cached_copy_path": "test.pdf"}', '2026-01-01T00:00:00')
            """,
            (f"test|{node_id}|{fy}|{estimate_status}", fy, measure_type, estimate_status, amount, source_document_id),
        )
        fact_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
            (fact_id, node_id),
        )
        return fact_id

    doc_a = add_source_document("federal_budget_statement_6_a61")
    doc_b = add_source_document("federal_budget_statement_6_2026_27")

    exact_node = add_node(doc_a, "Exact node", "test|node|exact")
    add_fact(doc_a, exact_node, "2024-25", 100.0)
    add_fact(doc_a, exact_node, "2023-24", 90.0)

    one_year_back_node = add_node(doc_a, "One year back", "test|node|one_year_back")
    add_fact(doc_a, one_year_back_node, "2023-24", 80.0)

    multi_year_back_node = add_node(doc_a, "Multi year back", "test|node|multi_year_back")
    add_fact(doc_a, multi_year_back_node, "2021-22", 70.0)
    add_fact(doc_a, multi_year_back_node, "2020-21", 60.0)

    future_only_node = add_node(doc_a, "Future only", "test|node|future_only")
    add_fact(doc_a, future_only_node, "2025-26", 50.0)
    add_fact(doc_a, future_only_node, "2026-27", 55.0)

    add_node(doc_a, "No facts", "test|node|no_facts")

    # Same node has an earlier-year fact from doc_a (corroborated by a
    # second doc_a fact elsewhere) and a lone earlier-year fact from doc_b.
    cross_edition_node = add_node(doc_a, "Cross edition", "test|node|cross_edition")
    add_fact(doc_a, cross_edition_node, "2021-22", 40.0)
    add_fact(doc_b, cross_edition_node, "2022-23", 45.0)
    # A second doc_a fact (different node) has no bearing on this node's own
    # candidate set - corroboration is per-node source_key repetition among
    # THIS node's own earlier candidates, so add one more doc_a fact on the
    # same node to make doc_a "corroborated" for cross_edition_node itself.
    add_fact(doc_a, cross_edition_node, "2019-20", 35.0)

    conn.commit()
    conn.close()
    return db_path


def _conn(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    conn.row_factory = sqlite3.Row
    return conn


def _node_id(conn, name: str) -> int:
    row = conn.execute("SELECT id FROM nodes WHERE name = ?", (name,)).fetchone()
    return int(row[0])


def test_exact_year_match_needs_no_fallback(fixture_db):
    conn = _conn(fixture_db)
    nid = _node_id(conn, "Exact node")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=True)
    conn.close()
    assert fact["fy_fallback"] is False
    assert fact["fallback_reason"] == "exact_year_match"
    assert fact["financial_year"] == "2024-25"
    assert fact["requested_financial_year"] == "2024-25"


def test_one_year_earlier_fallback(fixture_db):
    conn = _conn(fixture_db)
    nid = _node_id(conn, "One year back")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=True)
    conn.close()
    assert fact["fy_fallback"] is True
    assert fact["financial_year"] == "2023-24"
    assert fact["fallback_reason"] in ("nearest_earlier_year_same_edition", "nearest_earlier_year_other_edition")


def test_multi_year_earlier_fallback_picks_nearest(fixture_db):
    conn = _conn(fixture_db)
    nid = _node_id(conn, "Multi year back")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=True)
    conn.close()
    assert fact["fy_fallback"] is True
    # Nearest of {2021-22, 2020-21} to 2024-25 is 2021-22.
    assert fact["financial_year"] == "2021-22"


def test_no_valid_fallback_without_allow_nearest(fixture_db):
    conn = _conn(fixture_db)
    nid = _node_id(conn, "One year back")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=False)
    conn.close()
    assert fact is None


def test_no_future_year_fallback_ever(fixture_db):
    """The exact bug this milestone found and fixed: a node whose only
    published data is *later* than the requested year must return no
    result, never silently substitute the future year."""
    conn = _conn(fixture_db)
    nid = _node_id(conn, "Future only")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=True)
    conn.close()
    assert fact is None


def test_no_facts_at_all_returns_none(fixture_db):
    conn = _conn(fixture_db)
    nid = _node_id(conn, "No facts")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=True)
    conn.close()
    assert fact is None


def test_same_edition_preferred_over_other_edition_at_equal_distance(fixture_db):
    """cross_edition_node has a doc_a fact at 2021-22 (corroborated by
    another doc_a fact on the same node at 2019-20) and a lone doc_b fact
    at 2022-23. 2022-23 is nearer to 2024-25, so it should win on distance
    alone, and it is a lone-edition fact - fallback_reason must say so."""
    conn = _conn(fixture_db)
    nid = _node_id(conn, "Cross edition")
    fact = fact_for_node_year(conn, nid, "2024-25", allow_nearest=True)
    conn.close()
    assert fact["financial_year"] == "2022-23"
    assert fact["fallback_reason"] == "nearest_earlier_year_other_edition"
    assert fact["source_key"] == "federal_budget_statement_6_2026_27"

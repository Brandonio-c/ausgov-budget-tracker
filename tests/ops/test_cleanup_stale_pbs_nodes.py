"""Tests for scripts/ops/cleanup_stale_pbs_nodes.py (Task 8 of the
semantic-defect milestone).

Covers the exact bug found and fixed while building this script: a naive
"currently has zero facts" staleness check would have deleted 9,791 real
same_group edges belonging to legitimate, permanently fact-less PBS
portfolio-folder nodes (confirmed against the real data/facts.db via a
dry run before this was ever executed for real). Staleness must be a
transition (had a fact before the reload, has none after), never a
snapshot of the current state alone.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from cleanup_stale_pbs_nodes import cleanup, fact_bearing_pbs_node_ids  # noqa: E402
from schema_migrate import migrate  # noqa: E402


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "cleanup_fixture.db"
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

    def add_fact(source_document_id: int, node_id: int, fy: str, amount: float) -> int:
        cur = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_granularity, measure_type,
                accounting_basis, estimate_status, amount_aud, source_document_id,
                source_locator_json, retrieved_at
            ) VALUES (?, ?, 'financial_year', 'budget_estimate', 'accrual', 'budget', ?, ?, '{}', '2026-01-01T00:00:00')
            """,
            (f"test|{node_id}|{fy}", fy, amount, source_document_id),
        )
        fact_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
            (fact_id, node_id),
        )
        return fact_id

    def add_edge(parent_id: int, child_id: int, edge_kind: str, crosswalk_id: str | None = None) -> None:
        conn.execute(
            """
            INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id, financial_year, priority)
            VALUES (?, ?, ?, ?, NULL, 100)
            """,
            (parent_id, child_id, edge_kind, crosswalk_id),
        )

    pbs_doc = add_source_document("federal_pbs_programs_all")
    other_doc = add_source_document("some_other_source")

    # Folder node - NEVER has a direct fact, by design (mirrors real
    # portfolio folders like "Defence"). Must never be touched even though
    # it always has zero fact_nodes rows.
    folder = add_node(pbs_doc, "Some Portfolio", "pbs|node|folder")

    # Leaf that will be orphaned by a simulated reload: has a fact now,
    # linked from the folder via same_group, and will lose its fact.
    orphaned_leaf = add_node(pbs_doc, "Some Portfolio / Program 1.1", "pbs|node|orphaned_leaf")
    orphaned_fact_id = add_fact(pbs_doc, orphaned_leaf, "2024-25", 1_000_000)
    add_edge(folder, orphaned_leaf, "same_group")

    # Leaf that survives the reload (keeps its fact) - must never be
    # touched.
    surviving_leaf = add_node(pbs_doc, "Some Portfolio / Program 1.2", "pbs|node|surviving_leaf")
    add_fact(pbs_doc, surviving_leaf, "2024-25", 2_000_000)
    add_edge(folder, surviving_leaf, "same_group")

    # Leaf orphaned by the reload but ALSO referenced by an edge from a
    # non-orphaned node elsewhere (e.g. a related_breakdown crosswalk edge
    # from a Statement 6 node) - must be excluded from deletion (kept,
    # reported) since it still has a real edge after cleanup, even though
    # its own fact is gone.
    s6_doc = add_source_document("federal_budget_statement_6_a61")
    s6_node = add_node(s6_doc, "Health", "s6|node|health")
    add_fact(s6_doc, s6_node, "2024-25", 5_000_000)
    orphaned_but_still_wanted = add_node(
        pbs_doc, "Some Portfolio / Program 1.3", "pbs|node|orphaned_but_wanted"
    )
    add_fact(pbs_doc, orphaned_but_still_wanted, "2024-25", 3_000_000)
    add_edge(s6_node, orphaned_but_still_wanted, "related_breakdown", crosswalk_id="pbs_programs_all_under_s6")

    conn.commit()

    return {
        "conn_path": db_path,
        "conn": conn,
        "folder": folder,
        "orphaned_leaf": orphaned_leaf,
        "orphaned_fact_id": orphaned_fact_id,
        "surviving_leaf": surviving_leaf,
        "s6_node": s6_node,
        "orphaned_but_still_wanted": orphaned_but_still_wanted,
    }


def test_folder_node_never_flagged_as_orphaned(fixture_db):
    """The exact bug found and fixed: a permanently fact-less folder node
    must never appear in the fact-bearing snapshot, so it can never be
    treated as "newly orphaned" no matter what happens to leaves under it."""
    conn = fixture_db["conn"]
    before = fact_bearing_pbs_node_ids(conn)
    assert fixture_db["folder"] not in before


def test_simulated_reload_removes_only_the_truly_orphaned_leaf(fixture_db):
    conn = fixture_db["conn"]
    before = fact_bearing_pbs_node_ids(conn)

    # Simulate what replace_on_reload does when a row is now quarantined:
    # its fact is deleted (fact_nodes cascades).
    conn.execute("DELETE FROM facts WHERE id = ?", (fixture_db["orphaned_fact_id"],))
    conn.commit()

    result = cleanup(conn, before)
    conn.commit()

    assert result["newly_orphaned_nodes"] == 1  # only orphaned_leaf lost its fact here
    # The folder and its same_group edge to the surviving leaf must remain.
    remaining = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["folder"],)
    ).fetchone()[0]
    assert remaining == 1
    surviving_edge = conn.execute(
        "SELECT COUNT(*) FROM breakdown_edges WHERE parent_node_id = ? AND child_node_id = ?",
        (fixture_db["folder"], fixture_db["surviving_leaf"]),
    ).fetchone()[0]
    assert surviving_edge == 1

    # The truly orphaned leaf (no fact, and its only edge is now removable)
    # must be gone entirely.
    orphaned_gone = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["orphaned_leaf"],)
    ).fetchone()[0]
    assert orphaned_gone == 0
    assert result["stale_nodes_removed"] >= 1


def test_crosswalk_edge_into_an_orphaned_node_is_also_removed(fixture_db):
    """A related_breakdown crosswalk edge FROM a live Statement 6 node
    INTO a PBS node that just lost its fact is itself stale - the edge
    would point at a node with no data to show - so it is removed along
    with the node, not left dangling and not used to "protect" the node
    from deletion. The live Statement 6 node itself is untouched."""
    conn = fixture_db["conn"]
    before = fact_bearing_pbs_node_ids(conn)

    conn.execute(
        "DELETE FROM facts WHERE id IN (SELECT fact_id FROM fact_nodes WHERE node_id = ?)",
        (fixture_db["orphaned_but_still_wanted"],),
    )
    conn.commit()

    result = cleanup(conn, before)
    conn.commit()

    edge_count = conn.execute(
        "SELECT COUNT(*) FROM breakdown_edges WHERE child_node_id = ?",
        (fixture_db["orphaned_but_still_wanted"],),
    ).fetchone()[0]
    assert edge_count == 0
    node_exists = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["orphaned_but_still_wanted"],)
    ).fetchone()[0]
    assert node_exists == 0
    assert result["nodes_kept_with_remaining_edges"] == 0
    # The live Statement 6 node on the other end of that edge is unrelated
    # to the PBS reload and must be completely untouched.
    s6_still_there = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["s6_node"],)
    ).fetchone()[0]
    assert s6_still_there == 1


def test_no_op_when_nothing_changed(fixture_db):
    conn = fixture_db["conn"]
    before = fact_bearing_pbs_node_ids(conn)
    result = cleanup(conn, before)
    assert result["newly_orphaned_nodes"] == 0
    assert result["stale_edges_removed"] == 0
    assert result["stale_nodes_removed"] == 0

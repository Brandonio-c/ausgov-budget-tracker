"""Tests for scripts/ops/cleanup_orphan_nodes.py (Task 5 of the
database-hygiene-and-CI-hardening milestone): the generic,
transaction-safe orphan-node cleanup utility.

Uses a synthetic fixture database (never the real data/facts.db).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import cleanup_orphan_nodes as cleanup  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def _add_source_document(conn, source_key: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, 'Test', 'Test', 'NSW', 'state', 'test')
        """,
        (source_key,),
    )
    return int(cur.lastrowid)


def _add_node(conn, source_document_id: int, name: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
        VALUES (?, 'category', ?, 'NSW', 'state', ?, '{}')
        """,
        (f"test|node|{name}", name, source_document_id),
    )
    return int(cur.lastrowid)


def _add_fact(conn, fact_key: str, source_document_id: int, node_id: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type,
            accounting_basis, estimate_status, amount_aud, source_document_id,
            source_locator_json, retrieved_at
        ) VALUES (?, '2024-25', 'financial_year', 'borrowing_authority_debt_outstanding',
                  'gfs', 'actual', 1000, ?, '{"locator": "test"}', '2026-01-01T00:00:00')
        """,
        (fact_key, source_document_id),
    )
    fact_id = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (fact_id, node_id),
    )
    return fact_id


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "orphan_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    doc_id = _add_source_document(conn, "test_borrowing_source")
    live_node = _add_node(conn, doc_id, "Debt securities / TCorp / Fixed-rate bonds")
    _add_fact(conn, "live-fact", doc_id, live_node)

    # An orphan: a node from an old naming scheme with no facts/edges at all.
    orphan_node = _add_node(conn, doc_id, "Debt securities / Fixed-rate bonds")

    # A legitimate fact-less folder node: has a breakdown_edge to a child,
    # so it must NEVER be treated as an orphan.
    folder_node = _add_node(conn, doc_id, "Portfolio")
    child_node = _add_node(conn, doc_id, "Portfolio / Program")
    _add_fact(conn, "child-fact", doc_id, child_node)
    conn.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (folder_node, child_node),
    )
    conn.commit()
    conn.close()
    return {
        "path": db_path,
        "doc_id": doc_id,
        "live_node": live_node,
        "orphan_node": orphan_node,
        "folder_node": folder_node,
        "child_node": child_node,
    }


def test_orphan_nodes_finds_only_the_genuine_orphan(fixture_db):
    conn = sqlite3.connect(str(fixture_db["path"]))
    found = cleanup.orphan_nodes(conn)
    conn.close()
    ids = {n["id"] for n in found}
    assert ids == {fixture_db["orphan_node"]}


def test_folder_node_with_breakdown_edge_is_never_orphaned(fixture_db):
    conn = sqlite3.connect(str(fixture_db["path"]))
    found = cleanup.orphan_nodes(conn)
    conn.close()
    ids = {n["id"] for n in found}
    assert fixture_db["folder_node"] not in ids


def test_source_filter_restricts_results(fixture_db):
    conn = sqlite3.connect(str(fixture_db["path"]))
    found_match = cleanup.orphan_nodes(conn, ["test_borrowing_source"])
    found_nomatch = cleanup.orphan_nodes(conn, ["a_different_source"])
    conn.close()
    assert len(found_match) == 1
    assert len(found_nomatch) == 0


def test_orphan_node_ids_for_source_document(fixture_db):
    conn = sqlite3.connect(str(fixture_db["path"]))
    ids = cleanup.orphan_node_ids_for_source_document(conn, fixture_db["doc_id"])
    conn.close()
    assert ids == [fixture_db["orphan_node"]]


def test_delete_orphan_nodes_deletes_only_orphans(fixture_db):
    conn = sqlite3.connect(str(fixture_db["path"]))
    conn.execute("PRAGMA foreign_keys = ON")
    deleted = cleanup.delete_orphan_nodes(
        conn, [fixture_db["orphan_node"], fixture_db["live_node"], fixture_db["folder_node"]]
    )
    conn.commit()
    assert deleted == 1
    remaining_ids = {r[0] for r in conn.execute("SELECT id FROM nodes").fetchall()}
    conn.close()
    assert fixture_db["orphan_node"] not in remaining_ids
    assert fixture_db["live_node"] in remaining_ids
    assert fixture_db["folder_node"] in remaining_ids


def test_dry_run_cli_does_not_delete(fixture_db):
    rc = cleanup.main(["--dry-run", "--db", str(fixture_db["path"])])
    assert rc == 0
    conn = sqlite3.connect(str(fixture_db["path"]))
    count = conn.execute("SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["orphan_node"],)).fetchone()[0]
    conn.close()
    assert count == 1


def test_apply_cli_deletes_and_is_idempotent(fixture_db):
    rc = cleanup.main(["--apply", "--db", str(fixture_db["path"])])
    assert rc == 0
    conn = sqlite3.connect(str(fixture_db["path"]))
    count = conn.execute("SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["orphan_node"],)).fetchone()[0]
    conn.close()
    assert count == 0

    conn = sqlite3.connect(str(fixture_db["path"]))
    remaining = cleanup.orphan_nodes(conn)
    conn.close()
    assert remaining == []


def test_second_apply_run_finds_nothing_new(fixture_db):
    cleanup.main(["--apply", "--db", str(fixture_db["path"])])
    rc = cleanup.main(["--apply", "--db", str(fixture_db["path"])])
    assert rc == 0
    conn = sqlite3.connect(str(fixture_db["path"]))
    remaining = cleanup.orphan_nodes(conn)
    conn.close()
    assert remaining == []


def test_report_written(fixture_db, tmp_path):
    report_base = tmp_path / "orphan-report"
    cleanup.main(["--apply", "--db", str(fixture_db["path"]), "--report", str(report_base)])
    assert report_base.with_suffix(".json").is_file()
    assert report_base.with_suffix(".md").is_file()

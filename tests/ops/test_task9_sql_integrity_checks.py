"""Fixture-backed tests for scripts/ops/task9_sql_integrity_checks.py
(Task 6 of the database-hygiene-and-CI-hardening milestone): one test per
check, plus the reviewed-duplicate-facts partitioning and the accepted-
residual/reviewed-duplicate config-validity checks wired into main()'s
hard-failure count.

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

import task9_sql_integrity_checks as task9  # noqa: E402
from reviewed_duplicates import ReviewedDuplicateGroup  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def _add_source_document(conn, source_key: str, jurisdiction="QLD", level="state") -> int:
    cur = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, 'Test', 'Test', ?, ?, 'test')
        """,
        (source_key, jurisdiction, level),
    )
    return int(cur.lastrowid)


def _add_node(conn, source_document_id: int, name: str, jurisdiction="QLD", level="state") -> int:
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
        VALUES (?, 'category', ?, ?, ?, ?, '{}')
        """,
        (f"test|node|{name}|{source_document_id}", name, jurisdiction, level, source_document_id),
    )
    return int(cur.lastrowid)


def _add_fact(
    conn,
    fact_key: str,
    source_document_id: int,
    fy: str = "2024-25",
    amount: float = 1000,
    measure_type: str = "actual_accrual_expense",
    estimate_status: str = "actual",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type,
            accounting_basis, estimate_status, amount_aud, source_document_id,
            source_locator_json, retrieved_at
        ) VALUES (?, ?, 'financial_year', ?, 'accrual', ?, ?, ?, '{"locator": "test"}', '2026-01-01T00:00:00')
        """,
        (fact_key, fy, measure_type, estimate_status, amount, source_document_id),
    )
    return int(cur.lastrowid)


def _link(conn, fact_id: int, node_id: int, role: str = "primary") -> None:
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, ?)",
        (fact_id, node_id, role),
    )


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "task9_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


# ---- duplicate_facts / partition_duplicate_facts ----------------------


def test_duplicate_facts_detects_a_group_with_provenance(db):
    doc = _add_source_document(db, "src_a")
    node = _add_node(db, doc, "Program / Line item")
    f1 = _add_fact(db, "k1", doc)
    f2 = _add_fact(db, "k2", doc)
    _link(db, f1, node)
    _link(db, f2, node)
    db.commit()

    groups = task9.duplicate_facts(db)
    assert len(groups) == 1
    g = groups[0]
    assert g["node_path"] == "Program / Line item"
    assert g["source_key"] == "src_a"
    assert g["count"] == 2


def test_duplicate_facts_finds_nothing_when_facts_are_distinct(db):
    doc = _add_source_document(db, "src_a")
    node = _add_node(db, doc, "Program / Line item")
    f1 = _add_fact(db, "k1", doc, amount=1000)
    f2 = _add_fact(db, "k2", doc, amount=2000)
    _link(db, f1, node)
    _link(db, f2, node)
    db.commit()

    assert task9.duplicate_facts(db) == []


def test_partition_moves_a_reviewed_group_out_of_unresolved(db):
    doc = _add_source_document(db, "src_a")
    node = _add_node(db, doc, "Program / Line item")
    f1 = _add_fact(db, "k1", doc)
    f2 = _add_fact(db, "k2", doc)
    _link(db, f1, node)
    _link(db, f2, node)
    db.commit()

    groups = task9.duplicate_facts(db)
    reviewed_entry = ReviewedDuplicateGroup(
        source_key="src_a",
        node_path="Program / Line item",
        financial_year="2024-25",
        measure_type="actual_accrual_expense",
        estimate_status="actual",
        amount_aud=1000.0,
        classification="query_false_positive",
        reason="test",
        evidence_report="test.md",
        review_date="2026-08-04",
    )
    unresolved, reviewed = task9.partition_duplicate_facts(groups, [reviewed_entry])
    assert unresolved == []
    assert len(reviewed) == 1
    assert reviewed[0]["classification"] == "query_false_positive"


def test_partition_leaves_an_unreviewed_group_in_unresolved(db):
    doc = _add_source_document(db, "src_a")
    node = _add_node(db, doc, "Program / Line item")
    f1 = _add_fact(db, "k1", doc)
    f2 = _add_fact(db, "k2", doc)
    _link(db, f1, node)
    _link(db, f2, node)
    db.commit()

    groups = task9.duplicate_facts(db)
    unresolved, reviewed = task9.partition_duplicate_facts(groups, [])
    assert len(unresolved) == 1
    assert reviewed == []


def test_partition_does_not_match_a_group_with_a_different_amount(db):
    doc = _add_source_document(db, "src_a")
    node = _add_node(db, doc, "Program / Line item")
    f1 = _add_fact(db, "k1", doc, amount=999)
    f2 = _add_fact(db, "k2", doc, amount=999)
    _link(db, f1, node)
    _link(db, f2, node)
    db.commit()

    groups = task9.duplicate_facts(db)
    reviewed_entry = ReviewedDuplicateGroup(
        source_key="src_a",
        node_path="Program / Line item",
        financial_year="2024-25",
        measure_type="actual_accrual_expense",
        estimate_status="actual",
        amount_aud=1.0,  # does not match the live 999
        classification="query_false_positive",
        reason="test",
        evidence_report="test.md",
        review_date="2026-08-04",
    )
    unresolved, reviewed = task9.partition_duplicate_facts(groups, [reviewed_entry])
    assert len(unresolved) == 1
    assert reviewed == []


# ---- duplicate_breakdown_edges -----------------------------------------


def test_duplicate_breakdown_edges_detects_null_safe_duplicate(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent")
    child = _add_node(db, doc, "Child")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'related_breakdown')",
        (parent, child),
    )
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'related_breakdown')",
        (parent, child),
    )
    db.commit()
    found = task9.duplicate_breakdown_edges(db)
    assert len(found) == 1
    assert found[0]["count"] == 2


def test_duplicate_breakdown_edges_finds_nothing_for_a_single_edge(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent")
    child = _add_node(db, doc, "Child")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (parent, child),
    )
    db.commit()
    assert task9.duplicate_breakdown_edges(db) == []


# ---- orphan_facts -------------------------------------------------------


def test_orphan_facts_detects_a_fact_with_no_fact_nodes_row(db):
    doc = _add_source_document(db, "src_a")
    _add_fact(db, "k1", doc)
    db.commit()
    assert task9.orphan_facts(db) == 1


def test_orphan_facts_is_zero_when_every_fact_is_linked(db):
    doc = _add_source_document(db, "src_a")
    node = _add_node(db, doc, "Program")
    f1 = _add_fact(db, "k1", doc)
    _link(db, f1, node)
    db.commit()
    assert task9.orphan_facts(db) == 0


# ---- orphan_nodes -------------------------------------------------------


def test_orphan_nodes_detects_a_genuinely_unreachable_node(db):
    doc = _add_source_document(db, "src_a")
    _add_node(db, doc, "Nobody references me")
    db.commit()
    assert task9.orphan_nodes(db) == 1


def test_orphan_nodes_excludes_a_folder_node_with_a_breakdown_edge(db):
    doc = _add_source_document(db, "src_a")
    folder = _add_node(db, doc, "Folder")
    child = _add_node(db, doc, "Folder / Child")
    f1 = _add_fact(db, "k1", doc)
    _link(db, f1, child)
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (folder, child),
    )
    db.commit()
    assert task9.orphan_nodes(db) == 0


def test_orphan_nodes_excludes_a_node_referenced_only_via_node_edges(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent")
    child = _add_node(db, doc, "Child")
    db.execute(
        "INSERT INTO node_edges (hierarchy_type, parent_node_id, child_node_id) VALUES ('functional', ?, ?)",
        (parent, child),
    )
    db.commit()
    assert task9.orphan_nodes(db) == 0


# ---- orphan_edges --------------------------------------------------------


def test_orphan_edges_detects_a_dangling_reference(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent")
    child = _add_node(db, doc, "Child")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (parent, child),
    )
    db.commit()
    # PRAGMA foreign_keys only takes effect outside a transaction, and this
    # connection already has it ON from the fixture - use a fresh
    # connection with it OFF to construct the otherwise-impossible dangling
    # reference this check defends against.
    db_path = db.execute("PRAGMA database_list").fetchone()[2]
    raw = sqlite3.connect(db_path)
    raw.execute("PRAGMA foreign_keys = OFF")
    raw.execute("DELETE FROM nodes WHERE id = ?", (child,))
    raw.commit()
    raw.close()
    assert task9.orphan_edges(db) == 1


def test_orphan_edges_is_zero_when_both_endpoints_exist(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent")
    child = _add_node(db, doc, "Child")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (parent, child),
    )
    db.commit()
    assert task9.orphan_edges(db) == 0


# ---- dangling_source_documents -------------------------------------------


def test_dangling_source_documents_detects_a_fully_unused_document(db):
    _add_source_document(db, "src_unused")
    db.commit()
    assert task9.dangling_source_documents(db) == ["src_unused"]


def test_dangling_source_documents_excludes_a_document_still_used_by_a_node(db):
    doc = _add_source_document(db, "src_a")
    _add_node(db, doc, "Some node")
    db.commit()
    assert task9.dangling_source_documents(db) == []


# ---- cross_government_additive_edges / cross_jurisdiction_additive_edges -


def test_cross_government_additive_edge_is_detected(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent", level="federal")
    child = _add_node(db, doc, "Child", level="state")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (parent, child),
    )
    db.commit()
    found = task9.cross_government_additive_edges(db)
    assert len(found) == 1


def test_cross_government_additive_edge_excludes_related_breakdown(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent", level="federal")
    child = _add_node(db, doc, "Child", level="state")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'related_breakdown')",
        (parent, child),
    )
    db.commit()
    assert task9.cross_government_additive_edges(db) == []


def test_cross_jurisdiction_additive_edge_is_detected(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent", jurisdiction="NSW")
    child = _add_node(db, doc, "Child", jurisdiction="QLD")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (parent, child),
    )
    db.commit()
    found = task9.cross_jurisdiction_additive_edges(db)
    assert len(found) == 1


def test_cross_jurisdiction_additive_edge_finds_nothing_for_same_jurisdiction(db):
    doc = _add_source_document(db, "src_a")
    parent = _add_node(db, doc, "Parent", jurisdiction="NSW")
    child = _add_node(db, doc, "Child", jurisdiction="NSW")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind) VALUES (?, ?, 'same_group')",
        (parent, child),
    )
    db.commit()
    assert task9.cross_jurisdiction_additive_edges(db) == []


# ---- pbs_crosswalk_children_with_rejected_labels -------------------------


def test_pbs_crosswalk_rejects_a_non_publishable_child_label(db):
    doc = _add_source_document(db, "federal_pbs_programs_all", jurisdiction="Commonwealth", level="federal")
    parent = _add_node(db, doc, "Program 1.1", jurisdiction="Commonwealth", level="federal")
    child = _add_node(db, doc, "Program 1.1 / Total", jurisdiction="Commonwealth", level="federal")
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id) VALUES (?, ?, 'related_breakdown', 'pbs_programs_all_under_s6')",
        (parent, child),
    )
    db.commit()
    found = task9.pbs_crosswalk_children_with_rejected_labels(db)
    assert len(found) == 1


def test_pbs_crosswalk_accepts_a_publishable_child_label(db):
    doc = _add_source_document(db, "federal_pbs_programs_all", jurisdiction="Commonwealth", level="federal")
    parent = _add_node(db, doc, "Program 1.1", jurisdiction="Commonwealth", level="federal")
    child = _add_node(
        db, doc, "Program 1.1 / Key cost category / Capability Acquisition Program",
        jurisdiction="Commonwealth", level="federal",
    )
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id) VALUES (?, ?, 'related_breakdown', 'pbs_programs_all_under_s6')",
        (parent, child),
    )
    db.commit()
    assert task9.pbs_crosswalk_children_with_rejected_labels(db) == []


# ---- pbs_children_missing_source_year ------------------------------------


def test_pbs_children_missing_source_year_detects_blank_year(db):
    doc = _add_source_document(db, "federal_pbs_programs_all", jurisdiction="Commonwealth", level="federal")
    parent = _add_node(db, doc, "Program 1.1", jurisdiction="Commonwealth", level="federal")
    child = _add_node(db, doc, "Program 1.1 / Component", jurisdiction="Commonwealth", level="federal")
    f1 = _add_fact(db, "k1", doc, fy="   ")
    _link(db, f1, child)
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id) VALUES (?, ?, 'related_breakdown', 'pbs_programs_all_under_s6')",
        (parent, child),
    )
    db.commit()
    assert task9.pbs_children_missing_source_year(db) == 1


def test_pbs_children_missing_source_year_is_zero_for_a_real_year(db):
    doc = _add_source_document(db, "federal_pbs_programs_all", jurisdiction="Commonwealth", level="federal")
    parent = _add_node(db, doc, "Program 1.1", jurisdiction="Commonwealth", level="federal")
    child = _add_node(db, doc, "Program 1.1 / Component", jurisdiction="Commonwealth", level="federal")
    f1 = _add_fact(db, "k1", doc, fy="2024-25")
    _link(db, f1, child)
    db.execute(
        "INSERT INTO breakdown_edges (parent_node_id, child_node_id, edge_kind, crosswalk_id) VALUES (?, ?, 'related_breakdown', 'pbs_programs_all_under_s6')",
        (parent, child),
    )
    db.commit()
    assert task9.pbs_children_missing_source_year(db) == 0


# ---- main(): config-validity wiring and overall hard-failure aggregation -


def test_main_is_clean_against_a_healthy_fixture_database(tmp_path, monkeypatch):
    db_path = tmp_path / "healthy.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    doc = _add_source_document(conn, "src_a")
    node = _add_node(conn, doc, "Program")
    f1 = _add_fact(conn, "k1", doc)
    _link(conn, f1, node)
    conn.commit()
    conn.close()

    monkeypatch.setattr(task9, "DB_PATH", db_path)
    rc = task9.main()
    assert rc == 0


def test_main_fails_when_accepted_residual_config_is_invalid(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "healthy.db"
    migrate(db_path)
    monkeypatch.setattr(task9, "DB_PATH", db_path)
    monkeypatch.setattr(
        task9,
        "validate_accepted_residuals",
        lambda: {"valid": False, "errors": ["broken"], "entry_count": 0},
    )
    rc = task9.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert '"hard_failures": 1' in out


def test_main_fails_when_reviewed_duplicate_config_is_invalid(tmp_path, monkeypatch):
    db_path = tmp_path / "healthy.db"
    migrate(db_path)
    monkeypatch.setattr(task9, "DB_PATH", db_path)
    monkeypatch.setattr(
        task9,
        "validate_reviewed_duplicates",
        lambda: {"valid": False, "errors": ["broken"], "entry_count": 0},
    )
    rc = task9.main()
    assert rc == 1


def test_main_treats_dangling_source_documents_as_informational_only(tmp_path, monkeypatch):
    db_path = tmp_path / "healthy.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    _add_source_document(conn, "src_unused")
    conn.commit()
    conn.close()

    monkeypatch.setattr(task9, "DB_PATH", db_path)
    rc = task9.main()
    assert rc == 0

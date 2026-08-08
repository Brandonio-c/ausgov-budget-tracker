from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from edge_pack import policies_for_selector, run  # noqa: E402
from schema_migrate import migrate  # noqa: E402


@pytest.fixture()
def edge_db(tmp_path: Path) -> Path:
    db = tmp_path / "facts.db"
    migrate(db)
    conn = sqlite3.connect(str(db))
    doc_id = conn.execute(
        """
        INSERT INTO source_documents
            (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES
            ('federal_budget_statement_6_fixture', 'Treasury', 'Fixture',
             'Commonwealth', 'federal', 'budget_papers')
        """
    ).lastrowid
    parent_id = conn.execute(
        """
        INSERT INTO nodes
            (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('fixture|health', 'category', 'Health', 'Commonwealth', 'federal', ?)
        """,
        (doc_id,),
    ).lastrowid
    child_id = conn.execute(
        """
        INSERT INTO nodes
            (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('fixture|hospitals', 'category', 'Health / Hospitals',
                'Commonwealth', 'federal', ?)
        """,
        (doc_id,),
    ).lastrowid
    conn.execute(
        """
        INSERT INTO breakdown_edges
            (parent_node_id, child_node_id, edge_kind, source_document_id)
        VALUES (?, ?, 'same_group', ?)
        """,
        (parent_id, child_id, doc_id),
    )
    conn.commit()
    conn.close()
    return db


def _edge_count(db: Path) -> int:
    conn = sqlite3.connect(str(db))
    count = int(conn.execute("SELECT COUNT(*) FROM breakdown_edges").fetchone()[0])
    conn.close()
    return count


def test_delete_requires_apply_and_is_scoped(edge_db: Path) -> None:
    preview = run(
        db_path=edge_db,
        operation="delete",
        edge_set_id="statement_6_source_native",
        crosswalk_id=None,
        apply=False,
    )
    assert preview["before"] == {"statement_6_source_native": 1}
    assert _edge_count(edge_db) == 1

    applied = run(
        db_path=edge_db,
        operation="delete",
        edge_set_id="statement_6_source_native",
        crosswalk_id=None,
        apply=True,
    )
    assert applied["deleted"] == {"statement_6_source_native": 1}
    assert applied["after"] == {"statement_6_source_native": 0}
    assert _edge_count(edge_db) == 0


def test_rebuild_restores_pack_and_is_idempotent(edge_db: Path) -> None:
    first = run(
        db_path=edge_db,
        operation="rebuild",
        edge_set_id="statement_6_source_native",
        crosswalk_id=None,
        apply=True,
    )
    second = run(
        db_path=edge_db,
        operation="rebuild",
        edge_set_id="statement_6_source_native",
        crosswalk_id=None,
        apply=True,
    )
    assert first["after"] == {"statement_6_source_native": 1}
    assert second["before"] == {"statement_6_source_native": 1}
    assert second["after"] == {"statement_6_source_native": 1}
    assert _edge_count(edge_db) == 1


def test_crosswalk_selector_includes_each_registered_edge_set() -> None:
    policies = policies_for_selector(
        edge_set_id=None, crosswalk_id="cofog_to_budget_function"
    )
    assert {policy.id for policy in policies} == {
        "statement_6_under_abs",
        "fbo_2024_25_under_abs",
    }

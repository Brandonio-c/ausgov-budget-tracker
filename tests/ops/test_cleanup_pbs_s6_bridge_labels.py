"""Tests for scripts/ops/cleanup_pbs_s6_bridge_labels.py - a one-time,
classifier-driven cleanup of federal_pbs_programs_s6_bridge, a second,
older PBS-derived dataset found (during production audit re-verification
after Task 8's federal_pbs_programs_all reload) to still contain the same
kind of malformed/concatenated labels, reached via a different ingest path
that Task 8's reload never touched.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from cleanup_pbs_s6_bridge_labels import (  # noqa: E402
    _label_for_classification,
    cleanup_bridge_labels,
)
from schema_migrate import migrate  # noqa: E402


def test_label_for_classification_takes_last_path_segment():
    assert (
        _label_for_classification("Other economic affairs / Other economic affairs nec / Grants")
        == "Grants"
    )
    assert _label_for_classification("No separator") == "No separator"


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "bridge_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    doc_id = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('federal_pbs_programs_s6_bridge', 'Test', 'Test', 'Commonwealth', 'federal', 'test')
        """
    ).lastrowid
    other_doc_id = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('some_other_source', 'Test', 'Test', 'Commonwealth', 'federal', 'test')
        """
    ).lastrowid

    def add_node(name: str, canonical_key: str, source_document_id: int = doc_id) -> int:
        return conn.execute(
            """
            INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
            VALUES (?, 'category', ?, 'Commonwealth', 'federal', ?, '{}')
            """,
            (canonical_key, name, source_document_id),
        ).lastrowid

    def add_fact(node_id: int, fact_key: str, amount: float, source_document_id: int = doc_id) -> int:
        fact_id = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_granularity, measure_type,
                accounting_basis, estimate_status, amount_aud, source_document_id,
                source_locator_json, retrieved_at
            ) VALUES (?, '2024-25', 'financial_year', 'budget_estimate', 'accrual', 'budget', ?, ?, '{}', '2026-01-01T00:00:00')
            """,
            (fact_key, amount, source_document_id),
        ).lastrowid
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
            (fact_id, node_id),
        )
        return fact_id

    good_node = add_node(
        "Other economic affairs / Other economic affairs nec / Program 1.1: Consumer Protection",
        "bridge|node|good",
    )
    add_fact(good_node, "bridge|good|2024-25", 1_000_000)

    bad_node = add_node(
        "Other economic affairs / Other economic affairs nec / (Asialink Business) 3,700 3,774 - - -",
        "bridge|node|bad",
    )
    add_fact(bad_node, "bridge|bad|2024-25", 2_000_000)

    other_node = add_node("Some other unrelated label", "other|node|unrelated", other_doc_id)
    add_fact(other_node, "other|unrelated|2024-25", 3_000_000, other_doc_id)

    conn.commit()
    return {"conn": conn, "good_node": good_node, "bad_node": bad_node, "other_node": other_node}


def test_bad_label_quarantined_good_label_and_other_source_untouched(fixture_db):
    conn = fixture_db["conn"]
    result = cleanup_bridge_labels(conn)
    conn.commit()

    assert result["input_facts"] == 2
    assert result["quarantined"] == 1
    assert result["published"] == 1

    good_remaining = conn.execute(
        "SELECT COUNT(*) FROM fact_nodes WHERE node_id = ?", (fixture_db["good_node"],)
    ).fetchone()[0]
    assert good_remaining == 1

    bad_remaining = conn.execute(
        "SELECT COUNT(*) FROM fact_nodes WHERE node_id = ?", (fixture_db["bad_node"],)
    ).fetchone()[0]
    assert bad_remaining == 0
    bad_node_exists = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE id = ?", (fixture_db["bad_node"],)
    ).fetchone()[0]
    assert bad_node_exists == 0

    quarantine_row = conn.execute(
        "SELECT quarantine_reason FROM facts_pending_attribution WHERE fact_key = ?",
        ("bridge|bad|2024-25",),
    ).fetchone()
    assert quarantine_row is not None
    assert "Label quality" in quarantine_row[0]

    other_untouched = conn.execute(
        "SELECT COUNT(*) FROM fact_nodes WHERE node_id = ?", (fixture_db["other_node"],)
    ).fetchone()[0]
    assert other_untouched == 1


def test_second_run_is_idempotent(fixture_db):
    conn = fixture_db["conn"]
    cleanup_bridge_labels(conn)
    conn.commit()

    result2 = cleanup_bridge_labels(conn)
    conn.commit()
    assert result2["input_facts"] == 1  # only the surviving good fact remains
    assert result2["quarantined"] == 0
    assert result2["newly_orphaned_nodes"] == 0

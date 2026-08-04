"""Tests for scripts/ops/cleanup_duplicate_facts.py (Task 4 of the
database-hygiene-and-CI-hardening milestone): the idempotent, --dry-run
by default, cleanup for confirmed true-duplicate fact pairs declared in
config/audit/confirmed_duplicate_deletions.yaml.

Uses a synthetic fixture database (never the real data/facts.db).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import cleanup_duplicate_facts as cleanup  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def _add_source_document(conn, source_key: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, 'Test', 'Test', 'QLD', 'state', 'test')
        """,
        (source_key,),
    )
    return int(cur.lastrowid)


def _add_node(conn, source_document_id: int, name: str, canonical_key: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
        VALUES (?, 'category', ?, 'QLD', 'state', ?, '{}')
        """,
        (canonical_key, name, source_document_id),
    )
    return int(cur.lastrowid)


def _add_fact(
    conn,
    fact_key: str,
    source_document_id: int,
    node_id: int,
    fy: str = "2024-25",
    amount: float = 42750,
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
    fact_id = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (fact_id, node_id),
    )
    return fact_id


@pytest.fixture
def fixture_db(tmp_path):
    db_path = tmp_path / "cleanup_fixture.db"
    migrate(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    doc_id = _add_source_document(conn, "qld_qgip_expenditure")
    node_id = _add_node(conn, doc_id, "GOONDIWINDI REGIONAL COUNCIL / Black Spot", "qld|node|goondiwindi-black-spot")
    retain_id = _add_fact(conn, "retain-key", doc_id, node_id)
    delete_id = _add_fact(conn, "delete-key", doc_id, node_id)
    conn.commit()
    conn.close()
    return {"path": db_path, "retain_id": retain_id, "delete_id": delete_id, "node_id": node_id}


def _config(tmp_path, **overrides) -> Path:
    entry = {
        "source_key": "qld_qgip_expenditure",
        "node_path": "GOONDIWINDI REGIONAL COUNCIL / Black Spot",
        "financial_year": "2024-25",
        "measure_type": "actual_accrual_expense",
        "estimate_status": "actual",
        "amount_aud": 42750,
        "retain_fact_key": "retain-key",
        "delete_fact_key": "delete-key",
        "reason": "test",
        "evidence_report": "test.md",
        "review_date": "2026-08-04",
    }
    entry.update(overrides)
    path = tmp_path / "confirmed.yaml"
    path.write_text(yaml.safe_dump({"confirmed_duplicate_deletions": [entry]}), encoding="utf-8")
    return path


def test_dry_run_plans_deletion_without_writing(fixture_db, tmp_path):
    config = _config(tmp_path)
    rc = cleanup.main(["--dry-run", "--db", str(fixture_db["path"]), "--config", str(config)])
    assert rc == 0
    conn = sqlite3.connect(str(fixture_db["path"]))
    assert conn.execute("SELECT COUNT(*) FROM facts WHERE fact_key = 'delete-key'").fetchone()[0] == 1
    conn.close()


def test_plan_reports_would_delete(fixture_db, tmp_path):
    config = _config(tmp_path)
    conn = sqlite3.connect(str(fixture_db["path"]))
    entries = cleanup.load_confirmed_deletions(config)
    planned = cleanup.plan(conn, entries)
    conn.close()
    assert len(planned) == 1
    assert planned[0]["status"] == "would_delete"
    assert planned[0]["delete_fact_id"] == fixture_db["delete_id"]
    assert planned[0]["retain_fact_id"] == fixture_db["retain_id"]


def test_apply_deletes_only_the_confirmed_fact(fixture_db, tmp_path):
    config = _config(tmp_path)
    rc = cleanup.main(["--apply", "--db", str(fixture_db["path"]), "--config", str(config)])
    assert rc == 0
    conn = sqlite3.connect(str(fixture_db["path"]))
    assert conn.execute("SELECT COUNT(*) FROM facts WHERE fact_key = 'delete-key'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM facts WHERE fact_key = 'retain-key'").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM fact_nodes WHERE node_id = ?", (fixture_db["node_id"],)
    ).fetchone()[0] == 1
    conn.close()


def test_second_apply_run_is_idempotent(fixture_db, tmp_path):
    config = _config(tmp_path)
    cleanup.main(["--apply", "--db", str(fixture_db["path"]), "--config", str(config)])

    conn = sqlite3.connect(str(fixture_db["path"]))
    entries = cleanup.load_confirmed_deletions(config)
    planned = cleanup.plan(conn, entries)
    conn.close()
    assert len(planned) == 1
    assert planned[0]["status"] == "already_resolved"


def test_refuses_to_delete_if_retain_fact_missing(fixture_db, tmp_path):
    config = _config(tmp_path, retain_fact_key="does-not-exist")
    conn = sqlite3.connect(str(fixture_db["path"]))
    entries = cleanup.load_confirmed_deletions(config)
    planned = cleanup.plan(conn, entries)
    conn.close()
    assert planned[0]["status"] == "error"
    assert "retain_fact_key not found" in planned[0]["detail"]


def test_refuses_to_delete_on_identity_mismatch(fixture_db, tmp_path):
    config = _config(tmp_path, financial_year="2099-00")
    conn = sqlite3.connect(str(fixture_db["path"]))
    entries = cleanup.load_confirmed_deletions(config)
    planned = cleanup.plan(conn, entries)
    conn.close()
    assert planned[0]["status"] == "error"
    assert "does not match" in planned[0]["detail"]


def test_refuses_to_delete_fact_with_lineage_reference(fixture_db, tmp_path):
    conn = sqlite3.connect(str(fixture_db["path"]))
    conn.execute(
        """
        INSERT INTO lineage_edges (parent_fact_id, child_fact_id, relation_type, source_locator_json)
        VALUES (?, ?, 'supersedes', '{}')
        """,
        (fixture_db["delete_id"], fixture_db["retain_id"]),
    )
    conn.commit()
    config = _config(tmp_path)
    entries = cleanup.load_confirmed_deletions(config)
    planned = cleanup.plan(conn, entries)
    conn.close()
    assert planned[0]["status"] == "error"
    assert "references" in planned[0]["detail"]


def test_real_config_and_real_db_resolve_to_already_resolved_or_would_delete():
    """Smoke test against the real repo config (not the real DB - that is
    exercised operationally, not in pytest). Just proves the YAML parses
    and every entry has the required keys the script depends on."""
    entries = cleanup.load_confirmed_deletions()
    assert len(entries) == 1
    entry = entries[0]
    for key in (
        "source_key",
        "node_path",
        "financial_year",
        "measure_type",
        "estimate_status",
        "amount_aud",
        "retain_fact_key",
        "delete_fact_key",
    ):
        assert key in entry

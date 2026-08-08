"""Tests for M0 schema_migrate."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "facts.db"


def test_migrate_idempotent(tmp_db: Path) -> None:
    first = migrate(tmp_db)
    second = migrate(tmp_db)
    assert first["migrations"]["000_hierarchical_schema_draft"] == "applied"
    assert first["migrations"]["001_m0_deltas"] == "applied"
    assert second["migrations"]["000_hierarchical_schema_draft"] == "noop"
    assert second["migrations"]["001_m0_deltas"] == "noop"
    assert first["has_facts_pending_attribution"] is True
    assert first["has_payment_timing_disclosure"] is True
    assert first["has_native_unit"] is True
    assert second["has_native_unit"] is True


def test_territory_government_level_allowed(tmp_db: Path) -> None:
    migrate(tmp_db)
    conn = sqlite3.connect(str(tmp_db))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        INSERT INTO source_documents
            (source_key, publisher, title, jurisdiction, government_level,
             source_family)
        VALUES
            ('act_test', 'ACT', 'Test', 'ACT', 'territory', 'territory_actuals')
        """
    )
    conn.commit()
    level = conn.execute(
        "SELECT government_level FROM source_documents WHERE source_key='act_test'"
    ).fetchone()[0]
    assert level == "territory"
    conn.close()


def test_invalid_government_level_rejected(tmp_db: Path) -> None:
    migrate(tmp_db)
    conn = sqlite3.connect(str(tmp_db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO source_documents
                (source_key, publisher, title, jurisdiction, government_level,
                 source_family)
            VALUES
                ('bad', 'X', 'X', 'X', 'planet', 'x')
            """
        )
    conn.close()


def test_facts_pending_attribution_requires_reason(tmp_db: Path) -> None:
    migrate(tmp_db)
    conn = sqlite3.connect(str(tmp_db))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        INSERT INTO source_documents
            (source_key, publisher, title, jurisdiction, government_level,
             source_family)
        VALUES
            ('src1', 'Pub', 'Title', 'AU', 'federal', 'test')
        """
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO facts_pending_attribution
                (fact_key, financial_year, period_granularity, measure_type,
                 accounting_basis, estimate_status, amount_aud,
                 source_document_id, source_locator_json, retrieved_at,
                 quarantine_reason, quarantined_at)
            VALUES
                ('f1', '2024-25', 'financial_year', 'cash_payment', 'cash',
                 'actual', 1.0, 1, '{}', '2026-07-22T00:00:00+00:00',
                 NULL, '2026-07-22T00:00:00+00:00')
            """
        )
    conn.close()


def test_breakdown_edge_identity_is_null_safe(tmp_db: Path) -> None:
    result = migrate(tmp_db)
    assert result["migrations"]["017_breakdown_edge_uniqueness"] == "applied"
    conn = sqlite3.connect(str(tmp_db))
    conn.execute(
        """
        INSERT INTO breakdown_edges
            (parent_node_id, child_node_id, edge_kind, financial_year, crosswalk_id)
        VALUES (1, 2, 'same_group', NULL, NULL)
        """
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO breakdown_edges
                (parent_node_id, child_node_id, edge_kind, financial_year, crosswalk_id)
            VALUES (1, 2, 'same_group', NULL, NULL)
            """
        )
    conn.execute(
        """
        INSERT OR IGNORE INTO breakdown_edges
            (parent_node_id, child_node_id, edge_kind, financial_year, crosswalk_id)
        VALUES (1, 2, 'same_group', NULL, NULL)
        """
    )
    assert conn.execute("SELECT COUNT(*) FROM breakdown_edges").fetchone()[0] == 1
    conn.close()

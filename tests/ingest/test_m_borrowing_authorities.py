"""Regression test for scripts/ingest/m_borrowing_authorities.py (Task 5 of
the database-hygiene-and-CI-hardening milestone).

Root cause of the 278 orphan nodes found in this milestone (all in the
state/territory borrowing-authority debt-instrument sources - see
ops/reports/orphan-node-investigation-*.md): this ingest script deletes
facts + fact_nodes for a source before every reload ("path/valuation
upgrades do not double-count") but never touched the nodes table, and
this source family's node identity is a flat one-node-per-category-string
scheme with no breakdown_edges/node_edges ever created for it - so any
node whose category text differs from a prior run (e.g. an upstream
naming-scheme or instrument-classification change) was abandoned forever.

This test drives main() end-to-end against a synthetic temp database and
a monkeypatched single-source SOURCE_PARSERS entry (stubbing out PDF/CSV
parsing so it needs no real raw-data corpus), pre-seeding a fact under an
old-style category name to simulate "a previous run's now-superseded
node", and proves the reload deletes that now-orphaned node itself
instead of leaving it behind.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

import cleanup_orphan_nodes as cleanup  # noqa: E402
import m_borrowing_authorities as m_borrowing  # noqa: E402
from adapters.state_debt_instruments import InstrumentRow  # noqa: E402
from schema_migrate import migrate  # noqa: E402

SID = "test_borrowing_source"
STALE_CANONICAL_KEY = f"{SID}|node|Debt securities / Fixed-rate bonds"


def _seed_stale_fact(db_path: Path) -> tuple[int, int]:
    """Simulate a previous run's fact + node under an old-style category
    name (no authority segment) that the current run will not recreate."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, 'Test Authority', 'Test', 'NSW', 'state', 'state_borrowing')
        """,
        (SID,),
    )
    doc_id = int(cur.lastrowid)
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id, source_locator_json)
        VALUES (?, 'category', 'Debt securities / Fixed-rate bonds', 'NSW', 'state', ?, '{}')
        """,
        (STALE_CANONICAL_KEY, doc_id),
    )
    stale_node_id = int(cur.lastrowid)
    cur = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type,
            accounting_basis, estimate_status, amount_aud, source_document_id,
            source_locator_json, retrieved_at
        ) VALUES ('stale-fact-key', '2024-25', 'financial_year',
                  'borrowing_authority_debt_outstanding', 'gfs', 'actual', 500000000,
                  ?, '{"locator": "test"}', '2026-01-01T00:00:00')
        """,
        (doc_id,),
    )
    stale_fact_id = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (stale_fact_id, stale_node_id),
    )
    conn.commit()
    conn.close()
    return doc_id, stale_node_id


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    migrate(db_path)
    doc_id, stale_node_id = _seed_stale_fact(db_path)

    # STAGING/MAPPINGS write paths must stay real subpaths of REPO_ROOT
    # (main() computes csv_path.relative_to(REPO_ROOT) for attribution), so
    # use scratch dirs under the already-gitignored data/staging/ tree
    # instead of tmp_path, cleaned up at the end of this fixture.
    scratch_staging = REPO_ROOT / "data" / "staging" / "_test_m_borrowing_authorities_tmp"
    scratch_mappings = REPO_ROOT / "data" / "staging" / "_test_m_borrowing_authorities_tmp_mappings"
    scratch_raw_dir = REPO_ROOT / "data" / "raw" / "_test_m_borrowing_authorities_tmp"
    scratch_staging.mkdir(parents=True, exist_ok=True)
    scratch_mappings.mkdir(parents=True, exist_ok=True)
    scratch_raw_dir.mkdir(parents=True, exist_ok=True)
    dummy_path = scratch_raw_dir / "dummy_cached_copy.csv"
    dummy_path.write_text("dummy\n1\n", encoding="utf-8")

    monkeypatch.setattr(m_borrowing, "FACTS_DB", db_path)
    monkeypatch.setattr(m_borrowing, "STAGING", scratch_staging)
    monkeypatch.setattr(m_borrowing, "MAPPINGS", scratch_mappings)
    monkeypatch.setattr(m_borrowing, "SOURCE_PARSERS", {SID: ("NSW", "state", "TCorp", "fake_kind")})

    monkeypatch.setattr(m_borrowing, "resolve_raw_file", lambda repo_root, sid: (dummy_path, "https://example.test/data"))

    current_instruments = [
        InstrumentRow(
            instrument_type="Fixed-rate bonds",
            security_name="21 Jul 2027 3.00%",
            maturity_date="21 Jul 2027",
            coupon="3.00%",
            isin="AU000TEST001",
            face_value_aud=1_000_000_000.0,
            as_at=date(2026, 7, 17),
            authority="TCorp",
            source_url="https://example.test/data",
            locator="",
        )
    ]
    monkeypatch.setattr(m_borrowing, "parse_source", lambda path, kind, authority, source_url="": current_instruments)

    try:
        yield {"db_path": db_path, "doc_id": doc_id, "stale_node_id": stale_node_id}
    finally:
        shutil.rmtree(scratch_staging, ignore_errors=True)
        shutil.rmtree(scratch_mappings, ignore_errors=True)
        shutil.rmtree(scratch_raw_dir, ignore_errors=True)


def test_reload_deletes_its_own_now_orphaned_node(isolated_env):
    rc = m_borrowing.main()
    assert rc == 0

    conn = sqlite3.connect(str(isolated_env["db_path"]))
    # Checked by canonical_key, not the old row's numeric id: SQLite reuses
    # a freed rowid once a table is empty, so a fresh node created later in
    # the same run can legitimately land on the same integer id - that is
    # not evidence the stale node survived.
    stale_exists = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE canonical_key = ?", (STALE_CANONICAL_KEY,)
    ).fetchone()[0]
    live_node = conn.execute(
        "SELECT id FROM nodes WHERE name = 'Debt securities / TCorp / Fixed-rate bonds / 21 Jul 2027 3.00%'"
    ).fetchone()
    orphans = cleanup.orphan_node_ids_for_source_document(conn, isolated_env["doc_id"])
    conn.close()

    assert stale_exists == 0, "old-style node from the previous run must be cleaned up, not left orphaned"
    assert live_node is not None, "the current run's fresh node must exist"
    assert orphans == [], "reload must leave zero orphans behind for its own source"


def test_reload_is_idempotent_across_repeated_runs(isolated_env):
    m_borrowing.main()
    rc = m_borrowing.main()
    assert rc == 0

    conn = sqlite3.connect(str(isolated_env["db_path"]))
    orphans = cleanup.orphan_node_ids_for_source_document(conn, isolated_env["doc_id"])
    fact_count = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE source_document_id = ?", (isolated_env["doc_id"],)
    ).fetchone()[0]
    conn.close()

    assert orphans == []
    assert fact_count == 2  # 1 individual security fact + 1 instrument-type roll-up fact

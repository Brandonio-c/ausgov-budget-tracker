"""M1 ETL framework tests."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from run import run_mapping  # noqa: E402


def test_synthetic_publish_and_gate6_quarantine(tmp_path: Path) -> None:
    db = tmp_path / "facts.db"
    mapping = REPO_ROOT / "config" / "mappings" / "synthetic_demo.yaml"
    first = run_mapping(mapping, db)
    assert first["published"] == 2
    assert first["quarantined"] == 1
    assert first["gate6_quarantine"] == 1

    second = run_mapping(mapping, db)
    assert second["published"] == 2
    assert second["quarantined"] == 1

    conn = sqlite3.connect(str(db))
    n_facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    n_q = conn.execute("SELECT COUNT(*) FROM facts_pending_attribution").fetchone()[0]
    assert n_facts == 2
    assert n_q == 1
    reason = conn.execute(
        "SELECT quarantine_reason FROM facts_pending_attribution"
    ).fetchone()[0]
    assert "Gate 6" in reason
    assert "landing_url" in reason
    conn.close()

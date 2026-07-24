"""M2 citation API tests."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402


@pytest.fixture()
def facts_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "facts.db"
    migrate(db)
    run_mapping(REPO_ROOT / "config" / "mappings" / "synthetic_demo.yaml", db)
    monkeypatch.setenv("FACTS_DB_PATH", str(db))
    # reload facts_db module binding
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = db
    return db


@pytest.fixture()
def client(facts_db: Path) -> TestClient:
    from backend.main import app

    return TestClient(app)


def test_citation_complete_has_three_links(client: TestClient, facts_db: Path) -> None:
    conn = sqlite3.connect(str(facts_db))
    fact_id = conn.execute("SELECT id FROM facts ORDER BY id LIMIT 1").fetchone()[0]
    conn.close()
    r = client.get(f"/v2/facts/{fact_id}/citation")
    assert r.status_code == 200
    body = r.json()
    assert body["landing_url"]
    assert body["original_resource_url"]
    assert body["cached_copy_url"]
    assert body["locator"]
    assert body["sha256"]
    assert body["retrieved_at"]


def test_quarantined_not_reachable_by_pending_id(client: TestClient, facts_db: Path) -> None:
    conn = sqlite3.connect(str(facts_db))
    pending_id = conn.execute(
        "SELECT id FROM facts_pending_attribution LIMIT 1"
    ).fetchone()[0]
    # ensure not also a facts id collision meaning
    facts_ids = {r[0] for r in conn.execute("SELECT id FROM facts").fetchall()}
    conn.close()
    r = client.get(f"/v2/facts/{pending_id}/citation")
    if pending_id in facts_ids:
        # if id collision, still must be a published citation
        assert r.status_code == 200
    else:
        assert r.status_code == 404


def test_unknown_fact_404(client: TestClient, facts_db: Path) -> None:
    r = client.get("/v2/facts/999999/citation")
    assert r.status_code == 404

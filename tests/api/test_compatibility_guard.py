
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
from fastapi.testclient import TestClient



@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db = REPO_ROOT / "data" / "facts.db"
    monkeypatch.setenv("FACTS_DB_PATH", str(db))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = db
    from backend.main import app

    return TestClient(app)


def test_missing_triple_400(client: TestClient) -> None:
    r = client.get("/v2/aggregate")
    assert r.status_code == 400
    assert "compatibility_group" in r.json()["detail"]


def test_illegal_partial_400(client: TestClient) -> None:
    r = client.get("/v2/aggregate", params={"compatibility_group": "actual_expense"})
    assert r.status_code == 400


def test_valid_triple_200(client: TestClient) -> None:
    r = client.get(
        "/v2/aggregate",
        params={
            "compatibility_group": "actual_expense",
            "accounting_basis": "accrual",
            "estimate_status": "actual",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    if body["items"]:
        assert "citation" in body["items"][0]


def test_reconciliation_view_allowed(client: TestClient) -> None:
    r = client.get("/v2/aggregate", params={"view": "reconciliation"})
    assert r.status_code == 200
    assert r.json()["view"] == "reconciliation"


from __future__ import annotations

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


REQUIRED = (
    "landing_url",
    "original_resource_url",
    "cached_copy_url",
    "locator",
    "sha256",
    "retrieved_at",
)


def test_list_facts_citations_complete(client: TestClient) -> None:
    r = client.get("/v2/facts", params={"limit": 10})
    assert r.status_code == 200
    items = r.json()
    assert items
    for item in items:
        cit = item["citation"]
        for key in REQUIRED:
            assert cit.get(key), f"missing {key} in {cit}"


def test_tree_citations_complete(client: TestClient) -> None:
    r = client.get(
        "/v2/tree",
        params={
            "compatibility_group": "actual_expense",
            "accounting_basis": "accrual",
            "estimate_status": "actual",
            "financial_year": "2024-25",
            "limit": 5,
        },
    )
    assert r.status_code == 200
    for child in r.json().get("children") or []:
        cit = child["citation"]
        for key in REQUIRED:
            assert cit.get(key), f"missing {key}"

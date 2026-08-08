from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db = REPO_ROOT / "data" / "facts.db"
    monkeypatch.setenv("FACTS_DB_PATH", str(db))
    monkeypatch.setenv("DASHBOARD_PROJECTION_V2", "1")
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = db
    from backend.main import app

    return TestClient(app)


def _walk(node: dict):
    for child in node.get("children") or []:
        yield child
        yield from _walk(child)


def test_projection_contract_covers_every_non_root_node(client: TestClient) -> None:
    response = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    )
    assert response.status_code == 200
    body = response.json()
    projection = body["projection"]
    assert projection == {
        **projection,
        "requested_mode": "actuals",
        "requested_level": "federal",
        "requested_financial_year": "2024-25",
        "selected_accounting_basis": "gfs",
        "max_visible_depth": 4,
        "max_additive_depth": 2,
        "contains_related_branches": True,
    }

    nodes = list(_walk(body))
    assert nodes
    assert all(node.get("relationship") is not None for node in nodes)
    for node in nodes:
        relation = node["relationship"]
        assert relation["edge_kind"] in {"same_group", "related_breakdown"}
        assert relation["branch_kind"] in {"additive", "related"}
        assert relation["presentation_role"] in {"data", "navigation"}
        assert relation["requested_financial_year"] == "2024-25"
        assert relation["unit"] == "AUD"


def test_canonical_parent_stays_additive_and_related_edges_are_explicit(
    client: TestClient,
) -> None:
    body = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    commonwealth = next(child for child in body["children"] if child["name"] == "Commonwealth")
    defence = next(child for child in commonwealth["children"] if child["name"] == "Defence")
    assert defence["relationship"]["branch_kind"] == "additive"
    assert defence["relationship"]["compatibility_group"] == "actual_expense"
    assert defence["value"] == 50175000000.0

    related_defence = next(child for child in defence["children"] if child["name"] == "Defence")
    relation = related_defence["relationship"]
    assert relation["edge_kind"] == "related_breakdown"
    assert relation["branch_kind"] == "related"
    assert relation["presentation_role"] == "navigation"
    assert relation["edge_set_id"] == "statement_6_under_abs"
    assert relation["source_key"] == "federal_budget_statement_6_a61"

    descendants = list(_walk(related_defence))
    assert descendants
    assert all(node["relationship"]["branch_kind"] == "related" for node in descendants)
    assert any(node["relationship"]["edge_kind"] == "same_group" for node in descendants)


def test_historical_projection_remains_exact_and_additive(client: TestClient) -> None:
    body = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2022-23"},
    ).json()
    projection = body["projection"]
    assert projection["max_visible_depth"] == 2
    assert projection["max_additive_depth"] == 2
    assert projection["contains_related_branches"] is False
    assert all(node["relationship"]["is_year_fallback"] is False for node in _walk(body))


def test_projection_contract_has_rollback_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DASHBOARD_PROJECTION_V2", "0")
    body = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2022-23"},
    ).json()
    assert body["projection"] is None
    assert all(node["relationship"] is None for node in _walk(body))

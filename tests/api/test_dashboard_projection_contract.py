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
        # 3, not 4: the AusTender "contracts" related branch (previously
        # depth 4 via nearest-earlier fallback to stale 2019-20 data) was
        # refreshed to a current (2025-26+) sample - since fallback only
        # ever looks to an EARLIER year, never a future one, that branch is
        # now correctly absent for a 2024-25 request. The deepest surviving
        # branch for this year is "grants"/"pbs" at depth 3 (see
        # test_canonical_parent_stays_additive_and_related_edges_are_explicit,
        # which moved to 2025-26 to keep exercising AusTender's deep
        # cascade specifically).
        "max_visible_depth": 3,
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
    # 2025-26, not 2024-25: this test specifically exercises the deep
    # related cascade (PBS -> AusTender contracts), which after the
    # AusTender refresh to current (2025-26+) data only reaches its full
    # depth for years the current sample actually covers - a 2024-25
    # request now correctly stops at the bare Statement 6/FBO wrapper
    # nodes (verified live; see test_projection_contract_covers_every_
    # non_root_node's max_visible_depth comment for the full explanation).
    body = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2025-26"},
    ).json()
    commonwealth = next(child for child in body["children"] if child["name"] == "Commonwealth")
    defence = next(child for child in commonwealth["children"] if child["name"] == "Defence")
    assert defence["relationship"]["branch_kind"] == "additive"
    assert defence["relationship"]["compatibility_group"] == "actual_expense"
    assert defence["value"] == 46040125000.0

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


@pytest.mark.parametrize(
    ("year", "root_total"),
    (("2022-23", 639703000000.0), ("2023-24", 687277000000.0)),
)
def test_historical_fbo_projection_is_exact_related_and_non_additive(
    client: TestClient, year: str, root_total: float
) -> None:
    body = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": year},
    ).json()
    projection = body["projection"]
    assert projection["max_visible_depth"] == 3
    assert projection["max_additive_depth"] == 2
    assert projection["contains_related_branches"] is True
    fbo_summary = next(
        summary
        for summary in projection["branch_summaries"]
        if summary["branch_family"] == "fbo"
    )
    assert fbo_summary == {
        "branch_family": "fbo",
        "branch_kind": "related",
        "node_count": 81,
        "max_depth": 2,
    }
    assert all(node["relationship"]["is_year_fallback"] is False for node in _walk(body))

    commonwealth = next(child for child in body["children"] if child["name"] == "Commonwealth")
    assert commonwealth["value"] == root_total
    assert len(commonwealth["children"]) == 11
    folders = [
        child
        for purpose in commonwealth["children"]
        for child in purpose.get("children") or []
        if child["name"] == "Historical FBO Appendix A (audited)"
    ]
    assert len(folders) == 11
    assert all(folder["relationship"]["edge_set_id"] == "fbo_archive_under_abs" for folder in folders)
    assert all(folder["relationship"]["presentation_role"] == "navigation" for folder in folders)

    fbo_nodes = [
        node
        for folder in folders
        for node in _walk(folder)
        if node["relationship"].get("source_key")
        == "federal_budget_archive_function_series"
    ]
    assert fbo_nodes
    assert all(node["relationship"]["branch_kind"] == "related" for node in fbo_nodes)
    assert all(node["relationship"]["fact_financial_year"] == year for node in fbo_nodes)
    assert all(node["relationship"]["accounting_basis"] == "accrual" for node in fbo_nodes)
    assert all(node["relationship"]["estimate_status"] == "audited_actual" for node in fbo_nodes)


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

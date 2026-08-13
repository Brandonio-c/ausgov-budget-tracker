from __future__ import annotations

import sqlite3
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
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = db
    from backend.main import app

    return TestClient(app)


def test_list_explorers_returns_all_five_registered_families(client: TestClient) -> None:
    response = client.get("/v2/explorers")
    assert response.status_code == 200
    body = response.json()
    ids = {f["id"] for f in body["families"]}
    assert ids == {"contracts", "grants", "vic_output_performance", "act_invoices", "pbs"}

    pbs = next(f for f in body["families"] if f["id"] == "pbs")
    assert pbs["compatibility_group"] == "budget_expense"
    assert pbs["source_key"] == "federal_pbs_programs_all"
    assert pbs["estimate_statuses"] == [
        "budget",
        "forward_estimate",
        "estimated_actual",
        "actual",
    ]


def test_pbs_availability_matches_direct_sql(client: TestClient) -> None:
    response = client.get("/v2/explorers/pbs/availability")
    assert response.status_code == 200
    body = response.json()
    assert body["family"]["id"] == "pbs"

    row = next(
        r
        for r in body["years"]
        if r["financial_year"] == "2024-25" and r["estimate_status"] == "actual"
    )

    conn = sqlite3.connect(REPO_ROOT / "data" / "facts.db")
    expected = conn.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(f.amount_aud), 0)
        FROM facts f
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE m.compatibility_group = 'budget_expense'
          AND f.accounting_basis = 'accrual'
          AND f.estimate_status = 'actual'
          AND f.financial_year = '2024-25'
          AND d.source_key = 'federal_pbs_programs_all'
          AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
        """
    ).fetchone()
    conn.close()

    assert row["count"] == expected[0]
    assert row["value"] == pytest.approx(expected[1])


def test_contracts_availability_is_not_narrowed_by_a_source_key(
    client: TestClient,
) -> None:
    """contracts has no source_key in the registry - availability must equal
    the same multi-jurisdiction total /v2/tree reports for that scope."""
    availability = client.get("/v2/explorers/contracts/availability").json()
    row = next(
        r
        for r in availability["years"]
        if r["financial_year"] == "2024-25" and r["estimate_status"] == "contract"
    )

    tree = client.get(
        "/v2/tree",
        params={
            "compatibility_group": "commitment",
            "accounting_basis": "commitment",
            "estimate_status": "contract",
            "financial_year": "2024-25",
            "limit": 1,
        },
    ).json()

    assert row["count"] == tree["total_count"]
    assert row["value"] == pytest.approx(tree["total_value"])


def test_unknown_family_returns_404(client: TestClient) -> None:
    response = client.get("/v2/explorers/does-not-exist/availability")
    assert response.status_code == 404


# --- /{family}/tree -------------------------------------------------------


def test_pbs_family_tree_matches_direct_v2_tree_with_source_key(client: TestClient) -> None:
    family_tree = client.get(
        "/v2/explorers/pbs/tree",
        params={"financial_year": "2026-27", "limit": 5},
    ).json()
    direct = client.get(
        "/v2/tree",
        params={
            "compatibility_group": "budget_expense",
            "accounting_basis": "accrual",
            "estimate_status": "budget",  # pbs' default_estimate_status
            "financial_year": "2026-27",
            "source_key": "federal_pbs_programs_all",
            "limit": 5,
        },
    ).json()
    assert family_tree["total_count"] == direct["total_count"]
    assert family_tree["total_value"] == pytest.approx(direct["total_value"])
    assert family_tree["children"] == direct["children"]
    assert family_tree["family"] == "pbs"


def test_family_tree_explicit_estimate_status_must_be_registered(client: TestClient) -> None:
    ok = client.get(
        "/v2/explorers/pbs/tree",
        params={"financial_year": "2024-25", "estimate_status": "actual", "limit": 1},
    )
    assert ok.status_code == 200

    bad = client.get(
        "/v2/explorers/pbs/tree",
        params={"financial_year": "2024-25", "estimate_status": "invoice", "limit": 1},
    )
    assert bad.status_code == 400
    assert "must be one of" in bad.json()["detail"]


def test_family_tree_rejects_path_rather_than_fabricating_hierarchy(
    client: TestClient,
) -> None:
    response = client.get(
        "/v2/explorers/pbs/tree",
        params={"financial_year": "2026-27", "path": "some/agency"},
    )
    assert response.status_code == 400
    assert "no source-native hierarchy" in response.json()["detail"]


def test_contracts_family_tree_is_not_narrowed_by_a_source_key(client: TestClient) -> None:
    """Same discipline as the availability test above, applied to /tree."""
    family_tree = client.get(
        "/v2/explorers/contracts/tree",
        params={"financial_year": "2024-25", "limit": 1},
    ).json()
    direct = client.get(
        "/v2/tree",
        params={
            "compatibility_group": "commitment",
            "accounting_basis": "commitment",
            "estimate_status": "contract",
            "financial_year": "2024-25",
            "limit": 1,
        },
    ).json()
    assert family_tree["total_count"] == direct["total_count"] == 9036
    assert len(family_tree["source_breakdown"]) > 1


def test_family_tree_search_narrows_within_the_family_scope(client: TestClient) -> None:
    unfiltered = client.get(
        "/v2/explorers/pbs/tree", params={"financial_year": "2026-27", "limit": 1}
    ).json()
    filtered = client.get(
        "/v2/explorers/pbs/tree",
        params={"financial_year": "2026-27", "q": "health", "limit": 200},
    ).json()
    assert 0 < filtered["total_count"] < unfiltered["total_count"]
    assert all("health" in c["name"].lower() for c in filtered["children"])


def test_unknown_family_tree_returns_404(client: TestClient) -> None:
    response = client.get(
        "/v2/explorers/does-not-exist/tree", params={"financial_year": "2024-25"}
    )
    assert response.status_code == 404


# --- /{family}/facets -------------------------------------------------------


def test_pbs_facets_are_single_source_after_registry_scoping(client: TestClient) -> None:
    facets = client.get("/v2/explorers/pbs/facets").json()
    assert facets["family"]["id"] == "pbs"
    assert len(facets["sources"]) == 1
    assert facets["sources"][0]["source_key"] == "federal_pbs_programs_all"
    assert {s["measure_type"] for s in facets["measures"]} == {"budget_estimate"}
    statuses = {s["estimate_status"] for s in facets["estimate_statuses"]}
    assert statuses <= {"budget", "forward_estimate", "estimated_actual", "actual"}
    assert any(y["financial_year"] == "2026-27" for y in facets["years"])


def test_contracts_facets_reveal_multi_jurisdiction_sources(client: TestClient) -> None:
    facets = client.get("/v2/explorers/contracts/facets").json()
    source_keys = {s["source_key"] for s in facets["sources"]}
    assert source_keys == {
        "federal_austender_contracts",
        "nsw_procurement_ocds_registry",
        "nt_awarded_government_contracts",
        "qld_contract_disclosure_agency_datasets",
    }


def test_unknown_family_facets_returns_404(client: TestClient) -> None:
    response = client.get("/v2/explorers/does-not-exist/facets")
    assert response.status_code == 404


# --- /{family}/item/{fact_id} -----------------------------------------------


def test_pbs_item_lookup_matches_the_fact_from_its_own_tree(client: TestClient) -> None:
    tree = client.get(
        "/v2/explorers/pbs/tree",
        params={"financial_year": "2026-27", "limit": 1},
    ).json()
    fact_id = tree["children"][0]["id"]

    item = client.get(f"/v2/explorers/pbs/item/{fact_id}")
    assert item.status_code == 200
    body = item.json()
    assert body["family"] == "pbs"
    assert body["value"] == tree["children"][0]["value"]
    assert body["citation"]["fact_id"] == fact_id


def test_item_lookup_enforces_family_boundary_even_for_a_real_fact_id(
    client: TestClient,
) -> None:
    """A fact_id that is real and publishable in the grants family must
    still 404 under the pbs family - family scope must be meaningful, not
    just a UI label."""
    grants_tree = client.get(
        "/v2/explorers/grants/tree",
        params={"financial_year": "2024-25", "limit": 1},
    ).json()
    assert grants_tree["children"], "grants scope has no 2024-25 rows; test is stale"
    fact_id = grants_tree["children"][0]["id"]

    same_family = client.get(f"/v2/explorers/grants/item/{fact_id}")
    assert same_family.status_code == 200

    cross_family = client.get(f"/v2/explorers/pbs/item/{fact_id}")
    assert cross_family.status_code == 404


def test_item_lookup_unknown_fact_id_returns_404(client: TestClient) -> None:
    response = client.get("/v2/explorers/pbs/item/999999999")
    assert response.status_code == 404


def test_unknown_family_item_returns_404(client: TestClient) -> None:
    response = client.get("/v2/explorers/does-not-exist/item/1")
    assert response.status_code == 404

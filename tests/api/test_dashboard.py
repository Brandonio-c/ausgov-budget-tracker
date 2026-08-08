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
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = db
    from backend.main import app

    return TestClient(app)


def test_dashboard_levels_actuals(client: TestClient) -> None:
    r = client.get("/v2/dashboard/levels", params={"mode": "actuals"})
    assert r.status_code == 200
    levels = {row["level"] for row in r.json()}
    assert "federal" in levels


def test_dashboard_tree_actuals_federal(client: TestClient) -> None:
    years = client.get(
        "/v2/dashboard/years", params={"mode": "actuals", "level": "federal"}
    ).json()
    assert years
    year = years[-1]
    r = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": year},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["children"]
    # Totals should not dominate top-level jurisdiction children exclusively
    names = [c["name"] for c in body["children"]]
    assert names


def test_dashboard_availability_selects_basis_per_federal_actual_year(
    client: TestClient,
) -> None:
    response = client.get(
        "/v2/dashboard/availability",
        params={"mode": "actuals", "level": "federal"},
    )
    assert response.status_code == 200
    availability = response.json()
    by_year = {item["financial_year"]: item for item in availability}

    for year in ("2005-06", "2006-07", "2007-08"):
        assert by_year[year]["selected_basis"] == "accrual"
        assert by_year[year]["available_bases"] == ["accrual"]
        assert by_year[year]["source_families"]

    assert by_year["2008-09"]["selected_basis"] == "gfs"
    assert by_year["2008-09"]["available_bases"] == ["accrual", "gfs"]
    assert by_year["2024-25"]["selected_basis"] == "gfs"

    years = client.get(
        "/v2/dashboard/years",
        params={"mode": "actuals", "level": "federal"},
    ).json()
    assert years == [item["financial_year"] for item in availability]


def test_every_returned_federal_actual_year_is_queryable(client: TestClient) -> None:
    years = client.get(
        "/v2/dashboard/years",
        params={"mode": "actuals", "level": "federal"},
    ).json()
    for year in years:
        response = client.get(
            "/v2/dashboard/tree",
            params={"mode": "actuals", "level": "federal", "year": year},
        )
        assert response.status_code == 200, (year, response.text)
        assert response.json()["projection"]["selected_accounting_basis"] in {
            "gfs",
            "accrual",
        }


def test_dashboard_tree_budget(client: TestClient) -> None:
    levels = client.get("/v2/dashboard/levels", params={"mode": "budget"}).json()
    assert levels
    level = levels[0]["level"]
    years = client.get(
        "/v2/dashboard/years", params={"mode": "budget", "level": level}
    ).json()
    assert years
    r = client.get(
        "/v2/dashboard/tree",
        params={"mode": "budget", "level": level, "year": years[-1]},
    )
    assert r.status_code == 200
    assert r.json()["children"]


def test_dashboard_item_has_citation(client: TestClient) -> None:
    years = client.get(
        "/v2/dashboard/years", params={"mode": "actuals", "level": "federal"}
    ).json()
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": years[-1]},
    ).json()

    def find_leaf(node):
        if node.get("id") is not None and not node.get("children"):
            return node["id"]
        for child in node.get("children") or []:
            found = find_leaf(child)
            if found is not None:
                return found
        return None

    fact_id = find_leaf(tree)
    assert fact_id is not None
    r = client.get(f"/v2/dashboard/item/{fact_id}")
    assert r.status_code == 200
    cit = r.json()["citation"]
    assert cit["landing_url"]
    assert cit["original_resource_url"]
    assert cit["cached_copy_url"]
    assert cit["locator"]


def _find_leaf(node):
    if node.get("id") is not None and not node.get("children"):
        return node["id"]
    for child in node.get("children") or []:
        found = _find_leaf(child)
        if found is not None:
            return found
    return None


def test_dashboard_evidence_spreadsheet(client: TestClient) -> None:
    years = client.get(
        "/v2/dashboard/years", params={"mode": "actuals", "level": "federal"}
    ).json()
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": years[-1]},
    ).json()
    fact_id = _find_leaf(tree)
    assert fact_id is not None

    r = client.get(f"/v2/dashboard/item/{fact_id}/evidence")
    assert r.status_code == 200
    body = r.json()
    assert body["media_type"] in {"spreadsheet", "pdf", "text_chunk", "unsupported"}
    assert body["locator"]
    assert body["citation"]["locator"]
    assert "has_source_file" in body

    if body["has_source_file"]:
        file_r = client.get(f"/v2/dashboard/item/{fact_id}/source-file")
        assert file_r.status_code == 200
        assert len(file_r.content) > 0


def test_dashboard_evidence_pdf_page(client: TestClient) -> None:
    # Known Statement 6 budget fact with page locator
    r = client.get("/v2/dashboard/item/257675/evidence")
    if r.status_code == 404:
        pytest.skip("PDF fact 257675 not present in this facts.db")
    body = r.json()
    assert body["media_type"] == "pdf"
    assert body["page_number"] == 225
    assert body["has_source_file"] is True
    file_r = client.get("/v2/dashboard/item/257675/source-file")
    assert file_r.status_code == 200
    assert file_r.headers["content-type"].startswith("application/pdf")


def test_dashboard_evidence_cell_locator(client: TestClient) -> None:
    r = client.get("/v2/dashboard/item/3/evidence")
    if r.status_code == 404:
        pytest.skip("fact id 3 not present")
    body = r.json()
    assert body["media_type"] == "spreadsheet"
    assert body["sheet_name"] == "2005-06"
    assert body["cell"] == "L7"
    assert body["highlight"]["cell"] == "L7"


def test_dashboard_source_file_missing_fact(client: TestClient) -> None:
    r = client.get("/v2/dashboard/item/999999999/source-file")
    assert r.status_code == 404


def test_dashboard_abs_hierarchy_nests_health(client: TestClient) -> None:
    years = client.get(
        "/v2/dashboard/years", params={"mode": "actuals", "level": "federal"}
    ).json()
    assert "2024-25" in years
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    commonwealth = next(c for c in tree["children"] if c["name"] == "Commonwealth")
    names = {c["name"] for c in commonwealth["children"]}
    assert "Health" in names
    assert "Education" in names
    assert "Social protection" in names
    # Health detail should not sit at the top level anymore
    assert "Hospital services" not in names
    health = next(c for c in commonwealth["children"] if c["name"] == "Health")
    assert health["id"] is None
    assert health["children"]
    child_names = {c["name"] for c in health["children"]}
    assert "Hospital services" in child_names
    assert "Community health services" in child_names


def test_dashboard_social_protection_breakdown_note(client: TestClient) -> None:
    r = client.get("/v2/dashboard/item/4186/evidence")
    if r.status_code == 404:
        pytest.skip("fact 4186 missing")
    body = r.json()
    assert body.get("breakdown_note")
    assert "single aggregate" in body["breakdown_note"]

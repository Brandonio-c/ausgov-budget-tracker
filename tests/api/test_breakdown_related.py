"""Regression: related_breakdown children must not roll into parent pie totals."""

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


def _find_named(node: dict, name: str) -> dict | None:
    if node.get("name") == name:
        return node
    for child in node.get("children") or []:
        found = _find_named(child, name)
        if found:
            return found
    return None


def _max_depth(node: dict) -> int:
    kids = node.get("children") or []
    if not kids:
        return 0
    return 1 + max(_max_depth(c) for c in kids)


def test_social_protection_related_does_not_rollup(client: TestClient) -> None:
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    sp = _find_named(tree, "Social protection")
    assert sp is not None
    assert sp.get("breakdown", {}).get("kind") == "related_breakdown"
    assert sp.get("children")
    parent_value = sp["value"]
    child_sum = sum(c["value"] for c in sp["children"])
    # Parent keeps GFS amount; related budget children must not redefine it.
    assert abs(parent_value - child_sum) > 1_000_000
    assert sp["id"] is not None


def test_social_protection_subfunction_amounts_sane(client: TestClient) -> None:
    """Related SSW slices must be A.6.1-scale (~billions), not PBS $'000 double-scaled."""
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    sp = _find_named(tree, "Social protection")
    assert sp is not None
    aged = next(c for c in sp["children"] if c["name"] == "Assistance to the aged")
    # ~$100B AUD, never multi-quadrillion chart poison
    assert 50e9 < aged["value"] < 200e9
    child_sum = sum(c["value"] for c in (aged.get("children") or []))
    # Deeper packs must not re-total the A.6.1 slice on the related pie
    if aged.get("children"):
        assert abs(aged["value"] - child_sum) > 1.0 or child_sum == 0


def test_aged_component_drill_never_substitutes_a_future_year(client: TestClient) -> None:
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    aged = _find_named(tree, "Assistance to the aged")
    assert aged is not None
    # Task 7 (semantic-defect milestone): the fallback policy forbids
    # selecting a *later* year than requested - this A.6.1 slice itself has
    # an exact 2024-25 figure, so no fallback disclosure is needed here.
    bd = aged.get("breakdown") or {}
    assert bd.get("fallback_reason") == "exact_year_match"
    assert bd.get("is_year_fallback") is False
    assert bd.get("requested_financial_year") == "2024-25"
    # Its nested same_group components only have 2025-26+ data published -
    # since that is a *future* year relative to the 2024-25 request, they
    # must NOT be silently substituted in (this was the actual bug: the
    # old fallback preferred a later year over no result at all).
    assert not aged.get("children")


def test_dss_pbs_program_amounts_not_double_scaled(client: TestClient) -> None:
    import sqlite3

    conn = sqlite3.connect(str(REPO_ROOT / "data" / "facts.db"))
    row = conn.execute(
        """
        SELECT MAX(f.amount_aud)
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE d.source_key = 'federal_dss_pbs_programs'
        """
    ).fetchone()
    conn.close()
    assert row and row[0] is not None
    # Largest SSW program ~$70B; anything > $5T is the old double-scale bug
    assert row[0] < 5e12



def test_health_keeps_abs_kids_and_s6_folder(client: TestClient) -> None:
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    health = _find_named(tree, "Health")
    assert health is not None
    assert health.get("breakdown") in (None, {})
    child_names = {c["name"] for c in health.get("children") or []}
    assert "Hospital services" in child_names
    assert "Statement 6 (budget estimates)" in child_names
    s6 = next(c for c in health["children"] if c["name"] == "Statement 6 (budget estimates)")
    assert s6.get("breakdown", {}).get("kind") == "related_breakdown"
    # ABS same_group rollup excludes related folder
    additive = [
        c
        for c in health["children"]
        if (c.get("breakdown") or {}).get("kind") != "related_breakdown"
    ]
    assert abs(health["value"] - sum(c["value"] for c in additive)) < 1.0


def test_budget_ssw_edge_cascade(client: TestClient) -> None:
    years = client.get(
        "/v2/dashboard/years", params={"mode": "budget", "level": "federal"}
    ).json()
    year = "2025-26" if "2025-26" in years else years[-1]
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "budget", "level": "federal", "year": year},
    ).json()
    aged = _find_named(tree, "Assistance to the aged")
    assert aged is not None
    assert aged.get("children"), "budget Aged should nest components via edges"
    # Parent value is same_group rollup of children when children present
    if aged["children"]:
        assert abs(aged["value"] - sum(c["value"] for c in aged["children"])) < 1.0 or aged.get(
            "breakdown"
        )


def test_item_children_related_endpoint(client: TestClient) -> None:
    # Commonwealth Social protection 2024-25 fact
    r = client.get("/v2/dashboard/item/4186/children", params={"year": "2024-25"})
    if r.status_code == 404:
        pytest.skip("fact 4186 missing")
    body = r.json()
    assert body["kind"] == "related_breakdown"
    assert body["breakdown"]["kind"] == "related_breakdown"
    assert body["children"]
    assert body.get("parent_amount_aud")
    child_sum = sum(c["value"] for c in body["children"])
    assert abs(body["parent_amount_aud"] - child_sum) > 1_000_000
    # Task 7: nested same_group components under these 2024-25 related
    # children only have budget-year (2025-26+) data published. A future
    # year is never a legitimate substitute for an earlier requested year,
    # so none of them may show a nested cascade for this request.
    assert not any(c.get("children") for c in body["children"])


def test_commonwealth_pie_excludes_related_from_top_total(client: TestClient) -> None:
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    cw = _find_named(tree, "Commonwealth")
    assert cw is not None
    sp = next(c for c in cw["children"] if c["name"] == "Social protection")
    related_sum = sum(c["value"] for c in (sp.get("children") or []))
    assert abs(cw["value"] - sum(c["value"] for c in cw["children"])) < 1.0
    assert abs(sp["value"] - related_sum) > 1_000_000


def test_thin_purposes_have_related_depth(client: TestClient) -> None:
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    cw = _find_named(tree, "Commonwealth")
    assert cw is not None
    assert abs(cw["value"] - 745.03e9) < 0.5e9

    for purpose in ("Defence", "Economic affairs", "Transport"):
        node = _find_named(tree, purpose)
        assert node is not None, purpose
        assert _max_depth(node) > 1, f"{purpose} should expose related depth"

    # Task 7: the PBS "Program ..." same_group cascade only has budget-year
    # (2025-26+) data published, which is a *future* year relative to this
    # 2024-25 actuals request and must not be silently substituted in - so
    # it is correctly absent here. AusTender contracts were refreshed from
    # a stale 2019-20 sample (which happened to fall within 2024-25's
    # nearest-earlier range) to a current 2025-26+ sample (which, being
    # later than 2024-25, correctly does NOT fall back into this request -
    # fallback only ever looks earlier, never later). Verify the same
    # named supplier-level detail on the year the current sample actually
    # covers instead of pretending the (now historical) 2024-25 view still
    # reaches it.
    tree_current = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2025-26"},
    ).json()
    defence_current = _find_named(tree_current, "Defence")
    assert defence_current is not None
    assert any("–" in c["name"] for c in _walk(defence_current)), (
        "Defence related cascade should still reach named contract-level detail"
    )


def test_health_education_s6_folder_preserves_parent_amount(client: TestClient) -> None:
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "federal", "year": "2024-25"},
    ).json()
    for purpose in ("Health", "Education"):
        node = _find_named(tree, purpose)
        assert node is not None
        folders = [
            c
            for c in (node.get("children") or [])
            if c["name"].startswith("Statement 6") or c["name"].startswith("FBO")
        ]
        assert folders, f"{purpose} needs Statement 6 or FBO folder"
        for folder in folders:
            assert folder.get("breakdown", {}).get("kind") == "related_breakdown"
            assert abs(folder["value"] - node["value"]) < 1.0
        # Related folders must not inflate the GFS parent pie
        additive = [
            c
            for c in (node.get("children") or [])
            if not (
                (c.get("breakdown") or {}).get("kind") == "related_breakdown"
                and (
                    c["name"].startswith("Statement 6")
                    or c["name"].startswith("FBO")
                )
            )
        ]
        if additive:
            assert abs(node["value"] - sum(c["value"] for c in additive)) < 1.0


def _walk(node: dict):
    for child in node.get("children") or []:
        yield child
        yield from _walk(child)

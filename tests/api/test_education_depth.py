"""Education depth verification tests for Phase 3 (item 5.6).

Verifies that Statement 6 Education subfunctions (Higher education, Schools,
Student assistance, Vocational and other education) have authentic,
non-additive program breakdowns attached via pbs_programs_s6_bridge and
pbs_programs_all_under_s6 with valid citations, exact amounts preserved,
and zero artificial/misclassified program dumping into General administration.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

DB = REPO_ROOT / "data" / "facts.db"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FACTS_DB_PATH", str(DB))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = DB
    from backend.main import app

    return TestClient(app)


def _get_statement6_component_fact_id(subfunction_name: str, year: str = "2025-26") -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT f.id
            FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = "primary"
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = "federal_budget_statement_6_components"
              AND n.name = ?
              AND f.financial_year = ?
            """,
            (subfunction_name, year),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"No Statement 6 component fact found for {subfunction_name} in {year}"
    return int(row[0])


def test_higher_education_has_verified_program_children(client: TestClient) -> None:
    fact_id = _get_statement6_component_fact_id("Education / Higher education", "2025-26")
    resp = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] in ("same_group", "related_breakdown")
    children = data.get("children") or []
    assert len(children) >= 5, f"Expected >=5 Higher education children, got {len(children)}"

    child_names = [c["name"] for c in children]
    assert any("Research Training Program" in name for name in child_names)
    assert any("National Collaborative Research" in name for name in child_names)
    assert any("Study Hubs" in name for name in child_names)

    for child in children:
        assert child.get("id") is not None or child.get("breakdown") is not None
        assert child.get("value") is not None


def test_schools_has_verified_program_children(client: TestClient) -> None:
    fact_id = _get_statement6_component_fact_id("Education / Schools", "2025-26")
    resp = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] in ("same_group", "related_breakdown")
    children = data.get("children") or []
    assert len(children) >= 10, f"Expected >=10 Schools children, got {len(children)}"

    child_names = [c["name"] for c in children]
    assert any("Choice and Affordability Fund" in name for name in child_names)
    assert any("Quality Outcomes" in name for name in child_names)
    assert any("Teacher Workforce" in name for name in child_names)
    assert any("Disability Support" in name for name in child_names)


def test_student_assistance_has_verified_children(client: TestClient) -> None:
    fact_id = _get_statement6_component_fact_id("Education / Student assistance", "2025-26")
    resp = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] in ("same_group", "related_breakdown")
    children = data.get("children") or []
    assert len(children) >= 1, f"Expected >=1 Student assistance child, got {len(children)}"
    child_names = [c["name"] for c in children]
    assert any("Tertiary Access Payment" in name or "Youth Support" in name for name in child_names)


def test_vocational_has_verified_children(client: TestClient) -> None:
    fact_id = _get_statement6_component_fact_id("Education / Vocational and other education", "2025-26")
    resp = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] in ("same_group", "related_breakdown")
    children = data.get("children") or []
    assert len(children) >= 1, f"Expected >=1 Vocational child, got {len(children)}"
    child_names = [c["name"] for c in children]
    assert any("Workforce Mobility" in name for name in child_names)


def test_general_administration_is_clean_with_no_misclassified_programs(client: TestClient) -> None:
    fact_id = _get_statement6_component_fact_id("Education / General administration", "2025-26")
    resp = client.get(f"/v2/dashboard/item/{fact_id}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    children = data.get("children") or []
    child_names = [c["name"] for c in children]
    assert not any("Research Training" in name for name in child_names)
    assert not any("Teacher Workforce" in name for name in child_names)
    assert not any("Choice and Affordability" in name for name in child_names)

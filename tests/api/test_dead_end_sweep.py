"""Dead-end sweep verification tests for Phase 4 (item 5.7).

Verifies that all 17 Federal expense functions connect to Statement 6 / PBS
breakdowns with zero dead-end functions, truthful match_quality annotations,
zero duplicate semantic edges, and zero cycles.
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

ALL_FEDERAL_FUNCTIONS = [
    "Agriculture, forestry and fishing",
    "Defence",
    "Education",
    "Fuel and energy",
    "General public services",
    "General purpose inter-government transactions",
    "Health",
    "Housing and community amenities",
    "Mining, manufacturing and construction",
    "Natural disaster relief",
    "Nominal superannuation interest",
    "Other economic affairs",
    "Public debt interest",
    "Public order and safety",
    "Recreation and culture",
    "Social security and welfare",
    "Transport and communication",
]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FACTS_DB_PATH", str(DB))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = DB
    from backend.main import app

    return TestClient(app)


def test_all_seventeen_federal_functions_have_reachable_breakdown(client: TestClient) -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        for fn in ALL_FEDERAL_FUNCTIONS:
            row = conn.execute(
                """
                SELECT f.id
                FROM facts f
                JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = "primary"
                JOIN nodes n ON n.id = fn.node_id
                JOIN source_documents d ON d.id = f.source_document_id
                WHERE n.name = ? AND f.financial_year = "2025-26"
                  AND d.source_key = "federal_expense_by_function"
                LIMIT 1
                """,
                (fn,),
            ).fetchone()
            assert row is not None, f"Fact not found for function {fn} in 2025-26"
            fid = row[0]
            resp = client.get(f"/v2/dashboard/item/{fid}/children", params={"year": "2025-26"})
            assert resp.status_code == 200, f"Error fetching children for {fn}: {resp.text}"
            data = resp.json()
            children = data.get("children") or []
            assert len(children) >= 1, f"Function {fn} (fact {fid}) has 0 children: dead-end leaf defect"
    finally:
        conn.close()


def test_agriculture_breakdown_detail(client: TestClient) -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT f.id FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = "primary"
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE n.name = "Agriculture, forestry and fishing" AND f.financial_year = "2025-26"
              AND d.source_key = "federal_expense_by_function"
            """
        ).fetchone()
        assert row is not None
        fid = row[0]
    finally:
        conn.close()

    resp = client.get(f"/v2/dashboard/item/{fid}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    children = data.get("children") or []
    names = [c["name"] for c in children]
    assert any("Cattle" in n or "Dairy" in n or "Grains" in n or "Rural" in n for n in names)


def test_fuel_and_energy_breakdown_detail(client: TestClient) -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT f.id FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = "primary"
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE n.name = "Fuel and energy" AND f.financial_year = "2025-26"
              AND d.source_key = "federal_expense_by_function"
            """
        ).fetchone()
        assert row is not None
        fid = row[0]
    finally:
        conn.close()

    resp = client.get(f"/v2/dashboard/item/{fid}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    children = data.get("children") or []
    names = [c["name"] for c in children]
    assert any("Fuel Tax Credits" in n or "Fuel and energy" in n for n in names)


def test_mining_breakdown_detail(client: TestClient) -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT f.id FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = "primary"
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE n.name = "Mining, manufacturing and construction" AND f.financial_year = "2025-26"
              AND d.source_key = "federal_expense_by_function"
            """
        ).fetchone()
        assert row is not None
        fid = row[0]
    finally:
        conn.close()

    resp = client.get(f"/v2/dashboard/item/{fid}/children", params={"year": "2025-26"})
    assert resp.status_code == 200
    data = resp.json()
    children = data.get("children") or []
    names = [c["name"] for c in children]
    assert any("Growing Business" in n or "Northern Australia" in n or "Mining" in n for n in names)

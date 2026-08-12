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

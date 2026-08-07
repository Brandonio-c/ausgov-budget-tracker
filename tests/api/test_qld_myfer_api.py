"""API isolation and disclosure tests for Queensland MYFER."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))

from schema_migrate import migrate  # noqa: E402


def _seed(db: Path) -> None:
    conn = sqlite3.connect(str(db))
    myfer_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('qld_myfer', 'Queensland Treasury', 'Queensland MYFER', 'QLD', 'state', 'handoff_actuals_state')
        """
    ).lastrowid
    myfer_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('qld_myfer|node|qld_myfer_revenue', 'category', 'QLD MYFER revenue', 'QLD', 'state', ?)
        """,
        (myfer_doc,),
    ).lastrowid
    myfer_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_start, period_end, period_granularity,
            measure_type, accounting_basis, estimate_status, amount_aud, unit,
            currency, source_document_id, source_locator_json, retrieved_at,
            source_budget_year, publication_date, view_family
        ) VALUES (
            'qld_myfer|vintage:2018-19|fy:2018-19|qld_myfer_revenue|gfs|revised_estimate|QLD',
            '2018-19', '2018-07-01', '2019-06-30', 'financial_year',
            'qld_myfer_revenue', 'gfs', 'revised_estimate', 59002000000,
            'AUD', 'AUD', ?,
            '{"locator":"file:test.pdf | page:14 | row:Revenue | column:MYFER","cached_copy_path":"test.pdf"}',
            datetime('now'), '2018-19', '2019-01-14', 'qld_myfer'
        )
        """,
        (myfer_doc,),
    ).lastrowid
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (myfer_fact, myfer_node),
    )

    annual_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('test_annual_qld', 'Test', 'Test annual QLD', 'QLD', 'state', 'test')
        """
    ).lastrowid
    annual_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('test|qld|education', 'category', 'Education', 'QLD', 'state', ?)
        """,
        (annual_doc,),
    ).lastrowid
    annual_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type,
            accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_locator_json, retrieved_at
        ) VALUES (
            'test|annual|qld|education', '2024-25', 'financial_year',
            'gfs_expense', 'gfs', 'actual', 750000, 'AUD', 'AUD', ?,
            '{"locator":"test-annual"}', datetime('now')
        )
        """,
        (annual_doc,),
    ).lastrowid
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
        (annual_fact, annual_node),
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    db = tmp_path / "facts.db"
    migrate(db)
    _seed(db)
    monkeypatch.setenv("FACTS_DB_PATH", str(db))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = db
    from backend.main import app

    return TestClient(app)


def test_measure_list_is_the_five_measure_safe_cluster(client: TestClient):
    response = client.get("/v2/qld-myfer/measures")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert {item["measure_type"] for item in body} >= {
        "qld_myfer_revenue",
        "qld_myfer_fiscal_balance",
    }
    assert all(item["period_granularity"] == "financial_year" for item in body)


def test_series_discloses_period_vintage_status_and_citation(client: TestClient):
    response = client.get(
        "/v2/qld-myfer/series", params={"measure_type": "qld_myfer_revenue"}
    )
    assert response.status_code == 200
    fact = response.json()["facts"][0]
    assert fact["financial_year"] == "2018-19"
    assert fact["period_start"] == "2018-07-01"
    assert fact["period_end"] == "2019-06-30"
    assert fact["source_budget_year"] == "2018-19"
    assert fact["publication_date"] == "2019-01-14"
    assert fact["estimate_status"] == "revised_estimate"
    assert fact["flow_or_stock"] == "flow"
    assert "page:14" in fact["citation"]["locator"]


def test_unknown_measure_rejected(client: TestClient):
    response = client.get(
        "/v2/qld-myfer/series", params={"measure_type": "qld_rsf_revenue"}
    )
    assert response.status_code == 400


def test_annual_dashboard_is_unchanged_by_myfer(client: TestClient):
    response = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "state", "year": "2024-25"},
    )
    assert response.status_code == 200
    before = response.json()["value"]

    import backend.facts_db as facts_db_mod

    conn = sqlite3.connect(str(facts_db_mod.FACTS_DB_FILE))
    conn.execute("DELETE FROM facts WHERE measure_type LIKE 'qld_myfer_%'")
    conn.commit()
    conn.close()
    after = client.get(
        "/v2/dashboard/tree",
        params={"mode": "actuals", "level": "state", "year": "2024-25"},
    ).json()["value"]
    assert before == after == pytest.approx(750000.0)

"""API-level tests for the VIC BPO SOCE/Admin endpoints (Task 6 of the
VIC SOCE/Admin milestone). Uses a synthetic fixture database - never
the real data/facts.db.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from schema_migrate import migrate  # noqa: E402


def _seed(db: Path) -> None:
    conn = sqlite3.connect(str(db))

    vic_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('vic_budget_portfolio_outcomes_2024_25', 'Test', 'Test VIC BPO', 'VIC', 'state', 'handoff_actuals_state')
        """
    ).lastrowid
    income_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('vic_budget_portfolio_outcomes_2024_25|node|vic_bpo_admin_income', 'category', 'VIC BPO administered income', 'VIC', 'state', ?)
        """,
        (vic_doc,),
    ).lastrowid
    opening_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('vic_budget_portfolio_outcomes_2024_25|node|vic_bpo_net_assets_opening', 'category', 'VIC BPO net assets, opening balance (stock)', 'VIC', 'state', ?)
        """,
        (vic_doc,),
    ).lastrowid

    for estimate_status, amount in [("actual", 82428000000.0), ("budget", 95706000000.0)]:
        fact_id = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_start, period_end, period_granularity,
                measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
                source_document_id, source_locator_json, retrieved_at
            ) VALUES (?, '2024-25', '2024-07-01', '2025-06-30', 'financial_year', 'vic_bpo_admin_income', 'accrual', ?, ?, 'AUD', 'AUD', ?, '{"locator": "test-admin"}', datetime('now'))
            """,
            (
                f"vic_budget_portfolio_outcomes_2024_25|2024-25|vic_bpo_admin_income|accrual|{estimate_status}|VIC",
                estimate_status, amount, vic_doc,
            ),
        ).lastrowid
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (fact_id, income_node)
        )

    opening_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_start, period_end, period_granularity,
            measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_locator_json, retrieved_at
        ) VALUES (
            'vic_budget_portfolio_outcomes_2024_25|2024-25|vic_bpo_net_assets_opening|accrual|actual|VIC',
            '2024-25', NULL, '2025-06-30', 'financial_year', 'vic_bpo_net_assets_opening', 'accrual', 'actual', 76000000.0, 'AUD', 'AUD',
            ?, '{"locator": "test-soce"}', datetime('now')
        )
        """,
        (vic_doc,),
    ).lastrowid
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (opening_fact, opening_node)
    )

    # A real annual GFS actual expense fact, to prove this family never
    # contaminates it.
    annual_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('test_annual_gfs_bpo_soce_admin', 'Test', 'Test annual GFS', 'VIC', 'state', 'test')
        """
    ).lastrowid
    annual_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('test|node|Education-soce-admin', 'category', 'Education', 'VIC', 'state', ?)
        """,
        (annual_doc,),
    ).lastrowid
    annual_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type, accounting_basis,
            estimate_status, amount_aud, unit, currency, source_document_id,
            source_locator_json, retrieved_at
        ) VALUES (
            'test-soce-admin|education|2024-25', '2024-25', 'financial_year', 'gfs_expense', 'gfs',
            'actual', 750000.0, 'AUD', 'AUD', ?, '{"locator": "test-annual"}', datetime('now')
        )
        """,
        (annual_doc,),
    ).lastrowid
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (annual_fact, annual_node)
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


def test_measures_lists_all_9(client: TestClient):
    r = client.get("/v2/vic-bpo-soce-admin/measures")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 9
    types = {m["measure_type"] for m in body}
    assert "vic_bpo_admin_income" in types
    assert "vic_bpo_net_assets_opening" in types
    assert "vic_bpo_owner_transactions" in types


def test_series_returns_both_estimate_statuses(client: TestClient):
    r = client.get("/v2/vic-bpo-soce-admin/series", params={"measure_type": "vic_bpo_admin_income"})
    assert r.status_code == 200
    body = r.json()
    assert body["flow_or_stock"] == "flow"
    statuses = {f["estimate_status"] for f in body["facts"]}
    assert statuses == {"actual", "budget"}
    fys = {f["financial_year"] for f in body["facts"]}
    assert fys == {"2024-25"}


def test_series_unknown_measure_type_400s(client: TestClient):
    r = client.get("/v2/vic-bpo-soce-admin/series", params={"measure_type": "not_a_real_measure"})
    assert r.status_code == 400


def test_stock_fact_has_no_period_start_in_db_but_period_end_present(client: TestClient):
    r = client.get("/v2/vic-bpo-soce-admin/series", params={"measure_type": "vic_bpo_net_assets_opening"})
    facts = r.json()["facts"]
    assert len(facts) == 1
    assert facts[0]["period_end"] == "2025-06-30"
    assert facts[0]["flow_or_stock"] == "stock"


def test_citation_present_on_every_fact(client: TestClient):
    r = client.get("/v2/vic-bpo-soce-admin/series", params={"measure_type": "vic_bpo_admin_income"})
    for f in r.json()["facts"]:
        assert f["citation"]["locator"]


def test_existing_vic_bpo_endpoint_unaffected(client: TestClient):
    """The already-shipped vic_bpo.py router must still work exactly as
    before - no new measure appears there, and it doesn't error out
    just because the sibling router/semantics file now also exists."""
    r = client.get("/v2/vic-bpo/measures")
    assert r.status_code == 200
    types = {m["measure_type"] for m in r.json()}
    assert "vic_bpo_admin_income" not in types
    assert "vic_bpo_net_assets_opening" not in types


def test_annual_dashboard_total_unaffected_by_vic_bpo_soce_admin_facts(client: TestClient):
    """Proves the mission's core constraint: an annual dashboard query's
    total is identical whether or not vic_bpo_admin_*/vic_bpo_net_
    assets_opening/vic_bpo_owner_transactions facts exist in the same
    database - they are structurally invisible to /v2/dashboard/* since
    none of their compatibility_groups is registered under any
    mode_to_family mapping."""
    r = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "state", "year": "2024-25"})
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == pytest.approx(750000.0)

    import backend.facts_db as facts_db_mod

    conn = sqlite3.connect(str(facts_db_mod.FACTS_DB_FILE))
    conn.execute("DELETE FROM facts WHERE measure_type LIKE 'vic_bpo_admin_%' OR measure_type IN ('vic_bpo_net_assets_opening', 'vic_bpo_owner_transactions')")
    conn.commit()
    conn.close()

    r2 = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "state", "year": "2024-25"})
    assert r2.json()["value"] == body["value"]

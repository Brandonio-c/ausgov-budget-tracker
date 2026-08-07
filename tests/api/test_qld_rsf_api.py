"""API-level tests for the QLD Report on State Finances endpoints
(Task 8 of the QLD PDF milestone). Uses a synthetic fixture database -
never the real data/facts.db.
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

    qld_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('qld_report_on_state_finances_actuals', 'Test', 'Test QLD RSF', 'QLD', 'state', 'handoff_actuals_state')
        """
    ).lastrowid
    revenue_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('qld_report_on_state_finances_actuals|node|qld_rsf_revenue', 'category', 'QLD RSF general government revenue', 'QLD', 'state', ?)
        """,
        (qld_doc,),
    ).lastrowid
    fiscal_balance_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('qld_report_on_state_finances_actuals|node|qld_rsf_fiscal_balance', 'category', 'QLD RSF fiscal balance', 'QLD', 'state', ?)
        """,
        (qld_doc,),
    ).lastrowid

    for fy, estimate_status, amount in [
        ("2018-19", "estimated_actual", 60068000000.0),
        ("2018-19", "actual", 59834000000.0),
        ("2019-20", "estimated_actual", 57719000000.0),
        ("2019-20", "actual", 57764000000.0),
    ]:
        fact_id = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_start, period_end, period_granularity,
                measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
                source_document_id, source_locator_json, retrieved_at
            ) VALUES (?, ?, ?, ?, 'financial_year', 'qld_rsf_revenue', 'gfs', ?, ?, 'AUD', 'AUD', ?, '{"locator": "test-qld-rsf"}', datetime('now'))
            """,
            (
                f"qld_report_on_state_finances_actuals|{fy}|qld_rsf_revenue|gfs|{estimate_status}|QLD",
                fy, f"{fy[:4]}-07-01", f"20{fy[-2:]}-06-30", estimate_status, amount, qld_doc,
            ),
        ).lastrowid
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (fact_id, revenue_node)
        )

    balance_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_start, period_end, period_granularity,
            measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_locator_json, retrieved_at
        ) VALUES (
            'qld_report_on_state_finances_actuals|2018-19|qld_rsf_fiscal_balance|gfs|actual|QLD',
            '2018-19', '2018-07-01', '2019-06-30', 'financial_year', 'qld_rsf_fiscal_balance', 'gfs', 'actual', -2191000000.0, 'AUD', 'AUD',
            ?, '{"locator": "test-qld-rsf-balance"}', datetime('now')
        )
        """,
        (qld_doc,),
    ).lastrowid
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (balance_fact, fiscal_balance_node)
    )

    # A real annual GFS actual expense fact, to prove QLD RSF never
    # contaminates it.
    annual_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('test_annual_gfs_qld_rsf', 'Test', 'Test annual GFS', 'QLD', 'state', 'test')
        """
    ).lastrowid
    annual_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('test|node|Education-qld-rsf', 'category', 'Education', 'QLD', 'state', ?)
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
            'test-qld-rsf|education|2024-25', '2024-25', 'financial_year', 'gfs_expense', 'gfs',
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


def test_measures_lists_all_14(client: TestClient):
    r = client.get("/v2/qld-rsf/measures")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 14
    types = {m["measure_type"] for m in body}
    assert "qld_rsf_revenue" in types
    assert "qld_rsf_fiscal_balance" in types


def test_series_returns_both_vintages(client: TestClient):
    r = client.get("/v2/qld-rsf/series", params={"measure_type": "qld_rsf_revenue"})
    assert r.status_code == 200
    body = r.json()
    assert body["flow_or_stock"] == "flow"
    statuses = {f["estimate_status"] for f in body["facts"]}
    assert statuses == {"estimated_actual", "actual"}
    fys = {f["financial_year"] for f in body["facts"]}
    assert fys == {"2018-19", "2019-20"}


def test_series_ordered_by_financial_year(client: TestClient):
    r = client.get("/v2/qld-rsf/series", params={"measure_type": "qld_rsf_revenue"})
    fys = [f["financial_year"] for f in r.json()["facts"]]
    assert fys == sorted(fys)


def test_series_unknown_measure_type_400s(client: TestClient):
    r = client.get("/v2/qld-rsf/series", params={"measure_type": "not_a_real_measure"})
    assert r.status_code == 400


def test_balance_measure_negative_value_preserved(client: TestClient):
    r = client.get("/v2/qld-rsf/series", params={"measure_type": "qld_rsf_fiscal_balance"})
    facts = r.json()["facts"]
    assert len(facts) == 1
    assert facts[0]["amount_aud"] == pytest.approx(-2191000000.0)
    assert facts[0]["flow_or_stock"] == "balance"


def test_citation_present_on_every_fact(client: TestClient):
    r = client.get("/v2/qld-rsf/series", params={"measure_type": "qld_rsf_revenue"})
    for f in r.json()["facts"]:
        assert f["citation"]["locator"]


def test_no_budget_estimate_status_ever_appears(client: TestClient):
    """QLD's vintage is estimated_actual/actual, never budget - a real
    semantic distinction from TAS's TAFR adapter."""
    r = client.get("/v2/qld-rsf/series", params={"measure_type": "qld_rsf_revenue"})
    statuses = {f["estimate_status"] for f in r.json()["facts"]}
    assert "budget" not in statuses


def test_existing_tas_ggs_endpoint_unaffected(client: TestClient):
    """The already-shipped tas_ggs.py router must still work exactly as
    before - no QLD measure appears there, and it doesn't error out
    just because the sibling qld_rsf router now also exists."""
    r = client.get("/v2/tas-ggs/measures")
    assert r.status_code == 200
    types = {m["measure_type"] for m in r.json()}
    assert "qld_rsf_revenue" not in types


def test_annual_dashboard_total_unaffected_by_qld_rsf_facts(client: TestClient):
    """Proves the mission's core constraint: an annual dashboard query's
    total is identical whether or not qld_rsf_* facts exist in the same
    database - they are structurally invisible to /v2/dashboard/* since
    no qld_rsf_* compatibility_group is registered under any
    mode_to_family mapping."""
    r = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "state", "year": "2024-25"})
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == pytest.approx(750000.0)

    import backend.facts_db as facts_db_mod

    conn = sqlite3.connect(str(facts_db_mod.FACTS_DB_FILE))
    conn.execute("DELETE FROM facts WHERE measure_type LIKE 'qld_rsf_%'")
    conn.commit()
    conn.close()

    r2 = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "state", "year": "2024-25"})
    assert r2.json()["value"] == body["value"]

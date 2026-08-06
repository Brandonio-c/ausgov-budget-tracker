"""API-level tests for the TAS GGS Key Fiscal Measures endpoints (Task
8 of the QLD/TAS milestone). Uses a synthetic fixture database - never
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

    tas_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('tas_treasurer_annual_financial_reports', 'Test', 'Test TAS GGS', 'TAS', 'state', 'handoff_actuals_state')
        """
    ).lastrowid
    revenue_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('tas_treasurer_annual_financial_reports|node|tas_ggs_revenue', 'category', 'TAS GGS revenue from transactions', 'TAS', 'state', ?)
        """,
        (tas_doc,),
    ).lastrowid
    net_debt_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('tas_treasurer_annual_financial_reports|node|tas_ggs_net_debt', 'category', 'TAS GGS net debt (stock)', 'TAS', 'state', ?)
        """,
        (tas_doc,),
    ).lastrowid

    for fy, estimate_status, amount in [
        ("2013-14", "actual", 4910000000.0),
        ("2025-26", "revised_estimate", 9678700000.0),
        ("2026-27", "forward_estimate", 9772700000.0),
    ]:
        fact_id = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_start, period_end, period_granularity,
                measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
                source_document_id, source_locator_json, retrieved_at
            ) VALUES (?, ?, ?, ?, 'financial_year', 'tas_ggs_revenue', 'accrual', ?, ?, 'AUD', 'AUD', ?, '{"locator": "test-tas-ggs"}', datetime('now'))
            """,
            (
                f"tas_treasurer_annual_financial_reports|{fy}|tas_ggs_revenue|accrual|{estimate_status}|TAS",
                fy, f"{fy[:4]}-07-01", f"20{fy[-2:]}-06-30", estimate_status, amount, tas_doc,
            ),
        ).lastrowid
        conn.execute(
            "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (fact_id, revenue_node)
        )

    stock_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_start, period_end, period_granularity,
            measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_locator_json, retrieved_at
        ) VALUES (
            'tas_treasurer_annual_financial_reports|2016-17|tas_ggs_net_debt|accrual|actual|TAS',
            '2016-17', NULL, '2017-06-30', 'financial_year', 'tas_ggs_net_debt', 'accrual', 'actual', 1273400000.0, 'AUD', 'AUD',
            ?, '{"locator": "test-tas-ggs-stock"}', datetime('now')
        )
        """,
        (tas_doc,),
    ).lastrowid
    conn.execute(
        "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (stock_fact, net_debt_node)
    )

    # A real annual GFS actual expense fact, to prove TAS GGS never
    # contaminates it.
    annual_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('test_annual_gfs_tas_ggs', 'Test', 'Test annual GFS', 'TAS', 'state', 'test')
        """
    ).lastrowid
    annual_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('test|node|Education-tas-ggs', 'category', 'Education', 'TAS', 'state', ?)
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
            'test-tas-ggs|education|2024-25', '2024-25', 'financial_year', 'gfs_expense', 'gfs',
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


def test_measures_lists_all_10(client: TestClient):
    r = client.get("/v2/tas-ggs/measures")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 10
    types = {m["measure_type"] for m in body}
    assert "tas_ggs_revenue" in types
    assert "tas_ggs_net_debt" in types


def test_series_returns_multiple_years_and_vintages(client: TestClient):
    r = client.get("/v2/tas-ggs/series", params={"measure_type": "tas_ggs_revenue"})
    assert r.status_code == 200
    body = r.json()
    assert body["flow_or_stock"] == "flow"
    statuses = {f["estimate_status"] for f in body["facts"]}
    assert statuses == {"actual", "revised_estimate", "forward_estimate"}
    fys = {f["financial_year"] for f in body["facts"]}
    assert fys == {"2013-14", "2025-26", "2026-27"}


def test_series_ordered_by_financial_year(client: TestClient):
    r = client.get("/v2/tas-ggs/series", params={"measure_type": "tas_ggs_revenue"})
    fys = [f["financial_year"] for f in r.json()["facts"]]
    assert fys == sorted(fys)


def test_series_unknown_measure_type_400s(client: TestClient):
    r = client.get("/v2/tas-ggs/series", params={"measure_type": "not_a_real_measure"})
    assert r.status_code == 400


def test_stock_fact_has_no_period_start_in_db_but_period_end_present(client: TestClient):
    r = client.get("/v2/tas-ggs/series", params={"measure_type": "tas_ggs_net_debt"})
    facts = r.json()["facts"]
    assert len(facts) == 1
    assert facts[0]["period_end"] == "2017-06-30"
    assert facts[0]["flow_or_stock"] == "stock"
    assert facts[0]["amount_aud"] == pytest.approx(1273400000.0)


def test_citation_present_on_every_fact(client: TestClient):
    r = client.get("/v2/tas-ggs/series", params={"measure_type": "tas_ggs_revenue"})
    for f in r.json()["facts"]:
        assert f["citation"]["locator"]


def test_existing_vic_bpo_endpoint_unaffected(client: TestClient):
    """The already-shipped vic_bpo.py router must still work exactly as
    before - no TAS measure appears there, and it doesn't error out
    just because the sibling tas_ggs router now also exists."""
    r = client.get("/v2/vic-bpo/measures")
    assert r.status_code == 200
    types = {m["measure_type"] for m in r.json()}
    assert "tas_ggs_revenue" not in types


def test_annual_dashboard_total_unaffected_by_tas_ggs_facts(client: TestClient):
    """Proves the mission's core constraint: an annual dashboard query's
    total is identical whether or not tas_ggs_* facts exist in the same
    database - they are structurally invisible to /v2/dashboard/* since
    no tas_ggs_* compatibility_group is registered under any
    mode_to_family mapping."""
    r = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "state", "year": "2024-25"})
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == pytest.approx(750000.0)

    import backend.facts_db as facts_db_mod

    conn = sqlite3.connect(str(facts_db_mod.FACTS_DB_FILE))
    conn.execute("DELETE FROM facts WHERE measure_type LIKE 'tas_ggs_%'")
    conn.commit()
    conn.close()

    r2 = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "state", "year": "2024-25"})
    assert r2.json()["value"] == body["value"]

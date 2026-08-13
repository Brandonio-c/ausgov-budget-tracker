"""API-level tests for the dedicated MFS endpoints (Task 10 of the
MFS-aggregates milestone). Uses a synthetic fixture database (schema_migrate
against a tmp_path db) - never the real data/facts.db.
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

    mfs_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('federal_mfs_aggregates', 'Test', 'Test MFS', 'Commonwealth', 'federal', 'mfs_aggregates')
        """
    ).lastrowid
    rev_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('federal_mfs_aggregates|node|mfs_ytd_revenue', 'category', 'MFS YTD revenue', 'Commonwealth', 'federal', ?)
        """,
        (mfs_doc,),
    ).lastrowid
    assets_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('federal_mfs_aggregates|node|mfs_stock_total_assets', 'category', 'MFS total assets (stock)', 'Commonwealth', 'federal', ?)
        """,
        (mfs_doc,),
    ).lastrowid

    for month, fy, amount in [("July", "2023-24", 100.0), ("August", "2023-24", 210.0), ("July", "2024-25", 120.0)]:
        fact_id = conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_start, period_end, period_granularity,
                measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
                source_document_id, source_locator_json, retrieved_at
            ) VALUES (?, ?, ?, ?, 'month', 'mfs_ytd_revenue', 'accrual', 'actual', ?, 'AUD', 'AUD', ?, '{"locator": "test"}', datetime('now'))
            """,
            (
                f"federal_mfs_aggregates|{fy}|{month}|mfs_ytd_revenue|accrual|actual|Commonwealth",
                fy, f"{fy[:4]}-07-01", "2023-08-31" if month == "August" else f"{fy[:4]}-07-31", amount, mfs_doc,
            ),
        ).lastrowid
        conn.execute("INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (fact_id, rev_node))

    stock_fact = conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_start, period_end, period_granularity,
            measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_locator_json, retrieved_at
        ) VALUES (
            'federal_mfs_aggregates|2023-24|July|mfs_stock_total_assets|accrual|actual|Commonwealth',
            '2023-24', NULL, '2023-07-31', 'month', 'mfs_stock_total_assets', 'accrual', 'actual', 500.0, 'AUD', 'AUD',
            ?, '{"locator": "test-stock"}', datetime('now')
        )
        """,
        (mfs_doc,),
    ).lastrowid
    conn.execute("INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (stock_fact, assets_node))

    # A real annual GFS actual expense fact, to prove MFS never contaminates it.
    annual_doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES ('test_annual_gfs', 'Test', 'Test annual GFS', 'Commonwealth', 'federal', 'test')
        """
    ).lastrowid
    annual_node = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES ('test|node|Defence', 'category', 'Defence', 'Commonwealth', 'federal', ?)
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
            'test|defence|2023-24', '2023-24', 'financial_year', 'gfs_expense', 'gfs',
            'actual', 1000000.0, 'AUD', 'AUD', ?, '{"locator": "test-annual"}', datetime('now')
        )
        """,
        (annual_doc,),
    ).lastrowid
    conn.execute("INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (annual_fact, annual_node))

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


def test_measures_lists_all_35(client: TestClient):
    """15 Aggregates measures (unchanged) + 20 Note 3 measures added in
    item 7.1's second MFS sibling workbook load - this endpoint is driven
    entirely by config/measure-semantics/mfs.yaml, so no backend code
    change was needed for the count to grow from 15 to 35."""
    r = client.get("/v2/mfs/measures")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 35
    types = {m["measure_type"] for m in body}
    assert "mfs_ytd_revenue" in types
    assert "mfs_stock_total_assets" in types
    assert "mfs_note3_defence" in types
    assert "mfs_note3_total_expenses" in types


def test_series_filters_by_financial_year(client: TestClient):
    r = client.get("/v2/mfs/series", params={"measure_type": "mfs_ytd_revenue", "financial_year": "2023-24"})
    assert r.status_code == 200
    body = r.json()
    assert body["flow_or_stock"] == "flow"
    assert {f["financial_year"] for f in body["facts"]} == {"2023-24"}
    assert {f["reporting_month"] for f in body["facts"]} == {"July", "August"}


def test_series_filters_by_reporting_month(client: TestClient):
    r = client.get(
        "/v2/mfs/series",
        params={"measure_type": "mfs_ytd_revenue", "financial_year": "2023-24", "reporting_month": "August"},
    )
    body = r.json()
    assert len(body["facts"]) == 1
    assert body["facts"][0]["amount_aud"] == 210.0
    assert body["facts"][0]["elapsed_months"] == 2


def test_series_unknown_measure_type_400s(client: TestClient):
    r = client.get("/v2/mfs/series", params={"measure_type": "not_a_real_measure"})
    assert r.status_code == 400


def test_years_returns_distinct_years(client: TestClient):
    r = client.get("/v2/mfs/years", params={"measure_type": "mfs_ytd_revenue"})
    assert r.status_code == 200
    assert set(r.json()) == {"2023-24", "2024-25"}


def test_compare_valid_flow_pair_returns_parallel_series(client: TestClient):
    r = client.get("/v2/mfs/compare", params={"measure_types": "mfs_ytd_revenue", "financial_year": "2023-24"})
    assert r.status_code == 200
    body = r.json()
    assert body["warning"] is None
    assert len(body["series"]) == 1


def test_compare_rejects_stock_and_flow_mix(client: TestClient):
    r = client.get(
        "/v2/mfs/compare",
        params={"measure_types": "mfs_stock_total_assets,mfs_ytd_revenue"},
    )
    assert r.status_code == 422
    assert "stock" in r.json()["detail"].lower()


def test_compare_rejects_unknown_measure(client: TestClient):
    r = client.get("/v2/mfs/compare", params={"measure_types": "mfs_ytd_revenue,not_real"})
    assert r.status_code == 400


def test_compare_rejects_too_many_measures(client: TestClient):
    many = ",".join("mfs_ytd_revenue" for _ in range(7))
    r = client.get("/v2/mfs/compare", params={"measure_types": many})
    assert r.status_code == 400


def test_stock_fact_has_no_period_start(client: TestClient):
    r = client.get("/v2/mfs/series", params={"measure_type": "mfs_stock_total_assets"})
    facts = r.json()["facts"]
    assert len(facts) == 1
    assert facts[0]["period_start"] is None
    assert facts[0]["period_end"] == "2023-07-31"


def test_citation_present_on_every_fact(client: TestClient):
    r = client.get("/v2/mfs/series", params={"measure_type": "mfs_ytd_revenue"})
    for f in r.json()["facts"]:
        assert f["citation"]["locator"]


# ---- config path resolution: repo checkout vs Docker container ----------
#
# Found in Task 12 (production verification): the container's `COPY .
# /app/backend` (context: ./src/backend) makes this file's on-disk depth
# one level shallower than the repo checkout
# (.../ausgov-budget-tracker/src/backend/routers/v2/mfs.py locally vs
# /app/backend/routers/v2/mfs.py in the container) - a single fixed
# `parents[4]` resolved to the wrong path in the container
# (FileNotFoundError: /config/measure-semantics/mfs.yaml, missing /app),
# which only surfaced as a real 500 once actually deployed. Fixed to
# mirror compatibility.py's _default_view_families_path() multi-candidate
# pattern exactly.


def test_semantics_path_resolves_in_repo_checkout():
    import backend.routers.v2.mfs as mfs_module

    assert mfs_module.SEMANTICS_PATH.is_file()
    assert mfs_module.SEMANTICS_PATH.name == "mfs.yaml"


def test_semantics_path_candidates_cover_both_layouts(monkeypatch, tmp_path):
    import backend.routers.v2.mfs as mfs_module

    # Simulate the container layout: /app/backend/routers/v2 (one level
    # shallower than the repo checkout's src/backend/routers/v2).
    fake_app = tmp_path / "app"
    fake_here = fake_app / "backend" / "routers" / "v2"
    fake_here.mkdir(parents=True)
    (fake_app / "config" / "measure-semantics").mkdir(parents=True)
    (fake_app / "config" / "measure-semantics" / "mfs.yaml").write_text("measures: {}\n")

    monkeypatch.setattr(mfs_module, "_HERE", fake_here)
    resolved = mfs_module._default_semantics_path()
    assert resolved == fake_app / "config" / "measure-semantics" / "mfs.yaml"
    assert resolved.is_file()


# ---- the core non-negotiable: annual totals unchanged -------------------


def test_annual_dashboard_total_unaffected_by_mfs_facts(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Directly proves the mission's core constraint: an annual dashboard
    query's total is identical whether or not MFS facts exist in the same
    database - MFS facts are structurally invisible to /v2/dashboard/*
    since no mfs_* compatibility_group is registered under any
    mode_to_family mapping."""
    r = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "federal", "year": "2023-24"})
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == pytest.approx(1_000_000.0)
    assert body["warning"] is None

    # Remove every MFS fact and confirm the total is byte-identical - proves
    # the MFS rows were never contributing to it in the first place, not
    # just coincidentally absent from this particular query path.
    import backend.facts_db as facts_db_mod

    conn = sqlite3.connect(str(facts_db_mod.FACTS_DB_FILE))
    conn.execute("DELETE FROM facts WHERE measure_type LIKE 'mfs_%'")
    conn.commit()
    conn.close()

    r2 = client.get("/v2/dashboard/tree", params={"mode": "actuals", "level": "federal", "year": "2023-24"})
    assert r2.json()["value"] == body["value"]

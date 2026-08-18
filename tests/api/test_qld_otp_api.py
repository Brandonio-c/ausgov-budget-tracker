"""API-level tests for the dedicated QLD on-time-payments endpoints (item
7.5's explorer surface). Uses a synthetic fixture database (schema_migrate
against a tmp_path db, which already applies migration 022's measure_definitions
rows) - never the real data/facts.db.
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

SOURCE_KEY = "qld_on_time_payment_reports"


def _seed(db: Path) -> None:
    conn = sqlite3.connect(str(db))

    doc = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, 'Test', 'Test QLD OTP', 'QLD', 'state', 'qld_on_time_payments')
        """,
        (SOURCE_KEY,),
    ).lastrowid

    agency_a = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES (?, 'category', 'dpc', 'QLD', 'state', ?)
        """,
        (f"{SOURCE_KEY}|agency|dpc", doc),
    ).lastrowid
    agency_b = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES (?, 'category', 'dcyjma', 'QLD', 'state', ?)
        """,
        (f"{SOURCE_KEY}|agency|dcyjma", doc),
    ).lastrowid

    # A count measure (root_total_allowed=1) - dpc: 5, dcyjma: 3, one Q1 FY2020-21 fact each.
    for agency_node, agency_code, value in [(agency_a, "dpc", 5), (agency_b, "dcyjma", 3)]:
        conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_start, period_end, period_granularity,
                measure_type, accounting_basis, estimate_status, quantity, unit, currency,
                source_document_id, source_locator_json, retrieved_at
            ) VALUES (?, '2020-21', '2020-07-01', '2020-09-30', 'quarter', 'qld_otp_eligible_claims',
                      'count', 'actual', ?, 'count', 'AUD', ?, ?, datetime('now'))
            """,
            (
                f"{SOURCE_KEY}|2020-21|Q1|{agency_code}|qld_otp_eligible_claims|actual", value, doc,
                f'{{"locator": "source_id:{SOURCE_KEY} | file:{agency_code}.csv | row:x", "cached_copy_path": "x.csv"}}',
            ),
        )
        fact_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (fact_id, agency_node))

    # A percentage measure (root_total_allowed=0) - must never be summed.
    for agency_node, agency_code, value in [(agency_a, "dpc", 12.5), (agency_b, "dcyjma", 7.0)]:
        conn.execute(
            """
            INSERT INTO facts (
                fact_key, financial_year, period_start, period_end, period_granularity,
                measure_type, accounting_basis, estimate_status, quantity, unit, currency,
                source_document_id, source_locator_json, retrieved_at
            ) VALUES (?, '2020-21', '2020-07-01', '2020-09-30', 'quarter', 'qld_otp_pct_late_smallbus',
                      'not_applicable', 'actual', ?, 'percent', 'AUD', ?, ?, datetime('now'))
            """,
            (
                f"{SOURCE_KEY}|2020-21|Q1|{agency_code}|qld_otp_pct_late_smallbus|actual", value, doc,
                f'{{"locator": "source_id:{SOURCE_KEY} | file:{agency_code}.csv | row:y", "cached_copy_path": "y.csv"}}',
            ),
        )
        fact_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')", (fact_id, agency_node))

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


def test_measures_lists_all_8(client: TestClient) -> None:
    r = client.get("/v2/qld-otp/measures")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 8
    types = {m["measure_type"] for m in body}
    assert "qld_otp_eligible_claims" in types
    assert "qld_otp_mean_days_paid_late" in types
    eligible = next(m for m in body if m["measure_type"] == "qld_otp_eligible_claims")
    assert eligible["unit"] == "count"


def test_years_reflects_only_real_published_quarters(client: TestClient) -> None:
    r = client.get("/v2/qld-otp/years", params={"measure_type": "qld_otp_eligible_claims"})
    assert r.status_code == 200
    body = r.json()
    assert body == [{"financial_year": "2020-21", "quarter": 1}]


def test_breakdown_returns_both_agencies_sorted_by_value_descending(client: TestClient) -> None:
    r = client.get(
        "/v2/qld-otp/breakdown",
        params={"measure_type": "qld_otp_eligible_claims", "financial_year": "2020-21", "quarter": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_agencies"] == 2
    assert [a["agency_code"] for a in body["agencies"]] == ["dpc", "dcyjma"]
    assert body["agencies"][0]["value"] == 5
    assert body["agencies"][1]["value"] == 3


def test_breakdown_reports_a_meaningful_total_for_a_count_measure(client: TestClient) -> None:
    r = client.get(
        "/v2/qld-otp/breakdown",
        params={"measure_type": "qld_otp_eligible_claims", "financial_year": "2020-21", "quarter": 1},
    )
    body = r.json()
    assert body["total_value"] == 8
    assert body["total_value_note"] is None


def test_breakdown_never_sums_a_percentage_measure_across_agencies(client: TestClient) -> None:
    """qld_otp_pct_late_smallbus has root_total_allowed=0 - summing a
    per-agency percentage across agencies is not a meaningful quantity
    and must never be reported as a total."""
    r = client.get(
        "/v2/qld-otp/breakdown",
        params={"measure_type": "qld_otp_pct_late_smallbus", "financial_year": "2020-21", "quarter": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_value"] is None
    assert body["total_value_note"] is not None
    assert {a["agency_code"] for a in body["agencies"]} == {"dpc", "dcyjma"}


def test_breakdown_citation_includes_agency_specific_locator(client: TestClient) -> None:
    r = client.get(
        "/v2/qld-otp/breakdown",
        params={"measure_type": "qld_otp_eligible_claims", "financial_year": "2020-21", "quarter": 1},
    )
    body = r.json()
    dpc = next(a for a in body["agencies"] if a["agency_code"] == "dpc")
    assert "dpc.csv" in dpc["citation"]["locator"]


def test_unknown_measure_type_returns_400(client: TestClient) -> None:
    r = client.get("/v2/qld-otp/measures", params={})
    assert r.status_code == 200  # sanity: measures itself never takes a measure_type
    r2 = client.get("/v2/qld-otp/years", params={"measure_type": "not_a_real_measure"})
    assert r2.status_code == 400


def test_breakdown_empty_quarter_returns_zero_agencies_not_an_error(client: TestClient) -> None:
    r = client.get(
        "/v2/qld-otp/breakdown",
        params={"measure_type": "qld_otp_eligible_claims", "financial_year": "2020-21", "quarter": 4},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_agencies"] == 0
    assert body["agencies"] == []

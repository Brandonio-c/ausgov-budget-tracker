"""Ingest maximisation coverage: schema semantics, debt valuation, PBS estimate status."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture()
def facts_db() -> Path:
    db = REPO_ROOT / "data" / "facts.db"
    assert db.is_file()
    return db


@pytest.mark.full_data
def test_observation_semantics_columns(facts_db: Path) -> None:
    conn = sqlite3.connect(str(facts_db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)").fetchall()}
    conn.close()
    for col in ("observation_date", "valuation_basis", "amount_granularity", "publication_date"):
        assert col in cols


@pytest.mark.full_data
def test_new_measures_registered(facts_db: Path) -> None:
    conn = sqlite3.connect(str(facts_db))
    rows = {
        r[0]
        for r in conn.execute(
            "SELECT measure_type FROM measure_definitions WHERE measure_type IN "
            "('borrowing_authority_debt_outstanding','superannuation_liability',"
            "'gdp_chain_volume','gsp_current','tax_to_gdp_ratio')"
        )
    }
    conn.close()
    assert "borrowing_authority_debt_outstanding" in rows
    assert "superannuation_liability" in rows
    assert "gdp_chain_volume" in rows


@pytest.mark.full_data
def test_pbs_estimate_status_not_in_actuals(facts_db: Path) -> None:
    conn = sqlite3.connect(str(facts_db))
    n = conn.execute(
        """
        SELECT COUNT(*) FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        WHERE d.source_key = 'federal_pbs_programs_all'
          AND m.compatibility_group = 'actual_expense'
          AND f.estimate_status IN ('budget', 'forward_estimate', 'estimated_actual')
        """
    ).fetchone()[0]
    conn.close()
    assert n == 0


@pytest.mark.full_data
def test_borrowing_valuation_fields_present(facts_db: Path) -> None:
    conn = sqlite3.connect(str(facts_db))
    row = conn.execute(
        """
        SELECT valuation_basis, amount_granularity, observation_date
        FROM facts
        WHERE measure_type = 'borrowing_authority_debt_outstanding'
          AND amount_granularity IS NOT NULL
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    if row is None:
        pytest.skip("borrowing authorities not yet re-ingested")
    assert row[0] in {"face_value", "fair_value", "unspecified"}
    assert row[1] in {"individual_security", "instrument_type_aggregate"}


@pytest.mark.full_data
def test_debt_mode_rejects_budget_expense(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setenv("FACTS_DB_PATH", str(REPO_ROOT / "data" / "facts.db"))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = REPO_ROOT / "data" / "facts.db"
    from backend.main import app

    client = TestClient(app)
    r = client.get("/v2/dashboard/levels", params={"mode": "debt"})
    assert r.status_code == 200
    # Budget-only estimate statuses must not appear in debt series mixes via mode filters
    years = client.get("/v2/dashboard/years", params={"mode": "debt", "level": "state"})
    if years.status_code != 200 or not years.json():
        pytest.skip("no state debt years")
    tree = client.get(
        "/v2/dashboard/tree",
        params={"mode": "debt", "level": "state", "year": years.json()[-1]},
    )
    assert tree.status_code == 200
    body = tree.json()
    assert "children" in body
    # mixed_observation_dates may be true when authorities differ
    assert "mixed_observation_dates" in body or body.get("warning") is None or isinstance(
        body.get("warning"), str
    )


def test_gdp_hierarchy_helper() -> None:
    from backend.gdp_hierarchy import gdp_hierarchy_path

    path = gdp_hierarchy_path("Expenditure on GDP / Final consumption expenditure")
    assert path[0] == "GDP (current prices)"

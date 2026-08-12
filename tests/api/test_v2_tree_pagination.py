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


SCOPE = {
    "compatibility_group": "gfs_revenue",
    "accounting_basis": "gfs",
    "estimate_status": "actual",
    "financial_year": "2024-25",
}


def _expected_totals() -> tuple[int, float]:
    conn = sqlite3.connect(REPO_ROOT / "data" / "facts.db")
    row = conn.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(f.amount_aud), 0)
        FROM facts f
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        WHERE m.compatibility_group = ?
          AND f.accounting_basis = ?
          AND f.estimate_status = ?
          AND f.financial_year = ?
          AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
        """,
        tuple(SCOPE.values()),
    ).fetchone()
    conn.close()
    assert row is not None
    return int(row[0]), float(row[1])


def test_flat_tree_reports_full_totals_independent_of_page_limit(
    client: TestClient,
) -> None:
    response = client.get("/v2/tree", params={**SCOPE, "limit": 5})
    assert response.status_code == 200
    body = response.json()
    expected_count, expected_value = _expected_totals()

    assert body["shape"] == "flat"
    assert len(body["children"]) == 5
    assert body["total_count"] == expected_count
    assert body["total_value"] == pytest.approx(expected_value)
    assert body["value"] == body["total_value"]  # backward-compatible truthful root
    assert body["value"] != pytest.approx(
        sum(child["value"] or 0 for child in body["children"])
    )
    assert body["next_cursor"]


def test_flat_tree_cursor_pages_every_accepted_fact_once(client: TestClient) -> None:
    expected_count, _ = _expected_totals()
    cursor = None
    ids: list[int] = []
    while True:
        params = {**SCOPE, "limit": 17}
        if cursor:
            params["cursor"] = cursor
        response = client.get("/v2/tree", params=params)
        assert response.status_code == 200
        body = response.json()
        ids.extend(int(child["id"]) for child in body["children"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert len(ids) == expected_count
    assert len(ids) == len(set(ids))


def test_flat_tree_rejects_invalid_cursor(client: TestClient) -> None:
    response = client.get("/v2/tree", params={**SCOPE, "cursor": "not-a-cursor"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid tree cursor"


# federal_pbs_programs_all shares this exact compatibility triple with several
# other sources (state budget statements, other PBS-derived extractors) -
# built for item 6.3's PBS explorer, which needs to show only PBS facts.
PBS_SCOPE = {
    "compatibility_group": "budget_expense",
    "accounting_basis": "accrual",
    "estimate_status": "budget",
    "financial_year": "2026-27",
}


def test_source_key_filter_narrows_a_shared_compatibility_triple(
    client: TestClient,
) -> None:
    unfiltered = client.get("/v2/tree", params={**PBS_SCOPE, "limit": 1}).json()
    filtered = client.get(
        "/v2/tree",
        params={**PBS_SCOPE, "source_key": "federal_pbs_programs_all", "limit": 1},
    ).json()

    # This compatibility triple genuinely is shared by more than one source
    # in the real database - otherwise this test would not exercise
    # anything different from the unfiltered case.
    assert filtered["total_count"] < unfiltered["total_count"]
    assert filtered["total_count"] > 0
    assert filtered["name"].startswith("federal_pbs_programs_all / ")

    conn = sqlite3.connect(REPO_ROOT / "data" / "facts.db")
    expected = conn.execute(
        """
        SELECT COUNT(*)
        FROM facts f
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE m.compatibility_group = ?
          AND f.accounting_basis = ?
          AND f.estimate_status = ?
          AND f.financial_year = ?
          AND d.source_key = 'federal_pbs_programs_all'
          AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
        """,
        tuple(PBS_SCOPE.values()),
    ).fetchone()
    conn.close()
    assert filtered["total_count"] == expected[0]


def test_source_key_omitted_preserves_existing_unfiltered_behaviour(
    client: TestClient,
) -> None:
    """Every caller that predates the source_key parameter must see
    identical results with it simply absent from the query string."""
    with_param_absent = client.get("/v2/tree", params={**SCOPE, "limit": 5}).json()
    with_param_none = client.get(
        "/v2/tree", params={**SCOPE, "source_key": "", "limit": 5}
    ).json()
    assert with_param_absent["total_count"] == with_param_none["total_count"]
    assert with_param_absent["children"] == with_param_none["children"]

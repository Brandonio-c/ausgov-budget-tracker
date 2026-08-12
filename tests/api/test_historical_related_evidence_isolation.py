"""Historical Statement 6/PBS evidence facts must never inflate an existing
dashboard mode's root total.

Regression for a defect found while implementing plan item 5.4: giving these
facts `measure_type: budget_estimate` (compatibility_group 'budget_expense')
made mode='budget' additively sum them on top of every already-loaded
budget-basis fact for the same year, since _fact_rows() has no per-source
de-duplication - it just sums everything sharing a compatibility_group. On a
disposable database copy this inflated the FY2022-23 federal_budget root
total from $1.63b to as much as $2.34b *thousand million* (i.e. ~$2.34
trillion, roughly 1,400x), because Statement 6 (function-level) and PBS
(program-level) both represent near-complete, overlapping views of the same
underlying commonwealth expenditure. See
ops/reports/historical-related-evidence-measures-20260811T180000Z.md.
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

NEW_MEASURE_TYPES = (
    "historical_bp1_statement6_expense",
    "historical_treasury_pbs_program_expense",
)
LIVE_MODE_COMPATIBILITY_GROUPS = {
    "actual_expense",
    "budget_expense",
    "gfs_liability",
    "gfs_revenue",
    "gdp",
}
NEW_SOURCE_KEYS = (
    "federal_budget_statement_6_2022_23_march",
    "federal_budget_statement_6_2022_23_october",
    "federal_budget_statement_6_2023_24",
    "federal_pbs_2022_23_march_treasury",
    "federal_pbs_2022_23_october_treasury",
    "federal_pbs_2023_24_treasury",
)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FACTS_DB_PATH", str(DB))
    import backend.facts_db as facts_db_mod

    facts_db_mod.FACTS_DB_FILE = DB
    from backend.main import app

    return TestClient(app)


@pytest.mark.parametrize("measure_type", NEW_MEASURE_TYPES)
def test_new_measure_types_cannot_anchor_any_root_total(measure_type: str) -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT compatibility_group, additive_across_nodes, root_total_allowed "
            "FROM measure_definitions WHERE measure_type = ?",
            (measure_type,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"{measure_type} is not registered"
    compatibility_group, additive_across_nodes, root_total_allowed = row
    assert compatibility_group not in LIVE_MODE_COMPATIBILITY_GROUPS
    assert additive_across_nodes == 0
    assert root_total_allowed == 0


def test_new_sources_carry_no_canonical_dataset_assignment() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        for source_key in NEW_SOURCE_KEYS:
            row = conn.execute(
                """
                SELECT COUNT(*), SUM(CASE WHEN f.canonical_dataset_id IS NOT NULL THEN 1 ELSE 0 END)
                FROM facts f
                JOIN source_documents d ON d.id = f.source_document_id
                WHERE d.source_key = ?
                """,
                (source_key,),
            ).fetchone()
            fact_count, canonical_count = row
            assert fact_count and fact_count > 0, f"{source_key} has no loaded facts"
            assert not canonical_count, f"{source_key} has canonical-dataset-assigned facts"
    finally:
        conn.close()


@pytest.mark.parametrize(
    "year,expected_root_total",
    # 2023-24 was intentionally updated (from 1_818_520_572_000.0) by item
    # 5.5b's federal_pbs_programs_all reload: 158 genuinely garbled labels
    # that this item's classifier precision fix (item 5.5) correctly
    # rejects were still live as of this test's original value, incorrectly
    # inflating the total - see ops/reports/pbs-corpus-reload-*.md. The
    # guard this test exists for (the isolated historical-evidence measures
    # cannot move the mode='budget' root total) still holds; only the
    # correct baseline itself changed.
    [("2022-23", 1_629_222_000.0), ("2023-24", 1_787_437_333_000.0)],
)
def test_federal_budget_root_total_unaffected_by_historical_evidence(
    client: TestClient, year: str, expected_root_total: float
) -> None:
    r = client.get(
        "/v2/dashboard/tree",
        params={"mode": "budget", "level": "federal", "year": year},
    )
    assert r.status_code == 200
    assert r.json()["value"] == pytest.approx(expected_root_total)

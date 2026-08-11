"""The repaired NDIA PBS facts (item 5.5) must never be summed additively
with the portfolio department's own "Program 3.2 - National Disability
Insurance Scheme" administered expense already loaded under
federal_pbs_programs_all - both represent overlapping views of the same
Commonwealth-to-NDIA transfer (~$34-38b for FY2024-25/2025-26, verified
directly against the live database). See
ops/reports/ndia-pbs-repair-20260811T225949Z.md.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB = REPO_ROOT / "data" / "facts.db"

MEASURE_TYPE = "federal_pbs_2026_27_ndia_expense"
LIVE_MODE_COMPATIBILITY_GROUPS = {
    "actual_expense",
    "budget_expense",
    "gfs_liability",
    "gfs_revenue",
    "gdp",
}


def test_ndia_measure_cannot_anchor_any_root_total() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT compatibility_group, additive_across_nodes, root_total_allowed "
            "FROM measure_definitions WHERE measure_type = ?",
            (MEASURE_TYPE,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"{MEASURE_TYPE} is not registered"
    compatibility_group, additive_across_nodes, root_total_allowed = row
    assert compatibility_group not in LIVE_MODE_COMPATIBILITY_GROUPS
    assert additive_across_nodes == 0
    assert root_total_allowed == 0


def test_ndia_facts_loaded_with_no_canonical_assignment() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*), SUM(CASE WHEN f.canonical_dataset_id IS NOT NULL THEN 1 ELSE 0 END)
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = 'federal_pbs_2026_27_ndia'
            """
        ).fetchone()
    finally:
        conn.close()
    fact_count, canonical_count = row
    assert fact_count == 50
    assert not canonical_count


def test_ndia_program_totals_reconcile_to_expected_published_values() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT n.name, f.financial_year, f.amount_aud
            FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = 'federal_pbs_2026_27_ndia'
              AND n.name LIKE '%Program 1.1 - Reasonable and necessary support for participants'
              AND n.name NOT LIKE '%/%/%/%/%'
            """
        ).fetchall()
    finally:
        conn.close()
    by_year = {fy: amount for _name, fy, amount in rows}
    assert by_year == {
        "2025-26": 51_302_834_000,
        "2026-27": 53_703_813_000,
        "2027-28": 53_787_683_000,
        "2028-29": 54_273_595_000,
        "2029-30": 54_781_239_000,
    }

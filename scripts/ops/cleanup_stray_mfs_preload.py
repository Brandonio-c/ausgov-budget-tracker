#!/usr/bin/env python3
"""Remove the stray, pre-milestone `federal_monthly_financial_statements`
preload discovered while establishing the MFS-aggregates milestone's
baseline (Task 1).

288 facts (measure_type='monthly_actuals', compatibility_group=
'actual_expense' - the SAME group as annual GFS/PBS actual expense data)
were already present in data/facts.db from an earlier, incomplete/
exploratory run, despite the milestone's own framing that "the extractor
was deliberately not loaded." For FY2025-26 (the one year where no GFS-
basis annual data exists yet, so `_preferred_basis()` in
src/backend/routers/v2/dashboard.py falls back to 'accrual' instead of
filtering it out), these single-month ("| July") facts were confirmed -
via a direct query against the live production API - to be silently
summed into the federal actuals root total alongside real annual data.
This is exactly the contamination this milestone's non-negotiable
constraints prohibit, already live in production.

This is a narrow, one-time removal (not a declarative registry like
cleanup_duplicate_facts.py) because the stray dataset is fully isolated
(confirmed before deletion: exactly one source_document, all of it
measure_type='monthly_actuals', zero breakdown_edges referencing any of
its 22 nodes) and will be superseded by this same milestone's own
correctly-classified reload (Tasks 5-7).

Usage:
    python3 scripts/ops/cleanup_stray_mfs_preload.py --dry-run   (default)
    python3 scripts/ops/cleanup_stray_mfs_preload.py --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "facts.db"
STRAY_SOURCE_KEY = "federal_monthly_financial_statements"
STRAY_MEASURE_TYPE = "monthly_actuals"


def find_stray_state(conn: sqlite3.Connection) -> dict:
    doc = conn.execute(
        "SELECT id, source_key, title FROM source_documents WHERE source_key = ?",
        (STRAY_SOURCE_KEY,),
    ).fetchone()
    if doc is None:
        return {"source_document": None, "fact_ids": [], "node_ids": [], "safe_to_remove": True}

    doc_id = doc[0]

    other_measure_types = conn.execute(
        "SELECT DISTINCT measure_type FROM facts WHERE source_document_id = ? AND measure_type != ?",
        (doc_id, STRAY_MEASURE_TYPE),
    ).fetchall()

    fact_ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM facts WHERE source_document_id = ? AND measure_type = ?",
            (doc_id, STRAY_MEASURE_TYPE),
        ).fetchall()
    ]
    node_ids: list[int] = []
    if fact_ids:
        placeholders = ",".join("?" for _ in fact_ids)
        node_ids = [
            r[0]
            for r in conn.execute(
                f"SELECT DISTINCT node_id FROM fact_nodes WHERE fact_id IN ({placeholders})",
                fact_ids,
            ).fetchall()
        ]
    edge_count = 0
    if node_ids:
        placeholders = ",".join("?" for _ in node_ids)
        edge_count = conn.execute(
            f"""
            SELECT COUNT(*) FROM breakdown_edges
            WHERE parent_node_id IN ({placeholders}) OR child_node_id IN ({placeholders})
            """,
            node_ids + node_ids,
        ).fetchone()[0]

    safe = not other_measure_types and edge_count == 0
    return {
        "source_document": {"id": doc_id, "source_key": doc[1], "title": doc[2]},
        "other_measure_types_under_source": [r[0] for r in other_measure_types],
        "fact_ids": fact_ids,
        "node_ids": node_ids,
        "breakdown_edges_referencing_nodes": edge_count,
        "safe_to_remove": safe,
    }


def apply_cleanup(conn: sqlite3.Connection, state: dict) -> None:
    fact_ids = state["fact_ids"]
    node_ids = state["node_ids"]
    doc_id = state["source_document"]["id"]
    if fact_ids:
        placeholders = ",".join("?" for _ in fact_ids)
        conn.execute(f"DELETE FROM fact_nodes WHERE fact_id IN ({placeholders})", fact_ids)
        conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", fact_ids)
    if node_ids:
        placeholders = ",".join("?" for _ in node_ids)
        conn.execute(f"DELETE FROM nodes WHERE id IN ({placeholders})", node_ids)
    conn.execute("DELETE FROM source_documents WHERE id = ?", (doc_id,))
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Default behavior; explicit no-op flag.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(str(args.db))
    state = find_stray_state(conn)

    if state["source_document"] is None:
        print(json.dumps({"status": "already_clean", "detail": "no stray source_document found"}, indent=2))
        conn.close()
        return 0

    if not state["safe_to_remove"]:
        print(json.dumps({"status": "unsafe_to_remove", **state}, indent=2))
        conn.close()
        return 1

    if args.apply:
        apply_cleanup(conn, state)
        print(json.dumps({"status": "removed", "mode": "apply", **state}, indent=2))
    else:
        print(json.dumps({"status": "would_remove", "mode": "dry-run", **state}, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

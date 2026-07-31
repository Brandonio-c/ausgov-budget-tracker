#!/usr/bin/env python3
"""Reconcile GFS Table 1 Taxation revenue vs ABS detailed tax categories."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "facts.db"


def reconcile(conn: sqlite3.Connection, *, year: str, tolerance_pct: float = 5.0) -> list[dict]:
    rows = []
    # Control: GFS taxation revenue total-ish nodes
    controls = conn.execute(
        """
        SELECT d.jurisdiction, f.financial_year, SUM(f.amount_aud) AS control_aud
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        WHERE m.compatibility_group = 'gfs_revenue'
          AND f.measure_type = 'gfs_revenue'
          AND f.financial_year = ?
          AND lower(n.name) LIKE '%taxation revenue%'
          AND lower(n.name) NOT LIKE '%/%'
        GROUP BY 1, 2
        """,
        (year,),
    ).fetchall()
    for jurisdiction, fy, control in controls:
        detail = conn.execute(
            """
            SELECT COALESCE(SUM(f.amount_aud), 0)
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            WHERE m.compatibility_group = 'gfs_revenue'
              AND f.measure_type = 'tax_revenue'
              AND f.financial_year = ?
              AND d.jurisdiction = ?
            """,
            (fy, jurisdiction),
        ).fetchone()[0]
        control_f = float(control or 0)
        detail_f = float(detail or 0)
        diff = detail_f - control_f
        pct = (abs(diff) / control_f * 100.0) if control_f else None
        status = "ok"
        if control_f <= 0:
            status = "no_control"
        elif pct is not None and pct > tolerance_pct:
            status = "warning"
        rows.append(
            {
                "jurisdiction": jurisdiction,
                "financial_year": fy,
                "control_amount": control_f,
                "detail_sum": detail_f,
                "difference": diff,
                "difference_percentage": pct,
                "status": status,
                "tolerance_pct": tolerance_pct,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--year", default="2024-25")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    conn = sqlite3.connect(str(args.db))
    rows = reconcile(conn, year=args.year)
    out = args.out or (
        REPO / "ops" / "reports" / f"revenue-reconciliation-{args.year.replace('-', '')}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"year": args.year, "rows": rows}, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "n": len(rows), "warnings": sum(1 for r in rows if r["status"] == "warning")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

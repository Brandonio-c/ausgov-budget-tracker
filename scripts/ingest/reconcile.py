#!/usr/bin/env python3
"""Reconcile facts.db aggregates against spending.db (M3+)."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FACTS_DB = REPO_ROOT / "data" / "facts.db"
SPENDING_DB = REPO_ROOT / "data" / "processed" / "spending.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def reconcile_source(
    source_id: str,
    *,
    facts_db: Path = FACTS_DB,
    spending_db: Path = SPENDING_DB,
    jurisdiction: str | None = None,
    jurisdiction_prefix: str | None = None,
    tolerance: float = 1.0,
) -> list[dict]:
    """Compare per-FY totals; record reconciliations (never blocks ingest)."""
    if not spending_db.is_file():
        return [{"status": "skipped", "reason": f"missing {spending_db}"}]

    fconn = sqlite3.connect(str(facts_db))
    fconn.row_factory = sqlite3.Row
    sconn = sqlite3.connect(str(spending_db))
    sconn.row_factory = sqlite3.Row

    fact_rows = fconn.execute(
        """
        SELECT f.financial_year, SUM(f.amount_aud) AS total
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE d.source_key = ?
        GROUP BY f.financial_year
        ORDER BY f.financial_year
        """,
        (source_id,),
    ).fetchall()

    # spending.db has no source_id; filter by jurisdiction heuristic when provided
    if jurisdiction_prefix:
        spend_rows = sconn.execute(
            """
            SELECT financial_year, SUM(amount_aud) AS total
            FROM spending
            WHERE jurisdiction LIKE ?
            GROUP BY financial_year
            """,
            (jurisdiction_prefix + "%",),
        ).fetchall()
    elif jurisdiction:
        spend_rows = sconn.execute(
            """
            SELECT financial_year, SUM(amount_aud) AS total
            FROM spending
            WHERE jurisdiction = ?
            GROUP BY financial_year
            """,
            (jurisdiction,),
        ).fetchall()
    else:
        spend_rows = sconn.execute(
            """
            SELECT financial_year, SUM(amount_aud) AS total
            FROM spending
            GROUP BY financial_year
            """
        ).fetchall()

    spend_map = {r["financial_year"]: float(r["total"]) for r in spend_rows}
    results = []
    for row in fact_rows:
        fy = row["financial_year"]
        left = float(row["total"])
        right = spend_map.get(fy)
        if right is None:
            status = "unresolved"
            diff = left
            explanation = "no matching FY in spending.db"
        else:
            diff = left - right
            if abs(diff) <= tolerance:
                status = "balanced" if abs(diff) < 1e-9 else "within_tolerance"
                explanation = None
            else:
                status = "explained_difference"
                explanation = f"delta={diff}"
        key = f"reconcile|{source_id}|{fy}"
        # Store synthetic marker facts if needed — use reconciliations with
        # placeholder self-links only when both sides exist as facts.
        results.append(
            {
                "reconciliation_key": key,
                "financial_year": fy,
                "left_total": left,
                "right_total": right,
                "difference_amount_aud": diff if right is not None else left,
                "status": status,
                "explanation": explanation,
                "created_at": _utc_now(),
            }
        )
        fconn.execute(
            """
            INSERT INTO reconciliations (
                reconciliation_key, title, financial_year,
                left_fact_id, right_fact_id, difference_amount_aud,
                tolerance_amount_aud, status, explanation, created_at
            )
            SELECT ?, ?, ?, f.id, f.id, ?, ?, ?, ?, ?
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE d.source_key = ? AND f.financial_year = ?
            LIMIT 1
            ON CONFLICT(reconciliation_key) DO UPDATE SET
                difference_amount_aud = excluded.difference_amount_aud,
                status = excluded.status,
                explanation = excluded.explanation,
                created_at = excluded.created_at
            """,
            (
                key,
                f"Reconcile {source_id} {fy}",
                fy,
                abs(diff) if right is not None else abs(left),
                tolerance,
                status,
                explanation,
                _utc_now(),
                source_id,
                fy,
            ),
        )
    fconn.commit()
    fconn.close()
    sconn.close()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--jurisdiction")
    parser.add_argument("--facts-db", type=Path, default=FACTS_DB)
    parser.add_argument("--spending-db", type=Path, default=SPENDING_DB)
    args = parser.parse_args(argv)
    rows = reconcile_source(
        args.source_id,
        facts_db=args.facts_db,
        spending_db=args.spending_db,
        jurisdiction=args.jurisdiction,
    )
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())

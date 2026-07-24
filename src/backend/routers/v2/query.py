
"""API v2 query routes with compatibility_group guard."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ...facts_db import get_facts_connection
from .citation import build_citation


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

router = APIRouter()


def _require_triple(
    compatibility_group: str | None,
    accounting_basis: str | None,
    estimate_status: str | None,
    *,
    allow_reconciliation: bool,
    view: str | None,
) -> None:
    if view == "reconciliation" and allow_reconciliation:
        return
    missing = [
        name
        for name, val in (
            ("compatibility_group", compatibility_group),
            ("accounting_basis", accounting_basis),
            ("estimate_status", estimate_status),
        )
        if not val
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Query requires compatibility_group, accounting_basis, and "
                f"estimate_status (missing: {', '.join(missing)}). "
                "Cross-group aggregation is forbidden unless view=reconciliation."
            ),
        )


@router.get("/aggregate")
def aggregate(
    compatibility_group: str | None = Query(default=None),
    accounting_basis: str | None = Query(default=None),
    estimate_status: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    view: str | None = Query(default=None),
) -> dict:
    _require_triple(
        compatibility_group,
        accounting_basis,
        estimate_status,
        allow_reconciliation=True,
        view=view,
    )
    conn = _facts_conn()
    try:
        if view == "reconciliation":
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS n, SUM(difference_amount_aud) AS diff
                FROM reconciliations
                GROUP BY status
                """
            ).fetchall()
            return {
                "view": "reconciliation",
                "groups": [dict(r) for r in rows],
            }

        sql = """
            SELECT f.financial_year, SUM(f.amount_aud) AS total_aud, COUNT(*) AS n
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            WHERE m.compatibility_group = ?
              AND f.accounting_basis = ?
              AND f.estimate_status = ?
        """
        params: list = [compatibility_group, accounting_basis, estimate_status]
        if financial_year:
            sql += " AND f.financial_year = ?"
            params.append(financial_year)
        sql += " GROUP BY f.financial_year ORDER BY f.financial_year"
        rows = conn.execute(sql, params).fetchall()
        items = []
        for r in rows:
            # attach a sample citation-bearing fact id for the FY
            fact = conn.execute(
                """
                SELECT f.id FROM facts f
                JOIN measure_definitions m ON m.measure_type = f.measure_type
                WHERE m.compatibility_group = ?
                  AND f.accounting_basis = ?
                  AND f.estimate_status = ?
                  AND f.financial_year = ?
                LIMIT 1
                """,
                (
                    compatibility_group,
                    accounting_basis,
                    estimate_status,
                    r["financial_year"],
                ),
            ).fetchone()
            citation = build_citation(int(fact["id"])) if fact else None
            items.append(
                {
                    "financial_year": r["financial_year"],
                    "total_aud": r["total_aud"],
                    "n": r["n"],
                    "citation": citation,
                }
            )
        return {
            "compatibility_group": compatibility_group,
            "accounting_basis": accounting_basis,
            "estimate_status": estimate_status,
            "items": items,
        }
    finally:
        conn.close()


@router.get("/tree")
def tree(
    compatibility_group: str = Query(...),
    accounting_basis: str = Query(...),
    estimate_status: str = Query(...),
    financial_year: str = Query(...),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict:
    """Flat tree of primary nodes for one compatibility triple."""
    conn = _facts_conn()
    try:
        rows = conn.execute(
            """
            SELECT f.id, n.name AS node_name, f.amount_aud
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            WHERE m.compatibility_group = ?
              AND f.accounting_basis = ?
              AND f.estimate_status = ?
              AND f.financial_year = ?
            ORDER BY f.amount_aud DESC
            LIMIT ?
            """,
            (
                compatibility_group,
                accounting_basis,
                estimate_status,
                financial_year,
                limit,
            ),
        ).fetchall()
        children = []
        for r in rows:
            children.append(
                {
                    "name": r["node_name"],
                    "value": r["amount_aud"],
                    "id": r["id"],
                    "citation": build_citation(int(r["id"])),
                }
            )
        total = sum(c["value"] or 0 for c in children)
        return {
            "name": f"{compatibility_group} / {accounting_basis} / {estimate_status} / {financial_year}",
            "value": total,
            "children": children,
        }
    finally:
        conn.close()

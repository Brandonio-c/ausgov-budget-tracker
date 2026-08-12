
"""API v2 query routes with compatibility_group guard."""

from __future__ import annotations

import base64
import json
import math

from fastapi import APIRouter, HTTPException, Query

from ...facts_db import get_facts_connection
from .citation import build_citation, build_citation_from_row


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

router = APIRouter()


def _encode_tree_cursor(amount_aud: float | None, fact_id: int) -> str:
    raw = json.dumps(
        {"v": 1, "amount_aud": amount_aud, "fact_id": fact_id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_tree_cursor(cursor: str) -> tuple[float | None, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        if payload.get("v") != 1 or not isinstance(payload.get("fact_id"), int):
            raise ValueError
        amount = payload.get("amount_aud")
        if amount is not None and not isinstance(amount, (int, float)):
            raise ValueError
        if amount is not None and not math.isfinite(float(amount)):
            raise ValueError
        return (float(amount) if amount is not None else None, int(payload["fact_id"]))
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid tree cursor") from exc


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
    source_key: str | None = Query(
        default=None,
        description=(
            "Optional exact source_documents.source_key filter. A compatibility "
            "triple is commonly shared by several distinct sources (e.g. "
            "budget_expense/accrual/budget also covers state budget statements "
            "and other PBS-derived extractors alongside federal_pbs_programs_all) "
            "- omit to preserve the existing unfiltered behaviour of every caller "
            "that predates this parameter."
        ),
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
) -> dict:
    """Truthful, cursor-paginated flat list for one compatibility triple."""
    conn = _facts_conn()
    try:
        from_where = """
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            LEFT JOIN source_retrievals r ON r.id = f.source_retrieval_id
            WHERE m.compatibility_group = ?
              AND f.accounting_basis = ?
              AND f.estimate_status = ?
              AND f.financial_year = ?
              AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
        """
        scope_params: list = [
            compatibility_group,
            accounting_basis,
            estimate_status,
            financial_year,
        ]
        if source_key:
            from_where += " AND d.source_key = ?"
            scope_params.append(source_key)
        totals = conn.execute(
            f"""
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(f.amount_aud), 0) AS total_value
            {from_where}
            """,
            scope_params,
        ).fetchone()

        cursor_sql = ""
        page_params = list(scope_params)
        if cursor:
            cursor_amount, cursor_id = _decode_tree_cursor(cursor)
            if cursor_amount is None:
                cursor_sql = " AND f.amount_aud IS NULL AND f.id > ?"
                page_params.append(cursor_id)
            else:
                cursor_sql = """
                    AND (
                        f.amount_aud < ?
                        OR (f.amount_aud = ? AND f.id > ?)
                        OR f.amount_aud IS NULL
                    )
                """
                page_params.extend((cursor_amount, cursor_amount, cursor_id))
        page_params.append(limit + 1)
        rows = conn.execute(
            f"""
            SELECT
                f.id AS fact_id,
                n.name AS node_name,
                f.amount_aud,
                f.fact_key,
                f.financial_year,
                f.measure_type,
                f.source_locator_json,
                f.retrieved_at AS fact_retrieved_at,
                d.landing_url AS doc_landing_url,
                d.canonical_resource_url,
                r.sha256,
                r.retrieved_at AS retrieval_retrieved_at,
                r.local_path,
                r.resolved_url
            {from_where}
            {cursor_sql}
            ORDER BY f.amount_aud IS NULL, f.amount_aud DESC, f.id
            LIMIT ?
            """,
            page_params,
        ).fetchall()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        children = []
        for r in page_rows:
            children.append(
                {
                    "name": r["node_name"],
                    "value": r["amount_aud"],
                    "id": r["fact_id"],
                    "citation": build_citation_from_row(r),
                }
            )
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = _encode_tree_cursor(
                last["amount_aud"], int(last["fact_id"])
            )
        total_count = int(totals["total_count"] if totals else 0)
        total_value = float(totals["total_value"] if totals else 0)
        name = f"{compatibility_group} / {accounting_basis} / {estimate_status} / {financial_year}"
        if source_key:
            name = f"{source_key} / {name}"
        return {
            "name": name,
            "shape": "flat",
            "value": total_value,
            "total_count": total_count,
            "total_value": total_value,
            "next_cursor": next_cursor,
            "children": children,
        }
    finally:
        conn.close()

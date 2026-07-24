"""Read API for published facts + spending search."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from ...facts_db import get_facts_connection
from .citation import build_citation
from .dashboard import (
    Mode,
    _estatus_clause,
    _mode_filters,
    _normalize_level,
    _preferred_basis,
)

router = APIRouter()

SortOpt = Literal["amount_desc", "amount_asc", "fy_desc", "name"]
LEVELS = ("federal", "state", "territory", "local")


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/facts/search")
def search_facts(
    q: str | None = Query(default=None, description="Keyword match on node name / source title"),
    mode: Mode | None = Query(default=None),
    level: str | None = Query(default=None),
    jurisdiction: str | None = Query(default=None),
    fy_from: str | None = Query(default=None),
    fy_to: str | None = Query(default=None),
    amount_min: float | None = Query(default=None),
    amount_max: float | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: SortOpt = Query(default="amount_desc"),
) -> dict:
    """Basic + advanced spending search over primary nodes."""
    q_clean = (q or "").strip()
    has_q = len(q_clean) >= 2
    has_advanced = any(
        [
            mode,
            level,
            jurisdiction,
            fy_from,
            fy_to,
            amount_min is not None,
            amount_max is not None,
        ]
    )
    if not has_q and not has_advanced:
        raise HTTPException(
            status_code=400,
            detail="Provide q (at least 2 characters) and/or an advanced filter",
        )
    if q_clean and len(q_clean) < 2:
        raise HTTPException(status_code=400, detail="q must be at least 2 characters")

    level_norm = _normalize_level(level) if level else None
    if level_norm and level_norm not in LEVELS:
        raise HTTPException(status_code=400, detail=f"level must be one of {list(LEVELS)}")

    where: list[str] = ["fn.dimension_role = 'primary'"]
    params: list[Any] = []

    if has_q:
        like = f"%{q_clean}%"
        where.append("(n.name LIKE ? COLLATE NOCASE OR d.title LIKE ? COLLATE NOCASE)")
        params.extend([like, like])

    if mode:
        filt = _mode_filters(mode)
        est_sql, est_params = _estatus_clause(filt["estimate_statuses"])
        where.append("m.compatibility_group = ?")
        params.append(filt["compatibility_group"])
        where.append(f"f.estimate_status {est_sql}")
        params.extend(est_params)

    if level_norm:
        where.append(
            "CASE d.government_level WHEN 'national' THEN 'federal' ELSE d.government_level END = ?"
        )
        params.append(level_norm)

    if jurisdiction:
        where.append("d.jurisdiction = ?")
        params.append(jurisdiction.strip())

    if fy_from:
        where.append("f.financial_year >= ?")
        params.append(fy_from.strip())
    if fy_to:
        where.append("f.financial_year <= ?")
        params.append(fy_to.strip())

    if amount_min is not None:
        where.append("f.amount_aud >= ?")
        params.append(amount_min)
    if amount_max is not None:
        where.append("f.amount_aud <= ?")
        params.append(amount_max)

    conn = _facts_conn()
    try:
        if mode == "actuals":
            if level_norm:
                preferred = _preferred_basis(conn, mode, level_norm, None)
            else:
                # Nationwide actuals: prefer GFS when any GFS rows exist for the group
                has_gfs = conn.execute(
                    """
                    SELECT 1 FROM facts f
                    JOIN measure_definitions m ON m.measure_type = f.measure_type
                    WHERE m.compatibility_group = 'actual_expense'
                      AND f.accounting_basis = 'gfs'
                    LIMIT 1
                    """
                ).fetchone()
                preferred = "gfs" if has_gfs else None
            if preferred:
                where.append("f.accounting_basis = ?")
                params.append(preferred)

        where_sql = " AND ".join(where)
        order = {
            "amount_desc": "f.amount_aud DESC",
            "amount_asc": "f.amount_aud ASC",
            "fy_desc": "f.financial_year DESC, f.amount_aud DESC",
            "name": "n.name COLLATE NOCASE ASC, f.financial_year DESC",
        }[sort]

        count_row = conn.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN fact_nodes fn ON fn.fact_id = f.id
            JOIN nodes n ON n.id = fn.node_id
            WHERE {where_sql}
            """,
            params,
        ).fetchone()
        total = int(count_row["n"] if count_row else 0)

        rows = conn.execute(
            f"""
            SELECT
                f.id,
                n.name AS node_name,
                f.amount_aud,
                f.financial_year,
                d.jurisdiction,
                CASE d.government_level WHEN 'national' THEN 'federal'
                    ELSE d.government_level END AS level,
                f.measure_type,
                f.accounting_basis,
                f.estimate_status,
                d.title AS source_title
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            JOIN fact_nodes fn ON fn.fact_id = f.id
            JOIN nodes n ON n.id = fn.node_id
            WHERE {where_sql}
            ORDER BY {order}
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    finally:
        conn.close()

    items = [
        {
            "id": int(r["id"]),
            "node_name": r["node_name"],
            "amount_aud": float(r["amount_aud"] or 0),
            "financial_year": r["financial_year"],
            "jurisdiction": r["jurisdiction"],
            "level": r["level"],
            "measure_type": r["measure_type"],
            "accounting_basis": r["accounting_basis"],
            "estimate_status": r["estimate_status"],
            "source_title": r["source_title"],
        }
        for r in rows
    ]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/facts/{fact_id}")
def get_fact(fact_id: int) -> dict:
    citation = build_citation(fact_id)
    return {
        "id": citation["fact_id"],
        "fact_key": citation["fact_key"],
        "financial_year": citation["financial_year"],
        "measure_type": citation["measure_type"],
        "amount_aud": citation["amount_aud"],
        "citation": citation,
    }


@router.get("/facts")
def list_facts(
    source_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    conn = _facts_conn()
    try:
        if source_id:
            rows = conn.execute(
                """
                SELECT f.id FROM facts f
                JOIN source_documents d ON d.id = f.source_document_id
                WHERE d.source_key = ?
                ORDER BY f.id LIMIT ?
                """,
                (source_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id FROM facts ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        try:
            out.append(get_fact(int(r["id"])))
        except HTTPException:
            continue
    return out

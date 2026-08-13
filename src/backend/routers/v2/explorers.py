"""Reusable specialist explorer family registry API (plan item 6.1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ...explorer_registry import ExplorerFamily, load_explorer_registry
from ...facts_db import get_facts_connection
from .citation import build_citation_from_row
from .query import build_flat_tree_response

router = APIRouter(prefix="/explorers")


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _family_or_404(family_id: str) -> ExplorerFamily:
    family = load_explorer_registry().family_by_id(family_id)
    if family is None:
        raise HTTPException(status_code=404, detail=f"Unknown explorer family: {family_id}")
    return family


def _family_summary(family: ExplorerFamily) -> dict:
    return {
        "id": family.id,
        "label": family.label,
        "compatibility_group": family.compatibility_group,
        "accounting_basis": family.accounting_basis,
        "estimate_statuses": list(family.estimate_statuses),
        "default_estimate_status": family.default_estimate_status,
        "source_key": family.source_key,
        "additive_note": family.additive_note,
    }


def _family_where(family: ExplorerFamily) -> tuple[str, list]:
    """WHERE clause + params scoping to a family's full registered range
    (every one of its estimate_statuses, every year) - shared by
    availability/facets/item so family-boundary enforcement can't drift
    between endpoints."""
    placeholders = ",".join("?" for _ in family.estimate_statuses)
    params: list = [family.compatibility_group, family.accounting_basis]
    params.extend(family.estimate_statuses)
    sql = f"""
        WHERE m.compatibility_group = ?
          AND f.accounting_basis = ?
          AND f.estimate_status IN ({placeholders})
          AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
    """
    if family.source_key:
        sql += " AND d.source_key = ?"
        params.append(family.source_key)
    return sql, params


@router.get("")
def list_explorers() -> dict:
    registry = load_explorer_registry()
    return {"families": [_family_summary(f) for f in registry.families]}


@router.get("/{family_id}/availability")
def explorer_availability(family_id: str) -> dict:
    family = _family_or_404(family_id)
    where_sql, params = _family_where(family)

    conn = _facts_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT f.financial_year AS financial_year,
                   f.estimate_status AS estimate_status,
                   COUNT(*) AS n,
                   COALESCE(SUM(f.amount_aud), 0) AS v
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            {where_sql}
            GROUP BY f.financial_year, f.estimate_status
            ORDER BY f.financial_year, f.estimate_status
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return {
        "family": _family_summary(family),
        "years": [
            {
                "financial_year": r["financial_year"],
                "estimate_status": r["estimate_status"],
                "count": int(r["n"]),
                "value": float(r["v"]),
            }
            for r in rows
        ],
    }


@router.get("/{family_id}/tree")
def explorer_family_tree(
    family_id: str,
    financial_year: str = Query(...),
    estimate_status: str | None = Query(
        default=None,
        description="Defaults to the family's default_estimate_status. Must be one of the family's registered estimate_statuses.",
    ),
    path: str | None = Query(
        default=None,
        description=(
            "Hierarchical path browsing. None of the currently registered "
            "families have source-native hierarchy beyond their flat fact "
            "list (verified against node_edges directly, not inferred from "
            "label structure) - a non-empty path is rejected rather than "
            "silently ignored or faked."
        ),
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    q: str | None = Query(
        default=None,
        description="Case-insensitive substring search over node names, applied server-side over the full family scope - not just the loaded page.",
    ),
) -> dict:
    family = _family_or_404(family_id)
    if path:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Family '{family_id}' has no source-native hierarchy beyond its "
                "flat fact list yet; path browsing is not supported. Use the flat "
                "list (path omitted) with facets/search instead of a fabricated tree."
            ),
        )
    status = estimate_status or family.default_estimate_status
    if status not in family.estimate_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"estimate_status must be one of {list(family.estimate_statuses)} "
                f"for family '{family_id}' (got {status!r})"
            ),
        )

    conn = _facts_conn()
    try:
        body = build_flat_tree_response(
            conn,
            compatibility_group=family.compatibility_group,
            accounting_basis=family.accounting_basis,
            estimate_status=status,
            financial_year=financial_year,
            source_key=family.source_key,
            limit=limit,
            cursor=cursor,
            search=q,
        )
    finally:
        conn.close()
    body["family"] = family_id
    return body


@router.get("/{family_id}/facets")
def explorer_family_facets(family_id: str) -> dict:
    family = _family_or_404(family_id)
    where_sql, params = _family_where(family)

    conn = _facts_conn()
    try:
        years = conn.execute(
            f"""
            SELECT f.financial_year AS financial_year, COUNT(*) AS n
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            {where_sql}
            GROUP BY f.financial_year
            ORDER BY f.financial_year
            """,
            params,
        ).fetchall()
        statuses = conn.execute(
            f"""
            SELECT f.estimate_status AS estimate_status, COUNT(*) AS n
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            {where_sql}
            GROUP BY f.estimate_status
            ORDER BY f.estimate_status
            """,
            params,
        ).fetchall()
        sources = conn.execute(
            f"""
            SELECT d.source_key AS source_key, COUNT(*) AS n
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            {where_sql}
            GROUP BY d.source_key
            ORDER BY n DESC
            """,
            params,
        ).fetchall()
        measures = conn.execute(
            f"""
            SELECT f.measure_type AS measure_type, COUNT(*) AS n
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            {where_sql}
            GROUP BY f.measure_type
            ORDER BY n DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return {
        "family": _family_summary(family),
        "years": [{"financial_year": r["financial_year"], "count": int(r["n"])} for r in years],
        "estimate_statuses": [
            {"estimate_status": r["estimate_status"], "count": int(r["n"])} for r in statuses
        ],
        "sources": [{"source_key": r["source_key"], "count": int(r["n"])} for r in sources],
        "measures": [{"measure_type": r["measure_type"], "count": int(r["n"])} for r in measures],
    }


@router.get("/{family_id}/item/{fact_id}")
def explorer_family_item(family_id: str, fact_id: int) -> dict:
    """Item-level evidence lookup, scoped to this family only.

    A fact_id valid in another family's or the canonical dashboard's scope
    is deliberately still a 404 here - family boundaries must mean
    something, not just be a UI convenience.
    """
    family = _family_or_404(family_id)
    where_sql, params = _family_where(family)

    conn = _facts_conn()
    try:
        row = conn.execute(
            f"""
            SELECT
                f.id AS fact_id,
                n.name AS node_name,
                f.amount_aud,
                f.fact_key,
                f.financial_year,
                f.estimate_status,
                f.measure_type,
                f.source_locator_json,
                f.retrieved_at AS fact_retrieved_at,
                d.landing_url AS doc_landing_url,
                d.canonical_resource_url,
                r.sha256,
                r.retrieved_at AS retrieval_retrieved_at,
                r.local_path,
                r.resolved_url
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            JOIN source_documents d ON d.id = f.source_document_id
            LEFT JOIN source_retrievals r ON r.id = f.source_retrieval_id
            {where_sql}
              AND f.id = ?
            """,
            [*params, fact_id],
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fact {fact_id} not found in family '{family_id}' scope",
        )

    return {
        "family": family_id,
        "name": row["node_name"],
        "value": row["amount_aud"],
        "financial_year": row["financial_year"],
        "estimate_status": row["estimate_status"],
        "citation": build_citation_from_row(row),
    }

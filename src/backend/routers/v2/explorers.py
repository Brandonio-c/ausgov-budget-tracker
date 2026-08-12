"""Reusable specialist explorer family registry API (plan item 6.1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...explorer_registry import load_explorer_registry
from ...facts_db import get_facts_connection

router = APIRouter(prefix="/explorers")


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _family_summary(family) -> dict:
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


@router.get("")
def list_explorers() -> dict:
    registry = load_explorer_registry()
    return {"families": [_family_summary(f) for f in registry.families]}


@router.get("/{family_id}/availability")
def explorer_availability(family_id: str) -> dict:
    family = load_explorer_registry().family_by_id(family_id)
    if family is None:
        raise HTTPException(status_code=404, detail=f"Unknown explorer family: {family_id}")

    conn = _facts_conn()
    try:
        placeholders = ",".join("?" for _ in family.estimate_statuses)
        params: list = [family.compatibility_group, family.accounting_basis]
        params.extend(family.estimate_statuses)
        source_sql = ""
        if family.source_key:
            source_sql = " AND d.source_key = ?"
            params.append(family.source_key)
        rows = conn.execute(
            f"""
            SELECT f.financial_year AS financial_year,
                   f.estimate_status AS estimate_status,
                   COUNT(*) AS n,
                   COALESCE(SUM(f.amount_aud), 0) AS v
            FROM facts f
            JOIN measure_definitions m ON m.measure_type = f.measure_type
            JOIN source_documents d ON d.id = f.source_document_id
            WHERE m.compatibility_group = ?
              AND f.accounting_basis = ?
              AND f.estimate_status IN ({placeholders})
              AND COALESCE(f.quality_status, 'ok') NOT IN ('quarantined', 'rejected')
              {source_sql}
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

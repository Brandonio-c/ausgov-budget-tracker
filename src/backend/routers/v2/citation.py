"""Citation-bearing endpoints for published facts only."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ...facts_db import get_facts_connection

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parents[4]


def _facts_conn():
    try:
        return get_facts_connection()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _cached_copy_url(local_path: str | None, fact_id: int | None = None) -> str | None:
    if fact_id is not None:
        return f"/v2/dashboard/item/{fact_id}/source-file"
    if not local_path:
        return None
    p = Path(local_path)
    try:
        rel = p.resolve().relative_to(REPO_ROOT.resolve())
        return f"/v2/cached/{rel.as_posix()}"
    except ValueError:
        return f"/v2/cached/{p.name}"


def build_citation(fact_id: int) -> dict:
    conn = _facts_conn()
    try:
        row = conn.execute(
            """
            SELECT
                f.id AS fact_id,
                f.fact_key,
                f.amount_aud,
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
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            LEFT JOIN source_retrievals r ON r.id = f.source_retrieval_id
            WHERE f.id = ?
            """,
            (fact_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        # Distinguish missing vs quarantined by fact_key lookup is not available by id
        raise HTTPException(status_code=404, detail="Fact not found or not publishable")

    locator_obj = {}
    try:
        locator_obj = json.loads(row["source_locator_json"] or "{}")
    except json.JSONDecodeError:
        locator_obj = {"raw": row["source_locator_json"]}

    landing = locator_obj.get("landing_url") or row["doc_landing_url"]
    original = (
        locator_obj.get("original_resource_url")
        or row["resolved_url"]
        or row["canonical_resource_url"]
    )
    cached_path = locator_obj.get("cached_copy_path") or row["local_path"]
    locator = locator_obj.get("locator") or ""
    if isinstance(locator, dict):
        locator = json.dumps(locator)

    if not landing or not original or not cached_path or not str(locator).strip():
        raise HTTPException(
            status_code=404, detail="Fact not found or not publishable"
        )

    return {
        "fact_id": row["fact_id"],
        "fact_key": row["fact_key"],
        "financial_year": row["financial_year"],
        "measure_type": row["measure_type"],
        "amount_aud": row["amount_aud"],
        "landing_url": landing,
        "original_resource_url": original,
        "cached_copy_url": _cached_copy_url(cached_path, fact_id=row["fact_id"]),
        "locator": str(locator),
        "sha256": row["sha256"],
        "retrieved_at": row["retrieval_retrieved_at"] or row["fact_retrieved_at"],
    }


@router.get("/facts/{fact_id}/citation")
def get_citation(fact_id: int) -> dict:
    return build_citation(fact_id)

"""Unified hybrid search API (spending + document corpus)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ...search_index import search_db_available, unified_search

router = APIRouter()

ScopeParam = Literal["all", "spending", "documents"]


@router.get("/search")
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    scope: ScopeParam = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    """Hybrid search: FTS5 BM25 + FastEmbed semantic (RRF merge)."""
    try:
        return unified_search(q, scope=scope, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/search/status")
def search_status() -> dict:
    return {"index_ready": search_db_available()}

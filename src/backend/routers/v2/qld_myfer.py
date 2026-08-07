"""Dedicated API for isolated Queensland MYFER revised estimates."""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...facts_db import get_facts_connection

_HERE = Path(__file__).resolve().parent


def _default_semantics_path() -> Path:
    candidates = [Path("/app/config/measure-semantics/qld_myfer.yaml")]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config/measure-semantics/qld_myfer.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config/measure-semantics/qld_myfer.yaml")
    return next((path for path in candidates if path.is_file()), candidates[0])


SEMANTICS_PATH = _default_semantics_path()
router = APIRouter(prefix="/qld-myfer", tags=["v2-qld-myfer"])


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown QLD MYFER measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else _measure_spec(measure_type)["label"]


class QldMyferMeasureInfo(BaseModel):
    measure_type: str
    label: str
    flow_or_stock: str
    compatibility_group: str
    accounting_basis: str
    unit: str
    period_granularity: str


class QldMyferCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class QldMyferFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    financial_year: str
    period_start: Optional[str] = None
    period_end: str
    period_granularity: str
    source_budget_year: str
    publication_date: Optional[str] = None
    estimate_status: str
    compatibility_group: str
    citation: QldMyferCitation


class QldMyferSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[QldMyferFact]


@router.get("/measures", response_model=list[QldMyferMeasureInfo])
def qld_myfer_measures() -> list[QldMyferMeasureInfo]:
    semantics = _load_semantics()
    family = semantics["family"]
    conn = get_facts_connection()
    try:
        return [
            QldMyferMeasureInfo(
                measure_type=measure_type,
                label=_measure_label(conn, measure_type),
                flow_or_stock=spec["flow_or_stock"],
                compatibility_group=spec["compatibility_group"],
                accounting_basis=family["accounting_basis"],
                unit=family["output_unit"],
                period_granularity=family["period_granularity"],
            )
            for measure_type, spec in semantics["measures"].items()
        ]
    finally:
        conn.close()


@router.get("/series", response_model=QldMyferSeriesResponse)
def qld_myfer_series(measure_type: str = Query(...)) -> QldMyferSeriesResponse:
    spec = _measure_spec(measure_type)
    conn = get_facts_connection()
    try:
        label = _measure_label(conn, measure_type)
        rows = conn.execute(
            "SELECT * FROM facts WHERE measure_type = ? ORDER BY source_budget_year, financial_year",
            (measure_type,),
        ).fetchall()
    finally:
        conn.close()
    facts = []
    for row in rows:
        citation = json.loads(row["source_locator_json"] or "{}")
        facts.append(
            QldMyferFact(
                label=label,
                measure_type=measure_type,
                flow_or_stock=spec["flow_or_stock"],
                amount_aud=row["amount_aud"],
                financial_year=row["financial_year"],
                period_start=row["period_start"],
                period_end=row["period_end"],
                period_granularity=row["period_granularity"],
                source_budget_year=row["source_budget_year"],
                publication_date=row["publication_date"],
                estimate_status=row["estimate_status"],
                compatibility_group=spec["compatibility_group"],
                citation=QldMyferCitation(
                    locator=citation.get("locator", ""),
                    cached_copy_path=citation.get("cached_copy_path"),
                ),
            )
        )
    return QldMyferSeriesResponse(
        measure_type=measure_type,
        flow_or_stock=spec["flow_or_stock"],
        facts=facts,
    )

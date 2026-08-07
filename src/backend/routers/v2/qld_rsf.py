"""Dedicated API for the Queensland Treasury's "Report on State
Finances" - "Key UPF Financial Aggregates" table, General Government
Sector only (QLD PDF population milestone - Task 7).

8 measures, 7 financial years (2018-19 to 2024-25), each year carrying
two vintages (`estimated_actual`, `actual`) - a genuine multi-year
time series similar in shape to tas_ggs.py, but with a materially
different vintage concept (`estimated_actual` is the outcome as
projected in a LATER budget-cycle document, not an as-originally-
published Budget). Wired into the existing GFS/jurisdiction explorer
as another view rather than a new dedicated page - mirrors tas_ggs.py's
design exactly (same reasons: /v2/tree is compatibility_group-scoped
and expects one hierarchy per call; /v2/facts/search's jurisdiction-
only filtering would return unrelated QLD facts too, e.g. ABS GFS
series or QTC bond data).
"""

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
    """Resolve config in repo checkout or Docker (/app/config bind-mount) -
    mirrors compatibility.py's/mfs.py's/vic_afs.py's/tas_ggs.py's
    identical pattern."""
    candidates: list[Path] = [
        Path("/app/config/measure-semantics/qld_report_on_state_finances.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "qld_report_on_state_finances.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "qld_report_on_state_finances.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()

router = APIRouter(prefix="/qld-rsf", tags=["v2-qld-rsf"])


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown QLD RSF measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


class QldRsfMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    flow_or_stock: str
    row_label: str
    compatibility_group: str
    accounting_basis: str
    unit: str


class QldRsfCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class QldRsfFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    financial_year: str
    period_end: str
    accounting_basis: str
    estimate_status: str
    compatibility_group: str
    citation: QldRsfCitation


class QldRsfSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[QldRsfFact]


@router.get("/measures", response_model=list[QldRsfMeasureInfo])
def qld_rsf_measures() -> list[QldRsfMeasureInfo]:
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        out = []
        for measure_type, spec in semantics["measures"].items():
            out.append(
                QldRsfMeasureInfo(
                    measure_type=measure_type,
                    label=_measure_label(conn, measure_type),
                    economic_meaning=spec["economic_meaning"].strip(),
                    flow_or_stock=spec["flow_or_stock"],
                    row_label=spec["row_label_variants"][0],
                    compatibility_group=spec["compatibility_group"],
                    accounting_basis=spec["accounting_basis"],
                    unit=spec["unit"],
                )
            )
    finally:
        conn.close()
    return out


@router.get("/series", response_model=QldRsfSeriesResponse)
def qld_rsf_series(measure_type: str = Query(...)) -> QldRsfSeriesResponse:
    spec = _measure_spec(measure_type)
    conn = get_facts_connection()
    try:
        label = _measure_label(conn, measure_type)
        rows = conn.execute(
            "SELECT * FROM facts WHERE measure_type = ? ORDER BY financial_year",
            (measure_type,),
        ).fetchall()
    finally:
        conn.close()

    facts = []
    for row in rows:
        locator_payload = json.loads(row["source_locator_json"] or "{}")
        facts.append(
            QldRsfFact(
                label=label,
                measure_type=measure_type,
                flow_or_stock=spec["flow_or_stock"],
                amount_aud=row["amount_aud"],
                financial_year=row["financial_year"],
                period_end=row["period_end"],
                accounting_basis=row["accounting_basis"],
                estimate_status=row["estimate_status"],
                compatibility_group=spec["compatibility_group"],
                citation=QldRsfCitation(
                    locator=locator_payload.get("locator", ""),
                    cached_copy_path=locator_payload.get("cached_copy_path"),
                ),
            )
        )
    return QldRsfSeriesResponse(measure_type=measure_type, flow_or_stock=spec["flow_or_stock"], facts=facts)

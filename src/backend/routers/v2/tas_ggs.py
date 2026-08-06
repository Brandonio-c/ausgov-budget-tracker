"""Dedicated API for the Tasmanian Department of Treasury and
Finance's "GGS Key Fiscal Measures Time Series" (QLD/TAS mixed-format-
population milestone - Task 7).

Small by design: 10 measures, 16 financial years (2013-14 to 2028-29),
each year carrying exactly one vintage (Actual / Revised Estimate /
Forward Estimate) - a genuine multi-year time series, unlike vic_bpo_*'s
single-year actual-vs-budget comparison. Wired into the existing GFS/
jurisdiction explorer as another view (see ops/reports/qld-tas-*.md for
the full rationale) rather than a new dedicated page - mirrors
vic_bpo.py's/vic_bpo_soce_admin.py's design exactly (same reasons:
/v2/tree is compatibility_group-scoped and expects one hierarchy per
call; /v2/facts/search's jurisdiction-only filtering would return
unrelated TAS facts too, e.g. TASCORP debt or ABS GFS series).
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
    mirrors compatibility.py's/mfs.py's/vic_afs.py's/vic_bpo.py's
    identical pattern."""
    candidates: list[Path] = [
        Path("/app/config/measure-semantics/tas_ggs_key_fiscal_measures.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "tas_ggs_key_fiscal_measures.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "tas_ggs_key_fiscal_measures.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()

router = APIRouter(prefix="/tas-ggs", tags=["v2-tas-ggs"])


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown TAS GGS measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


class TasGgsMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    flow_or_stock: str
    source_column: str
    compatibility_group: str
    accounting_basis: str
    unit: str


class TasGgsCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class TasGgsFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    financial_year: str
    period_end: str
    accounting_basis: str
    estimate_status: str
    compatibility_group: str
    citation: TasGgsCitation


class TasGgsSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[TasGgsFact]


@router.get("/measures", response_model=list[TasGgsMeasureInfo])
def tas_ggs_measures() -> list[TasGgsMeasureInfo]:
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        out = []
        for measure_type, spec in semantics["measures"].items():
            out.append(
                TasGgsMeasureInfo(
                    measure_type=measure_type,
                    label=_measure_label(conn, measure_type),
                    economic_meaning=spec["economic_meaning"].strip(),
                    flow_or_stock=spec["flow_or_stock"],
                    source_column=spec["source_column"],
                    compatibility_group=spec["compatibility_group"],
                    accounting_basis=spec["accounting_basis"],
                    unit=spec["unit"],
                )
            )
    finally:
        conn.close()
    return out


@router.get("/series", response_model=TasGgsSeriesResponse)
def tas_ggs_series(measure_type: str = Query(...)) -> TasGgsSeriesResponse:
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
            TasGgsFact(
                label=label,
                measure_type=measure_type,
                flow_or_stock=spec["flow_or_stock"],
                amount_aud=row["amount_aud"],
                financial_year=row["financial_year"],
                period_end=row["period_end"],
                accounting_basis=row["accounting_basis"],
                estimate_status=row["estimate_status"],
                compatibility_group=spec["compatibility_group"],
                citation=TasGgsCitation(
                    locator=locator_payload.get("locator", ""),
                    cached_copy_path=locator_payload.get("cached_copy_path"),
                ),
            )
        )
    return TasGgsSeriesResponse(measure_type=measure_type, flow_or_stock=spec["flow_or_stock"], facts=facts)

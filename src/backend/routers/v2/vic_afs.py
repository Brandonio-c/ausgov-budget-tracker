"""Dedicated API for the VIC DTF Annual Financial Statements family
(Task 5 of the adapter-repair-followup milestone).

Small by design: 11 measures, 2 financial years, one department, one
acquired edition - no monthly/YTD cadence, no revision history yet.
Wired into the existing GFS/jurisdiction explorer as a third view
(see ops/reports/vic-afs-loader-*.md for why a whole new dedicated page
was not built, unlike MFS's monthly-cadence family) rather than getting
its own page - but still exposed through its own small, purpose-fit API
rather than awkwardly overloading /v2/tree (which is compatibility_
group-scoped and expects one hierarchy per call) or /v2/facts/search
(jurisdiction-only filtering would return unrelated VIC facts too).
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
    mirrors compatibility.py's _default_view_families_path() and mfs.py's
    _default_semantics_path() exactly (see ops/reports/mfs-production-
    verification-*.md for why a single fixed parents[N] cannot work in
    both places)."""
    candidates: list[Path] = [
        Path("/app/config/measure-semantics/vic_afs.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "vic_afs.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "vic_afs.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()

router = APIRouter(prefix="/vic-afs", tags=["v2-vic-afs"])


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown VIC AFS measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


class VicAfsMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    flow_or_stock: str
    source_sheet: str
    compatibility_group: str
    accounting_basis: str
    unit: str


class VicAfsCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class VicAfsFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    financial_year: str
    period_end: str
    accounting_basis: str
    estimate_status: str
    compatibility_group: str
    vintage: str = "current"
    citation: VicAfsCitation


class VicAfsSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[VicAfsFact]


@router.get("/measures", response_model=list[VicAfsMeasureInfo])
def vic_afs_measures() -> list[VicAfsMeasureInfo]:
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        out = []
        for measure_type, spec in semantics["measures"].items():
            out.append(
                VicAfsMeasureInfo(
                    measure_type=measure_type,
                    label=_measure_label(conn, measure_type),
                    economic_meaning=spec["economic_meaning"].strip(),
                    flow_or_stock=spec["flow_or_stock"],
                    source_sheet=spec["source_sheet"],
                    compatibility_group=spec["compatibility_group"],
                    accounting_basis=spec["accounting_basis"],
                    unit=spec["unit"],
                )
            )
    finally:
        conn.close()
    return out


@router.get("/series", response_model=VicAfsSeriesResponse)
def vic_afs_series(measure_type: str = Query(...)) -> VicAfsSeriesResponse:
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
            VicAfsFact(
                label=label,
                measure_type=measure_type,
                flow_or_stock=spec["flow_or_stock"],
                amount_aud=row["amount_aud"],
                financial_year=row["financial_year"],
                period_end=row["period_end"],
                accounting_basis=row["accounting_basis"],
                estimate_status=row["estimate_status"],
                compatibility_group=spec["compatibility_group"],
                citation=VicAfsCitation(
                    locator=locator_payload.get("locator", ""),
                    cached_copy_path=locator_payload.get("cached_copy_path"),
                ),
            )
        )
    return VicAfsSeriesResponse(measure_type=measure_type, flow_or_stock=spec["flow_or_stock"], facts=facts)

"""Dedicated API for the VIC DTF Budget Portfolio Outcomes workbook's
deferred `SOCE`/`Admin` sheets (VIC SOCE/Admin milestone - Task 5).

A new, separate router mirroring vic_bpo.py's design exactly (same
reasons: /v2/tree is compatibility_group-scoped and expects one
hierarchy per call; /v2/facts/search's jurisdiction-only filtering would
return unrelated VIC facts too) - but reading from its own semantics
file (config/measure-semantics/vic_bpo_soce_admin.yaml) rather than
vic_bpo.yaml, so the already-shipped vic_bpo.py router is never touched.

The frontend merges this router's /measures response with vic_bpo.py's
into the existing GFS/jurisdiction explorer's "VIC BPO" toggle (see
src/frontend/lib/api.ts's apiVicBpoSoceAdmin and app/explorers/gfs/
page.tsx) rather than adding a new dropdown/page - the 9 measures here
are a natural extension of the same family (same workbook, same
department, same FY2024-25 actual-vs-budget comparison shape) from the
user's point of view, even though they are served by a separate,
isolated backend endpoint and compatibility_group set.
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
        Path("/app/config/measure-semantics/vic_bpo_soce_admin.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "vic_bpo_soce_admin.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "vic_bpo_soce_admin.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()

router = APIRouter(prefix="/vic-bpo-soce-admin", tags=["v2-vic-bpo-soce-admin"])


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown VIC BPO SOCE/Admin measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


class VicBpoSoceAdminMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    flow_or_stock: str
    source_sheet: str
    compatibility_group: str
    accounting_basis: str
    unit: str


class VicBpoSoceAdminCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class VicBpoSoceAdminFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    financial_year: str
    period_end: str
    accounting_basis: str
    estimate_status: str
    compatibility_group: str
    citation: VicBpoSoceAdminCitation


class VicBpoSoceAdminSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[VicBpoSoceAdminFact]


@router.get("/measures", response_model=list[VicBpoSoceAdminMeasureInfo])
def vic_bpo_soce_admin_measures() -> list[VicBpoSoceAdminMeasureInfo]:
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        out = []
        for measure_type, spec in semantics["measures"].items():
            out.append(
                VicBpoSoceAdminMeasureInfo(
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


@router.get("/series", response_model=VicBpoSoceAdminSeriesResponse)
def vic_bpo_soce_admin_series(measure_type: str = Query(...)) -> VicBpoSoceAdminSeriesResponse:
    spec = _measure_spec(measure_type)
    conn = get_facts_connection()
    try:
        label = _measure_label(conn, measure_type)
        rows = conn.execute(
            "SELECT * FROM facts WHERE measure_type = ? ORDER BY estimate_status",
            (measure_type,),
        ).fetchall()
    finally:
        conn.close()

    facts = []
    for row in rows:
        locator_payload = json.loads(row["source_locator_json"] or "{}")
        facts.append(
            VicBpoSoceAdminFact(
                label=label,
                measure_type=measure_type,
                flow_or_stock=spec["flow_or_stock"],
                amount_aud=row["amount_aud"],
                financial_year=row["financial_year"],
                period_end=row["period_end"],
                accounting_basis=row["accounting_basis"],
                estimate_status=row["estimate_status"],
                compatibility_group=spec["compatibility_group"],
                citation=VicBpoSoceAdminCitation(
                    locator=locator_payload.get("locator", ""),
                    cached_copy_path=locator_payload.get("cached_copy_path"),
                ),
            )
        )
    return VicBpoSoceAdminSeriesResponse(
        measure_type=measure_type, flow_or_stock=spec["flow_or_stock"], facts=facts
    )

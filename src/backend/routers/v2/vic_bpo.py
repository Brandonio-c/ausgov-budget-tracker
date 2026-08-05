"""Dedicated API for the VIC DTF Budget Portfolio Outcomes family
(Task 5 of the adapter-repair-followup milestone, second family).

Small by design: 11 measures, one financial year (2024-25), two
estimate_status values (actual, budget) per measure - an actual-vs-
budget variance comparison, not a multi-year series like the sibling
vic_afs_* family. Wired into the existing GFS/jurisdiction explorer as
a fourth view (see ops/reports/vic-bpo-loader-*.md for why a whole new
dedicated page was not built) rather than getting its own page - but
still exposed through its own small, purpose-fit API, mirroring
vic_afs.py's design exactly (same reasons: /v2/tree is compatibility_
group-scoped and expects one hierarchy per call; /v2/facts/search's
jurisdiction-only filtering would return unrelated VIC facts too).
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
    mirrors compatibility.py's/mfs.py's/vic_afs.py's identical pattern."""
    candidates: list[Path] = [
        Path("/app/config/measure-semantics/vic_bpo.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "vic_bpo.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "vic_bpo.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()

router = APIRouter(prefix="/vic-bpo", tags=["v2-vic-bpo"])


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown VIC BPO measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


class VicBpoMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    flow_or_stock: str
    source_sheet: str
    compatibility_group: str
    accounting_basis: str
    unit: str


class VicBpoCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class VicBpoFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    financial_year: str
    period_end: str
    accounting_basis: str
    estimate_status: str
    compatibility_group: str
    citation: VicBpoCitation


class VicBpoSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[VicBpoFact]


@router.get("/measures", response_model=list[VicBpoMeasureInfo])
def vic_bpo_measures() -> list[VicBpoMeasureInfo]:
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        out = []
        for measure_type, spec in semantics["measures"].items():
            out.append(
                VicBpoMeasureInfo(
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


@router.get("/series", response_model=VicBpoSeriesResponse)
def vic_bpo_series(measure_type: str = Query(...)) -> VicBpoSeriesResponse:
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
            VicBpoFact(
                label=label,
                measure_type=measure_type,
                flow_or_stock=spec["flow_or_stock"],
                amount_aud=row["amount_aud"],
                financial_year=row["financial_year"],
                period_end=row["period_end"],
                accounting_basis=row["accounting_basis"],
                estimate_status=row["estimate_status"],
                compatibility_group=spec["compatibility_group"],
                citation=VicBpoCitation(
                    locator=locator_payload.get("locator", ""),
                    cached_copy_path=locator_payload.get("cached_copy_path"),
                ),
            )
        )
    return VicBpoSeriesResponse(measure_type=measure_type, flow_or_stock=spec["flow_or_stock"], facts=facts)

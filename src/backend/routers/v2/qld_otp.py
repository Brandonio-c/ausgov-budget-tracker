"""Dedicated QLD On-Time Payment (small business) compliance API (item 7.5's
explorer surface, plan item 6's "typed compliance product").

Deliberately NOT part of /v2/dashboard/* or the generic /v2/explorers/*
registry (config/explorers/families.yaml): that registry assumes one
shared compatibility_group per family (see explorers.py's
_family_where()), but this source has 8 distinct measure_types, each its
own dedicated compatibility_group and a different unit (count/AUD/days/
percent) - a shape closer to the dedicated MFS API (mfs.py) than to a
single-compatibility-group family. This router is the only way this
data is exposed.

Every endpoint enforces, not just documents, the loader's own
non-negotiable constraints (config/measure-semantics/qld_on_time_payments.yaml):
  - a quarter's fact is never summed across quarters into an annual
    figure;
  - a percentage/count measure is never compared or summed alongside a
    dollar measure as if interchangeable;
  - the agency identity returned is always the literal source-filename
    code, never expanded to a guessed department name.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...facts_db import get_facts_connection

_HERE = Path(__file__).resolve().parent
router = APIRouter(prefix="/qld-otp", tags=["v2-qld-otp"])

SOURCE_KEY = "qld_on_time_payment_reports"

_QUARTER_FROM_START_MONTH = {7: 1, 10: 2, 1: 3, 4: 4}


def _default_semantics_path() -> Path:
    """Mirrors mfs.py's _default_semantics_path() exactly - resolves in
    both a repo checkout and the Docker container's shallower on-disk
    depth."""
    candidates: list[Path] = [
        Path("/app/config/measure-semantics/qld_on_time_payments.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "qld_on_time_payments.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "qld_on_time_payments.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown QLD OTP measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


def _quarter_of(period_start: str) -> int:
    month = int(period_start.split("-")[1])
    return _QUARTER_FROM_START_MONTH.get(month, 0)


class QldOtpMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    unit: str
    accounting_basis: str
    dashboard_treatment: str


class QldOtpCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class QldOtpAgencyValue(BaseModel):
    agency_code: str
    value: float
    citation: QldOtpCitation


class QldOtpBreakdownResponse(BaseModel):
    measure_type: str
    label: str
    unit: str
    financial_year: str
    quarter: int
    agencies: list[QldOtpAgencyValue]
    total_agencies: int
    total_value: Optional[float] = None
    total_value_note: Optional[str] = None


class QldOtpAvailability(BaseModel):
    financial_year: str
    quarter: int


@router.get("/measures", response_model=list[QldOtpMeasureInfo])
def qld_otp_measures() -> list[QldOtpMeasureInfo]:
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        return [
            QldOtpMeasureInfo(
                measure_type=measure_type,
                label=_measure_label(conn, measure_type),
                economic_meaning=spec["economic_meaning"].strip(),
                unit=spec["unit"],
                accounting_basis=spec["accounting_basis"],
                dashboard_treatment=spec["dashboard_treatment"].strip(),
            )
            for measure_type, spec in semantics["measures"].items()
        ]
    finally:
        conn.close()


@router.get("/years", response_model=list[QldOtpAvailability])
def qld_otp_years(measure_type: str = Query(...)) -> list[QldOtpAvailability]:
    """Every (financial_year, quarter) pair this measure has real
    published facts for - never a fabricated full-year list."""
    _measure_spec(measure_type)
    conn = get_facts_connection()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT financial_year, period_start
            FROM facts
            WHERE measure_type = ?
            ORDER BY financial_year, period_start
            """,
            (measure_type,),
        ).fetchall()
    finally:
        conn.close()
    return [
        QldOtpAvailability(financial_year=r["financial_year"], quarter=_quarter_of(r["period_start"]))
        for r in rows
    ]


@router.get("/breakdown", response_model=QldOtpBreakdownResponse)
def qld_otp_breakdown(
    measure_type: str = Query(...),
    financial_year: str = Query(...),
    quarter: int = Query(..., ge=1, le=4),
) -> QldOtpBreakdownResponse:
    """Every agency's value for one measure/quarter - the primary
    explorer view. Sorted by value descending so the largest/most
    notable agencies surface first, matching the pattern already used by
    every other explorer this session (QGIP, contracts, grants)."""
    spec = _measure_spec(measure_type)
    label = None

    month = {1: "07", 2: "10", 3: "01", 4: "04"}[quarter]

    conn = get_facts_connection()
    try:
        label = _measure_label(conn, measure_type)
        root_total_allowed_row = conn.execute(
            "SELECT root_total_allowed FROM measure_definitions WHERE measure_type = ?", (measure_type,)
        ).fetchone()
        root_total_allowed = bool(root_total_allowed_row and root_total_allowed_row[0])
        rows = conn.execute(
            """
            SELECT f.amount_aud, f.quantity, f.source_locator_json, n.name AS agency_code
            FROM facts f
            JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
            JOIN nodes n ON n.id = fn.node_id
            WHERE f.measure_type = ?
              AND f.financial_year = ?
              AND strftime('%m', f.period_start) = ?
            ORDER BY n.name
            """,
            (measure_type, financial_year, month),
        ).fetchall()
    finally:
        conn.close()

    agencies = []
    for r in rows:
        value = r["amount_aud"] if r["amount_aud"] is not None else r["quantity"]
        if value is None:
            continue
        locator_payload = json.loads(r["source_locator_json"] or "{}")
        agencies.append(
            QldOtpAgencyValue(
                agency_code=r["agency_code"],
                value=value,
                citation=QldOtpCitation(
                    locator=locator_payload.get("locator", ""),
                    cached_copy_path=locator_payload.get("cached_copy_path"),
                ),
            )
        )
    agencies.sort(key=lambda a: a.value, reverse=True)

    total_value = sum(a.value for a in agencies) if root_total_allowed else None
    total_value_note = (
        None
        if root_total_allowed
        else "This measure is a per-agency mean/percentage - summing it across agencies would not be meaningful, so no total is reported."
    )

    return QldOtpBreakdownResponse(
        measure_type=measure_type,
        label=label,
        unit=spec["unit"],
        financial_year=financial_year,
        quarter=quarter,
        agencies=agencies,
        total_agencies=len(agencies),
        total_value=total_value,
        total_value_note=total_value_note,
    )

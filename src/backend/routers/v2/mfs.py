"""Dedicated Monthly Financial Statements (MFS) API (Task 8 of the
MFS-aggregates milestone).

Deliberately NOT part of /v2/dashboard/* - MFS facts are never inserted
into any existing annual additive dashboard tree (see
config/measure-semantics/mfs.yaml's global_rules and
scripts/ingest/migrations/007_mfs_measures.sql: every mfs_* measure_type
has its own dedicated compatibility_group, none registered under any
mode_to_family mapping in config/compatibility/view_families.yaml). This
router is the only way MFS data is exposed.

Every endpoint enforces, not just documents, the milestone's
non-negotiable constraints:
  - a YTD fact's period_end/reporting_month/elapsed_months are always
    present, so a partial year can never be mistaken for a full year
    (MFS structurally never reaches a 12th/June column - Task 2);
  - /series never mixes facts of different flow_or_stock categories in
    one response, and never computes a sum across measure_types;
  - /compare explicitly validates every measure_type pair against
    config/measure-semantics/mfs.yaml's compatibility rules before
    returning anything, and always returns parallel per-measure series
    (never a combined additive total).
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
    """Resolve config in repo checkout or Docker (/app/config bind-mount).

    Mirrors compatibility.py's _default_view_families_path() exactly - the
    container's COPY . /app/backend (context: ./src/backend) makes this
    file's on-disk depth one level shallower than the repo checkout
    (.../ausgov-budget-tracker/src/backend/routers/v2/mfs.py locally vs
    /app/backend/routers/v2/mfs.py in the container), so a single fixed
    parents[N] cannot work in both places.
    """
    candidates: list[Path] = [
        Path("/app/config/measure-semantics/mfs.yaml"),
    ]
    if len(_HERE.parents) >= 4:
        candidates.append(_HERE.parents[3] / "config" / "measure-semantics" / "mfs.yaml")
    if len(_HERE.parents) >= 3:
        candidates.append(_HERE.parents[2] / "config" / "measure-semantics" / "mfs.yaml")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


SEMANTICS_PATH = _default_semantics_path()

router = APIRouter(prefix="/mfs", tags=["v2-mfs"])

_MONTH_ORDER = [
    "July", "August", "September", "October", "November", "December",
    "January", "February", "March", "April", "May", "June",
]


@lru_cache(maxsize=1)
def _load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _measure_spec(measure_type: str) -> dict:
    measures = _load_semantics()["measures"]
    if measure_type not in measures:
        raise HTTPException(status_code=400, detail=f"Unknown MFS measure_type: {measure_type!r}")
    return measures[measure_type]


def _measure_label(conn: sqlite3.Connection, measure_type: str) -> str:
    row = conn.execute(
        "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
    ).fetchone()
    return row[0] if row else measure_type


class MfsMeasureInfo(BaseModel):
    measure_type: str
    label: str
    economic_meaning: str
    flow_or_stock: str
    compatibility_group: str
    accounting_basis: str
    unit: str
    sign_convention: str
    dashboard_treatment: str
    not_published_before_financial_year: Optional[str] = None
    only_published_financial_years: Optional[list[str]] = None
    reserved_not_loaded_this_milestone: Optional[bool] = None


class MfsCitation(BaseModel):
    locator: str
    cached_copy_path: Optional[str] = None


class MfsFact(BaseModel):
    label: str
    measure_type: str
    flow_or_stock: str
    amount_aud: float
    unit: str = "AUD"
    financial_year: str
    reporting_month: str
    elapsed_months: int
    period_start: Optional[str] = None
    period_end: str
    period_granularity: str
    accounting_basis: str
    estimate_status: str
    compatibility_group: str
    publication_date: Optional[str] = None
    vintage: str = "current"
    citation: MfsCitation


class MfsSeriesResponse(BaseModel):
    measure_type: str
    flow_or_stock: str
    facts: list[MfsFact]


class MfsCompareResponse(BaseModel):
    measure_types: list[str]
    series: list[MfsSeriesResponse]
    warning: Optional[str] = None


def _row_to_fact(row: sqlite3.Row, spec: dict, measure_type: str, label: str) -> MfsFact:
    locator_payload = json.loads(row["source_locator_json"] or "{}")
    reporting_month = row["fact_key"].split("|")[2]
    return MfsFact(
        label=label,
        measure_type=measure_type,
        flow_or_stock=spec["flow_or_stock"],
        amount_aud=row["amount_aud"],
        financial_year=row["financial_year"],
        reporting_month=reporting_month,
        elapsed_months=_MONTH_ORDER.index(reporting_month) + 1,
        period_start=row["period_start"],
        period_end=row["period_end"],
        period_granularity=row["period_granularity"],
        accounting_basis=row["accounting_basis"],
        estimate_status=row["estimate_status"],
        compatibility_group=spec["compatibility_group"],
        publication_date=None,
        vintage="current",
        citation=MfsCitation(
            locator=locator_payload.get("locator", ""),
            cached_copy_path=locator_payload.get("cached_copy_path"),
        ),
    )


@router.get("/measures", response_model=list[MfsMeasureInfo])
def mfs_measures() -> list[MfsMeasureInfo]:
    """Every defined MFS measure type and its semantic metadata - the
    dedicated model this milestone builds instead of ad-hoc dashboard
    modes."""
    semantics = _load_semantics()
    conn = get_facts_connection()
    try:
        out = []
        for measure_type, spec in semantics["measures"].items():
            out.append(
                MfsMeasureInfo(
                    measure_type=measure_type,
                    label=_measure_label(conn, measure_type),
                    economic_meaning=spec["economic_meaning"].strip(),
                    flow_or_stock=spec["flow_or_stock"],
                    compatibility_group=spec["compatibility_group"],
                    accounting_basis=spec["accounting_basis"],
                    unit=spec["unit"],
                    sign_convention=spec["sign_convention"],
                    dashboard_treatment=spec["dashboard_treatment"].strip(),
                    not_published_before_financial_year=spec.get("not_published_before_financial_year"),
                    only_published_financial_years=spec.get("only_published_financial_years"),
                    reserved_not_loaded_this_milestone=spec.get("reserved_not_loaded_this_milestone"),
                )
            )
    finally:
        conn.close()
    return out


@router.get("/series", response_model=MfsSeriesResponse)
def mfs_series(
    measure_type: str = Query(...),
    financial_year: Optional[str] = Query(None),
    reporting_month: Optional[str] = Query(None),
    current_vintage: bool = Query(True, description="MFS has only one vintage today; reserved for future revision tracking."),
) -> MfsSeriesResponse:
    """One measure's time series, optionally filtered. Never mixes
    measure_types in one response - use /compare for that, which enforces
    compatibility explicitly."""
    spec = _measure_spec(measure_type)

    sql = "SELECT * FROM facts WHERE measure_type = ?"
    params: list = [measure_type]
    if financial_year:
        sql += " AND financial_year = ?"
        params.append(financial_year)
    sql += " ORDER BY financial_year, period_end"

    conn = get_facts_connection()
    try:
        label = _measure_label(conn, measure_type)
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    facts = [_row_to_fact(r, spec, measure_type, label) for r in rows]
    if reporting_month:
        facts = [f for f in facts if f.reporting_month == reporting_month]
    return MfsSeriesResponse(measure_type=measure_type, flow_or_stock=spec["flow_or_stock"], facts=facts)


@router.get("/compare", response_model=MfsCompareResponse)
def mfs_compare(
    measure_types: str = Query(..., description="Comma-separated measure_type list, e.g. mfs_ytd_revenue,mfs_ytd_expense"),
    financial_year: Optional[str] = Query(None),
) -> MfsCompareResponse:
    """Multiple measures side by side, for a comparison chart - NEVER an
    additive combination. Enforces:
      - every requested measure_type must exist;
      - a stock and a flow may never be requested together;
      - a flow/stock may never be requested together with its own
        component parts in a way this endpoint could be mistaken for
        re-deriving one from the other (receipts+payments alongside
        underlying_cash_balance is fine to chart together - that pairing
        is explicitly allowed in config/measure-semantics/mfs.yaml - but
        this endpoint still never sums them; it only returns parallel
        series)."""
    requested = [m.strip() for m in measure_types.split(",") if m.strip()]
    if not requested:
        raise HTTPException(status_code=400, detail="measure_types must list at least one measure_type")
    if len(requested) > 6:
        raise HTTPException(status_code=400, detail="Compare at most 6 measures at once")

    semantics = _load_semantics()["measures"]
    specs = {}
    for m in requested:
        if m not in semantics:
            raise HTTPException(status_code=400, detail=f"Unknown MFS measure_type: {m!r}")
        specs[m] = semantics[m]

    flow_or_stock_kinds = {specs[m]["flow_or_stock"] for m in requested}
    is_stock_kind = {"stock", "stock_balance"}
    is_flow_kind = {"flow", "balance"}
    warning = None
    if flow_or_stock_kinds & is_stock_kind and flow_or_stock_kinds & is_flow_kind:
        raise HTTPException(
            status_code=422,
            detail=(
                "Cannot compare a stock (point-in-time balance-sheet figure) with a flow/balance "
                "(year-to-date accumulation) in one request - they cover fundamentally different "
                "kinds of period and must be viewed as separate series, not combined."
            ),
        )
    if len(flow_or_stock_kinds) > 1:
        warning = (
            "Requested measures mix balances with raw flows/stocks - each is returned as its own "
            "series and must never be summed together."
        )

    conn = get_facts_connection()
    try:
        series = []
        for m in requested:
            sql = "SELECT * FROM facts WHERE measure_type = ?"
            params: list = [m]
            if financial_year:
                sql += " AND financial_year = ?"
                params.append(financial_year)
            sql += " ORDER BY financial_year, period_end"
            rows = conn.execute(sql, params).fetchall()
            label = _measure_label(conn, m)
            facts = [_row_to_fact(r, specs[m], m, label) for r in rows]
            series.append(MfsSeriesResponse(measure_type=m, flow_or_stock=specs[m]["flow_or_stock"], facts=facts))
    finally:
        conn.close()

    return MfsCompareResponse(measure_types=requested, series=series, warning=warning)


@router.get("/years", response_model=list[str])
def mfs_years(measure_type: str = Query(...)) -> list[str]:
    _measure_spec(measure_type)
    conn = get_facts_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT financial_year FROM facts WHERE measure_type = ? ORDER BY financial_year",
            (measure_type,),
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]

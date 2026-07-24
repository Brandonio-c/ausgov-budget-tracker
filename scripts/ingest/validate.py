#!/usr/bin/env python3
"""Validation Gates 1–6 for ingest rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

FY_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass
class GateResult:
    gate: int
    name: str
    ok: bool
    message: str = ""


@dataclass
class RowDecision:
    row: dict[str, Any]
    publishable: bool
    quarantine_reason: str | None = None
    gate_failures: list[GateResult] = field(default_factory=list)


REQUIRED_LOGICAL = ("financial_year", "amount_aud", "locator")


def gate1_schema(mapping: dict[str, Any], row: dict[str, Any]) -> GateResult:
    missing = [c for c in REQUIRED_LOGICAL if c not in row]
    if missing:
        return GateResult(1, "schema", False, f"missing columns: {missing}")
    return GateResult(1, "schema", True)


def gate2_types(row: dict[str, Any]) -> GateResult:
    amount = row.get("amount_aud")
    try:
        if amount is None:
            return GateResult(2, "types", False, "amount_aud is null")
        float(amount)
    except (TypeError, ValueError):
        return GateResult(2, "types", False, f"amount_aud not numeric: {amount!r}")
    return GateResult(2, "types", True)


def gate3_period(row: dict[str, Any]) -> GateResult:
    fy = row.get("financial_year")
    if fy is None or not FY_RE.match(str(fy).strip()):
        return GateResult(3, "period", False, f"bad financial_year: {fy!r}")
    return GateResult(3, "period", True)


def gate4_node(row: dict[str, Any]) -> GateResult:
    name = row.get("node_name") or row.get("category")
    if name is None or not str(name).strip():
        return GateResult(4, "node", False, "missing node_name/category")
    return GateResult(4, "node", True)


def gate5_measure(mapping: dict[str, Any]) -> GateResult:
    for key in ("measure_type", "accounting_basis", "estimate_status"):
        if not mapping.get(key):
            return GateResult(5, "measure", False, f"mapping missing {key}")
    return GateResult(5, "measure", True)


def gate6_attribution(row: dict[str, Any]) -> GateResult:
    missing = []
    if not row.get("landing_url"):
        missing.append("landing_url")
    if not row.get("original_resource_url"):
        missing.append("original_resource_url")
    if not row.get("_cached_copy_path"):
        missing.append("cached_copy_path")
    locator = row.get("locator")
    if locator is None or not str(locator).strip():
        missing.append("locator")
    if not row.get("_sha256"):
        missing.append("sha256")
    if not row.get("_retrieved_at"):
        missing.append("retrieved_at")
    if missing:
        return GateResult(6, "attribution", False, f"incomplete citation: {missing}")
    return GateResult(6, "attribution", True)


def validate_row(mapping: dict[str, Any], row: dict[str, Any]) -> RowDecision:
    failures: list[GateResult] = []
    # Gate 5 is mapping-level; still evaluate per row for consistency
    for gate_fn in (
        lambda: gate1_schema(mapping, row),
        lambda: gate2_types(row),
        lambda: gate3_period(row),
        lambda: gate4_node(row),
        lambda: gate5_measure(mapping),
    ):
        result = gate_fn()
        if not result.ok:
            failures.append(result)

    g6 = gate6_attribution(row)
    if not g6.ok:
        failures.append(g6)

    # Hard reject (non-publish, non-quarantine of soft type) for gates 1-5
    hard = [f for f in failures if f.gate < 6]
    if hard:
        reason = "; ".join(f"Gate {f.gate} {f.name}: {f.message}" for f in hard)
        if g6.ok is False:
            reason += "; " + f"Gate 6 attribution: {g6.message}"
        return RowDecision(row=row, publishable=False, quarantine_reason=reason, gate_failures=failures)

    if not g6.ok:
        return RowDecision(
            row=row,
            publishable=False,
            quarantine_reason=f"Gate 6 attribution: {g6.message}",
            gate_failures=failures,
        )

    return RowDecision(row=row, publishable=True, quarantine_reason=None, gate_failures=[])


def validate_batch(mapping: dict[str, Any], rows: list[dict[str, Any]]) -> list[RowDecision]:
    return [validate_row(mapping, r) for r in rows]

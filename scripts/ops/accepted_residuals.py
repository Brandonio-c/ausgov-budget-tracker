#!/usr/bin/env python3
"""Declarative accepted-residual matching for additive-reconciliation
findings (Task 2 of the database-hygiene-and-CI-hardening milestone).

Loads config/audit/accepted_reconciliation_residuals.yaml and matches a
live additive_reconciliation_failures candidate against it by exact
(source_key, node_path, financial_year, measure_type, estimate_status)
identity, then checks the live variance does not exceed the entry's
declared expected_max_variance_pct. Every field must match exactly - a
changed year, source, label, amount, or a materially larger variance
never matches, so a residual entry can never silently widen to cover a
different or worse case than the one it was written for.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "audit" / "accepted_reconciliation_residuals.yaml"

REQUIRED_FIELDS = (
    "source_key",
    "node_path",
    "financial_year",
    "measure_type",
    "estimate_status",
    "expected_max_variance_pct",
    "actual_verified_variance_pct",
    "reason",
    "source_locator",
    "review_date",
)


@dataclass(frozen=True)
class ResidualEntry:
    source_key: str
    node_path: str
    financial_year: str
    measure_type: str
    estimate_status: str
    expected_max_variance_pct: float
    actual_verified_variance_pct: float
    reason: str
    source_locator: str
    review_date: str


class InvalidResidualConfig(ValueError):
    pass


def load_accepted_residuals(path: Path = DEFAULT_CONFIG_PATH) -> list[ResidualEntry]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_entries = data.get("residuals") or []
    entries: list[ResidualEntry] = []
    for i, raw in enumerate(raw_entries):
        missing = [f for f in REQUIRED_FIELDS if f not in raw]
        if missing:
            raise InvalidResidualConfig(
                f"residuals[{i}] missing required fields: {missing}"
            )
        entries.append(
            ResidualEntry(
                source_key=str(raw["source_key"]),
                node_path=str(raw["node_path"]),
                financial_year=str(raw["financial_year"]),
                measure_type=str(raw["measure_type"]),
                estimate_status=str(raw["estimate_status"]),
                expected_max_variance_pct=float(raw["expected_max_variance_pct"]),
                actual_verified_variance_pct=float(raw["actual_verified_variance_pct"]),
                reason=str(raw["reason"]),
                source_locator=str(raw["source_locator"]),
                review_date=str(raw["review_date"]),
            )
        )
    return entries


def match_residual(
    entries: list[ResidualEntry],
    *,
    source_key: str,
    node_path: str,
    financial_year: str,
    measure_type: str,
    estimate_status: str,
    variance_pct: float,
) -> ResidualEntry | None:
    """Return the matching entry, or None if no entry matches. variance_pct
    is (child_amount / parent_amount) - 1.0, i.e. 0.0052 for 100.52%."""
    for entry in entries:
        if (
            entry.source_key == source_key
            and entry.node_path == node_path
            and entry.financial_year == financial_year
            and entry.measure_type == measure_type
            and entry.estimate_status == estimate_status
            and variance_pct <= entry.expected_max_variance_pct + 1e-9
        ):
            return entry
    return None


def validate_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Structural validity check used by scripts/ops/task9_sql_integrity_checks.py:
    the file parses, every entry has all required fields, and variance
    fields are numeric and non-negative."""
    errors: list[str] = []
    try:
        entries = load_accepted_residuals(path)
    except InvalidResidualConfig as exc:
        return {"valid": False, "errors": [str(exc)], "entry_count": 0}
    for i, entry in enumerate(entries):
        if entry.expected_max_variance_pct < 0:
            errors.append(f"residuals[{i}] expected_max_variance_pct must be >= 0")
        if entry.actual_verified_variance_pct < 0:
            errors.append(f"residuals[{i}] actual_verified_variance_pct must be >= 0")
        if entry.actual_verified_variance_pct > entry.expected_max_variance_pct + 1e-9:
            errors.append(
                f"residuals[{i}] actual_verified_variance_pct exceeds its own "
                f"expected_max_variance_pct - the entry would not match its own evidence"
            )
    return {"valid": not errors, "errors": errors, "entry_count": len(entries)}

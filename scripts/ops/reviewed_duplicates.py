#!/usr/bin/env python3
"""Declarative reviewed-duplicate-group matching for
scripts/ops/task9_sql_integrity_checks.py's duplicate_facts() candidates
(Task 4/6 of the database-hygiene-and-CI-hardening milestone).

Loads config/audit/reviewed_duplicate_facts.yaml and matches a live
duplicate_facts() candidate group against it by exact (source_key,
node_path, financial_year, measure_type, estimate_status, amount_aud)
identity. Every field must match exactly - a changed year, source, node
path, measure type, estimate status, or amount always falls through to a
hard failure, so a reviewed entry can never silently widen to cover a new
or different duplicate-look-alike group.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "audit" / "reviewed_duplicate_facts.yaml"

REQUIRED_FIELDS = (
    "source_key",
    "node_path",
    "financial_year",
    "measure_type",
    "estimate_status",
    "amount_aud",
    "classification",
    "reason",
    "evidence_report",
    "review_date",
)

VALID_CLASSIFICATIONS = (
    "query_false_positive",
    "independent_authoritative_sources",
    "different_accounting_meaning",
    "different_provenance",
    "superseded_record",
)


@dataclass(frozen=True)
class ReviewedDuplicateGroup:
    source_key: str
    node_path: str
    financial_year: str
    measure_type: str
    estimate_status: str
    amount_aud: float
    classification: str
    reason: str
    evidence_report: str
    review_date: str


class InvalidReviewedDuplicateConfig(ValueError):
    pass


def load_reviewed_duplicates(
    path: Path = DEFAULT_CONFIG_PATH,
) -> list[ReviewedDuplicateGroup]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_entries = data.get("reviewed_duplicate_facts") or []
    entries: list[ReviewedDuplicateGroup] = []
    for i, raw in enumerate(raw_entries):
        missing = [f for f in REQUIRED_FIELDS if f not in raw]
        if missing:
            raise InvalidReviewedDuplicateConfig(
                f"reviewed_duplicate_facts[{i}] missing required fields: {missing}"
            )
        if raw["classification"] not in VALID_CLASSIFICATIONS:
            raise InvalidReviewedDuplicateConfig(
                f"reviewed_duplicate_facts[{i}] has unknown classification "
                f"{raw['classification']!r} (must be one of {VALID_CLASSIFICATIONS})"
            )
        entries.append(
            ReviewedDuplicateGroup(
                source_key=str(raw["source_key"]),
                node_path=str(raw["node_path"]),
                financial_year=str(raw["financial_year"]),
                measure_type=str(raw["measure_type"]),
                estimate_status=str(raw["estimate_status"]),
                amount_aud=float(raw["amount_aud"]),
                classification=str(raw["classification"]),
                reason=str(raw["reason"]),
                evidence_report=str(raw["evidence_report"]),
                review_date=str(raw["review_date"]),
            )
        )
    return entries


def match_reviewed_duplicate(
    entries: list[ReviewedDuplicateGroup],
    *,
    source_key: str,
    node_path: str,
    financial_year: str,
    measure_type: str,
    estimate_status: str,
    amount_aud: float,
) -> ReviewedDuplicateGroup | None:
    for entry in entries:
        if (
            entry.source_key == source_key
            and entry.node_path == node_path
            and entry.financial_year == financial_year
            and entry.measure_type == measure_type
            and entry.estimate_status == estimate_status
            and abs(entry.amount_aud - amount_aud) < 1e-6
        ):
            return entry
    return None


def validate_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Structural validity check used by scripts/ops/task9_sql_integrity_checks.py:
    the file parses, every entry has all required fields, and every
    classification is a recognized non-true-duplicate outcome (a
    genuinely confirmed true duplicate must never be "reviewed" into a
    permanent pass - it must be deleted, not registered here)."""
    try:
        entries = load_reviewed_duplicates(path)
    except InvalidReviewedDuplicateConfig as exc:
        return {"valid": False, "errors": [str(exc)], "entry_count": 0}
    return {"valid": True, "errors": [], "entry_count": len(entries)}

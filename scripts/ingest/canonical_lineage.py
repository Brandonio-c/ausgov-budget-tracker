"""Validated single-valued canonical dataset ownership for published facts."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LINEAGE = REPO_ROOT / "config" / "lineage" / "canonical_datasets.yaml"


@dataclass(frozen=True)
class CanonicalLineage:
    source_owners: dict[str, str]
    dataset_ids: tuple[str, ...]


@lru_cache(maxsize=4)
def load_canonical_lineage(path: str | None = None) -> CanonicalLineage:
    lineage_path = Path(path) if path else DEFAULT_LINEAGE
    data = yaml.safe_load(lineage_path.read_text(encoding="utf-8")) or {}
    if int(data.get("version", 0)) != 1:
        raise ValueError(f"Unsupported canonical lineage version in {lineage_path}")
    dataset_ids: list[str] = []
    source_owners: dict[str, str] = {}
    for raw in data.get("datasets") or []:
        dataset_id = str(raw.get("canonical_dataset_id") or "").strip()
        if not dataset_id:
            raise ValueError("Canonical dataset ID must not be empty")
        if dataset_id in dataset_ids:
            raise ValueError(f"Duplicate canonical dataset ID: {dataset_id}")
        dataset_ids.append(dataset_id)
        for raw_source_key in raw.get("fact_source_keys") or []:
            source_key = str(raw_source_key).strip()
            existing = source_owners.get(source_key)
            if existing and existing != dataset_id:
                raise ValueError(
                    f"Fact source {source_key!r} belongs to multiple canonical "
                    f"datasets: {existing!r}, {dataset_id!r}"
                )
            source_owners[source_key] = dataset_id
    return CanonicalLineage(
        source_owners=source_owners, dataset_ids=tuple(dataset_ids)
    )


def canonical_dataset_for_source(
    source_key: str, lineage_path: str | None = None
) -> str | None:
    return load_canonical_lineage(lineage_path).source_owners.get(source_key)


def audit_assignments(
    conn: sqlite3.Connection, lineage: CanonicalLineage
) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT d.source_key, f.canonical_dataset_id, COUNT(*)
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        GROUP BY d.source_key, f.canonical_dataset_id
        """
    ).fetchall()
    expected_counts = {dataset_id: 0 for dataset_id in lineage.dataset_ids}
    assigned_counts = {dataset_id: 0 for dataset_id in lineage.dataset_ids}
    mismatched = 0
    noncanonical_assigned = 0
    total = 0
    for source_key, assigned, count in rows:
        count = int(count)
        total += count
        expected = lineage.source_owners.get(str(source_key))
        if expected:
            expected_counts[expected] += count
        if assigned in assigned_counts:
            assigned_counts[str(assigned)] += count
        if assigned != expected:
            mismatched += count
        if expected is None and assigned is not None:
            noncanonical_assigned += count
    return {
        "total_facts": total,
        "expected_canonical_facts": sum(expected_counts.values()),
        "assigned_canonical_facts": sum(assigned_counts.values()),
        "mismatched_facts": mismatched,
        "noncanonical_assigned_facts": noncanonical_assigned,
        "expected_by_dataset": expected_counts,
        "assigned_by_dataset": assigned_counts,
    }


def backfill_assignments(
    conn: sqlite3.Connection, lineage: CanonicalLineage
) -> dict[str, Any]:
    before = audit_assignments(conn, lineage)
    changes_before = conn.total_changes
    source_keys = tuple(lineage.source_owners)
    if source_keys:
        placeholders = ", ".join("?" for _ in source_keys)
        conn.execute(
            f"""
            UPDATE facts
            SET canonical_dataset_id = NULL
            WHERE canonical_dataset_id IS NOT NULL
              AND source_document_id IN (
                  SELECT id FROM source_documents
                  WHERE source_key NOT IN ({placeholders})
              )
            """,
            source_keys,
        )
    for source_key, dataset_id in lineage.source_owners.items():
        conn.execute(
            """
            UPDATE facts
            SET canonical_dataset_id = ?
            WHERE source_document_id IN (
                SELECT id FROM source_documents WHERE source_key = ?
            )
              AND canonical_dataset_id IS NOT ?
            """,
            (dataset_id, source_key, dataset_id),
        )
    after = audit_assignments(conn, lineage)
    return {
        "rows_changed": conn.total_changes - changes_before,
        "before": before,
        "after": after,
    }

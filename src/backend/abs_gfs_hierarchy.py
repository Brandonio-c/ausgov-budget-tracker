"""ABS GFS Table_4 purpose hierarchy — loaded from breakdown pack config."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Fallback when config/breakdowns/abs_gfs_table4.yaml is not mounted (Docker).
_FALLBACK_PACK: dict[str, Any] = {
    "id": "abs_gfs_table4",
    "compatibility_group": "actual_expense",
    "edge_kind": "same_group",
    "source_key_prefix": "abs_gfs_",
    "child_to_parent": {
        "Public debt transactions": "General public services",
        "Other general public services": "General public services",
        "Medical products, appliances and equipment": "Health",
        "Outpatient services": "Health",
        "Hospital services": "Health",
        "Community health services": "Health",
        "Public health services": "Health",
        "Other health": "Health",
        "Pre-primary, primary and secondary education": "Education",
        "Tertiary education": "Education",
        "Other education": "Education",
    },
    "total_to_parent": {
        "Total general public services": "General public services",
        "Total health": "Health",
        "Total education": "Education",
    },
    "skip": ["Total Expenses", "Total expenses"],
}


def _candidate_pack_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        # Repo checkout: src/backend → repo/config/...
        here.parents[2] / "config" / "breakdowns" / "abs_gfs_table4.yaml",
        # Docker: /app/backend → /app/config/...
        Path("/app/config/breakdowns/abs_gfs_table4.yaml"),
        here.parent / "config" / "breakdowns" / "abs_gfs_table4.yaml",
    ]


@lru_cache(maxsize=1)
def _load_pack() -> dict[str, Any]:
    for path in _candidate_pack_paths():
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(_FALLBACK_PACK)


def _child_to_parent() -> dict[str, str]:
    return dict(_load_pack().get("child_to_parent") or {})


def _total_to_parent() -> dict[str, str]:
    return dict(_load_pack().get("total_to_parent") or {})


def _skip() -> frozenset[str]:
    return frozenset(_load_pack().get("skip") or [])


def abs_gfs_hierarchy_path(category: str) -> list[str] | None:
    """Return path parts under jurisdiction for an ABS GFS purpose label."""
    name = (category or "").strip()
    if not name or name in _skip():
        return None
    totals = _total_to_parent()
    if name in totals:
        return [totals[name]]
    parent = _child_to_parent().get(name)
    if parent:
        return [parent, name]
    return [name]


def is_abs_gfs_source(source_key: str | None) -> bool:
    prefix = _load_pack().get("source_key_prefix") or "abs_gfs_"
    return bool(source_key) and source_key.startswith(prefix)


def abs_gfs_breakdown_note(source_key: str | None, category: str | None) -> str | None:
    """Explain when a major ABS purpose has no same-group children in Table_4."""
    if not is_abs_gfs_source(source_key):
        return None
    name = (category or "").strip()
    children = _child_to_parent()
    totals = _total_to_parent()
    if not name or name in children:
        return None
    if name in totals or name in totals.values():
        return None
    if name in children.values():
        return None
    return (
        f"ABS GFS Table 4 publishes “{name}” as a single aggregate line — "
        "there are no sub-function rows in this workbook. "
        "Where a Statement 6 related breakdown exists, drill the chart segment "
        "to open that provenance-labelled breakdown."
    )

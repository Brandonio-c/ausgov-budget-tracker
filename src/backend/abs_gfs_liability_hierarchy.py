"""ABS GFS Table_3 liability hierarchy — flat components under jurisdiction."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_FALLBACK_PACK: dict[str, Any] = {
    "id": "abs_gfs_table3_liabilities",
    "compatibility_group": "gfs_liability",
    "source_key_suffix": "_liabilities",
    "source_key_prefix": "abs_gfs_",
    "skip": ["Total Liabilities", "Total liabilities"],
}


def _candidate_pack_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "config" / "breakdowns" / "abs_gfs_table3_liabilities.yaml",
        Path("/app/config/breakdowns/abs_gfs_table3_liabilities.yaml"),
        here.parent / "config" / "breakdowns" / "abs_gfs_table3_liabilities.yaml",
    ]


@lru_cache(maxsize=1)
def _load_pack() -> dict[str, Any]:
    for path in _candidate_pack_paths():
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(_FALLBACK_PACK)


def is_abs_gfs_liability_source(source_key: str | None) -> bool:
    if not source_key:
        return False
    pack = _load_pack()
    prefix = pack.get("source_key_prefix") or "abs_gfs_"
    suffix = pack.get("source_key_suffix") or "_liabilities"
    return source_key.startswith(prefix) and source_key.endswith(suffix)


def abs_gfs_liability_path(category: str) -> list[str] | None:
    """Path under jurisdiction for a liability line (omit totals)."""
    name = (category or "").strip()
    if not name or name in frozenset(_load_pack().get("skip") or []):
        return None
    return [name]

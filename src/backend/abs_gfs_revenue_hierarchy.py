"""ABS GFS Table_1 revenue hierarchy — flat components under jurisdiction."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_FALLBACK: dict[str, Any] = {
    "source_key_prefix": "abs_gfs_",
    "source_key_suffix": "_revenue",
    "skip": ["Total GFS revenue", "Total gfs revenue"],
}


def _paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "config" / "breakdowns" / "abs_gfs_table1_revenue.yaml",
        Path("/app/config/breakdowns/abs_gfs_table1_revenue.yaml"),
    ]


@lru_cache(maxsize=1)
def _pack() -> dict[str, Any]:
    for path in _paths():
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(_FALLBACK)


def is_abs_gfs_revenue_source(source_key: str | None) -> bool:
    if not source_key:
        return False
    pack = _pack()
    return source_key.startswith(pack.get("source_key_prefix") or "abs_gfs_") and source_key.endswith(
        pack.get("source_key_suffix") or "_revenue"
    )


def abs_gfs_revenue_path(category: str) -> list[str] | None:
    name = (category or "").strip()
    if not name or name in frozenset(_pack().get("skip") or []):
        return None
    return [name]

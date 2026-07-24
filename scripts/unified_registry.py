"""Load the unified procurement registry and Phase 1-compatible views."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "config" / "procurement_sources.yaml"


def load_registry() -> dict[str, Any]:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def all_sources() -> list[dict[str, Any]]:
    return list(load_registry().get("sources") or [])


def phase1_sources() -> list[dict[str, Any]]:
    """Shape expected by legacy fetch_sources / build_processed_db."""
    out = []
    for s in all_sources():
        if not s.get("phase1_parser"):
            continue
        out.append(
            {
                "id": s["id"],
                "level": s.get("phase1_level") or s.get("government_level"),
                "jurisdiction": s["jurisdiction"],
                "title": s["title"],
                "ckan_package_id": s["ckan_package_id"],
                **(
                    {"resource_id": s["resource_id"]}
                    if s.get("resource_id")
                    else {"resource_match": s.get("resource_match")}
                ),
                "parser": s["phase1_parser"],
                "raw_filename": s["phase1_raw_filename"],
            }
        )
    return out

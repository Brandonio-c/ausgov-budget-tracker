"""Declarative registry of specialist explorer families (plan item 6.1)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent


def _default_path() -> Path:
    candidates = [
        Path("/app/config/explorers/families.yaml"),
        _HERE.parents[1] / "config" / "explorers" / "families.yaml",
        _HERE.parent / "config" / "explorers" / "families.yaml",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


@dataclass(frozen=True)
class ExplorerFamily:
    id: str
    label: str
    compatibility_group: str
    accounting_basis: str
    estimate_statuses: tuple[str, ...]
    default_estimate_status: str
    source_key: str | None
    additive_note: str


@dataclass(frozen=True)
class ExplorerRegistry:
    families: tuple[ExplorerFamily, ...]

    def family_by_id(self, family_id: str) -> ExplorerFamily | None:
        for family in self.families:
            if family.id == family_id:
                return family
        return None


def _family(raw: dict) -> ExplorerFamily:
    family_id = str(raw["id"])
    estimate_statuses = tuple(raw.get("estimate_statuses") or ())
    if not estimate_statuses:
        raise ValueError(f"explorer family {family_id}: estimate_statuses must not be empty")
    default_estimate_status = str(raw["default_estimate_status"])
    if default_estimate_status not in estimate_statuses:
        raise ValueError(
            f"explorer family {family_id}: default_estimate_status "
            f"{default_estimate_status!r} not in estimate_statuses {estimate_statuses!r}"
        )
    for field in ("compatibility_group", "accounting_basis"):
        if not raw.get(field):
            raise ValueError(f"explorer family {family_id}: {field} is required")
    return ExplorerFamily(
        id=family_id,
        label=str(raw["label"]),
        compatibility_group=str(raw["compatibility_group"]),
        accounting_basis=str(raw["accounting_basis"]),
        estimate_statuses=estimate_statuses,
        default_estimate_status=default_estimate_status,
        source_key=raw.get("source_key") or None,
        additive_note=str(raw.get("additive_note") or "").strip(),
    )


@lru_cache(maxsize=4)
def load_explorer_registry(path: str | None = None) -> ExplorerRegistry:
    config_path = Path(path) if path else _default_path()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if int(data.get("version", 0)) != 1:
        raise ValueError(f"unsupported explorer registry version in {config_path}")
    families = tuple(_family(dict(raw)) for raw in data.get("families") or [])
    ids = [family.id for family in families]
    if len(ids) != len(set(ids)):
        raise ValueError("explorer family IDs must be unique")
    return ExplorerRegistry(families=families)

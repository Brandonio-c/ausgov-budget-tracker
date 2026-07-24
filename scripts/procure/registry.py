"""Load, validate, normalize and filter the procurement registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .models import AccessType, Source


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "procurement_sources.yaml"
DEFAULT_SCHEMA = ROOT / "config" / "procurement_sources.schema.json"


class RegistryError(ValueError):
    pass


def _default_access(raw: dict) -> dict:
    access = dict(raw.get("access") or {})
    access.setdefault("type", raw["access_method"])
    domains = set(access.get("allowed_domains") or [])
    for key in ("landing_url", "resource_url"):
        value = raw.get(key)
        if value and urlparse(value).hostname:
            domains.add(urlparse(value).hostname.lower())
    access["allowed_domains"] = sorted(domains)
    discovery = dict(access.get("discovery") or {})
    discovery.setdefault("max_depth", 1)
    discovery.setdefault("allowed_extensions", [f".{item.lower().lstrip('.')}" for item in raw.get("formats", [])])
    discovery.setdefault("financial_year_start", "2012-13")
    discovery.setdefault("financial_year_end", "current")
    discovery.setdefault("latest_only", False)
    access["discovery"] = discovery
    return access


def load_registry(
    registry_path: Path = DEFAULT_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> tuple[dict, list[Source]]:
    raw_registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(raw_registry), key=lambda error: list(error.path))
    if errors:
        rendered = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:20])
        raise RegistryError(f"registry schema validation failed: {rendered}")

    raw_sources = raw_registry["sources"]
    ids = [item["id"] for item in raw_sources]
    duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
    if duplicates:
        raise RegistryError(f"duplicate source IDs: {', '.join(duplicates)}")

    sources = []
    for raw in raw_sources:
        known = {
            "id", "priority", "publisher", "jurisdiction", "government_level",
            "source_family", "title", "landing_url", "resource_url",
            "access_method", "automation", "formats", "enabled", "access",
            "storage", "validation", "manual",
        }
        # Legacy alias: early Phase-1 rows used access_method "ckan".
        access_method = raw["access_method"]
        if access_method == "ckan":
            access_method = "ckan_api"
        access = _default_access(raw)
        if access.get("type") == "ckan":
            access["type"] = "ckan_api"
        sources.append(
            Source(
                id=raw["id"],
                priority=raw["priority"],
                publisher=raw["publisher"],
                jurisdiction=raw["jurisdiction"],
                government_level=raw["government_level"],
                source_family=raw["source_family"],
                title=raw["title"],
                landing_url=raw["landing_url"],
                resource_url=raw.get("resource_url"),
                access_method=AccessType(access_method),
                automation=raw["automation"],
                formats=[item.lower() for item in raw["formats"]],
                enabled=raw.get("enabled", True),
                access=access,
                storage=dict(raw.get("storage") or {}),
                validation=dict(raw.get("validation") or {}),
                manual=dict(raw.get("manual") or {}),
                research={key: value for key, value in raw.items() if key not in known},
            )
        )
    return raw_registry, sources


def filter_sources(
    sources: Iterable[Source],
    *,
    source_ids: set[str] | None = None,
    priorities: set[str] | None = None,
    jurisdictions: set[str] | None = None,
    levels: set[str] | None = None,
    families: set[str] | None = None,
    automation: set[str] | None = None,
) -> list[Source]:
    selected = [
        source for source in sources
        if (not source_ids or source.id in source_ids)
        and (not priorities or source.priority in priorities)
        and (not jurisdictions or source.jurisdiction in jurisdictions)
        and (not levels or source.government_level in levels)
        and (not families or source.source_family in families)
        and (not automation or source.automation in automation)
    ]
    if source_ids:
        missing = sorted(source_ids - {source.id for source in selected})
        if missing:
            raise RegistryError(f"unknown or filtered source IDs: {', '.join(missing)}")
    return sorted(selected, key=lambda source: (source.priority, source.id))

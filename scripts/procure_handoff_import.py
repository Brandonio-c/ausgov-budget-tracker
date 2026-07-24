#!/usr/bin/env python3
"""Import data/new handoff YAML rows into config/procurement_sources.yaml."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / "data" / "new" / "ausgov_additional_data_handoff.yaml"
DEFAULT_REGISTRY = ROOT / "config" / "procurement_sources.yaml"

LEVEL_MAP = {
    "federal": "federal",
    "national": "federal",
    "state": "state",
    "territory": "territory",
    "local": "local",
    "cross_level": "cross_level",
    "state/territory": "state",
    "territory/local combined": "local",
}


def _formats(raw: str | None) -> list[str]:
    text = (raw or "pdf").lower()
    found: list[str] = []
    for token in ("xlsx", "xls", "csv", "zip", "json", "pdf", "html"):
        if token in text and token not in found:
            found.append(token if token != "xls" else "xlsx")
    return found or ["pdf"]


def _normalize_level(raw: str | None) -> str:
    key = (raw or "federal").strip().lower()
    return LEVEL_MAP.get(key, "cross_level")


def _access_method(row: dict[str, Any]) -> tuple[str, str]:
    """Return (access_method, automation)."""
    status = (row.get("verification_status") or "").upper()
    bucket = (row.get("action_bucket") or "").upper()
    fmt = (row.get("format") or "").lower()
    url = (row.get("direct_file_url") or "").strip()
    dynamic = any(t in fmt for t in ("html", "dynamic", "dashboard"))

    if bucket == "MANUAL_OR_BLOCKED" or dynamic:
        return "manual", "manual"
    if status in {"RESOLVER_REQUIRED", "VERIFIED_LANDING"} or not url:
        if bucket == "REFERENCE_ONLY" and not url:
            return "manual", "manual"
        return "landing_page_discovery", "medium"
    if status == "VERIFIED_DIRECT" or url.startswith("http"):
        return "direct_file", "high"
    return "landing_page_discovery", "medium"


def _source_family(row: dict[str, Any]) -> str:
    domain = (row.get("data_domain") or "actuals").strip().lower()
    level = _normalize_level(row.get("government_level"))
    return f"handoff_{domain}_{level}"


def _allowed_domains(landing: str | None, resource: str | None) -> list[str]:
    domains: set[str] = set()
    for value in (landing, resource):
        if not value:
            continue
        host = urlparse(value).hostname
        if host:
            domains.add(host.lower())
    return sorted(domains)


def handoff_row_to_registry(row: dict[str, Any]) -> dict[str, Any] | None:
    sid = (row.get("proposed_source_id") or "").strip()
    if not sid or not re.match(r"^[a-z0-9][a-z0-9_]*$", sid):
        return None
    landing = (row.get("landing_url") or "").strip()
    if not landing.startswith("http"):
        return None
    resource = (row.get("direct_file_url") or "").strip() or None
    access_method, automation = _access_method(row)
    formats = _formats(row.get("format"))
    bucket = (row.get("action_bucket") or "").upper()
    enabled = True
    if bucket == "REFERENCE_ONLY" and not resource:
        enabled = False

    entry: dict[str, Any] = {
        "id": sid,
        "priority": row.get("priority") or "P1",
        "publisher": row.get("publisher") or "Unknown",
        "jurisdiction": row.get("jurisdiction") or "Australia",
        "government_level": _normalize_level(row.get("government_level")),
        "source_family": _source_family(row),
        "title": row.get("title") or sid,
        "landing_url": landing,
        "access_method": access_method,
        "automation": automation,
        "formats": formats,
        "enabled": enabled,
        "access": {
            "type": access_method,
            "allowed_domains": _allowed_domains(landing, resource),
            "discovery": {
                "max_depth": 1,
                "allowed_extensions": [f".{f}" for f in formats],
                "latest_only": True,
            },
        },
        "handoff_action_bucket": row.get("action_bucket"),
        "handoff_data_domain": row.get("data_domain"),
        "handoff_fills_gap": row.get("fills_gap"),
        "handoff_already_on_disk": bool(row.get("already_on_disk")),
        "handoff_repo_source_key": row.get("repo_source_key") or None,
        "handoff_verification_status": row.get("verification_status"),
        "parser_strategy": row.get("parse_notes") or None,
        "caveats": [c for c in [row.get("caveats")] if c],
    }
    if resource and resource.startswith("http"):
        entry["resource_url"] = resource
    if bucket == "MANUAL_OR_BLOCKED":
        entry["manual"] = {
            "reason": row.get("caveats") or "Blocked or manual acquisition required",
            "instructions": row.get("parse_notes") or "Use browser session / manual import.",
        }
    return entry


def import_handoff(
    handoff_path: Path = DEFAULT_HANDOFF,
    registry_path: Path = DEFAULT_REGISTRY,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    handoff = yaml.safe_load(handoff_path.read_text(encoding="utf-8"))
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    existing = {s["id"]: i for i, s in enumerate(registry["sources"])}
    added = updated = skipped = 0
    for row in handoff.get("sources") or []:
        entry = handoff_row_to_registry(row)
        if entry is None:
            skipped += 1
            continue
        # Prefer updating by proposed id; if only repo_source_key exists, leave
        # that row alone and add the proposed_source_id as a sibling download target.
        sid = entry["id"]
        if sid in existing:
            idx = existing[sid]
            merged = dict(registry["sources"][idx])
            # Fill missing resource_url / handoff metadata without wiping phase1 fields.
            for key, value in entry.items():
                if key in {"id"}:
                    continue
                if key.startswith("handoff_") or key in {
                    "parser_strategy",
                    "caveats",
                    "resource_url",
                    "enabled",
                    "access_method",
                    "automation",
                    "formats",
                    "access",
                }:
                    if value is not None:
                        merged[key] = value
            registry["sources"][idx] = merged
            updated += 1
        else:
            registry["sources"].append(entry)
            existing[sid] = len(registry["sources"]) - 1
            added += 1

    summary = {
        "handoff_rows": len(handoff.get("sources") or []),
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "registry_total": len(registry["sources"]),
        "dry_run": dry_run,
    }
    if not dry_run:
        registry["researched_at"] = handoff.get("generated_at") or registry.get("researched_at")
        registry_path.write_text(
            yaml.dump(registry, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate", action="store_true", help="Load registry after write")
    args = parser.parse_args()
    summary = import_handoff(args.handoff, args.registry, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))
    if args.validate and not args.dry_run:
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        from procure.registry import load_registry

        _, sources = load_registry(args.registry)
        print(json.dumps({"validated_sources": len(sources)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

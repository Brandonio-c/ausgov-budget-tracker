#!/usr/bin/env python3
"""Ingest ABS GFS Table_1 revenue for all jurisdiction workbooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.abs_gfs import JURISDICTION_MAP, export_revenue  # noqa: E402
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "m4_revenue"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"


def write_mapping(meta: dict) -> Path:
    doc = {
        "source_id": meta["source_id"],
        "title": meta.get("title", meta["source_id"]),
        "publisher": "Australian Bureau of Statistics",
        "jurisdiction": meta["jurisdiction"],
        "government_level": meta["government_level"],
        "source_family": "abs_gfs_operating_statement",
        "measure_type": "gfs_revenue",
        "accounting_basis": "gfs",
        "estimate_status": "actual",
        "period_granularity": "financial_year",
        "input": {"path": str(Path(meta["path"]).relative_to(REPO_ROOT)), "format": "csv"},
        "columns": {
            "financial_year": "fy",
            "amount_aud": "amount",
            "node_name": "category",
            "locator": "locator",
            "landing_url": "landing_url",
            "original_resource_url": "resource_url",
        },
        "attribution": {
            "landing_url_column": "landing_url",
            "original_resource_url_column": "resource_url",
            "cached_copy_path": meta["cached_copy_path"],
        },
        "fact_key_template": (
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
        ),
        "notes": "ABS GFS Table_1 revenue lines. Total GFS revenue pruned when components exist.",
    }
    path = MAPPINGS / f"{meta['source_id']}.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return path


def main() -> int:
    migrate(FACTS_DB)
    summaries = []
    for source_id in JURISDICTION_MAP:
        meta = export_revenue(source_id, STAGING)
        meta["title"] = f"ABS GFS Revenue — {meta['base_source_id']}"
        mpath = write_mapping(meta)
        summaries.append(
            {
                "source_id": meta["source_id"],
                "rows": meta["rows"],
                "ingest": run_mapping(mpath, FACTS_DB),
            }
        )
    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    total = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE measure_type = 'gfs_revenue'"
    ).fetchone()[0]
    conn.close()
    print(json.dumps({"summaries": summaries, "gfs_revenue_facts": total}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

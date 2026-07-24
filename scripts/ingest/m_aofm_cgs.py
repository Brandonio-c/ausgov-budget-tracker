#!/usr/bin/env python3
"""Ingest AOFM CGS instrument outstanding into facts.db (Debt securities children)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.aofm import export_aofm_instruments  # noqa: E402
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "aofm"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"


def write_mapping(meta: dict) -> Path:
    doc = {
        "source_id": meta["source_id"],
        "title": f"AOFM {meta['instrument']}",
        "publisher": "Australian Office of Financial Management",
        "jurisdiction": "Commonwealth",
        "government_level": "federal",
        "source_family": "aofm_cgs",
        "measure_type": "aofm_cgs_outstanding",
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
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}|{locator}"
        ),
    }
    path = MAPPINGS / f"{meta['source_id']}.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return path


def main() -> int:
    migrate(FACTS_DB)
    metas = export_aofm_instruments(STAGING)
    summaries = []
    for meta in metas:
        mpath = write_mapping(meta)
        summaries.append({"source_id": meta["source_id"], "rows": meta["rows"], "ingest": run_mapping(mpath, FACTS_DB)})
    print(json.dumps({"aofm_sources": len(metas), "summaries": summaries}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Ingest Statement 11 net debt + CGS face value into facts.db."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

FACTS_DB = REPO_ROOT / "data" / "facts.db"
MAPPINGS = REPO_ROOT / "config" / "mappings"
CACHED = (
    "data/raw/federal/federal_budget_statement_11_historical/"
    "snapshots/20260723T024822Z/files/bp1_bs-11.pdf"
)


def write_mapping(
    *,
    source_id: str,
    title: str,
    csv_rel: str,
    measure_type: str,
) -> Path:
    doc = {
        "source_id": source_id,
        "title": title,
        "publisher": "Australian Government Treasury",
        "jurisdiction": "Commonwealth",
        "government_level": "federal",
        "source_family": "budget_historical_aggregates",
        "measure_type": measure_type,
        "accounting_basis": "gfs",
        "estimate_status": "audited_actual",
        "period_granularity": "financial_year",
        "input": {"path": csv_rel, "format": "csv"},
        "columns": {
            "financial_year": "fy",
            "amount_aud": "amount",
            "node_name": "category",
            "estimate_status": "estimate_status",
            "locator": "locator",
            "landing_url": "landing_url",
            "original_resource_url": "resource_url",
        },
        "attribution": {
            "landing_url_column": "landing_url",
            "original_resource_url_column": "resource_url",
            "cached_copy_path": CACHED,
        },
        "fact_key_template": (
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
        ),
    }
    path = MAPPINGS / f"{source_id}.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return path


def main() -> int:
    migrate(FACTS_DB)
    # Extract
    from extractors.statement_11_stocks import main as extract_main

    extract_main()
    specs = [
        (
            "federal_statement_11_net_debt",
            "Statement 11 Table 11.4 Net debt",
            "data/staging/breakdowns/federal_statement_11_net_debt.csv",
            "net_debt",
        ),
        (
            "federal_statement_11_cgs_face_value",
            "Statement 11 Table 11.5 CGS face value",
            "data/staging/breakdowns/federal_statement_11_cgs_face_value.csv",
            "gross_debt_face_value",
        ),
    ]
    out = []
    for sid, title, csv_rel, measure in specs:
        mpath = write_mapping(source_id=sid, title=title, csv_rel=csv_rel, measure_type=measure)
        out.append(run_mapping(mpath, FACTS_DB))
    print(json.dumps({"ingest": out}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

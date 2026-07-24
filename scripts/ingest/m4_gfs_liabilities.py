#!/usr/bin/env python3
"""Ingest ABS GFS Table_3 liability stocks for all jurisdiction workbooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.abs_gfs import JURISDICTION_MAP, export_liabilities  # noqa: E402
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "m4_liabilities"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"


def write_mapping(meta: dict) -> Path:
    doc = {
        "source_id": meta["source_id"],
        "title": meta.get("title", meta["source_id"]),
        "publisher": meta.get("publisher", "Australian Bureau of Statistics"),
        "jurisdiction": meta["jurisdiction"],
        "government_level": meta["government_level"],
        "source_family": "abs_gfs_balance_sheet",
        "measure_type": "gfs_liability",
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
        "notes": (
            "ABS GFS Table_3 balance-sheet liability lines (end-of-year stocks). "
            "Total Liabilities is pruned in the dashboard tree when components exist."
        ),
    }
    path = MAPPINGS / f"{meta['source_id']}.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return path


def main() -> int:
    migrate(FACTS_DB)
    (MAPPINGS / "templates").mkdir(parents=True, exist_ok=True)
    (MAPPINGS / "templates" / "abs_gfs_table3_liabilities.yaml").write_text(
        "# Shared ABS GFS Table_3 liability melt (see adapters/abs_gfs.py).\n"
        "measure_type: gfs_liability\naccounting_basis: gfs\nestimate_status: actual\n"
        "compatibility_group: gfs_liability\n",
        encoding="utf-8",
    )

    summaries = []
    for source_id in JURISDICTION_MAP:
        meta = export_liabilities(source_id, STAGING)
        meta.update(
            {
                "publisher": "Australian Bureau of Statistics",
                "title": f"ABS GFS Liabilities — {meta['base_source_id']}",
            }
        )
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
    by_level = conn.execute(
        """
        SELECT CASE d.government_level WHEN 'national' THEN 'federal'
               ELSE d.government_level END AS lvl,
               COUNT(*)
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE f.measure_type = 'gfs_liability'
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE measure_type = 'gfs_liability'"
    ).fetchone()[0]
    conn.close()
    print(
        json.dumps(
            {"summaries": summaries, "gfs_liability_facts": total, "by_level": by_level},
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

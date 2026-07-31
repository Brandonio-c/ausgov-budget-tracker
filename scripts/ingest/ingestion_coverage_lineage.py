#!/usr/bin/env python3
"""Lineage-backed ingestion coverage audit."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "facts.db"
LINEAGE = REPO / "config" / "lineage" / "canonical_datasets.yaml"


def audit(conn: sqlite3.Connection, lineage_path: Path) -> dict:
    data = yaml.safe_load(lineage_path.read_text(encoding="utf-8")) or {}
    facts_by_key = {
        r[0]: r[1]
        for r in conn.execute(
            """
            SELECT d.source_key, COUNT(*)
            FROM facts f
            JOIN source_documents d ON d.id = f.source_document_id
            GROUP BY 1
            """
        )
    }
    rows = []
    for ds in data.get("datasets") or []:
        keys = ds.get("fact_source_keys") or []
        count = sum(facts_by_key.get(k, 0) for k in keys)
        status = ds.get("coverage_status") or "not_acquired"
        if keys and count == 0 and status == "fully_ingested":
            status = "adapter_failed"
        elif keys and count > 0 and status == "not_acquired":
            status = "partially_ingested"
        rows.append(
            {
                "canonical_dataset_id": ds.get("canonical_dataset_id"),
                "coverage_status": status,
                "fact_count": count,
                "fact_source_keys": keys,
                "extractor_name": ds.get("extractor_name"),
                "notes": ds.get("notes"),
            }
        )
    return {
        "datasets": rows,
        "alias_count": len(data.get("aliases") or {}),
        "facts_source_keys_observed": len(facts_by_key),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--lineage", type=Path, default=LINEAGE)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "ops" / "reports" / "ingestion-coverage-lineage.json",
    )
    args = ap.parse_args()
    conn = sqlite3.connect(str(args.db))
    report = audit(conn, args.lineage)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = args.out.with_suffix(".md")
    lines = ["# Ingestion coverage (lineage)", "", f"Observed source keys: {report['facts_source_keys_observed']}", ""]
    for r in report["datasets"]:
        lines.append(
            f"- **{r['canonical_dataset_id']}**: `{r['coverage_status']}` — {r['fact_count']} facts"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out), "datasets": len(report["datasets"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

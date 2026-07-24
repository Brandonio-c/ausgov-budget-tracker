#!/usr/bin/env python3
"""Ingest state borrowing-authority instrument outstandings into facts.db."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.state_debt_instruments import SOURCE_PARSERS, parse_source, resolve_raw_file  # noqa: E402
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

FACTS_DB = REPO_ROOT / "data" / "facts.db"
STAGING = REPO_ROOT / "data" / "staging" / "borrowing"
MAPPINGS = REPO_ROOT / "config" / "mappings"


def main() -> int:
    migrate(FACTS_DB)
    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    conn.execute(
        "UPDATE measure_definitions SET compatibility_group='gfs_liability' "
        "WHERE measure_type IN ('aofm_cgs_outstanding','gross_debt_face_value','net_debt')"
    )
    conn.commit()
    conn.close()

    STAGING.mkdir(parents=True, exist_ok=True)
    out = []
    for sid, (juris, level, authority, kind) in SOURCE_PARSERS.items():
        resolved = resolve_raw_file(REPO_ROOT, sid)
        if resolved is None:
            out.append({"source_id": sid, "status": "missing"})
            continue
        path, source_url = resolved
        instruments = parse_source(path, kind, authority, source_url=source_url)
        if not instruments:
            out.append({"source_id": sid, "status": "no_instrument_rows", "path": str(path)})
            continue
        fact_rows = [r.to_fact_dict() for r in instruments]
        # roll-up totals by instrument type
        by_type: dict[str, float] = {}
        as_at = instruments[0].as_at.isoformat()
        for r in instruments:
            by_type[r.instrument_type] = by_type.get(r.instrument_type, 0.0) + r.face_value_aud
        for inst_type, total in by_type.items():
            fact_rows.insert(
                0,
                {
                    "fy": instruments[0].financial_year(),
                    "category": f"Debt securities / {inst_type}",
                    "amount": total,
                    "locator": (
                        f"authority:{authority} | instrument_type:{inst_type} | "
                        f"roll_up:sum_instruments | as_at_date:{as_at} | source_url:{source_url}"
                    ),
                    "landing_url": source_url,
                    "resource_url": source_url,
                    "as_at_date": as_at,
                },
            )
        csv_path = STAGING / f"{sid}.csv"
        pd.DataFrame(fact_rows).to_csv(csv_path, index=False)
        doc = {
            "source_id": sid,
            "title": f"{authority} debt instruments",
            "publisher": authority,
            "jurisdiction": juris,
            "government_level": level,
            "source_family": "state_borrowing",
            "measure_type": "gross_debt_face_value",
            "accounting_basis": "gfs",
            "estimate_status": "actual",
            "period_granularity": "financial_year",
            "input": {"path": str(csv_path.relative_to(REPO_ROOT)), "format": "csv"},
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
                "cached_copy_path": str(path.relative_to(REPO_ROOT)),
            },
            "fact_key_template": (
                "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}|{locator}"
            ),
        }
        mpath = MAPPINGS / f"{sid}.yaml"
        mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
        summary = run_mapping(mpath, FACTS_DB)
        out.append(
            {
                "source_id": sid,
                "status": "ok",
                "instruments": len(instruments),
                "fact_rows": len(fact_rows),
                "as_at": as_at,
                "by_type": {k: round(v / 1e6, 1) for k, v in by_type.items()},
                "ingest": summary,
            }
        )
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

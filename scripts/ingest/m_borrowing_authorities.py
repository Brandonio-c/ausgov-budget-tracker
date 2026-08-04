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

from adapters.state_debt_instruments import (  # noqa: E402
    SOURCE_PARSERS,
    parse_source,
    resolve_raw_file,
)
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))
from cleanup_orphan_nodes import (  # noqa: E402
    delete_orphan_nodes,
    orphan_node_ids_for_source_document,
)

FACTS_DB = REPO_ROOT / "data" / "facts.db"
STAGING = REPO_ROOT / "data" / "staging" / "borrowing"
MAPPINGS = REPO_ROOT / "config" / "mappings"


def main() -> int:
    migrate(FACTS_DB)
    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    conn.execute(
        "UPDATE measure_definitions SET compatibility_group='gfs_liability' "
        "WHERE measure_type IN ("
        "'aofm_cgs_outstanding','gross_debt_face_value','net_debt',"
        "'borrowing_authority_debt_outstanding','superannuation_liability')"
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
        # Drop prior facts for this source so path/valuation upgrades do not double-count.
        conn = sqlite3.connect(str(FACTS_DB))
        doc_ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM source_documents WHERE source_key = ?", (sid,)
            ).fetchall()
        ]
        for doc_id in doc_ids:
            fact_ids = [
                r[0]
                for r in conn.execute(
                    "SELECT id FROM facts WHERE source_document_id = ?", (doc_id,)
                ).fetchall()
            ]
            for fid in fact_ids:
                conn.execute("DELETE FROM fact_nodes WHERE fact_id = ?", (fid,))
            conn.execute("DELETE FROM facts WHERE source_document_id = ?", (doc_id,))
            # This source's node identity is a flat one-node-per-category-string
            # scheme (ensure_node() in load_facts.py) with no breakdown_edges/
            # node_edges ever created for it, so any node that just lost its
            # last fact above is permanently unreachable - clean it up now
            # rather than leaving it to accumulate across every future reload
            # (the root cause of the 278 orphan nodes found in this milestone;
            # see ops/reports/orphan-node-investigation-*.md).
            orphaned = orphan_node_ids_for_source_document(conn, doc_id)
            delete_orphan_nodes(conn, orphaned)
        conn.commit()
        conn.close()
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
                    "category": f"Debt securities / {authority} / {inst_type}",
                    "amount": total,
                    "locator": (
                        f"authority:{authority} | instrument_type:{inst_type} | "
                        f"roll_up:sum_instruments | as_at_date:{as_at} | "
                        f"amount_granularity:instrument_type_aggregate | source_url:{source_url}"
                    ),
                    "landing_url": source_url,
                    "resource_url": source_url,
                    "as_at_date": as_at,
                    "observation_date": as_at,
                    "valuation_basis": instruments[0].to_fact_dict().get("valuation_basis", "face_value"),
                    "amount_granularity": "instrument_type_aggregate",
                    "authority": authority,
                    "isin": "",
                    "maturity_date": "",
                    "coupon": "",
                },
            )
        csv_path = STAGING / f"{sid}.csv"
        pd.DataFrame(fact_rows).to_csv(csv_path, index=False)
        # Prefer dedicated measure; keep gfs_liability compatibility via measure_definitions.
        measure = "borrowing_authority_debt_outstanding"
        doc = {
            "source_id": sid,
            "title": f"{authority} debt instruments",
            "publisher": authority,
            "jurisdiction": juris,
            "government_level": level,
            "source_family": "state_borrowing",
            "measure_type": measure,
            "accounting_basis": "gfs",
            "estimate_status": "actual",
            "period_granularity": "financial_year",
            "valuation_basis": fact_rows[0].get("valuation_basis") if fact_rows else "face_value",
            "amount_granularity": "individual_security",
            "input": {"path": str(csv_path.relative_to(REPO_ROOT)), "format": "csv"},
            "columns": {
                "financial_year": "fy",
                "amount_aud": "amount",
                "node_name": "category",
                "locator": "locator",
                "landing_url": "landing_url",
                "original_resource_url": "resource_url",
                "observation_date": "observation_date",
                "valuation_basis": "valuation_basis",
                "amount_granularity": "amount_granularity",
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

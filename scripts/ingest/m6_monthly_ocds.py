#!/usr/bin/env python3
"""M6: NSW OCDS contract_value flatten.

This file's original federal-MFS loading path (export_federal_monthly(),
measure_type='monthly_actuals', compatibility_group='actual_expense') was
removed by the MFS-aggregates milestone (see
ops/reports/mfs-semantics-baseline-*.md, Task 1): it demo-loaded a small
subset (last 3 sheets, July column only) of the real MFS corpus under the
SAME compatibility_group as annual GFS/PBS actuals, which was confirmed
to silently contaminate the live federal actuals dashboard total for any
financial year lacking GFS-basis data (FY2025-26 at the time). That
contamination was removed from data/facts.db in Task 1
(scripts/ops/cleanup_stray_mfs_preload.py). The correct, fully-classified
MFS load now lives in scripts/ingest/load_mfs_aggregates.py, using its
own dedicated measure types and compatibility groups
(config/measure-semantics/mfs.yaml) that can never enter an annual
additive group. Do not reintroduce a 'monthly_actuals'/'actual_expense'
federal MFS load here or anywhere else.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import run_mapping  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "m6"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"


def write_and_run(meta: dict) -> dict:
    STAGING.mkdir(parents=True, exist_ok=True)
    doc = {
        "source_id": meta["source_id"],
        "title": meta["title"],
        "publisher": meta["publisher"],
        "jurisdiction": meta["jurisdiction"],
        "government_level": meta["government_level"],
        "source_family": meta["source_family"],
        "measure_type": meta["measure_type"],
        "accounting_basis": meta["accounting_basis"],
        "estimate_status": meta["estimate_status"],
        "period_granularity": meta.get("period_granularity", "financial_year"),
        "input": {"path": str(Path(meta["csv"]).relative_to(REPO_ROOT)), "format": "csv"},
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
    }
    mpath = MAPPINGS / f"{meta['source_id']}.yaml"
    mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return run_mapping(mpath, FACTS_DB)


def export_nsw_ocds(limit: int | None = None) -> tuple[dict, list[dict]]:
    src = REPO_ROOT / "data/raw/state/nsw_procurement_ocds_registry"
    data = json.loads((src / "latest.json").read_text())
    assets = [a for a in data["assets"] if a.get("original_filename") == "australia_new_south_wales_2024.jsonl.gz"]
    asset = assets[0]
    fp = REPO_ROOT / "data" / asset["stored_path"]
    landing = "https://www.tenders.nsw.gov.au/"
    resource = asset.get("final_url") or asset.get("requested_url") or landing
    rows = []
    spot = []
    with gzip.open(fp, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if limit and len(rows) >= limit:
                break
            obj = json.loads(line)
            awards = obj.get("awards") or []
            for award in awards:
                value = (award.get("value") or {}).get("amount")
                if value is None:
                    continue
                try:
                    amount = float(value)
                except (TypeError, ValueError):
                    continue
                title = str(award.get("title") or obj.get("ocid") or "award")[:160]
                suppliers = award.get("suppliers") or []
                supplier = suppliers[0].get("name") if suppliers else "unknown"
                award_id = str(award.get("id") or "").strip()
                date = str(award.get("date") or obj.get("date") or "")[:10]
                fy = "2023-24"
                if date:
                    try:
                        y, m = int(date[:4]), int(date[5:7])
                        fy = f"{y}-{str(y+1)[-2:]}" if m >= 7 else f"{y-1}-{str(y)[-2:]}"
                    except Exception:
                        pass
                node = f"{award_id} / {supplier} / {title}"
                rows.append(
                    {
                        "fy": fy,
                        "amount": amount,
                        "category": node,
                        "locator": f"ocds:{obj.get('ocid')} | award:{award_id} | line:{line_no}",
                        "landing_url": landing,
                        "resource_url": resource,
                    }
                )
                if len(spot) < 5 and award_id:
                    spot.append(
                        {
                            "award_id": award_id,
                            "title": title,
                            "supplier": supplier,
                            "amount": amount,
                            "ocid": obj.get("ocid"),
                            "buyer": (award.get("buyer") or {}).get("name"),
                            "etendering_search": f"https://www.tenders.nsw.gov.au/?event=public.CN.search&keyword={award_id.strip()}",
                        }
                    )
    out = STAGING / "nsw_procurement_ocds_registry.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    meta = {
        "source_id": "nsw_procurement_ocds_registry",
        "csv": out,
        "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
        "title": "NSW procurement OCDS awards (2024 file)",
        "publisher": "NSW Government",
        "jurisdiction": "NSW",
        "government_level": "state",
        "source_family": "procurement_contracts",
        "measure_type": "contract_value",
        "accounting_basis": "commitment",
        "estimate_status": "contract",
        "rows": len(rows),
    }
    return meta, spot


def main() -> int:
    m2, spot = export_nsw_ocds()
    s2 = write_and_run(m2)
    # write spot-check notes (manual URL targets; not live-fetched here)
    spot_path = REPO_ROOT / "ops" / "reports" / "m6-nsw-ocds-spotchecks.json"
    spot_path.write_text(json.dumps(spot, indent=2), encoding="utf-8")
    print(json.dumps({"ocds": s2, "spotchecks": spot}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

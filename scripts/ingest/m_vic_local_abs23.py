#!/usr/bin/env python3
"""Ingest VIC VLGGC ABS2-3 Balance Sheets borrowings / liabilities by council."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

FACTS_DB = REPO_ROOT / "data" / "facts.db"
STAGING = REPO_ROOT / "data" / "staging" / "local"
MAPPINGS = REPO_ROOT / "config" / "mappings"
SOURCE_ID = "vic_local_abs2_3_balance_finance_2024_25"

METRIC_COLS = {
    "Total Borrowings": "borrowings",
    "Borrowings - Domestic Loans": "borrowings_domestic",
    "Borrowings - Loans from the Treasury Corporation of Victoria": "borrowings_tcv",
    "Total Liabilities": "total_liabilities",
}


def _resolve() -> tuple[Path, str]:
    matches = [
        m
        for m in (REPO_ROOT / "data" / "raw").rglob(SOURCE_ID)
        if m.is_dir() and (m / "latest.json").exists()
    ]
    data = json.loads((matches[0] / "latest.json").read_text(encoding="utf-8"))
    asset = data["assets"][0]
    path = REPO_ROOT / "data" / asset["stored_path"]
    if not path.exists():
        path = REPO_ROOT / asset["stored_path"]
    return path, asset.get("requested_url") or "https://www.localgovernment.vic.gov.au/"


def melt(path: Path, url: str) -> list[dict]:
    sheet = "Balance Sheets"
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    label_row = 6
    col_map: dict[int, str] = {}
    for j in range(df.shape[1]):
        label = df.iloc[label_row, j]
        if pd.isna(label):
            continue
        label_s = re.sub(r"\s+", " ", str(label)).strip()
        if label_s in METRIC_COLS:
            col_map[j] = label_s
    rows: list[dict] = []
    for i in range(9, len(df)):
        council = df.iloc[i, 0]
        if pd.isna(council):
            continue
        council = re.sub(r"\s+", " ", str(council)).strip()
        if not council or council.lower().startswith("total"):
            continue
        for j, label in col_map.items():
            val = df.iloc[i, j]
            if pd.isna(val):
                continue
            try:
                amount = float(val)
            except (TypeError, ValueError):
                continue
            if amount == 0:
                continue
            rows.append(
                {
                    "fy": "2024-25",
                    "category": f"VIC / {council} / {label}",
                    "amount": amount,
                    "locator": (
                        f"source:{SOURCE_ID} | sheet:{sheet} | council:{council} | "
                        f"metric:{label} | code:{METRIC_COLS[label]}"
                    ),
                    "landing_url": url,
                    "resource_url": url,
                    "observation_date": "2025-06-30",
                    "valuation_basis": "carrying_amount",
                    "amount_granularity": "council_aggregate",
                }
            )
    return rows


def main() -> int:
    migrate(FACTS_DB)
    path, url = _resolve()
    rows = melt(path, url)
    STAGING.mkdir(parents=True, exist_ok=True)
    csv_path = STAGING / f"{SOURCE_ID}.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    doc = {
        "source_id": SOURCE_ID,
        "title": "VIC VLGGC ABS2-3 balance sheets borrowings 2024-25",
        "publisher": "Victorian Local Government Grants Commission",
        "jurisdiction": "VIC",
        "government_level": "local",
        "source_family": "local_government",
        "measure_type": "gfs_liability",
        "accounting_basis": "accrual",
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
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
        ),
    }
    mpath = MAPPINGS / f"{SOURCE_ID}.yaml"
    mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    summary = run_mapping(mpath, FACTS_DB) if rows else {"published": 0}
    print(json.dumps({"rows": len(rows), "ingest": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Ingest ACT 2026-27 budget tables — GGS expenses by function."""

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
STAGING = REPO_ROOT / "data" / "staging" / "state_budget"
MAPPINGS = REPO_ROOT / "config" / "mappings"
SOURCE_ID = "act_budget_tables_2026_27"
FY_STATUS = {
    "2025-26 Estimated Outcome": ("2025-26", "estimated_actual"),
    "2026-27 Budget": ("2026-27", "budget"),
    "2027-28 Estimate": ("2027-28", "forward_estimate"),
    "2028-29 Estimate": ("2028-29", "forward_estimate"),
    "2029-30 Estimate": ("2029-30", "forward_estimate"),
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
    return path, asset.get("requested_url") or "https://www.treasury.act.gov.au/"


def melt_expenses_by_function(path: Path, source_url: str) -> list[dict]:
    df = pd.read_excel(path, sheet_name="Chapter 3.4", header=None)
    # Find header row with years
    header_i = None
    year_cols: list[tuple[int, str, str]] = []
    for i in range(min(10, len(df))):
        vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[i].tolist()]
        matched = []
        for j, v in enumerate(vals):
            for label, (fy, status) in FY_STATUS.items():
                if v == label or label in v:
                    matched.append((j, fy, status))
        if len(matched) >= 3:
            header_i = i
            year_cols = matched
            break
    if header_i is None:
        return []
    rows = []
    for i in range(header_i + 1, len(df)):
        label = df.iloc[i, 0]
        if pd.isna(label):
            continue
        label = re.sub(r"\s+", " ", str(label)).strip()
        if not label or label.lower().startswith("total") or label.lower().startswith("source"):
            continue
        for j, fy, status in year_cols:
            val = df.iloc[i, j]
            if pd.isna(val):
                continue
            try:
                amount = float(str(val).replace(",", "")) * 1000  # $'000
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "fy": fy,
                    "category": f"ACT / Expenses by function / {label}",
                    "amount": amount,
                    "estimate_status": status,
                    "locator": (
                        f"source:{SOURCE_ID} | sheet:Chapter 3.4 | table:3.4.1 | "
                        f"function:{label} | fy:{fy} | unit:$000"
                    ),
                    "landing_url": source_url,
                    "resource_url": source_url,
                }
            )
    return rows


def main() -> int:
    migrate(FACTS_DB)
    path, url = _resolve()
    rows = melt_expenses_by_function(path, url)
    STAGING.mkdir(parents=True, exist_ok=True)
    csv_path = STAGING / f"{SOURCE_ID}_expenses_by_function.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    doc = {
        "source_id": SOURCE_ID,
        "title": "ACT 2026-27 Budget tables — expenses by function",
        "publisher": "ACT Treasury",
        "jurisdiction": "ACT",
        "government_level": "territory",
        "source_family": "state_budget",
        "measure_type": "budget_estimate",
        "accounting_basis": "accrual",
        "estimate_status": "budget",
        "period_granularity": "financial_year",
        "input": {"path": str(csv_path.relative_to(REPO_ROOT)), "format": "csv"},
        "columns": {
            "financial_year": "fy",
            "amount_aud": "amount",
            "node_name": "category",
            "locator": "locator",
            "landing_url": "landing_url",
            "original_resource_url": "resource_url",
            "estimate_status": "estimate_status",
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

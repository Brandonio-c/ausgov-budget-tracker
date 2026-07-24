#!/usr/bin/env python3
"""Ingest NSW budgeted financial statements (GG operating expenses/revenues)."""

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
STAGING = REPO_ROOT / "data" / "staging" / "state"
MAPPINGS = REPO_ROOT / "config" / "mappings"
SOURCE_ID = "nsw_budgeted_financial_statements_2026_27"

# Columns: 2=2024-25 Actual, 3=2025-26 Revised, 4=2026-27 Budget ($m)
YEAR_COLS = [
    (2, "2024-25", "actual", "actual_expense", "gfs_expense"),
    (2, "2024-25", "actual", "gfs_revenue", "gfs_revenue"),
    (4, "2026-27", "budget", "budget_expense", "budget_estimate"),
]


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
    return path, asset.get("requested_url") or "https://www.budget.nsw.gov.au/"


def melt(path: Path, url: str) -> dict[str, list[dict]]:
    sheet = "GG Operating Statement"
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    section = None
    buckets: dict[str, list[dict]] = {
        "nsw_gg_expenses_actual_2024_25": [],
        "nsw_gg_revenue_actual_2024_25": [],
        "nsw_gg_expenses_budget_2026_27": [],
    }
    for i in range(6, len(df)):
        label = df.iloc[i, 1]
        if pd.isna(label):
            continue
        label = re.sub(r"\s+", " ", str(label)).strip()
        if not label:
            continue
        low = label.lower()
        if "revenue from transactions" in low:
            section = "revenue"
            continue
        if "expenses from transactions" in low:
            section = "expense"
            continue
        if low.startswith("total ") or "net result" in low or "other economic flows" in low:
            continue
        if section is None:
            continue
        for col, fy, est, _group, measure in YEAR_COLS:
            if section == "revenue" and measure == "budget_estimate":
                continue
            if section == "expense" and measure == "gfs_revenue":
                continue
            if section == "revenue" and measure != "gfs_revenue":
                continue
            if section == "expense" and measure not in {"gfs_expense", "budget_estimate"}:
                continue
            val = df.iloc[i, col]
            if pd.isna(val):
                continue
            try:
                amount = float(val) * 1_000_000
            except (TypeError, ValueError):
                continue
            row = {
                "fy": fy,
                "category": f"NSW / General government / {label}",
                "amount": amount,
                "locator": (
                    f"source:{SOURCE_ID} | sheet:{sheet} | row:{label} | "
                    f"fy:{fy} | unit:$m"
                ),
                "landing_url": url,
                "resource_url": url,
            }
            if section == "revenue" and fy == "2024-25":
                buckets["nsw_gg_revenue_actual_2024_25"].append({**row, "measure_type": "gfs_revenue"})
            elif section == "expense" and fy == "2024-25":
                buckets["nsw_gg_expenses_actual_2024_25"].append({**row, "measure_type": "gfs_expense"})
            elif section == "expense" and fy == "2026-27":
                buckets["nsw_gg_expenses_budget_2026_27"].append(
                    {**row, "measure_type": "budget_estimate"}
                )
    return buckets


def ingest_bucket(source_id: str, rows: list[dict], *, measure: str, title: str, path: Path, url: str) -> dict:
    if not rows:
        return {"published": 0}
    csv_path = STAGING / f"{source_id}.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    est = "actual" if measure != "budget_estimate" else "budget"
    basis = "gfs" if measure.startswith("gfs") else "accrual"
    # Remap expense actuals to actual_expense compatibility via measure_definitions
    # gfs_expense already maps; budget_estimate maps to budget_expense.
    doc = {
        "source_id": source_id,
        "title": title,
        "publisher": "NSW Treasury",
        "jurisdiction": "NSW",
        "government_level": "state",
        "source_family": "state_budget",
        "measure_type": measure,
        "accounting_basis": basis,
        "estimate_status": est,
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
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
        ),
    }
    mpath = MAPPINGS / f"{source_id}.yaml"
    mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return run_mapping(mpath, FACTS_DB)


def main() -> int:
    migrate(FACTS_DB)
    STAGING.mkdir(parents=True, exist_ok=True)
    path, url = _resolve()
    buckets = melt(path, url)
    # Ensure gfs_expense maps into actual_expense if needed
    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    conn.execute(
        "INSERT OR IGNORE INTO measure_definitions "
        "(measure_type, label, description, additive_across_time, additive_across_nodes, "
        "default_accounting_basis, compatibility_group) "
        "VALUES ('gfs_expense', 'GFS expense', 'GFS expense', 0, 1, 'gfs', 'actual_expense')"
    )
    conn.commit()
    conn.close()

    out = []
    mapping = [
        ("nsw_gg_expenses_actual_2024_25", "gfs_expense", "NSW GG expenses actual 2024-25"),
        ("nsw_gg_revenue_actual_2024_25", "gfs_revenue", "NSW GG revenue actual 2024-25"),
        ("nsw_gg_expenses_budget_2026_27", "budget_estimate", "NSW GG expenses budget 2026-27"),
    ]
    for sid, measure, title in mapping:
        summary = ingest_bucket(sid, buckets.get(sid, []), measure=measure, title=title, path=path, url=url)
        out.append({"source_id": sid, "rows": len(buckets.get(sid, [])), "ingest": summary})
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

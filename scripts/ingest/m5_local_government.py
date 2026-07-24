#!/usr/bin/env python3
"""M5: NSW OLG time series, TAS CDC (ZIP unpack), VIC VGC returns."""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import run_mapping  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "m5"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"
UNPACK = REPO_ROOT / "data" / "staging" / "m5" / "tas_unpacked"


def write_and_run(meta: dict) -> dict:
    STAGING.mkdir(parents=True, exist_ok=True)
    doc = {
        "source_id": meta["source_id"],
        "title": meta["title"],
        "publisher": meta["publisher"],
        "jurisdiction": meta["jurisdiction"],
        "government_level": "local",
        "source_family": meta["source_family"],
        "measure_type": meta["measure_type"],
        "accounting_basis": meta["accounting_basis"],
        "estimate_status": meta["estimate_status"],
        "period_granularity": "financial_year",
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


def _fy_from_name(name: str) -> str | None:
    m = re.search(r"(20\d{2})\D?(20\d{2}|\d{2})", name)
    if not m:
        return None
    y1 = int(m.group(1))
    y2 = m.group(2)
    y2 = int(y2) if len(y2) == 4 else 2000 + int(y2)
    return f"{y1}-{str(y2)[-2:]}"


def export_nsw() -> dict:
    src = REPO_ROOT / "data/raw/local/nsw_local_olg_time_series"
    data = json.loads((src / "latest.json").read_text())
    # Prefer newest time-series workbook
    assets = [a for a in data["assets"] if "time-series-data" in (a.get("original_filename") or "")]
    assets = sorted(assets, key=lambda a: a.get("original_filename") or "", reverse=True)
    asset = assets[0]
    fp = REPO_ROOT / "data" / asset["stored_path"]
    fy = _fy_from_name(asset.get("original_filename") or fp.name) or "2024-25"
    df = pd.read_excel(fp, sheet_name="Councils ", header=None)
    headers = [str(h).strip() if pd.notna(h) else f"col{i}" for i, h in enumerate(df.iloc[2].tolist())]
    # expense $ columns (not %)
    expense_cols = []
    for i, h in enumerate(headers):
        low = h.lower()
        if "expenditure" in low and "($)" in h.replace("\n", " ") and "%" not in h:
            expense_cols.append((i, re.sub(r"\s+", " ", h).strip()))
        if "total expenses from continuing operations" in low:
            expense_cols.append((i, "Total Expenses from Continuing Operations"))
    # dedupe
    seen = set()
    uniq = []
    for i, label in expense_cols:
        if i not in seen:
            seen.add(i)
            uniq.append((i, label))
    landing = "https://www.olg.nsw.gov.au/public/about-councils/your-council/"
    resource = asset.get("final_url") or asset.get("requested_url") or landing
    rows = []
    for ridx in range(3, len(df)):
        council = df.iloc[ridx, 0]
        if pd.isna(council) or not str(council).strip():
            continue
        council = str(council).strip()
        for cidx, label in uniq:
            val = df.iloc[ridx, cidx]
            if pd.isna(val):
                continue
            try:
                amount = float(val)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "fy": fy,
                    "amount": amount,
                    "category": f"{council} / {label}",
                    "locator": f"sheet:Councils | council:{council} | col:{label} | row:{ridx+1}",
                    "landing_url": landing,
                    "resource_url": resource,
                }
            )
    out = STAGING / "nsw_local_olg_time_series.csv"
    STAGING.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    return {
        "source_id": "nsw_local_olg_time_series",
        "csv": out,
        "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
        "title": "NSW OLG Your Council time series",
        "publisher": "NSW Office of Local Government",
        "jurisdiction": "NSW",
        "source_family": "local_actuals",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "actual",
        "rows": len(rows),
    }


def export_tas() -> dict:
    src = REPO_ROOT / "data/raw/local/tas_local_cdc"
    data = json.loads((src / "latest.json").read_text())
    # Prefer 2015-2025 zip
    assets = sorted(
        data["assets"],
        key=lambda a: "2015-2025" in (a.get("original_filename") or ""),
        reverse=True,
    )
    asset = assets[0]
    zpath = REPO_ROOT / "data" / asset["stored_path"]
    UNPACK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(UNPACK)
        names = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls", ".csv"))]
    xlsx = UNPACK / names[0]
    df = pd.read_excel(xlsx)
    # Year like 2015-2016 → 2015-16
    def norm_fy(y):
        s = str(y)
        m = re.match(r"(20\d{2})\D?(20\d{2}|\d{2})", s)
        if not m:
            return None
        y1 = int(m.group(1))
        y2 = m.group(2)
        y2n = int(y2) if len(y2) == 4 else 2000 + int(y2)
        return f"{y1}-{str(y2n)[-2:]}"

    money_cols = [
        c
        for c in df.columns
        if any(
            k in str(c).lower()
            for k in (
                "total rates",
                "employee",
                "materials",
                "depreciation",
                "total expenses",
                "total expenditure",
            )
        )
    ]
    if not money_cols:
        # fallback: pick numeric-looking financial columns with Total in name
        money_cols = [c for c in df.columns if str(c).startswith("Total") ][:8]
    landing = "https://www.treasury.tas.gov.au/"
    resource = asset.get("requested_url") or landing
    rows = []
    for idx, r in df.iterrows():
        fy = norm_fy(r.get("Year"))
        council = str(r.get("Council") or "").strip()
        if not fy or not council:
            continue
        for col in money_cols:
            val = r.get(col)
            if pd.isna(val):
                continue
            try:
                amount = float(val)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "fy": fy,
                    "amount": amount,
                    "category": f"{council} / {col}",
                    "locator": f"zip:{zpath.name} | file:{xlsx.name} | row:{idx+2} | col:{col}",
                    "landing_url": landing,
                    "resource_url": resource,
                }
            )
    out = STAGING / "tas_local_cdc.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return {
        "source_id": "tas_local_cdc",
        "csv": out,
        "cached_copy_path": str(zpath.relative_to(REPO_ROOT)),
        "title": "Tasmania LGA CDC data repository",
        "publisher": "Tasmanian Government",
        "jurisdiction": "TAS",
        "source_family": "local_actuals",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "actual",
        "rows": len(rows),
        "year_layout": sorted({r["fy"] for r in rows})[:20],
    }


def export_vic() -> dict:
    src = REPO_ROOT / "data/raw/local/vic_local_vgc_abs_returns"
    data = json.loads((src / "latest.json").read_text())
    assets = [
        a
        for a in data["assets"]
        if "VGC1" in (a.get("original_filename") or "") and "2024-25" in (a.get("original_filename") or "")
    ]
    if not assets:
        assets = [a for a in data["assets"] if "VGC1" in (a.get("original_filename") or "")]
    asset = assets[0]
    fp = REPO_ROOT / "data" / asset["stored_path"]
    xl = pd.ExcelFile(fp)
    sheet = "Total Exp" if "Total Exp" in xl.sheet_names else xl.sheet_names[1]
    df = pd.read_excel(fp, sheet_name=sheet, header=None)
    # Heuristic: find a header row with 'Council' and numeric body
    header_idx = 0
    for i in range(min(30, len(df))):
        vals = " ".join(str(v) for v in df.iloc[i].tolist() if pd.notna(v)).lower()
        if "council" in vals:
            header_idx = i
            break
    headers = [str(h).strip() if pd.notna(h) else f"c{j}" for j, h in enumerate(df.iloc[header_idx].tolist())]
    landing = "https://www.localgovernment.vic.gov.au/"
    resource = asset.get("requested_url") or landing
    rows = []
    for ridx in range(header_idx + 1, len(df)):
        council = df.iloc[ridx, 0]
        if pd.isna(council) or not str(council).strip():
            continue
        # skip notes
        if str(council).strip().lower().startswith("note"):
            continue
        council = str(council).strip()
        for cidx, label in enumerate(headers[1:], start=1):
            val = df.iloc[ridx, cidx]
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
                    "amount": amount,
                    "category": f"{council} / {label}",
                    "locator": f"sheet:{sheet} | council:{council} | col:{label} | row:{ridx+1}",
                    "landing_url": landing,
                    "resource_url": resource,
                }
            )
    out = STAGING / "vic_local_vgc_abs_returns.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return {
        "source_id": "vic_local_vgc_abs_returns",
        "csv": out,
        "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
        "title": "VIC VLGGC VGC1 Expenditure and Revenue",
        "publisher": "Victorian Local Government Grants Commission",
        "jurisdiction": "VIC",
        "source_family": "local_actuals",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "actual",
        "rows": len(rows),
    }


def main() -> int:
    import sqlite3

    before = sqlite3.connect(str(FACTS_DB)).execute(
        """
        SELECT COUNT(*) FROM facts f
        JOIN source_documents d ON d.id=f.source_document_id
        WHERE d.source_key='vic_local_govt_financial'
          AND f.financial_year BETWEEN '2014-15' AND '2018-19'
        """
    ).fetchone()[0]

    metas = [export_nsw(), export_tas(), export_vic()]
    summaries = []
    for meta in metas:
        print({k: meta[k] for k in meta if k != "csv"})
        summaries.append(write_and_run(meta))

    after = sqlite3.connect(str(FACTS_DB)).execute(
        """
        SELECT COUNT(*) FROM facts f
        JOIN source_documents d ON d.id=f.source_document_id
        WHERE d.source_key='vic_local_govt_financial'
          AND f.financial_year BETWEEN '2014-15' AND '2018-19'
        """
    ).fetchone()[0]
    print(json.dumps({
        "summaries": summaries,
        "vic_m3_baseline_2014_19_before": before,
        "vic_m3_baseline_2014_19_after": after,
        "baseline_preserved": before == after and before > 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

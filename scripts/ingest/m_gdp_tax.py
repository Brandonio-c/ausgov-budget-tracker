#!/usr/bin/env python3
"""Melt ABS Taxation Revenue key tables + ASNA GVA-by-industry into facts.db."""

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
MAPPINGS = REPO_ROOT / "config" / "mappings"
STAGING = REPO_ROOT / "data" / "staging" / "gdp_tax"
FY_RE = re.compile(r"^\d{4}-\d{2}$")

TAX_SHEETS = {
    "Table_1": ("Commonwealth", "federal"),
    "Table_2": ("NSW", "state"),
    "Table_3": ("VIC", "state"),
    "Table_4": ("QLD", "state"),
    "Table_5": ("SA", "state"),
    "Table_6": ("WA", "state"),
    "Table_7": ("TAS", "state"),
    "Table_8": ("NT", "territory"),
    "Table_9": ("ACT", "territory"),
}

SKIP_TAX = frozenset(
    {
        "Taxes on income",
        "Income taxes levied on individuals",
        "Income taxes levied on enterprises",
        "Income taxes levied on non-residents",
        "Taxes on the provision of goods and services",
        "Excises and levies",
    }
)


def _resolve(source_id: str) -> Path:
    matches = [
        m
        for m in (REPO_ROOT / "data" / "raw").rglob(source_id)
        if m.is_dir() and (m / "latest.json").exists()
    ]
    if not matches:
        raise FileNotFoundError(source_id)
    data = json.loads((matches[0] / "latest.json").read_text(encoding="utf-8"))
    stored = Path(data["assets"][0]["stored_path"])
    fp = REPO_ROOT / "data" / stored if not stored.is_absolute() else stored
    if not fp.exists():
        fp = REPO_ROOT / stored
    if not fp.exists():
        cands = list(matches[0].rglob("*.xlsx"))
        if not cands:
            raise FileNotFoundError(stored)
        fp = cands[0]
    return fp


def melt_tax(path: Path) -> list[dict]:
    out = []
    xl = pd.ExcelFile(path)
    for sheet, (juris, level) in TAX_SHEETS.items():
        if sheet not in xl.sheet_names:
            continue
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        header_idx = None
        years, year_cols = [], []
        for i in range(min(12, len(df))):
            vals = [str(v).strip() for v in df.iloc[i].tolist() if pd.notna(v)]
            if sum(1 for v in vals if FY_RE.match(v)) >= 2:
                header_idx = i
                for j, v in enumerate(df.iloc[i].tolist()):
                    if pd.notna(v) and FY_RE.match(str(v).strip()):
                        years.append(str(v).strip())
                        year_cols.append(j)
                break
        if header_idx is None:
            continue
        for i in range(header_idx + 1, len(df)):
            label = df.iloc[i, 0]
            if pd.isna(label):
                continue
            label = re.sub(r"\s+", " ", str(label)).strip()
            if not label or label in SKIP_TAX or label.lower().startswith("total"):
                continue
            amounts = [df.iloc[i, j] for j in year_cols]
            if all(pd.isna(a) for a in amounts):
                continue
            for fy, j in zip(years, year_cols):
                val = df.iloc[i, j]
                if pd.isna(val):
                    continue
                try:
                    amount = float(val) * 1_000_000
                except (TypeError, ValueError):
                    continue
                out.append(
                    {
                        "fy": fy,
                        "category": label,
                        "amount": amount,
                        "jurisdiction": juris,
                        "government_level": level,
                        "locator": f"sheet:{sheet} | tax:{label} | fy:{fy}",
                    }
                )
    return out


def melt_gva(path: Path) -> list[dict]:
    """Take ANZSIC division total chain-volume series for latest FY."""
    df = pd.read_excel(path, sheet_name="Data1", header=None)
    headers = [str(c) if pd.notna(c) else "" for c in df.iloc[0].tolist()]
    # Division totals look like: "Mining (B) ;  Chain volume measures ;"
    div_cols = []
    for j, h in enumerate(headers):
        if j == 0:
            continue
        if re.search(r"\([A-S]\)\s*;\s*Chain volume measures\s*;\s*$", h):
            name = h.split(";")[0].strip()
            div_cols.append((j, name))
    if not div_cols:
        return []
    # Find latest June year row
    latest_i = None
    latest_fy = None
    for i in range(10, len(df)):
        dt = df.iloc[i, 0]
        ts = pd.to_datetime(dt, errors="coerce")
        if pd.isna(ts):
            continue
        if ts.month == 6:
            y = ts.year - 1
            latest_fy = f"{y}-{str(y + 1)[-2:]}"
            latest_i = i
    if latest_i is None:
        return []
    rows = []
    for j, name in div_cols:
        val = df.iloc[latest_i, j]
        if pd.isna(val):
            continue
        try:
            amount = float(val) * 1_000_000
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "fy": latest_fy,
                "category": name,
                "amount": amount,
                "jurisdiction": "Australia",
                "government_level": "federal",
                "locator": f"sheet:Data1 | gva:{name} | fy:{latest_fy}",
            }
        )
    return rows


def write_and_ingest(rows: list[dict], *, source_id: str, measure_type: str, title: str, cached: str) -> dict:
    if not rows:
        return {"source_id": source_id, "rows": 0}
    STAGING.mkdir(parents=True, exist_ok=True)
    # one CSV per source; jurisdiction from rows for tax multi-sheet
    # For mapping we need single government_level — split by level for tax
    by_level: dict[str, list] = {}
    for r in rows:
        by_level.setdefault(r["government_level"], []).append(r)
    summaries = []
    for level, level_rows in by_level.items():
        sid = f"{source_id}_{level}" if len(by_level) > 1 else source_id
        csv_path = STAGING / f"{sid}.csv"
        # attach attribution urls
        for r in level_rows:
            r.setdefault("landing_url", "https://www.abs.gov.au/")
            r.setdefault("resource_url", "https://www.abs.gov.au/")
        pd.DataFrame(level_rows).to_csv(csv_path, index=False)
        juris = level_rows[0]["jurisdiction"] if level == "federal" else level_rows[0]["jurisdiction"]
        if level != "federal" and measure_type == "tax_revenue":
            # multi-jurisdiction in one level file — use level label
            juris = level.title()
        doc = {
            "source_id": sid,
            "title": f"{title} ({level})",
            "publisher": "Australian Bureau of Statistics",
            "jurisdiction": juris,
            "government_level": level,
            "source_family": "abs_gdp_tax",
            "measure_type": measure_type,
            "accounting_basis": "gfs" if measure_type == "tax_revenue" else "not_applicable",
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
                "cached_copy_path": cached,
            },
            "fact_key_template": (
                "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
            ),
        }
        if level != "federal" and measure_type == "tax_revenue":
            for r in level_rows:
                if not str(r["category"]).startswith(f"{r['jurisdiction']} /"):
                    r["category"] = f"{r['jurisdiction']} / {r['category']}"
            pd.DataFrame(level_rows).to_csv(csv_path, index=False)
            doc["jurisdiction"] = "States and Territories"
        mpath = MAPPINGS / f"{sid}.yaml"
        mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
        summaries.append(run_mapping(mpath, FACTS_DB))
    return {"source_id": source_id, "parts": summaries}


def main() -> int:
    migrate(FACTS_DB)
    # Align tax with revenue dashboard mode
    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    conn.execute(
        "UPDATE measure_definitions SET compatibility_group='gfs_revenue' WHERE measure_type='tax_revenue'"
    )
    conn.commit()
    conn.close()

    out = []
    tax_path = _resolve("abs_taxation_revenue_key_tables_2024_25")
    tax_rows = melt_tax(tax_path)
    out.append(
        write_and_ingest(
            tax_rows,
            source_id="abs_taxation_revenue_key_tables_2024_25",
            measure_type="tax_revenue",
            title="ABS Taxation Revenue key tables",
            cached=str(tax_path.relative_to(REPO_ROOT)),
        )
    )
    gva_path = _resolve("abs_asna_gva_industry_2024_25")
    gva_rows = melt_gva(gva_path)
    out.append(
        write_and_ingest(
            gva_rows,
            source_id="abs_asna_gva_industry_2024_25",
            measure_type="gdp_current",
            title="ABS ASNA GVA by industry",
            cached=str(gva_path.relative_to(REPO_ROOT)),
        )
    )
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

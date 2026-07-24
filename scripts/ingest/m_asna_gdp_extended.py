#!/usr/bin/env python3
"""Melt additional ABS national / state accounts workbooks into facts.db.

Extends m_gdp_tax coverage for ASNA key aggregates, expenditure GDP,
QNA key aggregates, and state accounts GSP — without re-acquiring files.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from m_gdp_tax import _resolve, write_and_ingest  # noqa: E402
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

FACTS_DB = REPO_ROOT / "data" / "facts.db"
MAPPINGS = REPO_ROOT / "config" / "mappings"
STAGING = REPO_ROOT / "data" / "staging" / "gdp_tax"
FY_RE = re.compile(r"^(\d{4})-(\d{2})$")

STATE_ACCOUNT_IDS = {
    "abs_state_accounts_nsw_2024_25": ("NSW", "state"),
    "abs_state_accounts_vic_2024_25": ("VIC", "state"),
    "abs_state_accounts_qld_2024_25": ("QLD", "state"),
    "abs_state_accounts_sa_2024_25": ("SA", "state"),
    "abs_state_accounts_wa_2024_25": ("WA", "state"),
    "abs_state_accounts_tas_2024_25": ("TAS", "state"),
    "abs_state_accounts_nt_2024_25": ("NT", "territory"),
    "abs_state_accounts_act_2024_25": ("ACT", "territory"),
}


def _find_fy_header(df: pd.DataFrame) -> tuple[int, list[str], list[int]] | None:
    for i in range(min(20, len(df))):
        years, cols = [], []
        for j, v in enumerate(df.iloc[i].tolist()):
            if pd.isna(v):
                continue
            s = str(v).strip()
            if FY_RE.match(s):
                years.append(s)
                cols.append(j)
            # also accept Jun-2025 style
            m = re.match(r"(?:Jun|June)[- ]?(\d{4})", s, re.I)
            if m:
                y = int(m.group(1))
                years.append(f"{y - 1}-{str(y)[2:]}")
                cols.append(j)
        if len(years) >= 2:
            return i, years, cols
    return None


def melt_key_aggregates(path: Path, *, source_id: str) -> list[dict]:
    """Melt current-price GDP / GNI style rows from ASNA/QNA key tables."""
    out: list[dict] = []
    xl = pd.ExcelFile(path)
    sheet = "Data1" if "Data1" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    # Prefer series in columns with Series ID rows (ABS Time Series Workbook style)
    headers = [str(c) if pd.notna(c) else "" for c in df.iloc[0].tolist()]
    # Find GDP current price column
    targets = []
    for j, h in enumerate(headers):
        if j == 0:
            continue
        hl = h.lower()
        if "gross domestic product" in hl and "current prices" in hl:
            targets.append((j, "GDP current prices", "gdp_current"))
        elif "gross domestic product" in hl and ("chain volume" in hl or "chain-volume" in hl):
            targets.append((j, "GDP chain volume", "gdp_chain_volume"))
        elif "gross national income" in hl and "current prices" in hl:
            targets.append((j, "GNI current prices", "gdp_current"))
    if not targets:
        # fallback: first numeric series labeled GDP
        for j, h in enumerate(headers):
            if j and re.search(r"\bGDP\b", h, re.I):
                measure = "gdp_chain_volume" if re.search(r"chain", h, re.I) else "gdp_current"
                targets.append((j, h.split(";")[0].strip()[:80] or "GDP", measure))
                break
    latest_i = None
    latest_fy = None
    for i in range(10, len(df)):
        ts = pd.to_datetime(df.iloc[i, 0], errors="coerce")
        if pd.isna(ts):
            continue
        if ts.month == 6:
            latest_fy = f"{ts.year - 1}-{str(ts.year)[2:]}"
            latest_i = i
    if latest_i is None:
        return out
    for j, label, measure in targets:
        val = df.iloc[latest_i, j]
        if pd.isna(val):
            continue
        try:
            amount = float(val) * 1_000_000
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "fy": latest_fy,
                "category": label,
                "amount": amount,
                "jurisdiction": "Australia",
                "government_level": "federal",
                "measure_type": measure,
                "locator": f"source:{source_id} | sheet:{sheet} | series:{label} | fy:{latest_fy}",
                "landing_url": "https://www.abs.gov.au/",
                "resource_url": "https://www.abs.gov.au/",
            }
        )
    return out


def melt_expenditure_components(path: Path, *, source_id: str) -> list[dict]:
    """Melt major expenditure-on-GDP current-price components (latest FY)."""
    df = pd.read_excel(path, sheet_name="Data1", header=None)
    headers = [str(c) if pd.notna(c) else "" for c in df.iloc[0].tolist()]
    want = [
        ("final consumption expenditure", "Final consumption expenditure"),
        ("gross fixed capital formation", "Gross fixed capital formation"),
        ("changes in inventories", "Changes in inventories"),
        ("exports of goods and services", "Exports of goods and services"),
        ("imports of goods and services", "Imports of goods and services"),
    ]
    cols = []
    for j, h in enumerate(headers):
        if j == 0:
            continue
        hl = h.lower()
        if "current prices" not in hl and "current price" not in hl:
            continue
        for needle, label in want:
            if needle in hl:
                cols.append((j, label))
                break
    latest_i = None
    latest_fy = None
    for i in range(10, len(df)):
        ts = pd.to_datetime(df.iloc[i, 0], errors="coerce")
        if pd.isna(ts):
            continue
        if ts.month == 6:
            latest_fy = f"{ts.year - 1}-{str(ts.year)[2:]}"
            latest_i = i
    if latest_i is None:
        return []
    rows = []
    for j, label in cols:
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
                "category": f"Expenditure on GDP / {label}",
                "amount": amount,
                "jurisdiction": "Australia",
                "government_level": "federal",
                "locator": f"source:{source_id} | sheet:Data1 | component:{label} | fy:{latest_fy}",
                "landing_url": "https://www.abs.gov.au/",
                "resource_url": "https://www.abs.gov.au/",
            }
        )
    return rows


def melt_gsp(path: Path, *, source_id: str, juris: str, level: str) -> list[dict]:
    df = pd.read_excel(path, sheet_name="Data1", header=None)
    headers = [str(c) if pd.notna(c) else "" for c in df.iloc[0].tolist()]
    gsp_cols = []
    for j, h in enumerate(headers):
        if j == 0:
            continue
        hl = h.lower()
        if "gross state product" in hl and "current prices" in hl:
            gsp_cols.append((j, "GSP current prices", "gsp_current"))
        elif "gross state product" in hl and "chain" in hl:
            gsp_cols.append((j, "GSP chain volume", "gdp_chain_volume"))
    latest_i = None
    latest_fy = None
    for i in range(10, len(df)):
        ts = pd.to_datetime(df.iloc[i, 0], errors="coerce")
        if pd.isna(ts):
            continue
        if ts.month == 6:
            latest_fy = f"{ts.year - 1}-{str(ts.year)[2:]}"
            latest_i = i
    if latest_i is None:
        return []
    rows = []
    for j, label, measure in gsp_cols:
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
                "category": f"{juris} / {label}",
                "amount": amount,
                "jurisdiction": juris,
                "government_level": level,
                "measure_type": measure,
                "locator": f"source:{source_id} | gsp:{label} | fy:{latest_fy}",
                "landing_url": "https://www.abs.gov.au/",
                "resource_url": "https://www.abs.gov.au/",
            }
        )
    return rows


def _ingest_multi_measure(rows: list[dict], *, source_id: str, title: str, cached: str) -> dict:
    if not rows:
        return {"source_id": source_id, "rows": 0}
    STAGING.mkdir(parents=True, exist_ok=True)
    by_measure: dict[str, list] = {}
    for r in rows:
        by_measure.setdefault(r.get("measure_type") or "gdp_current", []).append(r)
    parts = []
    for measure, mrows in by_measure.items():
        sid = f"{source_id}_{measure}" if len(by_measure) > 1 else source_id
        csv_path = STAGING / f"{sid}.csv"
        pd.DataFrame(mrows).to_csv(csv_path, index=False)
        doc = {
            "source_id": sid,
            "title": f"{title} ({measure})",
            "publisher": "Australian Bureau of Statistics",
            "jurisdiction": mrows[0]["jurisdiction"],
            "government_level": mrows[0]["government_level"],
            "source_family": "abs_gdp_tax",
            "measure_type": measure,
            "accounting_basis": "not_applicable",
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
        mpath = MAPPINGS / f"{sid}.yaml"
        mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
        parts.append(run_mapping(mpath, FACTS_DB))
    return {"source_id": source_id, "parts": parts}


def derive_tax_to_gdp(conn) -> dict:
    """Create tax_to_gdp_ratio facts where FY matches Commonwealth tax and GDP."""
    gdp = conn.execute(
        """
        SELECT f.financial_year, f.amount_aud, f.fact_key
        FROM facts f
        WHERE f.measure_type IN ('gdp_current')
          AND f.source_document_id IN (
            SELECT id FROM source_documents WHERE source_key LIKE 'abs_asna%'
               OR source_key LIKE '%gdp%' OR source_key LIKE '%key_aggregates%'
          )
        ORDER BY f.amount_aud DESC
        """
    ).fetchall()
    # Prefer largest GDP current for each FY (true GDP over components)
    gdp_by_fy: dict[str, tuple[float, str]] = {}
    for fy, amount, key in gdp:
        prev = gdp_by_fy.get(fy)
        if prev is None or float(amount) > prev[0]:
            gdp_by_fy[fy] = (float(amount), key)
    tax = conn.execute(
        """
        SELECT f.financial_year, SUM(f.amount_aud), MIN(f.fact_key)
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE f.measure_type = 'tax_revenue'
          AND d.government_level = 'federal'
        GROUP BY f.financial_year
        """
    ).fetchall()
    rows = []
    for fy, tax_sum, tax_key in tax:
        if fy not in gdp_by_fy or gdp_by_fy[fy][0] <= 0:
            continue
        gdp_amt, gdp_key = gdp_by_fy[fy]
        ratio = float(tax_sum) / gdp_amt
        rows.append(
            {
                "fy": fy,
                "category": "Taxation revenue as % of GDP",
                "amount": round(ratio * 100, 4),  # store as percent points * still amount_aud
                "jurisdiction": "Australia",
                "government_level": "federal",
                "locator": (
                    f"derived:tax_to_gdp | numerator:{tax_key} | denominator:{gdp_key} | "
                    f"tax_aud:{tax_sum} | gdp_aud:{gdp_amt}"
                ),
                "landing_url": "https://www.abs.gov.au/",
                "resource_url": "https://www.abs.gov.au/",
                "numerator_fact_key": tax_key,
                "denominator_fact_key": gdp_key,
            }
        )
    if not rows:
        return {"derived_tax_to_gdp": 0}
    STAGING.mkdir(parents=True, exist_ok=True)
    csv_path = STAGING / "derived_tax_to_gdp_ratio.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return write_and_ingest(
        rows,
        source_id="derived_tax_to_gdp_ratio",
        measure_type="tax_to_gdp_ratio",
        title="Derived Commonwealth tax to GDP ratio",
        cached=str(csv_path.relative_to(REPO_ROOT)),
    )


def main() -> int:
    migrate(FACTS_DB)
    import sqlite3

    out = []
    for sid, title, melter in [
        (
            "abs_asna_key_aggregates_2024_25",
            "ABS ASNA key aggregates",
            lambda p: melt_key_aggregates(p, source_id="abs_asna_key_aggregates_2024_25"),
        ),
        (
            "abs_asna_expenditure_gdp_2024_25",
            "ABS ASNA expenditure on GDP",
            lambda p: melt_expenditure_components(p, source_id="abs_asna_expenditure_gdp_2024_25"),
        ),
        (
            "abs_qna_key_aggregates_mar_2026",
            "ABS QNA key aggregates",
            lambda p: melt_key_aggregates(p, source_id="abs_qna_key_aggregates_mar_2026"),
        ),
    ]:
        try:
            path = _resolve(sid)
        except FileNotFoundError:
            out.append({"source_id": sid, "status": "missing"})
            continue
        rows = melter(path)
        if sid.endswith("expenditure_gdp_2024_25"):
            out.append(
                write_and_ingest(
                    rows,
                    source_id=sid,
                    measure_type="gdp_current",
                    title=title,
                    cached=str(path.relative_to(REPO_ROOT)),
                )
            )
        else:
            out.append(
                _ingest_multi_measure(
                    rows,
                    source_id=sid,
                    title=title,
                    cached=str(path.relative_to(REPO_ROOT)),
                )
            )

    for sid, (juris, level) in STATE_ACCOUNT_IDS.items():
        try:
            path = _resolve(sid)
        except FileNotFoundError:
            out.append({"source_id": sid, "status": "missing"})
            continue
        rows = melt_gsp(path, source_id=sid, juris=juris, level=level)
        out.append(
            _ingest_multi_measure(
                rows,
                source_id=sid,
                title=f"ABS State Accounts GSP — {juris}",
                cached=str(path.relative_to(REPO_ROOT)),
            )
        )

    conn = sqlite3.connect(str(FACTS_DB))
    out.append(derive_tax_to_gdp(conn))
    conn.close()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

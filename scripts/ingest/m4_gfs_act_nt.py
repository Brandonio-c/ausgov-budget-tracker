#!/usr/bin/env python3
"""M4: ABS GFS ×16 Table_4 + ACT invoices + NT contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters.abs_gfs import JURISDICTION_MAP, export_source  # noqa: E402
from run import run_mapping  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "m4"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"


def write_mapping(meta: dict) -> Path:
    doc = {
        "source_id": meta["source_id"],
        "title": meta.get("title", meta["source_id"]),
        "publisher": meta.get("publisher", "ABS"),
        "jurisdiction": meta["jurisdiction"],
        "government_level": meta["government_level"],
        "source_family": meta.get("source_family", "gfs"),
        "measure_type": meta["measure_type"],
        "accounting_basis": meta["accounting_basis"],
        "estimate_status": meta["estimate_status"],
        "period_granularity": meta.get("period_granularity", "financial_year"),
        "input": {"path": str(Path(meta["path"]).relative_to(REPO_ROOT)), "format": "csv"},
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
    path = MAPPINGS / f"{meta['source_id']}.yaml"
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return path


def export_act() -> dict:
    src = REPO_ROOT / "data/raw/territory/act_notifiable_invoices"
    data = json.loads((src / "latest.json").read_text())
    asset = data["assets"][0]
    fp = REPO_ROOT / "data" / asset["stored_path"]
    df = pd.read_csv(fp)
    # Derive FY from Payment Date
    def to_fy(s):
        try:
            dt = pd.to_datetime(s, dayfirst=False, errors="coerce")
            if pd.isna(dt):
                return None
            y = dt.year if dt.month >= 7 else dt.year - 1
            return f"{y}-{str(y+1)[-2:]}"
        except Exception:
            return None

    out_rows = []
    for idx, r in df.iterrows():
        fy = to_fy(r.get("Payment Date"))
        if not fy:
            continue
        amount = r.get("Payment Amount")
        if pd.isna(amount):
            continue
        entity = str(r.get("Reporting Entity") or "ACT")
        desc = str(r.get("Publish Description") or r.get("Supplier Name") or "invoice")[:120]
        out_rows.append(
            {
                "fy": fy,
                "amount": float(amount),
                "category": f"{entity} / {desc}",
                "locator": f"csv:row:{idx+2} | payment_date:{r.get('Payment Date')} | contract:{r.get('Contract Number')}",
                "landing_url": "https://www.data.act.gov.au/Government/Notifiable-Invoices-Register/kzmf-7uhp",
                "resource_url": asset.get("final_url") or asset.get("requested_url"),
            }
        )
    out = STAGING / "act_notifiable_invoices.csv"
    STAGING.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out_rows).to_csv(out, index=False)
    return {
        "source_id": "act_notifiable_invoices",
        "path": out,
        "rows": len(out_rows),
        "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
        "jurisdiction": "ACT",
        "government_level": "territory",
        "publisher": "ACT Government",
        "title": "ACT Notifiable Invoices Register",
        "source_family": "territory_actuals",
        "measure_type": "invoice_paid",
        "accounting_basis": "cash",
        "estimate_status": "invoice",
    }


def export_nt() -> dict:
    src = REPO_ROOT / "data/raw/territory/nt_awarded_government_contracts"
    data = json.loads((src / "latest.json").read_text())
    asset = data["assets"][0]
    fp = REPO_ROOT / "data" / asset["stored_path"]
    df = pd.read_excel(fp, sheet_name=0, header=0)

    def parse_amount(v):
        if pd.isna(v):
            return None
        s = re.sub(r"[^0-9.]", "", str(v))
        try:
            return float(s) if s else None
        except ValueError:
            return None

    def to_fy(s):
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            return "2025-26"
        y = dt.year if dt.month >= 7 else dt.year - 1
        return f"{y}-{str(y+1)[-2:]}"

    rows = []
    for idx, r in df.iterrows():
        amount = parse_amount(r.get("Amount"))
        if amount is None:
            continue
        tender = str(r.get("Tender Number") or idx)
        title = str(r.get("Title") or "contract")[:120]
        rows.append(
            {
                "fy": to_fy(r.get("Tender Award Date")),
                "amount": amount,
                "category": f"{tender} / {title}",
                "locator": f"sheet:Awarded Contracts | row:{idx+2} | tender:{tender}",
                "landing_url": "https://tendersonline.nt.gov.au/",
                "resource_url": asset.get("requested_url")
                or "https://tendersonline.nt.gov.au/",
            }
        )
    out = STAGING / "nt_awarded_government_contracts.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return {
        "source_id": "nt_awarded_government_contracts",
        "path": out,
        "rows": len(rows),
        "cached_copy_path": str(fp.relative_to(REPO_ROOT)),
        "jurisdiction": "NT",
        "government_level": "territory",
        "publisher": "Northern Territory Government",
        "title": "NT Awarded Government Contracts",
        "source_family": "procurement_contracts",
        "measure_type": "contract_value",
        "accounting_basis": "commitment",
        "estimate_status": "contract",
    }


def main() -> int:
    summaries = []
    # Shared template note
    (MAPPINGS / "templates" / "abs_gfs_table4.yaml").write_text(
        "# Shared ABS GFS Table_4 melt template (see adapters/abs_gfs.py).\n"
        "# All abs_gfs_* jurisdiction workbooks share sheets Contents+Table_1..4.\n"
        "measure_type: gfs_expense\naccounting_basis: gfs\nestimate_status: actual\n",
        encoding="utf-8",
    )

    for source_id in JURISDICTION_MAP:
        meta = export_source(source_id, STAGING)
        meta.update(
            {
                "publisher": "Australian Bureau of Statistics",
                "title": f"ABS GFS Expenses by Purpose — {source_id}",
                "source_family": "abs_gfs",
                "measure_type": "gfs_expense",
                "accounting_basis": "gfs",
                "estimate_status": "actual",
            }
        )
        mpath = write_mapping(meta)
        summaries.append(run_mapping(mpath, FACTS_DB))

    for exporter in (export_act, export_nt):
        meta = exporter()
        mpath = write_mapping(meta)
        summaries.append(run_mapping(mpath, FACTS_DB))

    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    territory = conn.execute(
        """
        SELECT d.government_level, COUNT(*) FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE d.government_level = 'territory'
        GROUP BY 1
        """
    ).fetchall()
    pub = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    pend = conn.execute("SELECT COUNT(*) FROM facts_pending_attribution").fetchone()[0]
    conn.close()
    print(json.dumps({"summaries": summaries, "territory_facts": territory, "facts": pub, "pending": pend}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

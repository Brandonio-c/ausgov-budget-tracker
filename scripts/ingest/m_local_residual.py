#!/usr/bin/env python3
"""Residual local government structured returns + QAO limit notes."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
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
OPS = REPO_ROOT / "ops" / "reports"


def _resolve(source_id: str) -> tuple[Path, str] | None:
    matches = [
        m
        for m in (REPO_ROOT / "data" / "raw").rglob(source_id)
        if m.is_dir() and (m / "latest.json").exists()
    ]
    if not matches:
        return None
    data = json.loads((matches[0] / "latest.json").read_text(encoding="utf-8"))
    for asset in data.get("assets") or []:
        stored = asset.get("stored_path") or ""
        path = REPO_ROOT / "data" / stored
        if not path.exists():
            path = REPO_ROOT / stored
        if path.exists() and path.suffix.lower() in {".xlsx", ".xls", ".csv"}:
            return path, asset.get("requested_url") or ""
    return None


def ingest_nsw_grants() -> dict:
    sid = "nsw_local_grants_commission"
    resolved = _resolve(sid)
    path = None
    url = ""
    if resolved:
        path, url = resolved
    else:
        # ZIP-only acquisition: unpack first spreadsheet
        matches = [
            m
            for m in (REPO_ROOT / "data" / "raw").rglob(sid)
            if m.is_dir() and (m / "latest.json").exists()
        ]
        if not matches:
            return {"source_id": sid, "status": "missing"}
        data = json.loads((matches[0] / "latest.json").read_text(encoding="utf-8"))
        for asset in data.get("assets") or []:
            stored = asset.get("stored_path") or ""
            zpath = REPO_ROOT / "data" / stored
            if not zpath.exists():
                zpath = REPO_ROOT / stored
            if zpath.suffix.lower() != ".zip" or not zpath.exists():
                continue
            url = asset.get("requested_url") or ""
            unpack = STAGING / "nsw_grants_unpacked"
            unpack.mkdir(parents=True, exist_ok=True)
            import zipfile

            with zipfile.ZipFile(zpath) as zf:
                zf.extractall(unpack)
            cands = sorted(unpack.rglob("*.xlsx")) + sorted(unpack.rglob("*.xls")) + sorted(
                unpack.rglob("*.csv")
            )
            if cands:
                path = cands[0]
                break
            pdfs = sorted(unpack.rglob("*.pdf"))
            if pdfs:
                return {
                    "source_id": sid,
                    "status": "pdf_only_no_structured_xlsx",
                    "reason": (
                        "NSW grants commission capture is a ZIP of payment-schedule PDFs; "
                        "no machine-readable XLSX schedule was present. Prefer OLG time-series "
                        "already ingested via m5_local_government."
                    ),
                    "pdf_count": len(pdfs),
                    "report_note": "Documented under local residual gaps.",
                }
    if path is None:
        return {"source_id": sid, "status": "missing"}
    xl = pd.ExcelFile(path)
    sheet = xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    # Find a header row with council + grant-like columns
    header_i = 0
    for i in range(min(20, len(df))):
        vals = [str(v).lower() if pd.notna(v) else "" for v in df.iloc[i].tolist()[:12]]
        if any("council" in v or "lga" in v for v in vals) and any(
            "grant" in v or "total" in v or "amount" in v for v in vals
        ):
            header_i = i
            break
    headers = [
        re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) else f"col{j}"
        for j, v in enumerate(df.iloc[header_i].tolist())
    ]
    council_j = next(
        (j for j, h in enumerate(headers) if re.search(r"council|lga|authority", h, re.I)),
        0,
    )
    value_cols = [
        (j, h[:80])
        for j, h in enumerate(headers)
        if j != council_j and re.search(r"grant|total|financial assistance|road|local", h, re.I)
    ][:6]
    if not value_cols:
        value_cols = [(j, headers[j][:80] or f"metric_{j}") for j in range(council_j + 1, min(council_j + 4, len(headers)))]
    rows = []
    for i in range(header_i + 1, len(df)):
        council = df.iloc[i, council_j]
        if pd.isna(council):
            continue
        council = re.sub(r"\s+", " ", str(council)).strip()
        if not council or council.lower().startswith("total"):
            continue
        for j, label in value_cols:
            val = df.iloc[i, j]
            if pd.isna(val):
                continue
            try:
                amount = float(val)
            except (TypeError, ValueError):
                continue
            if abs(amount) < 1:
                continue
            if abs(amount) < 1_000_000:
                amount *= 1000
            rows.append(
                {
                    "fy": "2024-25",
                    "category": f"NSW / {council} / {label}",
                    "amount": amount,
                    "locator": f"source:{sid} | sheet:{sheet} | council:{council} | metric:{label}",
                    "landing_url": url,
                    "resource_url": url,
                }
            )
    if not rows:
        return {"source_id": sid, "status": "no_rows", "path": str(path)}
    STAGING.mkdir(parents=True, exist_ok=True)
    csv_path = STAGING / f"{sid}_residual.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    source_id = f"{sid}_grants_residual"
    doc = {
        "source_id": source_id,
        "title": "NSW Local Grants Commission schedules (residual)",
        "publisher": "NSW Local Government Grants Commission",
        "jurisdiction": "NSW",
        "government_level": "local",
        "source_family": "local_government",
        "measure_type": "grant_revenue",
        "accounting_basis": "cash",
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
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
        ),
    }
    import sqlite3

    conn = sqlite3.connect(str(FACTS_DB))
    conn.execute(
        "INSERT OR IGNORE INTO measure_definitions "
        "(measure_type, label, description, additive_across_time, additive_across_nodes, "
        "default_accounting_basis, compatibility_group) "
        "VALUES ('grant_revenue', 'Grant revenue', 'Local grants commission revenue', "
        "0, 1, 'cash', 'gfs_revenue')"
    )
    conn.commit()
    conn.close()
    mpath = MAPPINGS / f"{source_id}.yaml"
    mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    return {"source_id": source_id, "rows": len(rows), "ingest": run_mapping(mpath, FACTS_DB)}


def document_qao_limits() -> dict:
    notes = []
    for sid in ("qld_local_qao_2025", "qld_qao_local_government_2025"):
        matches = list((REPO_ROOT / "data" / "raw").rglob(f"{sid}/latest.json"))
        if not matches:
            notes.append({"source_id": sid, "status": "not_acquired"})
            continue
        data = json.loads(matches[0].read_text(encoding="utf-8"))
        assets = data.get("assets") or []
        pdfs = [a for a in assets if str(a.get("stored_path", "")).lower().endswith(".pdf")]
        notes.append(
            {
                "source_id": sid,
                "status": "no_useful_fiscal_data" if pdfs else "partial",
                "reason": (
                    "QAO local government PDF is narrative / audit-focused; "
                    "structured council liability tables are not reliably extractable "
                    "without agency-specific layouts. Prefer VLGGC/OLG/CDC machine-readable returns."
                ),
                "pdf_assets": len(pdfs),
            }
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OPS.mkdir(parents=True, exist_ok=True)
    path = OPS / f"local-qao-limits-{stamp}.md"
    lines = ["# Local QAO extraction limits\n"]
    for n in notes:
        lines.append(f"- `{n['source_id']}`: **{n['status']}** — {n.get('reason', '')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"report": str(path.relative_to(REPO_ROOT)), "notes": notes}


def main() -> int:
    migrate(FACTS_DB)
    # Reuse VIC ABS2-3 runner
    from m_vic_local_abs23 import main as vic_main

    vic_main()
    out = {
        "nsw_grants": ingest_nsw_grants(),
        "qao": document_qao_limits(),
    }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

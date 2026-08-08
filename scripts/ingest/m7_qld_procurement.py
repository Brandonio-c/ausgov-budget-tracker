#!/usr/bin/env python3
"""M7: QLD QGIP + Contract Disclosure with schema-variance auto decision."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import run_mapping  # noqa: E402

STAGING = REPO_ROOT / "data" / "staging" / "m7"
MAPPINGS = REPO_ROOT / "config" / "mappings"
FACTS_DB = REPO_ROOT / "data" / "facts.db"


def _norm_cols(cols) -> tuple[str, ...]:
    out = []
    for c in cols:
        s = re.sub(r"\s+", " ", str(c).strip().lower())
        s = re.sub(r"[^a-z0-9 ]", "", s)
        out.append(s)
    return tuple(out)


def analyze_disclosure_schemas(sample_n: int = 20) -> dict:
    src = REPO_ROOT / "data/raw/state/qld_contract_disclosure_agency_datasets"
    data = json.loads((src / "latest.json").read_text())
    assets = [a for a in data["assets"] if (a.get("detected_type") == "csv")]
    # sample first N + spread
    step = max(1, len(assets) // sample_n)
    sample = assets[::step][:sample_n]
    schemas = []
    for a in sample:
        fp = REPO_ROOT / "data" / a["stored_path"]
        try:
            df = pd.read_csv(fp, nrows=5, dtype=str, encoding_errors="replace")
            schemas.append(
                {
                    "file": a.get("original_filename") or fp.name,
                    "path": str(fp.relative_to(REPO_ROOT)),
                    "cols": list(df.columns),
                    "norm": _norm_cols(df.columns),
                }
            )
        except Exception as e:
            schemas.append({"file": a.get("original_filename"), "error": str(e)})
    counts = Counter(s["norm"] for s in schemas if "norm" in s)
    if not counts:
        return {"sample_size": 0, "decision": "blocked", "schemas": schemas}
    dominant, dom_n = counts.most_common(1)[0]
    ratio = dom_n / sum(counts.values())
    decision = "single_mapping" if ratio >= 0.9 else "split_mappings"
    exceptions = [s for s in schemas if s.get("norm") and s["norm"] != dominant]
    return {
        "sample_size": len(schemas),
        "unique_schemas": len(counts),
        "dominant_share": ratio,
        "decision": decision,
        "dominant_cols": list(dominant),
        "exceptions": exceptions,
        "schemas": schemas,
    }


def export_qgip() -> dict:
    src = REPO_ROOT / "data/raw/state/qld_qgip_expenditure"
    data = json.loads((src / "latest.json").read_text())
    assets = [a for a in data["assets"] if a.get("detected_type") == "csv"]
    landing = "https://www.data.qld.gov.au/"
    rows = []
    cached = None
    for a in assets:
        fp = REPO_ROOT / "data" / a["stored_path"]
        if cached is None:
            cached = fp
        try:
            df = pd.read_csv(fp, dtype=str, encoding_errors="replace")
        except Exception:
            continue
        cols = { _norm_cols([c])[0]: c for c in df.columns }
        # find amount / agency / category-ish
        amount_col = next((cols[k] for k in cols if "amount" in k or "expenditure" in k or "value" in k or "total" in k), None)
        agency_col = next((cols[k] for k in cols if "agency" in k or "department" in k or "entity" in k), None)
        cat_col = next((cols[k] for k in cols if "category" in k or "description" in k or "supplier" in k or "program" in k), None)
        fy_col = next(
            (cols[k] for k in cols if k in {"fy", "financial year", "year"}),
            None,
        )
        if fy_col is None:
            fy_col = next(
                (
                    cols[k]
                    for k in cols
                    if "financial year" in k
                    and not any(
                        token in k for token in ("amount", "expenditure", "value", "total")
                    )
                ),
                None,
            )
        fy_guess = None
        m = re.search(r"(20\d{2})\D?(\d{2})", a.get("original_filename") or fp.name)
        if m:
            fy_guess = f"{m.group(1)}-{m.group(2)}"
        resource = a.get("final_url") or a.get("requested_url") or landing
        for idx, r in df.iterrows():
            if amount_col is None:
                break
            raw = r.get(amount_col)
            if pd.isna(raw) or raw is None or str(raw).strip() == "":
                continue
            try:
                amount = float(re.sub(r"[^0-9.-]", "", str(raw)))
            except ValueError:
                continue
            agency = str(r.get(agency_col) or "QLD").strip() if agency_col else "QLD"
            cat = str(r.get(cat_col) or "expenditure").strip() if cat_col else "expenditure"
            agency = re.sub(r"\s+", " ", agency)
            cat = re.sub(r"\s+", " ", cat)
            fy = str(r.get(fy_col) or fy_guess or "2024-25")
            if re.match(r"20\d{2}$", fy):
                y = int(fy)
                fy = f"{y}-{str(y+1)[-2:]}"
            rows.append(
                {
                    "fy": fy if re.match(r"\d{4}-\d{2}", fy) else (fy_guess or "2024-25"),
                    "amount": amount,
                    "category": f"{agency} / {cat}"[:240],
                    "locator": f"file:{fp.name} | row:{idx+2} | amount_col:{amount_col}",
                    "landing_url": landing,
                    "resource_url": resource,
                    "agency": agency,
                }
            )
    out = STAGING / "qld_qgip_expenditure.csv"
    STAGING.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    return {
        "source_id": "qld_qgip_expenditure",
        "csv": out,
        "cached_copy_path": str(cached.relative_to(REPO_ROOT)),
        "title": "QLD QGIP expenditure consolidated",
        "publisher": "Queensland Government",
        "jurisdiction": "QLD",
        "government_level": "state",
        "source_family": "state_actuals",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "actual",
        "rows": len(rows),
    }


def export_disclosure(analysis: dict, max_files: int = 40) -> dict:
    src = REPO_ROOT / "data/raw/state/qld_contract_disclosure_agency_datasets"
    data = json.loads((src / "latest.json").read_text())
    assets = [a for a in data["assets"] if a.get("detected_type") == "csv"]
    dominant = tuple(analysis["dominant_cols"])
    landing = "https://www.data.qld.gov.au/"
    rows = []
    cached = None
    used = 0
    for a in assets:
        if used >= max_files:
            break
        fp = REPO_ROOT / "data" / a["stored_path"]
        try:
            df = pd.read_csv(fp, dtype=str, encoding_errors="replace")
        except Exception:
            continue
        norm = _norm_cols(df.columns)
        if analysis["decision"] == "single_mapping" and norm != dominant:
            continue  # exceptions documented, not force-fit
        used += 1
        if cached is None:
            cached = fp
        cols = { _norm_cols([c])[0]: c for c in df.columns }
        amount_col = next((cols[k] for k in cols if any(x in k for x in ("value", "amount", "contract value", "total"))), None)
        supplier_col = next((cols[k] for k in cols if "supplier" in k or "contractor" in k or "vendor" in k), None)
        agency_col = next((cols[k] for k in cols if "agency" in k or "department" in k), None)
        title_col = next((cols[k] for k in cols if "title" in k or "description" in k or "contract" in k), None)
        resource = a.get("final_url") or a.get("requested_url") or landing
        fy_guess = "2024-25"
        m = re.search(r"(20\d{2})\D?(\d{2})", a.get("original_filename") or "")
        if m:
            fy_guess = f"{m.group(1)}-{m.group(2)}"
        for idx, r in df.iterrows():
            if amount_col is None:
                break
            raw = r.get(amount_col)
            if pd.isna(raw) or raw is None or str(raw).strip() == "":
                continue
            try:
                amount = float(re.sub(r"[^0-9.-]", "", str(raw)))
            except ValueError:
                continue
            supplier = str(r.get(supplier_col) or "supplier")[:80] if supplier_col else "supplier"
            agency = str(r.get(agency_col) or "QLD agency")[:80] if agency_col else "QLD agency"
            title = str(r.get(title_col) or fp.stem)[:100] if title_col else fp.stem
            rows.append(
                {
                    "fy": fy_guess,
                    "amount": amount,
                    "category": f"{agency} / {supplier} / {title}"[:240],
                    "locator": f"file:{fp.name} | row:{idx+2}",
                    "landing_url": landing,
                    "resource_url": resource,
                    "agency": agency,
                }
            )
    out = STAGING / "qld_contract_disclosure_agency_datasets.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return {
        "source_id": "qld_contract_disclosure_agency_datasets",
        "csv": out,
        "cached_copy_path": str((cached or STAGING).relative_to(REPO_ROOT)) if cached else "data/staging/m7",
        "title": "QLD agency contract disclosure (dominant schema)",
        "publisher": "Queensland Government agencies",
        "jurisdiction": "QLD",
        "government_level": "state",
        "source_family": "procurement_contracts",
        "measure_type": "contract_value",
        "accounting_basis": "commitment",
        "estimate_status": "contract",
        "rows": len(rows),
        "files_used": used,
    }


def write_and_run(meta: dict) -> dict:
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


def seed_agency_entities(csv_path: Path) -> int:
    import sqlite3

    df = pd.read_csv(csv_path, usecols=lambda c: c in {"agency", "fy"})
    if "agency" not in df.columns:
        return 0
    conn = sqlite3.connect(str(FACTS_DB))
    n = 0
    for agency, g in df.groupby("agency"):
        years = sorted(set(str(y) for y in g["fy"].dropna()))
        if not years:
            continue
        valid_from = years[0][:4] + "-07-01"
        # open-ended until known rename
        conn.execute(
            """
            INSERT OR IGNORE INTO entities
                (canonical_name, entity_type, jurisdiction, government_level,
                 valid_from, valid_to)
            VALUES (?, 'agency', 'QLD', 'state', ?, NULL)
            """,
            (str(agency)[:200], valid_from),
        )
        n += 1
    conn.commit()
    conn.close()
    return n


def main() -> int:
    analysis = analyze_disclosure_schemas(20)
    exceptions_path = REPO_ROOT / "ops" / "reports" / "m7-schema-exceptions.md"
    lines = [
        "# M7 QLD contract disclosure — schema exceptions",
        "",
        f"Sample size: {analysis['sample_size']}",
        f"Unique schemas: {analysis.get('unique_schemas')}",
        f"Dominant share: {analysis.get('dominant_share')}",
        f"Decision: **{analysis.get('decision')}** (≥90% identical → single mapping)",
        "",
        "## Dominant normalised columns",
        "",
        "```",
        "\n".join(analysis.get("dominant_cols") or []),
        "```",
        "",
        "## Exceptions (not force-fit)",
        "",
    ]
    for ex in analysis.get("exceptions") or []:
        lines.append(f"- `{ex.get('file')}` cols={ex.get('cols')}")
    exceptions_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    qgip = export_qgip()
    disc = export_disclosure(analysis)
    s1 = write_and_run(qgip)
    s2 = write_and_run(disc)
    entities = seed_agency_entities(disc["csv"]) + seed_agency_entities(qgip["csv"])
    print(
        json.dumps(
            {
                "schema_decision": analysis["decision"],
                "dominant_share": analysis["dominant_share"],
                "qgip": s1,
                "disclosure": s2,
                "entities_seeded": entities,
                "exceptions_doc": str(exceptions_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

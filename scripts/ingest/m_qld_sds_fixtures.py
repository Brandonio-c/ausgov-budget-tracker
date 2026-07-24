#!/usr/bin/env python3
"""Targeted QLD SDS table extract for high-spend agencies; mark others unreliable."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extractors import iter_pdf_pages  # noqa: E402
from run import run_mapping  # noqa: E402
from schema_migrate import migrate  # noqa: E402

FACTS_DB = REPO_ROOT / "data" / "facts.db"
STAGING = REPO_ROOT / "data" / "staging" / "state"
MAPPINGS = REPO_ROOT / "config" / "mappings"
OPS = REPO_ROOT / "ops" / "reports"

# High-spend agencies only (plan: 2–3 fixtures)
TARGET_SOURCES = {
    "qld_sds_2026_27_health": "Queensland Health",
    "qld_sds_2026_27_education": "Department of Education",
    "qld_sds_2026_27_transport_main_roads": "Transport and Main Roads",
}

AMOUNT_RE = re.compile(
    r"(?P<label>.{6,100}?)\s+(?P<a>-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)\s*$"
)


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
        if not stored.lower().endswith(".pdf"):
            continue
        path = REPO_ROOT / "data" / stored
        if not path.exists():
            path = REPO_ROOT / stored
        if path.exists():
            return path, asset.get("requested_url") or ""
    return None


def extract_budgeted_expenses(pdf: Path, *, agency: str, source_id: str, url: str) -> list[dict]:
    rows: list[dict] = []
    for page_no, text in iter_pdf_pages(pdf):
        if not re.search(r"budgeted|expenses|controlled|administered", text, re.I):
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or len(line) < 10:
                continue
            if not re.search(r"expense|employee|supplies|grant|depreciation|total", line, re.I):
                continue
            m = AMOUNT_RE.match(line)
            if not m:
                continue
            label = re.sub(r"\s+", " ", m.group("label")).strip()
            if re.search(r"^total\b", label, re.I):
                continue
            try:
                # SDS tables are typically $'000
                amount = float(m.group("a").replace(",", "")) * 1000
            except ValueError:
                continue
            if amount < 100_000:
                continue
            rows.append(
                {
                    "fy": "2026-27",
                    "category": f"QLD / {agency} / {label}",
                    "amount": amount,
                    "locator": (
                        f"source:{source_id} | pdf:{pdf.name} | page:{page_no} | "
                        f"label:{label} | unit:$000"
                    ),
                    "landing_url": url,
                    "resource_url": url,
                }
            )
    # Keep largest distinct labels (page noise)
    best: dict[str, dict] = {}
    for r in rows:
        key = r["category"]
        prev = best.get(key)
        if prev is None or r["amount"] > prev["amount"]:
            best[key] = r
    return list(best.values())[:40]


def main() -> int:
    migrate(FACTS_DB)
    STAGING.mkdir(parents=True, exist_ok=True)
    OPS.mkdir(parents=True, exist_ok=True)
    out = []
    unreliable = []
    # Record remaining SDS PDFs as extraction_unreliable
    for latest in (REPO_ROOT / "data" / "raw").rglob("qld_sds_*/latest.json"):
        sid = latest.parent.name
        if sid in TARGET_SOURCES or sid.startswith("qld_sds_machine"):
            continue
        if re.match(r"qld_sds_\d", sid) or sid.startswith("qld_sds_202"):
            unreliable.append(
                {
                    "source_id": sid,
                    "status": "extraction_unreliable",
                    "reason": "QLD SDS PDF table layouts vary; only Health/Education/Transport fixtures extracted this sprint",
                }
            )

    for sid, agency in TARGET_SOURCES.items():
        resolved = _resolve(sid)
        if not resolved:
            out.append({"source_id": sid, "status": "missing"})
            continue
        path, url = resolved
        rows = extract_budgeted_expenses(path, agency=agency, source_id=sid, url=url)
        if not rows:
            out.append({"source_id": sid, "status": "no_rows", "path": str(path)})
            continue
        csv_path = STAGING / f"{sid}.csv"
        pd.DataFrame(rows).to_csv(csv_path, index=False)
        doc = {
            "source_id": sid,
            "title": f"QLD SDS 2026-27 {agency} budgeted expenses (fixture)",
            "publisher": "Queensland Treasury",
            "jurisdiction": "QLD",
            "government_level": "state",
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
        mpath = MAPPINGS / f"{sid}.yaml"
        mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
        summary = run_mapping(mpath, FACTS_DB)
        out.append({"source_id": sid, "rows": len(rows), "ingest": summary})

    report = {
        "targets": out,
        "extraction_unreliable": unreliable,
        "notes": [
            "Mass OCR of remaining QLD SDS PDFs is an explicit non-goal this sprint.",
            "Fixtures limited to Health, Education, Transport and Main Roads.",
        ],
    }
    stamp = __import__("datetime").datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    (OPS / f"qld-sds-extraction-{stamp}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (OPS / f"qld-sds-extraction-{stamp}.md").write_text(
        "# QLD SDS extraction status\n\n"
        + f"- Fixture agencies ingested: {len([x for x in out if x.get('rows')])}\n"
        + f"- Marked extraction_unreliable: {len(unreliable)}\n"
        + "\n".join(f"- {n}" for n in report["notes"])
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extract Commonwealth defined-benefit superannuation liabilities from CFS / LTCR PDFs."""

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
STAGING = REPO_ROOT / "data" / "staging" / "super"
MAPPINGS = REPO_ROOT / "config" / "mappings"

SCHEME_PATTERNS = [
    (re.compile(r"\bCSS\b|Commonwealth Superannuation Scheme", re.I), "CSS"),
    (re.compile(r"\bPSS\b|Public Sector Superannuation Scheme(?!\s*Accumulation)", re.I), "PSS"),
    (re.compile(r"Military Super|MSBS|ADF Super|DFRDB", re.I), "Military schemes"),
    (re.compile(r"defined benefit superannuation|unfunded superannuation", re.I), "Other schemes"),
]

AMOUNT_RE = re.compile(
    r"(?P<label>.{8,120}?)\s+(?P<a>-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)\s*$"
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


def _parse_millions(tok: str) -> float | None:
    try:
        return float(tok.replace(",", "")) * 1_000_000
    except ValueError:
        return None


def extract_super_rows(pdf: Path, *, source_id: str, source_url: str) -> list[dict]:
    rows: list[dict] = []
    for page_no, text in iter_pdf_pages(pdf):
        if not re.search(r"superannuation|defined benefit|CSS|PSS|MSBS", text, re.I):
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or len(line) < 12:
                continue
            m = AMOUNT_RE.match(line)
            if not m:
                continue
            label = re.sub(r"\s+", " ", m.group("label")).strip()
            scheme = None
            for pattern, name in SCHEME_PATTERNS:
                if pattern.search(label) or pattern.search(line):
                    scheme = name
                    break
            if scheme is None:
                continue
            if not re.search(r"liabilit|provision|obligation|unfunded", label, re.I):
                # Still accept scheme-named liability table lines with large amounts
                if not re.search(r"\b(CSS|PSS|MSBS|DFRDB)\b", label, re.I):
                    continue
            amount = _parse_millions(m.group("a"))
            if amount is None or abs(amount) < 1_000_000:
                continue
            # Heuristic FY from document
            fy = "2024-25"
            rows.append(
                {
                    "fy": fy,
                    "category": f"Provisions for defined-benefit superannuation / {scheme}",
                    "amount": abs(amount),
                    "locator": (
                        f"source:{source_id} | pdf:{pdf.name} | page:{page_no} | "
                        f"label:{label} | scheme:{scheme}"
                    ),
                    "landing_url": source_url,
                    "resource_url": source_url,
                    "observation_date": "2025-06-30",
                    "valuation_basis": "actuarial",
                    "amount_granularity": "scheme_aggregate",
                }
            )
    # Dedupe by scheme keeping largest amount (most likely the liability total)
    best: dict[str, dict] = {}
    for r in rows:
        scheme = r["category"]
        prev = best.get(scheme)
        if prev is None or r["amount"] > prev["amount"]:
            best[scheme] = r
    return list(best.values())


def main() -> int:
    migrate(FACTS_DB)
    STAGING.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    used_sources = []
    for sid in (
        "federal_cfs_2024_25",
        "commonwealth_pss_css_long_term_cost_reports",
        "csc_annual_report_archive",
    ):
        resolved = _resolve(sid)
        if not resolved:
            continue
        path, url = resolved
        rows = extract_super_rows(path, source_id=sid, source_url=url)
        print(json.dumps({"source_id": sid, "rows": len(rows), "pdf": path.name}))
        if rows:
            used_sources.append((sid, path, url, rows))
            all_rows.extend(rows)

    # Prefer CFS rows when duplicate schemes
    best: dict[str, dict] = {}
    for r in all_rows:
        key = r["category"]
        # Prefer CFS source_id in locator
        prev = best.get(key)
        if prev is None:
            best[key] = r
        elif "federal_cfs" in r["locator"] and "federal_cfs" not in prev["locator"]:
            best[key] = r
        elif r["amount"] > prev["amount"] * 1.05:
            best[key] = r
    final_rows = list(best.values())
    if not final_rows:
        print(json.dumps({"status": "no_rows_extracted"}))
        return 0

    source_id = "commonwealth_defined_benefit_super_liabilities"
    csv_path = STAGING / f"{source_id}.csv"
    pd.DataFrame(final_rows).to_csv(csv_path, index=False)
    cached = used_sources[0][1] if used_sources else csv_path
    doc = {
        "source_id": source_id,
        "title": "Commonwealth defined-benefit superannuation liabilities",
        "publisher": "Department of Finance / CSC",
        "jurisdiction": "Commonwealth",
        "government_level": "federal",
        "source_family": "superannuation",
        "measure_type": "superannuation_liability",
        "accounting_basis": "aasb",
        "estimate_status": "audited_actual",
        "period_granularity": "financial_year",
        "valuation_basis": "actuarial",
        "amount_granularity": "scheme_aggregate",
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
            "cached_copy_path": str(Path(cached).relative_to(REPO_ROOT)),
        },
        "fact_key_template": (
            "{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}"
        ),
    }
    mpath = MAPPINGS / f"{source_id}.yaml"
    mpath.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
    summary = run_mapping(mpath, FACTS_DB)
    print(json.dumps({"rows": len(final_rows), "ingest": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

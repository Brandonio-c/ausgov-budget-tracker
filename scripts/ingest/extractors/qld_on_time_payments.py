#!/usr/bin/env python3
"""Extractor for the QLD Government On-Time Payment (small business) quarterly
compliance reports (item 7.5, plan section 7.5).

42 acquired CSV files, one per QLD agency per acquisition batch, independently
published by ~35 different departments/agencies on data.qld.gov.au with no
central consolidation - unlike QGIP's single "consolidated" publisher, each
agency's file has its own filename convention and (found by direct inspection
of all 42 files before writing this) real header-wording drift. Verified
before writing any mapping:

  - 9-column shape is genuinely stable across every file (Quarter, Eligible
    claims for penalty interest, Penalty interest paid, Total eligible and
    undisputed invoices, Invoices paid late, Value of invoices paid late,
    Mean days paid late, Percent of late payments for small business,
    Percent of late payments for others) - all counts/percentages/days/
    payment-values, matching the plan's "Create typed measures for counts,
    percentages, days and payment values" instruction exactly;
  - column 4 ("Total eligible...") has 5 distinct real wording variants
    across files (capitalisation and word-order drift) plus one file where
    it is absent entirely (8 columns, not 9) - never backfilled, that
    file's total-eligible-invoices measure is simply absent for it;
  - values are formatted inconsistently across files: plain numbers,
    "$X,XXX", " X,XXX.XX " (leading/trailing spaces), "Nil" (a literal,
    intentional zero), and blank (a genuinely missing observation, not
    zero - never conflated with "Nil");
  - agency identity and financial year are NOT reliably present inside the
    CSV data itself (rows only carry a bare "1"-"4" quarter number) - both
    must come from the filename, and for several files neither is
    determinable with confidence (no agency code, or no year, or an
    ambiguous bare "q4-2021" with no month context to resolve which
    financial year Q4 belongs to). These files are skipped, not guessed -
    matching this program's standing rule against inferring identity from
    label similarity alone.

Loading (measure_type classification, quantity vs amount_aud routing) is
load_qld_on_time_payments.py's job, not this one's - this module only
extracts, normalizes, and quarantines.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = "qld_on_time_payment_reports"

# --- Column normalization ---------------------------------------------------
# Real wording variants, verified directly against all 42 files (see module
# docstring). Matched after whitespace-collapse + lowercasing (this source's
# variance genuinely includes both, unlike the MFS workbooks) - never
# fuzzy/substring matched against arbitrary text.
_COLUMN_VARIANTS: dict[str, str] = {
    "quarter": "quarter",
    "eligible claims for penalty interest smallbus": "eligible_claims",
    "penalty interest paid smallbus": "penalty_interest_paid",
    "total eligible and undisputed invs smallbus": "total_eligible_invoices",
    "total eligible and undisputed small business invoices": "total_eligible_invoices",
    "total eligible and undisputed invs": "total_eligible_invoices",
    "total eligible and undisputed undisputed invs small business": "total_eligible_invoices",
    "total eligible and undisputed invs small business": "total_eligible_invoices",
    "eligible and undisputed invs paid late smallbus": "invoices_paid_late",
    "value eligible and undisputed inv paid late smallbus": "value_paid_late",
    "mean days paid late eligible and undisputed inv smallbus": "mean_days_paid_late",
    "percent of all late payments smallbus": "pct_late_smallbus",
    "percent of all late payments others": "pct_late_others",
}


def _normalize_header(raw: str) -> str:
    return re.sub(r"\s+", " ", str(raw).replace("﻿", "")).strip().lower()


def _clean_numeric(raw: object) -> float | None:
    """Strips $, commas, %, and whitespace. "Nil" is a literal, intentional
    zero (seen explicitly in the real corpus); a blank/NaN cell is a
    genuinely missing observation and returns None, never coerced to zero.

    pandas represents a blank CSV cell as float NaN, not Python None, even
    with dtype=str - str(float('nan')) is the non-empty string "nan", which
    would otherwise survive every check below and silently convert back to
    a real NaN via float("nan"), never hitting the CHECK constraint that
    catches a true None. Checked explicitly with pd.isna() first."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.lower() == "nil":
        return 0.0
    cleaned = text.replace("$", "").replace(",", "").replace("%", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


# --- Filename -> (agency_code, financial_year) ------------------------------
# Agency identity is always the raw filename-derived code exactly as the
# source itself names it - never expanded to a guessed full department name
# (QLD agencies undergo frequent machinery-of-government renames; a wrong
# guess here would misattribute real compliance data). A reader can follow
# the citation to the source URL to see which real department it is.
_FY_RANGE_RE = re.compile(r"(20\d{2})[_-](\d{2,4})(?!\d)")
_FY_SINGLE_RE = re.compile(r"fy ?(20\d{2})\b", re.IGNORECASE)
_STOPWORDS = {
    "qld", "on", "time", "payment", "payments", "report", "reports",
    "reporting", "open", "data", "file", "amended", "otpp",
}


def _financial_year_from_filename(name: str) -> str | None:
    m = _FY_RANGE_RE.search(name)
    if m:
        first, second = m.group(1), m.group(2)
        return f"{first}-{second[-2:]}"
    m = _FY_SINGLE_RE.search(name)
    if m:
        y = int(m.group(1))
        return f"{y}-{str(y + 1)[-2:]}"
    return None


def _agency_code_from_filename(name: str) -> str | None:
    stem = re.sub(r"\.csv$", "", name, flags=re.IGNORECASE)
    stem = re.sub(r"^qld_on_time_payment_reports__", "", stem)
    tokens = re.split(r"[-_ ]+", stem)
    for tok in tokens:
        low = tok.lower()
        if not low or low in _STOPWORDS:
            continue
        if re.fullmatch(r"\d+", low):
            continue
        if re.fullmatch(r"q\d|qtr\d|20\d{2}", low):
            continue
        return low
    return None


def extract_workbook(path: Path, original_filename: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []

    financial_year = _financial_year_from_filename(original_filename)
    agency_code = _agency_code_from_filename(original_filename)
    if financial_year is None:
        quarantine.append({"reason": "financial_year_undeterminable_from_filename", "file": original_filename})
        return rows, quarantine
    if agency_code is None:
        quarantine.append({"reason": "agency_code_undeterminable_from_filename", "file": original_filename})
        return rows, quarantine

    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", encoding_errors="replace")
    except Exception as exc:
        quarantine.append({"reason": "unreadable_csv", "file": original_filename, "error": str(exc)})
        return rows, quarantine

    col_map: dict[str, str] = {}
    for raw_col in df.columns:
        norm = _normalize_header(raw_col)
        logical = _COLUMN_VARIANTS.get(norm)
        if logical is None and norm.endswith(" quarter"):
            # One real file (verified directly) has the financial year and
            # "Quarter" merged into a single quoted, newline-containing CSV
            # cell, e.g. "2025-26\nQuarter" - the year prefix is discarded
            # here since the filename already independently determines the
            # financial year for this file.
            logical = "quarter"
        if logical:
            col_map[logical] = raw_col
        elif norm and not norm.lower().startswith("unnamed:"):
            quarantine.append(
                {"reason": "unrecognized_column_header", "file": original_filename, "header_text": raw_col}
            )

    if "quarter" not in col_map:
        quarantine.append({"reason": "no_quarter_column", "file": original_filename})
        return rows, quarantine

    measure_cols = {k: v for k, v in col_map.items() if k != "quarter"}

    for idx, r in df.iterrows():
        quarter_raw = r.get(col_map["quarter"])
        try:
            quarter = int(str(quarter_raw).strip())
        except (TypeError, ValueError):
            quarantine.append(
                {"reason": "unparseable_quarter", "file": original_filename, "row": idx + 2, "value": quarter_raw}
            )
            continue
        if quarter not in (1, 2, 3, 4):
            quarantine.append(
                {"reason": "quarter_out_of_range", "file": original_filename, "row": idx + 2, "value": quarter}
            )
            continue

        for measure, raw_col in measure_cols.items():
            value = _clean_numeric(r.get(raw_col))
            if value is None:
                continue
            rows.append(
                {
                    "fy": financial_year,
                    "agency_code": agency_code,
                    "quarter": quarter,
                    "measure": measure,
                    "value": value,
                    "locator": (
                        f"source_id:{SOURCE_ID} | file:{original_filename} | row:{idx + 2} | "
                        f"col:{raw_col} | agency_code:{agency_code}"
                    ),
                    "cached_copy_path": str(path.resolve().relative_to(REPO_ROOT))
                    if path.resolve().is_relative_to(REPO_ROOT)
                    else str(path),
                }
            )
    return rows, quarantine


def find_all_assets(repo_root: Path = REPO_ROOT) -> list[dict]:
    latest = repo_root / "data" / "raw" / "state" / SOURCE_ID / "latest.json"
    if not latest.is_file():
        return []
    data = json.loads(latest.read_text(encoding="utf-8"))
    return [a for a in data.get("assets") or [] if a.get("detected_type") == "csv"]


def extract_all(repo_root: Path = REPO_ROOT) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    for asset in find_all_assets(repo_root):
        path = repo_root / "data" / asset["stored_path"]
        if not path.is_file():
            quarantine.append({"reason": "file_missing_on_disk", "file": asset.get("original_filename")})
            continue
        original_filename = asset.get("original_filename") or path.name
        file_rows, file_quarantine = extract_workbook(path, original_filename)
        rows.extend(file_rows)
        quarantine.extend(file_quarantine)
    return rows, quarantine


def main() -> int:
    rows, quarantine = extract_all()
    out_dir = REPO_ROOT / "data" / "staging" / "qld_on_time_payments"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "qld_on_time_payments.csv"
    if rows:
        pd.DataFrame(rows).to_csv(out, index=False)
    qpath = REPO_ROOT / "data" / "staging" / "quarantine" / "qld_on_time_payments_extract_quarantine.jsonl"
    qpath.parent.mkdir(parents=True, exist_ok=True)
    with qpath.open("w", encoding="utf-8") as fh:
        for item in quarantine:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "quarantined": len(quarantine),
                "distinct_agencies": sorted({r["agency_code"] for r in rows}),
                "out": str(out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

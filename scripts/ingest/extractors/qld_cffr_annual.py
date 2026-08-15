#!/usr/bin/env python3
"""Extractor for Queensland Treasury's annual Consolidated Fund Financial
Report (CFFR) editions - item 7.4's first slice, the "Statement of
Receipts and Payments for the Year ended 30 June" cash-basis table.

The raw files live under `data/raw/state/qld_report_on_state_finances_actuals/`
- a genuinely different, unrelated document series co-located in the same
raw-acquisition folder as Queensland's annual "Report on State Finances"
- this module only reads the "Consolidated Fund Financial Report"-named
files, publishing them under a distinct `qld_cffr_annual` source_key
(never conflated with `qld_report_on_state_finances_actuals`'s own
GFS/UPF-basis fiscal aggregates, a different methodology from a
different table).

Scope of this pass: only the 17 ANNUAL editions (FY2008-09..FY2024-25,
each a "Year Ended 30 June" edition, identified by filename - see
_ANNUAL_EDITIONS below), never the many QUARTERLY interim editions
(Sep/Dec/Mar snapshots) also present in the same raw folder - a quarterly
edition's own "Year to Date" table describes a partial year, not the
final Year Ended figures this module extracts, and mixing the two would
violate this program's "never sum incompatible... vintages" rule.
Verified directly against all 17 real files before writing this: every
edition's "Balance as at 1 July" (Total column) exactly matches the prior
edition's own "Consolidated Fund Balance as at 30 June" (Total column) -
a genuine chained cross-check across the full 2008-09..2024-25 span,
confirming byte-for-byte correct extraction (never merely "row count
matches").

Only the "Total" column (never the Operating/Investment Account split,
and never the prior-year comparative column already independently
extracted from that prior year's own file) is extracted - deliberately
NOT loading the Operating/Investment Account breakdown or the receipt
sub-line-items with genuine multi-generation composition drift
("Capital return from Public Enterprises" vs "Disposal of Public
Enterprise Investments" vs "Receipts from Other Government Entities" -
these three coexisted as distinct rows in at least FY2010-11, so are not
a simple rename chain) - see ops/reports/qld-cffr-scoping-*.md for the
full evidence and the recommended follow-up scope.

This module only extracts and quarantines; loading (measure_type
classification against config/measure-semantics/qld_cffr.yaml) is
load_qld_cffr_annual.py's job, not this one's.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "qld_cffr_annual"

_RAW_DIR = (
    REPO_ROOT
    / "data"
    / "raw"
    / "state"
    / "qld_report_on_state_finances_actuals"
    / "snapshots"
    / "20260724T190604Z"
    / "files"
)

# (financial_year, filename) - the 17 real annual (Year Ended 30 June)
# editions, identified by direct inspection (never a filename-pattern
# guess) - see module docstring.
_ANNUAL_EDITIONS: list[tuple[str, str]] = [
    ("2008-09", "consolidated-fund-financial-report-2008-09.pdf"),
    ("2009-10", "consolidated-fund-financial-report-2009-10.pdf"),
    ("2010-11", "consolidated-fund-financial-report-2010-11.pdf"),
    ("2011-12", "consolidated-fund-financial-report-2011-12.pdf"),
    ("2012-13", "consolidated-fund-financial-report-2012-13.pdf"),
    ("2013-14", "consolidated-fund-financial-report-2013-14.pdf"),
    ("2014-15", "consolidated-fund-financial-report-2014-15.pdf"),
    ("2015-16", "consolidated-fund-financial-report-2015-16.pdf"),
    ("2016-17", "Consolidated-Fund-Financial-Report-2016-17.pdf"),
    ("2017-18", "Consolidated-Fund-Financial-Report-2017-18.pdf"),
    ("2018-19", "Consolidated-Fund-Financial-Report-2018-19.pdf"),
    ("2019-20", "Consolidated-Fund-Financial-Report-2019-20.pdf"),
    ("2020-21", "FG-CFFR-2020-21-Final.pdf"),
    ("2021-22", "Consolidated-Fund-Financial-Report-2021-22-Downloadable-PDF.pdf"),
    ("2022-23", "CFFR-2022-23-final.pdf"),
    ("2023-24", "2023-24-consolidated-fund-financial-report.pdf"),
    ("2024-25", "Consolidated-Fund-Financial-Report-2024-25.pdf"),
]

# label -> measure_key. Matched against the "Year Ended" block only (never
# the "Quarter Ended" block earlier on the same page). A trailing digit
# (a footnote marker, e.g. "...Departments 1 26,786,058") is consumed by
# the regex, never treated as part of the label or a data value.
_NUM = r"(\(?-?[\d,]+(?:\.\d+)?\)?|-)"
_LABEL_PATTERNS: list[tuple[str, str]] = [
    (r"Balance as at 1 July", "opening_balance"),
    (r"Collections received from [Dd]epartments", "collections_from_departments"),
    (r"Investment [Ii]nterest", "investment_interest"),
    (r"Dividends and [Ii]ncome [Tt]ax [Ee]quivalents", "dividends_income_tax_equivalents"),
    (r"Non-[Aa]ppropriated [Ee]quity [Aa]djustments", "non_appropriated_equity_adjustments"),
    (
        # A stray "-" (an empty adjacent-column placeholder bleeding into
        # the line wrap) sometimes interrupts "Queensland" and "Government"
        # in the real text extraction (confirmed directly, e.g. FY2017-18) -
        # tolerated here; FY2010-11 drops this label's first line entirely
        # in extraction and is correctly quarantined instead, never guessed.
        r"Superannuation,\s*[Ll]ong [Ss]ervice [Ll]eave,?\s*(?:and\s*)?Queensland\s*"
        r"(?:-\s*)?Government Insurance Fund and ALCS [Cc]ontributions",
        "superannuation_lsl_qgif_alcs_contributions",
    ),
    (r"Other [Rr]eceipts", "other_receipts"),
    (r"Appropriations provided to [Dd]epartments", "appropriations_provided_to_departments"),
    (r"Consolidated Fund Balance as at 30 June", "closing_balance"),
]


def _extract_year_ended_block(text: str) -> str | None:
    """The page has two tables (Quarter Ended, then Year Ended) - this
    module only ever reads the second. Located by the label that is
    unique to the year-ended block's opening row."""
    idx = text.rfind("Balance as at 1 July")
    if idx == -1:
        return None
    end = text.find("Notes:", idx)
    return text[idx : end if end != -1 else None]


def extract_edition(path: Path, financial_year: str, original_filename: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        quarantine.append({"reason": "unreadable_pdf", "file": original_filename, "error": str(exc)})
        return rows, quarantine

    block = None
    page_num = None
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        candidate = _extract_year_ended_block(text)
        if candidate:
            block = candidate
            page_num = i + 1
            break
    if block is None:
        quarantine.append({"reason": "year_ended_table_not_found", "file": original_filename})
        return rows, quarantine

    found_keys: set[str] = set()
    for label_re, measure_key in _LABEL_PATTERNS:
        m = re.search(
            rf"{label_re}\s*\d?\s*{_NUM}\s*{_NUM}\s*{_NUM}\s*{_NUM}",
            block,
            re.S,
        )
        if not m:
            quarantine.append(
                {"reason": "label_not_found_in_year_ended_block", "file": original_filename, "measure_key": measure_key}
            )
            continue
        total_current_raw = m.group(3)
        value = _parse_number(total_current_raw)
        if value is None:
            quarantine.append(
                {
                    "reason": "unparseable_total_value",
                    "file": original_filename,
                    "measure_key": measure_key,
                    "raw": total_current_raw,
                }
            )
            continue
        # Every table in this document is denominated in $'000 (confirmed
        # directly against every edition's own column header) - scale to
        # real AUD, never left as thousands.
        value *= 1_000
        found_keys.add(measure_key)
        rows.append(
            {
                "fy": financial_year,
                "amount": value,
                "measure_key": measure_key,
                "locator": (
                    f"source_id:{SOURCE_ID} | file:{original_filename} | page:{page_num} | "
                    f"row:{measure_key} | column:Total (Year Ended)"
                ),
                "cached_copy_path": _relative_or_str(path),
            }
        )
    return rows, quarantine


def _parse_number(raw: str) -> float | None:
    raw = raw.strip()
    if raw == "-" or not raw:
        return 0.0
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.strip("()").replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def extract_all(raw_dir: Path = _RAW_DIR) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    for fy, filename in _ANNUAL_EDITIONS:
        path = raw_dir / filename
        if not path.is_file():
            quarantine.append({"reason": "edition_file_missing_on_disk", "fy": fy, "filename": filename})
            continue
        edition_rows, edition_quarantine = extract_edition(path, fy, filename)
        rows.extend(edition_rows)
        quarantine.extend(edition_quarantine)
    return rows, quarantine


def main() -> int:
    rows, quarantine = extract_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "qld_cffr_annual.csv"
    if rows:
        import csv

        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    if quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        qpath = QUARANTINE_DIR / f"{SOURCE_ID}_extract_quarantine.jsonl"
        with qpath.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "rows": len(rows),
                "quarantined": len(quarantine),
                "distinct_measure_keys": sorted({r["measure_key"] for r in rows}),
                "editions": len(_ANNUAL_EDITIONS),
                "out": str(out),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extractor for the pre-2019 Final Budget Outcome (FBO) "Appendix A:
Expenses by Function and Sub-function" table - item 8.1's first two
sub-generations, covering FY2010-11 through FY2013-14 (the confirmed-
tractable years found in the page-anchor scoping pass).

Two distinct, individually-verified column layouts are covered, never
assumed uniform across years:
  - FY2010-11/FY2011-12: 3 numeric columns (prior-year Outcome | current-
    year Estimate at Outcome | next-year Budget).
  - FY2012-13/FY2013-14: 4 numeric columns (prior-year Outcome | current-
    year Estimate at Outcome | next-year Budget | "Change on Budget").
Each edition in _EDITIONS below carries its own verified column count -
never inferred or guessed - and only the second ("Estimate at Outcome")
column is ever extracted, which sits at the same position in both
layouts.

The existing broad `fbo_appendix_a.extract()` is confirmed unsafe to
reuse (it latches onto unrelated tables earlier in each consolidated FBO,
e.g. "Table 5: ... expenses by function", a function-level-ONLY summary
table with no sub-function detail and a different page/column shape -
see ops/reports/fbo-historical-archive-triage-20260807T175900Z.md). This
module locates the genuine Appendix A ("Table A1") page range directly,
using a title anchor confirmed present in two different physical forms
across these editions (a chapter-heading form on the section's very
first page, and a running-header form on every continuation page - see
ops/reports/fbo-appendix-a-page-anchor-scoping-20260818T160000Z.md).

Scope: function-level totals only (13 COFOG-style functions + 5 "Other
purposes" line items + "Total other purposes" + "Total expenses" = 20
measures), deliberately NOT the individual sub-function line items
beneath each function - the same granularity choice already made for
the MFS Note 3 workbook (item 7.1), and for the same reason: the ~60+
sub-function labels are a much larger surface with more real drift risk
across editions, not attempted this pass.

Each function is either:
  - "total-terminated": several sub-function rows followed by a
    "Total <function>" row (e.g. "Total general public services") - the
    total row's own middle numeric column is extracted, never
    recomputed by summing the sub-function rows; or
  - "single-line": the bare function-name row itself already carries
    the 3 numeric columns directly (no separate Total row exists,
    verified directly - e.g. "Defence", "Fuel and energy", "Public debt
    interest") - some of these also have informational sub-items listed
    below them (e.g. "Public debt interest" is followed by "Interest on
    Australian Government's behalf", a near-identical restatement), but
    those sub-items are never separately extracted or summed here.

Only the middle numeric column ("<FY> Estimate at Outcome" - FBO's own
term for its best current estimate of the actual final outcome, the
figure this whole database treats as the "actual" for consistency with
every other measure family) is extracted - never the leading prior-year-
outcome comparative column (independently extracted from that prior
year's own edition) or the trailing next-year Budget forecast column (a
forecast, never an actual, per this program's standing rule).

This module only extracts and quarantines; loading is
load_fbo_appendix_a_function.py's job, not this one's.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "fbo_appendix_a_function"

_RAW_DIR = (
    REPO_ROOT
    / "data"
    / "raw"
    / "federal"
    / "federal_budget_archive_function_series"
    / "snapshots"
    / "20260723T033445Z"
    / "files"
)

# (financial_year, filename, numeric_column_count) - only the confirmed-
# tractable years/layouts (see the page-anchor scoping report). Every
# other pre-2019 edition (FY2014-15 onward, and the entire pre-2010-11
# population) needs its own dedicated investigation before being added
# here - never guessed at.
_EDITIONS: list[tuple[str, str, int]] = [
    ("2010-11", "FBO_2010-11_Consolidated.pdf", 3),
    ("2011-12", "FBO_2011-12_Consolidated.pdf", 3),
    ("2012-13", "2012-13_FBO_Consolidated.pdf", 4),
    ("2013-14", "2013-14_FBO_Consolidated.pdf", 4),
]

_ANCHOR_RE = re.compile(r"appendix a:\s*expenses by function and\s*sub-function", re.I)
_NUM = r"(\(?-?[\d,]+(?:\.\d+)?\)?|-)"

# measure_key -> (search_label_regex_fragment, is_total_terminated)
# is_total_terminated=True means the search text is a "Total <label>" row;
# False means the bare function-name row itself carries the numbers.
_LABEL_PATTERNS: list[tuple[str, str, bool]] = [
    ("general_public_services", r"Total general public services", True),
    ("defence", r"Defence", False),
    ("public_order_safety", r"Total public order and safety", True),
    ("education", r"Total education", True),
    ("health", r"Total health", True),
    ("social_security_welfare", r"Total social security and welfare", True),
    ("housing_community_amenities", r"Total housing and community\s+amenities", True),
    ("recreation_culture", r"Total recreation and culture", True),
    ("fuel_energy", r"Fuel and energy", False),
    ("agriculture_forestry_fishing", r"Total agriculture, forestry and fishing", True),
    ("mining_manufacturing_construction", r"Mining, manufacturing and construction", False),
    ("transport_communication", r"Total transport and communication", True),
    ("other_economic_affairs", r"Total other economic affairs", True),
    ("public_debt_interest", r"Public debt interest", False),
    ("nominal_superannuation_interest", r"Nominal superannuation interest", False),
    ("general_purpose_intergovt_transactions", r"General purpose inter-government\s+transactions", False),
    ("natural_disaster_relief", r"Natural disaster relief", False),
    ("contingency_reserve", r"Contingency reserve", False),
    ("total_other_purposes", r"Total other purposes", True),
    ("total_expenses", r"Total expenses", True),
]


def _find_appendix_a_pages(reader: PdfReader) -> list[int]:
    """The genuine Appendix A page range, never a Table-of-Contents
    mention (which always appears well before page 50 in every edition
    checked - see the scoping report)."""
    pages = []
    for i, page in enumerate(reader.pages):
        if i + 1 <= 50:
            continue
        text = (page.extract_text() or "").replace("\n", " ")
        if _ANCHOR_RE.search(text):
            pages.append(i + 1)
    return pages


def extract_edition(
    path: Path, financial_year: str, original_filename: str, num_columns: int = 3
) -> tuple[list[dict], list[dict]]:
    """num_columns is the edition's own verified numeric-column count (3
    for FY2010-11/FY2011-12, 4 for FY2012-13/FY2013-14 - see _EDITIONS).
    The second column ("Estimate at Outcome") is always extracted,
    regardless of how many trailing columns follow it."""
    rows: list[dict] = []
    quarantine: list[dict] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        quarantine.append({"reason": "unreadable_pdf", "file": original_filename, "error": str(exc)})
        return rows, quarantine

    pages = _find_appendix_a_pages(reader)
    if not pages:
        quarantine.append({"reason": "appendix_a_pages_not_found", "file": original_filename})
        return rows, quarantine

    block = "\n".join((reader.pages[p - 1].extract_text() or "") for p in pages)
    num_pattern = r"\s+".join([_NUM] * num_columns)

    for measure_key, label_re, _is_total in _LABEL_PATTERNS:
        m = re.search(rf"{label_re}\s+{num_pattern}", block, re.S)
        if not m:
            quarantine.append({"reason": "label_not_found", "file": original_filename, "measure_key": measure_key})
            continue
        value = _parse_number(m.group(2))
        if value is None:
            quarantine.append(
                {"reason": "unparseable_value", "file": original_filename, "measure_key": measure_key, "raw": m.group(2)}
            )
            continue
        rows.append(
            {
                "fy": financial_year,
                "amount": value,
                "measure_key": measure_key,
                "locator": (
                    f"source_id:{SOURCE_ID} | file:{original_filename} | pages:{pages[0]}-{pages[-1]} | "
                    f"row:{measure_key} | column:Estimate at Outcome"
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
    for fy, filename, num_columns in _EDITIONS:
        path = raw_dir / filename
        if not path.is_file():
            quarantine.append({"reason": "edition_file_missing_on_disk", "fy": fy, "filename": filename})
            continue
        edition_rows, edition_quarantine = extract_edition(path, fy, filename, num_columns)
        rows.extend(edition_rows)
        quarantine.extend(edition_quarantine)
    return rows, quarantine


def main() -> int:
    rows, quarantine = extract_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "fbo_appendix_a_function.csv"
    if rows:
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
                "editions": len(_EDITIONS),
                "out": str(out),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

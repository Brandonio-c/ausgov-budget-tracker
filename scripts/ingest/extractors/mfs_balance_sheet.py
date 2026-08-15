#!/usr/bin/env python3
"""Extractor for the Australian Government Monthly Financial Statements'
Balance Sheet workbook (federal_mfs_balance_sheet), item 7.1's fifth and
final MFS sibling workbook.

Verified directly against all 21 real sheets (FY2005-06..FY2025-26) before
writing any label mapping - this workbook is structurally unlike every
other MFS sibling in two ways, both handled here rather than by extending
mfs_common.py's shared YTD-flow logic (which does not fit a stock at all):

  1. Header shape is "ACTUAL\\nas at\\n<DD Month YYYY>\\n$m" (a point-in-time
     balance date), not "ACTUAL\\n<FY>\\n[YTD ]<Month>\\n$m" (a YTD-through-
     month flow accumulation) - there is no "YTD" concept for a stock, so
     mfs_common.py's HEADER_RE/is_ytd logic would incorrectly quarantine
     every non-July column as "non_ytd_column_not_supported". This module
     parses the exact "as at" date directly from the header instead, which
     is both more precise than reconstructing a month-end date from a bare
     month name and semantically correct for a stock (period_start is
     always null - a balance has no accumulation start).
  2. FY2005-06 and FY2006-07 use a genuinely different physical layout
     (row labels in column 1, indented under column-0 section headers,
     e.g. "Financial assets" then a blank column 0 with "Cash" in column
     1) with their own distinct label set (e.g. "Cash", "Debt"/"Total
     debt", a "Net Assets" equity reconciliation with "Operating Result"/
     "Asset revaluation reserve"/"Other movements"/"Closing net assets")
     that does not map cleanly onto the modern generation's structure
     (e.g. gen1's single "Investments" row vs gen2's four separate
     equity-investment line items - a genuine one-to-many split, not a
     rename). FY2007-08 is a further one-off transition year with its own
     unique "GFS assets"/"GFS liabilities" framing alongside bare (no "as
     at") month-name headers. All three of these early years are
     deliberately NOT extracted here - see
     ops/reports/mfs-balance-sheet-scoping-*.md for the full evidence.
     Every measure loaded from this module spans FY2008-09..FY2025-26 (18
     years) or a documented subset of it, never inferring continuity with
     the excluded early years from label similarity alone.

Four already-loaded headline figures (mfs_stock_total_assets,
mfs_stock_total_liabilities, mfs_stock_net_worth, mfs_stock_net_debt - see
config/measure-semantics/mfs.yaml) are sourced from the separate
federal_mfs_aggregates workbook's own embedded summary rows, not from this
file - "Total assets"/"Total liabilities" rows in this file are
deliberately NOT re-extracted here to avoid two independent, differently-
provenanced series under the same measure_type. "Net worth"/"Net debt"
rows are excluded for the same reason (mfs_stock_cash_and_deposits is the
one already-defined measure_type genuinely reserved for this workbook,
per its own semantics comment, and is loaded here).

This module only extracts and quarantines; loading (measure_type
classification against config/measure-semantics/mfs.yaml) is
load_mfs_balance_sheet.py's job, not this one's.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mfs_common import FOOTNOTE_ROW, UNIT_SCALE, clean_label, find_latest_asset, relative_or_str  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "federal_mfs_balance_sheet"

# FY2005-06/FY2006-07 (indented column-1 labels, a distinct early-generation
# label set) and FY2007-08 (a one-off "GFS assets/liabilities" transition
# year with bare, non-"as at" month headers) are structurally incompatible
# with the uniform "as at <date>" shape every later sheet uses - excluded
# by name, never guessed at.
_EXCLUDED_SHEETS = {"2005-06", "2006-07", "2007-08"}

_MONTH_NUM = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

_HEADER_RE = re.compile(
    r"^(?P<status>[A-Z]+)\s*\n\s*as at\s*\n\s*(?P<day>\d{1,2}) (?P<month>[A-Za-z]+) (?P<year>\d{4})"
    r"\s*(?:\([a-z]\))?\s*\n\s*(?P<unit>\$[a-z]+)\s*$"
)


def _parse_header(raw: str) -> dict | None:
    m = _HEADER_RE.match(raw.strip())
    if not m:
        return None
    month = m.group("month")
    if month not in _MONTH_NUM:
        return None
    year, day, month_num = int(m.group("year")), int(m.group("day")), _MONTH_NUM[month]
    financial_year_start_year = year if month_num >= 7 else year - 1
    return {
        "status": m.group("status").lower(),
        "period_end": f"{year:04d}-{month_num:02d}-{day:02d}",
        "financial_year": f"{financial_year_start_year}-{str(financial_year_start_year + 1)[-2:]}",
        "reporting_month": month,
        "unit": m.group("unit"),
        "header_text": raw.replace("\n", " "),
    }


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        if sheet in _EXCLUDED_SHEETS:
            continue
        df = xl.parse(sheet, header=None)
        if df.shape[0] < 3 or df.shape[1] < 2:
            quarantine.append({"reason": "sheet_too_small", "sheet": sheet})
            continue

        col_meta: dict[int, dict] = {}
        header_row = df.iloc[1]
        for col_idx in range(1, df.shape[1]):
            raw = header_row[col_idx]
            if not isinstance(raw, str):
                continue
            meta = _parse_header(raw)
            if meta is None:
                quarantine.append({"reason": "unparsed_column_header", "sheet": sheet, "column": col_idx, "header_text": raw})
                continue
            if meta["unit"] not in UNIT_SCALE:
                quarantine.append({"reason": "unknown_unit", "sheet": sheet, "column": col_idx, "unit": meta["unit"]})
                continue
            col_meta[col_idx] = meta

        for row_idx in range(2, df.shape[0]):
            label_raw = df.iloc[row_idx, 0]
            if not isinstance(label_raw, str) or not label_raw.strip():
                continue
            if FOOTNOTE_ROW.match(label_raw.strip()):
                break
            label = clean_label(label_raw)
            for col_idx, meta in col_meta.items():
                val = df.iloc[row_idx, col_idx]
                if pd.isna(val):
                    continue
                try:
                    amount = float(val) * UNIT_SCALE[meta["unit"]]
                except (TypeError, ValueError):
                    continue
                rows.append(
                    {
                        "fy": meta["financial_year"],
                        "amount": amount,
                        "measure_label": label,
                        "estimate_status": meta["status"],
                        "reporting_month": meta["reporting_month"],
                        "period_end": meta["period_end"],
                        "unit": meta["unit"],
                        "sheet": sheet,
                        "locator": (
                            f"source_id:{source_id} | sheet:{sheet} | row:{label} | "
                            f"col:{meta['header_text']}"
                        ),
                        "cached_copy_path": relative_or_str(path),
                    }
                )
    return rows, quarantine


def main() -> int:
    path = find_latest_asset(SOURCE_ID)
    if path is None:
        print(json.dumps({"error": f"no asset found for {SOURCE_ID}"}))
        return 1

    rows, quarantine = extract_workbook(path, SOURCE_ID)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "mfs_balance_sheet.csv"
    if rows:
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    if quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        qpath = QUARANTINE_DIR / f"mfs_quarantine_{SOURCE_ID}.jsonl"
        with qpath.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    distinct_labels = sorted({r["measure_label"] for r in rows})
    print(
        json.dumps(
            {
                "source_id": SOURCE_ID,
                "path": str(path),
                "rows": len(rows),
                "quarantined": len(quarantine),
                "distinct_measure_labels": distinct_labels,
                "out": str(out),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

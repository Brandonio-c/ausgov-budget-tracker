#!/usr/bin/env python3
"""Extractor for the Australian Government Monthly Financial Statements'
'Note 3 - Total expense by function' workbook (federal_mfs_note3_function),
the second of the five MFS sibling workbooks item 7.1 completes one at a
time (federal_mfs_aggregates was the first, done previously).

Same sheet shape as the Aggregates workbook (one sheet per financial year,
row 0 = title, row 1 = per-column YTD header, data rows follow until a
footnote row) - see mfs_common.py, shared verbatim. Verified directly
against all 21 real sheets (FY2005-06..2025-26) before writing any label
mapping:

  - two structural section-heading rows ("Expenses by function", "Other
    purposes") carry no numeric values in any column and so naturally
    produce zero extracted rows - no special-casing needed;
  - 13 COFOG-style function rows plus 5 "Other purposes" line items plus a
    "Total expenses" row, all independently, directly published by the
    source (Total expenses is never computed here - always the source's
    own stated total-row cell);
  - a genuinely separate "Asset Sales" row exists only in FY2005-06
    through FY2007-08 (folded into Contingency reserve from FY2008-09
    onward, per that year's own footnote) - mapped as its own
    only_published_financial_years-scoped measure, never dropped and
    never merged into Contingency reserve's figures;
  - real label drift requiring explicit variant mapping (not case-folding
    or fuzzy matching): "Mining and Mineral Resources (other than fuels);
    \\n   Manufacturing and Construction" (FY2005-06..2008-09) vs "Mining,
    manufacturing and construction" (FY2009-10+, two further case variants
    across eras); "Agriculture, Forestry and Fishing" (title case,
    ..FY2016-17) vs "Agriculture, forestry and fishing" (sentence case,
    FY2017-18+); trailing footnote markers on "General public services(a)"/
    "Defence(a)" in FY2016-17 only, stripped by the shared clean_label()
    the same way "(a)" markers are handled throughout the MFS corpus;
    trailing whitespace/newlines on several labels ("Education ",
    "Health ", "...transactions\\n").

This module only extracts and quarantines; loading (measure_type
classification against config/measure-semantics/mfs.yaml) is
load_mfs_note3_function.py's job, not this one's.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mfs_common import extract_ytd_workbook, find_latest_asset  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "federal_mfs_note3_function"


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    return extract_ytd_workbook(path, source_id)


def main() -> int:
    path = find_latest_asset(SOURCE_ID)
    if path is None:
        print(json.dumps({"error": f"no asset found for {SOURCE_ID}"}))
        return 1

    rows, quarantine = extract_workbook(path, SOURCE_ID)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "mfs_note3_function.csv"
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

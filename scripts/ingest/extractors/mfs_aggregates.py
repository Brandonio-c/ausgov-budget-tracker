#!/usr/bin/env python3
"""Extractor for the Australian Government Monthly Financial Statements'
'Aggregates' workbook (federal_mfs_aggregates, one of the six MFS files in
the Task 4 adapter-repair queue).

Each sheet is one fiscal year. Row 0 = title (skipped). Row 1 = per-column
header, e.g. "ACTUAL\n2024-2025\nYTD July\n$b". Data rows follow (row label
in column 0) until a footnote row ("(a) ..."). Row labels vary across eras
(e.g. "Assets"/"Operating Result" pre-~2020 vs "Total assets"/"Net operating
balance" from ~2020 onward) and cover both cash-basis (Receipts, Payments,
Underlying/Headline cash balance) and accrual/GFS-basis (Revenue, Expenses,
Total assets/liabilities, Net worth, Net debt) rows in the same sheet - the
two must not be conflated.

This module only extracts and quarantines; it does not write to facts.db.
Loading requires deciding which measure_type each row label maps to without
mixing this file's year-to-date (partial-year) figures into the same
additive/comparable bucket as complete full-year GFS actuals - see the
accompanying ops report for why that decision is deferred rather than
guessed.

The actual sheet-parsing logic lives in mfs_common.py, shared with every
MFS sibling workbook extractor (they all share the same sheet shape) -
this module is a thin, source_id-bound wrapper around it.
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


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    return extract_ytd_workbook(path, source_id)


def _find_latest_asset(source_id: str) -> Path | None:
    return find_latest_asset(source_id)


def main() -> int:
    source_id = "federal_mfs_aggregates"
    path = _find_latest_asset(source_id)
    if path is None:
        print(json.dumps({"error": f"no asset found for {source_id}"}))
        return 1

    rows, quarantine = extract_workbook(path, source_id)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "mfs_aggregates.csv"
    if rows:
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    if quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        qpath = QUARANTINE_DIR / f"mfs_quarantine_{source_id}.jsonl"
        with qpath.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    distinct_labels = sorted({r["measure_label"] for r in rows})
    print(
        json.dumps(
            {
                "source_id": source_id,
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

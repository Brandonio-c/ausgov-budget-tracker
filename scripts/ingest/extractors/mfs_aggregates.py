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
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"

HEADER_RE = re.compile(
    r"^(?P<status>[A-Z]+)\s*\n(?P<fy_long>\d{4}-\d{4})\s*\n(?P<ytd>YTD\s+)?(?P<month>[A-Za-z]+)\s*\n(?P<unit>\$[a-z]+)\s*$"
)
UNIT_SCALE = {"$m": 1_000_000, "$b": 1_000_000_000, "$": 1}
FOOTNOTE_ROW = re.compile(r"^\([a-z]\)")
TRAILING_FOOTNOTE_MARK = re.compile(r"\([a-z]\)\s*$")


def _fy_short(fy_long: str) -> str:
    y1, y2 = fy_long.split("-")
    return f"{y1}-{y2[-2:]}"


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, header=None)
        if df.shape[0] < 3 or df.shape[1] < 2:
            quarantine.append({"reason": "sheet_too_small", "sheet": sheet})
            continue

        header_row = df.iloc[1]
        col_meta: dict[int, dict] = {}
        for col_idx in range(1, df.shape[1]):
            raw = header_row[col_idx]
            if not isinstance(raw, str):
                continue
            m = HEADER_RE.match(raw.strip())
            if not m:
                quarantine.append(
                    {"reason": "unparsed_column_header", "sheet": sheet, "column": col_idx, "header_text": raw}
                )
                continue
            is_ytd = bool(m.group("ytd")) or m.group("month") == "July"
            unit = m.group("unit")
            if unit not in UNIT_SCALE:
                quarantine.append(
                    {"reason": "unknown_unit", "sheet": sheet, "column": col_idx, "unit": unit}
                )
                continue
            col_meta[col_idx] = {
                "status": m.group("status").lower(),
                "fy": _fy_short(m.group("fy_long")),
                "is_ytd": is_ytd,
                "month": m.group("month"),
                "unit": unit,
                "header_text": raw.replace("\n", " "),
            }

        for row_idx in range(2, df.shape[0]):
            label_raw = df.iloc[row_idx, 0]
            if not isinstance(label_raw, str) or not label_raw.strip():
                continue
            if FOOTNOTE_ROW.match(label_raw.strip()):
                break
            label = TRAILING_FOOTNOTE_MARK.sub("", label_raw).strip()
            for col_idx, meta in col_meta.items():
                val = df.iloc[row_idx, col_idx]
                if pd.isna(val):
                    continue
                try:
                    amount = float(val) * UNIT_SCALE[meta["unit"]]
                except (TypeError, ValueError):
                    continue
                if not meta["is_ytd"]:
                    quarantine.append(
                        {
                            "reason": "non_ytd_column_not_supported",
                            "sheet": sheet,
                            "label": label,
                            "column": meta["header_text"],
                        }
                    )
                    continue
                rows.append(
                    {
                        "fy": meta["fy"],
                        "amount": amount,
                        "measure_label": label,
                        "estimate_status": meta["status"],
                        "month": meta["month"],
                        "unit": meta["unit"],
                        "sheet": sheet,
                        "locator": (
                            f"source_id:{source_id} | sheet:{sheet} | row:{label} | "
                            f"col:{meta['header_text']}"
                        ),
                        "cached_copy_path": _relative_or_str(path),
                    }
                )
    return rows, quarantine


def _find_latest_asset(source_id: str) -> Path | None:
    latest = REPO_ROOT / "data" / "raw" / "federal" / source_id / "latest.json"
    if not latest.is_file():
        return None
    data = json.loads(latest.read_text(encoding="utf-8"))
    for asset in data.get("assets") or []:
        stored = asset.get("stored_path") or ""
        if stored.lower().endswith((".xlsx", ".xls")):
            p = REPO_ROOT / "data" / stored
            if p.is_file():
                return p
    return None


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

#!/usr/bin/env python3
"""Extractor for the Victorian Department of Treasury and Finance (DTF)
Annual Financial Statements workbook (vic_annual_financial_statements_2024_25,
one entry in the adapter-repair-followup backlog - see
ops/reports/next-backlog-ranking-20260805T161821Z.md).

Only the three primary financial statement sheets are extracted -
Operating Statement, Balance Sheet, Cash Flow Statement - which share one
consistent layout: a title row (skipped), a unit row ("($ thousand)"),
a header row ("Notes | <year1> | <year2>"), then labelled data rows with
two years of already-numeric comparative figures. Statement of Changes in
Equity has a different rolling-balance-across-multiple-columns shape and
is intentionally not extracted here.

This module only extracts and quarantines; it does not write to
facts.db. See config/measure-semantics/vic_afs.yaml for which row labels
map to which measure_type, and scripts/ingest/reload_vic_afs.py for
classification/validation/loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"

TARGET_SHEETS = ["Operating Statement", "Balance Sheet", "Cash Flow Statement"]
EXPECTED_UNIT_TEXT = "($ thousand)"
SOURCE_FOOTER_RE = re.compile(r"^Source:", re.IGNORECASE)
# Cash Flow Statement embeds numbered notes appendices after the primary
# statement (e.g. "7.2 Cash flow information and balances",
# "7.2.1 Reconciliation of net result..."), which restate primary-statement
# totals under different or identical labels as cross-checks (e.g. "Net
# cash flows from/(used in) operating activities" appears twice with the
# identical value - once in the primary statement, once in the 7.2.1
# reconciliation note). Stopping at the first such heading keeps only the
# primary statement's own rows, avoiding a same-label duplicate.
NUMBERED_NOTE_HEADING_RE = re.compile(r"^\d+\.\d+(\.\d+)?\s")


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _financial_year_for_calendar_year(calendar_year: int) -> str:
    """Header value 2025 (year ended 30 June 2025) -> FY "2024-25"."""
    return f"{calendar_year - 1}-{str(calendar_year)[-2:]}"


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    xl = pd.ExcelFile(path)

    for sheet in TARGET_SHEETS:
        if sheet not in xl.sheet_names:
            quarantine.append({"reason": "expected_sheet_missing", "sheet": sheet})
            continue
        df = xl.parse(sheet, header=None)
        if df.shape[0] < 4 or df.shape[1] < 4:
            quarantine.append({"reason": "sheet_too_small", "sheet": sheet, "shape": list(df.shape)})
            continue

        unit_cell = df.iloc[1, df.shape[1] - 1]
        if not isinstance(unit_cell, str) or unit_cell.strip() != EXPECTED_UNIT_TEXT:
            quarantine.append(
                {"reason": "unexpected_unit_cell", "sheet": sheet, "unit_cell": repr(unit_cell)}
            )
            continue

        header_row = df.iloc[2]
        col_years: dict[int, str] = {}
        for col_idx in (2, 3):
            raw = header_row[col_idx]
            if not isinstance(raw, (int, float)) or pd.isna(raw):
                quarantine.append(
                    {"reason": "unparsed_year_header", "sheet": sheet, "column": col_idx, "header_text": repr(raw)}
                )
                continue
            col_years[col_idx] = _financial_year_for_calendar_year(int(raw))

        if len(col_years) != 2:
            quarantine.append({"reason": "expected_two_year_columns", "sheet": sheet, "found": list(col_years.values())})
            continue

        for row_idx in range(3, df.shape[0]):
            label_raw = df.iloc[row_idx, 0]
            if not isinstance(label_raw, str) or not label_raw.strip():
                continue
            label = label_raw.strip()
            if SOURCE_FOOTER_RE.match(label) or NUMBERED_NOTE_HEADING_RE.match(label):
                break

            for col_idx, fy in col_years.items():
                value = df.iloc[row_idx, col_idx]
                if not isinstance(value, (int, float)) or pd.isna(value):
                    # Section headers (e.g. "Income from transactions",
                    # "Assets") have a label but no value - not an error,
                    # just not a data row.
                    continue
                rows.append(
                    {
                        "source_id": source_id,
                        "sheet": sheet,
                        "row_label": label,
                        "financial_year": fy,
                        "amount_thousand_aud": float(value),
                        "locator": f"source_id:{source_id} | sheet:{sheet} | row:{label} | fy:{fy}",
                        "cached_copy_path": _relative_or_str(path),
                    }
                )

    return rows, quarantine


def main() -> int:
    import argparse
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", default="vic_annual_financial_statements_2024_25")
    parser.add_argument(
        "--path",
        type=Path,
        default=REPO_ROOT
        / "data/raw/state/vic_annual_financial_statements_2024_25/snapshots/20260724T190604Z/files/Annual-financial-statements-2024-25.xlsx",
    )
    args = parser.parse_args()

    rows, quarantine = extract_workbook(args.path, args.source_id)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE_DIR / "vic_afs_extract_quarantine.jsonl", "w", encoding="utf-8") as fh:
        for q in quarantine:
            fh.write(json.dumps(q) + "\n")

    print(
        json.dumps(
            {"rows_extracted": len(rows), "rows_quarantined": len(quarantine)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

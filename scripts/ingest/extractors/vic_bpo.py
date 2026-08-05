#!/usr/bin/env python3
"""Extractor for the Victorian Department of Treasury and Finance (DTF)
Budget Portfolio Outcomes workbook (vic_budget_portfolio_outcomes_2024_25 -
see ops/reports/next-structured-pack-selection-20260805T182251Z.md for
why this was selected next after the already-loaded Annual Financial
Statements family).

Only the three primary financial statement sheets are extracted - OS
(Operating Statement), BS (Balance Sheet), CFS (Cash Flow Statement) -
which share one consistent layout, genuinely different from the AFS
workbook's:

  - Row 0: title (skipped). Row 1: unit row ("($ million)" - not
    "($ thousand)" like AFS).
  - Row 2: header row with THREE data columns and NO "Notes" column at
    all (AFS has Notes/year1/year2; this workbook has
    Actual/Budget/Variance for the SAME single year, 2024-25) -
    "2024-25\\nActual", "2024-25\\nBudget" (sometimes with a trailing
    footnote marker, e.g. "2024-25\\nBudget (a)"), "Variance".
  - Rows 3+: labelled data rows, with inline trailing footnote markers
    on many labels (e.g. "Output appropriations (a)").
  - No "Source: ..." footer line - instead a lowercase-letter-
    parenthetical footnote block terminates the sheet (e.g. "(a) Higher
    actuals primarily reflect...").

The "Variance" column is never extracted as its own fact - it is
Actual minus Budget, entirely derivable from the other two columns, and
loading it separately would double-count exactly like the Net assets/
Net worth duplicate pattern found in the AFS family.

This module only extracts and quarantines; it does not write to
facts.db. See config/measure-semantics/vic_bpo.yaml for which row
labels map to which measure_type, and scripts/ingest/reload_vic_bpo.py
for classification/validation/loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"

TARGET_SHEETS = ["OS", "BS", "CFS"]
EXPECTED_UNIT_TEXT = "($ million)"
FOOTNOTE_ROW_RE = re.compile(r"^\([a-z]\)")
TRAILING_FOOTNOTE_MARK_RE = re.compile(r"\s*\([a-z]\)\s*$")
HEADER_CELL_RE = re.compile(r"^(?P<fy>\d{4}-\d{2})\n(?P<status>Actual|Budget)\s*(?:\([a-z]\))?$")


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _strip_trailing_footnote(label: str) -> str:
    return TRAILING_FOOTNOTE_MARK_RE.sub("", label).strip()


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
        col_status: dict[int, tuple[str, str]] = {}  # col_idx -> (financial_year, estimate_status)
        variance_col: int | None = None
        for col_idx in (1, 2, 3):
            raw = header_row[col_idx]
            if not isinstance(raw, str):
                quarantine.append(
                    {"reason": "unparsed_header_cell", "sheet": sheet, "column": col_idx, "header_text": repr(raw)}
                )
                continue
            text = raw.strip()
            if text == "Variance":
                variance_col = col_idx
                continue
            m = HEADER_CELL_RE.match(text)
            if not m:
                quarantine.append(
                    {"reason": "unparsed_header_cell", "sheet": sheet, "column": col_idx, "header_text": text}
                )
                continue
            estimate_status = "actual" if m.group("status") == "Actual" else "budget"
            col_status[col_idx] = (m.group("fy"), estimate_status)

        if len(col_status) != 2 or variance_col is None:
            quarantine.append(
                {
                    "reason": "expected_actual_budget_variance_columns",
                    "sheet": sheet,
                    "found_data_columns": list(col_status.values()),
                    "found_variance": variance_col is not None,
                }
            )
            continue

        for row_idx in range(3, df.shape[0]):
            label_raw = df.iloc[row_idx, 0]
            if not isinstance(label_raw, str) or not label_raw.strip():
                continue
            raw_label = label_raw.strip()
            if FOOTNOTE_ROW_RE.match(raw_label):
                break
            label = _strip_trailing_footnote(raw_label)

            for col_idx, (fy, estimate_status) in col_status.items():
                value = df.iloc[row_idx, col_idx]
                if not isinstance(value, (int, float)) or pd.isna(value):
                    continue
                rows.append(
                    {
                        "source_id": source_id,
                        "sheet": sheet,
                        "row_label": label,
                        "financial_year": fy,
                        "estimate_status": estimate_status,
                        "amount_million_aud": float(value),
                        "locator": f"source_id:{source_id} | sheet:{sheet} | row:{label} | fy:{fy} | estimate_status:{estimate_status}",
                        "cached_copy_path": _relative_or_str(path),
                    }
                )

    return rows, quarantine


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", default="vic_budget_portfolio_outcomes_2024_25")
    parser.add_argument(
        "--path",
        type=Path,
        default=REPO_ROOT
        / "data/raw/state/vic_budget_portfolio_outcomes_2024_25/snapshots/20260724T190604Z/files/Budget-portfolio-outcomes-2024-25.xlsx",
    )
    args = parser.parse_args()

    rows, quarantine = extract_workbook(args.path, args.source_id)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE_DIR / "vic_bpo_extract_quarantine.jsonl", "w", encoding="utf-8") as fh:
        for q in quarantine:
            fh.write(json.dumps(q) + "\n")

    print(json.dumps({"rows_extracted": len(rows), "rows_quarantined": len(quarantine)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

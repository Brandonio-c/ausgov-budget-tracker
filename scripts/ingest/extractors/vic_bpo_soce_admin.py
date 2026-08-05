#!/usr/bin/env python3
"""Extractor for the VIC DTF Budget Portfolio Outcomes workbook's two
deferred sheets - `SOCE` (Statement of Changes in Equity) and `Admin`
(Administered Items statement) - see
ops/reports/vic-soce-admin-scope-20260805T212053Z.md for why these were
selected (they are the exact two sheets the mission names, matching the
BPO workbook's own tab names) and why this is a NEW, separate adapter
rather than an extension of scripts/ingest/extractors/vic_bpo.py: `Admin`
reuses `vic_bpo.py`'s row labels ("Net result", "Net assets") for a
materially different concept (administered items, not the department's
own controlled operations), which would collide in a single shared,
sheet-unaware label index. `vic_bpo.py`/`reload_vic_bpo.py` are
unmodified by this file.

`Admin` shares `vic_bpo.py`'s column shape exactly (Actual/Budget/
Variance, multi-line headers, inline footnote markers, a lowercase-
letter-parenthetical footnote block terminating the sheet) - the same
regex helpers are reused here (imported, not duplicated).

`SOCE` has a genuinely different, rolling-balance-across-multiple-
columns shape: 3 row-blocks (`2024-25 actuals`, `2024-25 original
budget`, `Variance`), each containing the same 4 line items across 3
equity-component columns (`Accumulated surplus`, `Contributions by
owner`, `Total equity`). Only the `Total equity` aggregate column is
extracted (the `Accumulated surplus`/`Contributions by owner` sub-
component breakdown is out of scope this milestone - a further level of
detail not modelled anywhere else in this family). The `Variance`
row-block is never extracted (same principle as the Actual/Budget/
Variance column tables: it is derivable, not a fact in its own right).

This module only extracts and quarantines; it does not write to
facts.db. See config/measure-semantics/vic_bpo_soce_admin.yaml for which
row labels map to which measure_type, and
scripts/ingest/reload_vic_bpo_soce_admin.py for classification/
validation/loading.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vic_bpo import (  # noqa: E402
    FOOTNOTE_ROW_RE,
    HEADER_CELL_RE,
    _strip_trailing_footnote,
)

EXPECTED_UNIT_TEXT = "($ million)"
SOCE_BLOCK_HEADER_RE = re.compile(r"^2024-25\s+(actuals|original budget)$|^Variance$")
SOCE_TOTAL_EQUITY_COL = 3


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def extract_admin_sheet(df: pd.DataFrame, source_id: str, path: Path) -> tuple[list[dict], list[dict]]:
    """Same Actual/Budget/Variance column shape as vic_bpo.py's OS/BS/CFS
    sheets - reuses the same header/footnote regex helpers."""
    rows: list[dict] = []
    quarantine: list[dict] = []

    if df.shape[0] < 4 or df.shape[1] < 4:
        return rows, [{"reason": "sheet_too_small", "sheet": "Admin", "shape": list(df.shape)}]

    unit_cell = df.iloc[1, df.shape[1] - 1]
    if not isinstance(unit_cell, str) or unit_cell.strip() != EXPECTED_UNIT_TEXT:
        return rows, [{"reason": "unexpected_unit_cell", "sheet": "Admin", "unit_cell": repr(unit_cell)}]

    header_row = df.iloc[2]
    col_status: dict[int, tuple[str, str]] = {}
    variance_col: int | None = None
    for col_idx in (1, 2, 3):
        raw = header_row[col_idx]
        if not isinstance(raw, str):
            quarantine.append({"reason": "unparsed_header_cell", "sheet": "Admin", "column": col_idx, "header_text": repr(raw)})
            continue
        text = raw.strip()
        if text == "Variance":
            variance_col = col_idx
            continue
        m = HEADER_CELL_RE.match(text)
        if not m:
            quarantine.append({"reason": "unparsed_header_cell", "sheet": "Admin", "column": col_idx, "header_text": text})
            continue
        estimate_status = "actual" if m.group("status") == "Actual" else "budget"
        col_status[col_idx] = (m.group("fy"), estimate_status)

    if len(col_status) != 2 or variance_col is None:
        return rows, quarantine + [
            {
                "reason": "expected_actual_budget_variance_columns",
                "sheet": "Admin",
                "found_data_columns": list(col_status.values()),
                "found_variance": variance_col is not None,
            }
        ]

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
                    "sheet": "Admin",
                    "row_label": label,
                    "financial_year": fy,
                    "estimate_status": estimate_status,
                    "amount_million_aud": float(value),
                    "locator": f"source_id:{source_id} | sheet:Admin | row:{label} | fy:{fy} | estimate_status:{estimate_status}",
                    "cached_copy_path": _relative_or_str(path),
                }
            )

    return rows, quarantine


def extract_soce_sheet(df: pd.DataFrame, source_id: str, path: Path) -> tuple[list[dict], list[dict]]:
    """Rolling-balance-across-multiple-columns shape - 3 row-blocks
    (actuals/original budget/Variance), each with the same line items
    across 3 equity-component columns. Only the Total equity column
    (index 3) is extracted; the Variance block is never extracted."""
    rows: list[dict] = []
    quarantine: list[dict] = []

    if df.shape[0] < 4 or df.shape[1] < 4:
        return rows, [{"reason": "sheet_too_small", "sheet": "SOCE", "shape": list(df.shape)}]

    unit_cell = df.iloc[1, df.shape[1] - 1]
    if not isinstance(unit_cell, str) or unit_cell.strip() != EXPECTED_UNIT_TEXT:
        return rows, [{"reason": "unexpected_unit_cell", "sheet": "SOCE", "unit_cell": repr(unit_cell)}]

    current_estimate_status: str | None = None
    fy = "2024-25"  # the only year in this workbook edition

    for row_idx in range(3, df.shape[0]):
        label_raw = df.iloc[row_idx, 0]
        if not isinstance(label_raw, str) or not label_raw.strip():
            continue
        raw_label = label_raw.strip()
        if FOOTNOTE_ROW_RE.match(raw_label):
            break

        block_match = SOCE_BLOCK_HEADER_RE.match(raw_label)
        if block_match:
            block_text = raw_label
            if block_text == "2024-25 actuals":
                current_estimate_status = "actual"
            elif block_text == "2024-25 original budget":
                current_estimate_status = "budget"
            else:  # "Variance"
                current_estimate_status = None  # never extracted
            continue

        if current_estimate_status is None:
            continue  # inside the Variance block, or before the first block header

        label = _strip_trailing_footnote(raw_label)
        value = df.iloc[row_idx, SOCE_TOTAL_EQUITY_COL]
        if not isinstance(value, (int, float)) or pd.isna(value):
            continue
        rows.append(
            {
                "source_id": source_id,
                "sheet": "SOCE",
                "row_label": label,
                "financial_year": fy,
                "estimate_status": current_estimate_status,
                "amount_million_aud": float(value),
                "locator": f"source_id:{source_id} | sheet:SOCE | row:{label} | fy:{fy} | estimate_status:{current_estimate_status} | column:Total equity",
                "cached_copy_path": _relative_or_str(path),
            }
        )

    return rows, quarantine


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    xl = pd.ExcelFile(path)
    rows: list[dict] = []
    quarantine: list[dict] = []

    if "Admin" not in xl.sheet_names:
        quarantine.append({"reason": "expected_sheet_missing", "sheet": "Admin"})
    else:
        admin_rows, admin_q = extract_admin_sheet(xl.parse("Admin", header=None), source_id, path)
        rows.extend(admin_rows)
        quarantine.extend(admin_q)

    if "SOCE" not in xl.sheet_names:
        quarantine.append({"reason": "expected_sheet_missing", "sheet": "SOCE"})
    else:
        soce_rows, soce_q = extract_soce_sheet(xl.parse("SOCE", header=None), source_id, path)
        rows.extend(soce_rows)
        quarantine.extend(soce_q)

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
    with open(QUARANTINE_DIR / "vic_bpo_soce_admin_extract_quarantine.jsonl", "w", encoding="utf-8") as fh:
        for q in quarantine:
            fh.write(json.dumps(q) + "\n")

    print(json.dumps({"rows_extracted": len(rows), "rows_quarantined": len(quarantine)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

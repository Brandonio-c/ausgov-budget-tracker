"""Shared column-header/footnote parsing for the Australian Government
Monthly Financial Statements (MFS) sibling workbooks.

Every MFS workbook (Aggregates, Note 3 Function Statement, Operating
Statement, Balance Sheet, Tax Notes 1/2, Monthly Profiles) shares the same
column-header shape - "ACTUAL\\n<FY>\\n[YTD ]<Month>\\n$<unit>" - and the
same row-label conventions (a trailing "(a)"/"(b)" footnote marker, a
footnote-explanation paragraph row that ends extraction for a sheet).
Extracted here (built while adding the second workbook, mfs_note3_function)
so each sibling extractor does not re-implement or subtly diverge on this
parsing - a real, evidenced duplication risk, not a speculative one, since
three more siblings are already acquired and awaiting the same treatment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]

HEADER_RE = re.compile(
    r"^(?P<status>[A-Z]+)\s*\n(?P<fy_long>\d{4}-\d{4})\s*\n\s*(?P<ytd>YTD\s+)?(?P<month>[A-Za-z]+)\s*\n(?P<unit>\$[a-z]+)\s*$"
)
UNIT_SCALE = {"$m": 1_000_000, "$b": 1_000_000_000, "$": 1}
FOOTNOTE_ROW = re.compile(r"^\([a-z]\)")
TRAILING_FOOTNOTE_MARK = re.compile(r"\([a-z]\)\s*$")


def fy_short(fy_long: str) -> str:
    y1, y2 = fy_long.split("-")
    return f"{y1}-{y2[-2:]}"


def relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def clean_label(label_raw: str) -> str:
    """Strip a trailing footnote marker and surrounding whitespace/newlines
    (row labels in these workbooks routinely carry a trailing space or a
    literal "\\n", e.g. "Education " or "...transactions\\n") - never
    case-folded or fuzzy-matched, only whitespace/marker-stripped."""
    return TRAILING_FOOTNOTE_MARK.sub("", label_raw).strip()


def parse_header_row(header_row, num_cols: int, *, sheet: str, quarantine: list[dict]) -> dict[int, dict]:
    """Parse column headers for columns 1..num_cols-1 of a sheet's header
    row. Column 0 is always the row-label column, never a data column.
    Appends a quarantine entry (not raised) for any column whose header
    does not match the expected shape."""
    col_meta: dict[int, dict] = {}
    for col_idx in range(1, num_cols):
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
            quarantine.append({"reason": "unknown_unit", "sheet": sheet, "column": col_idx, "unit": unit})
            continue
        col_meta[col_idx] = {
            "status": m.group("status").lower(),
            "fy": fy_short(m.group("fy_long")),
            "is_ytd": is_ytd,
            "month": m.group("month"),
            "unit": unit,
            "header_text": raw.replace("\n", " "),
        }
    return col_meta


def _combined_header_and_data_start(df, header_row: int = 1) -> tuple[dict[int, object], int]:
    """Two known header shapes exist across these workbooks' 20+ year
    history, verified directly against the real Note 3 Function Statement
    file (FY2005-06..FY2025-26), not assumed from one era's format:

      - a single combined cell per column, e.g.
        "ACTUAL\\n2024-2025\\nJuly\\n$m" (FY2012-13 onward) - header at
        `header_row`, data starts at `header_row` + 1;
      - four separate physical rows - status/financial_year/month/unit,
        one each - at `header_row`..`header_row`+3 (FY2005-06..FY2011-12) -
        header spans those 4 rows, data starts at `header_row` + 4.

    `header_row` defaults to 1 (immediately after a sheet's single title
    row, the shape every MFS sibling except Tax Notes 1-2 uses); Tax Notes
    1-2 stacks two independently-titled blocks per sheet, each with its own
    title-then-header shape starting at a different row, so
    extract_multi_block_ytd_workbook() passes each block's own header_row.

    Detected per-block (not assumed from a fixed year cutoff) by checking
    whether the header row's first data column already contains embedded
    newlines. Returns a column-index-keyed dict of combined header strings
    (or None where a column's header could not be assembled), in the same
    shape parse_header_row() already expects for the single-cell case - so
    both shapes feed the identical downstream regex/quarantine logic.
    """
    num_cols = df.shape[1]
    probe = df.iloc[header_row, 1] if num_cols > 1 else None
    is_single_cell = isinstance(probe, str) and "\n" in probe

    combined: dict[int, object] = {}
    if is_single_cell:
        for c in range(1, num_cols):
            v = df.iloc[header_row, c]
            combined[c] = v if isinstance(v, str) else None
        return combined, header_row + 1

    for c in range(1, num_cols):
        parts: list[str] = []
        complete = df.shape[0] > header_row + 3
        if complete:
            for r in range(header_row, header_row + 4):
                v = df.iloc[r, c]
                if not isinstance(v, str):
                    complete = False
                    break
                parts.append(v)
        combined[c] = "\n".join(parts) if complete else None
    return combined, header_row + 4


def _extract_block_rows(
    df, *, header_row: int, block_end: int, sheet: str, source_id: str, path: Path, quarantine: list[dict]
) -> list[dict]:
    """Extract every (row label, YTD monthly value) pair from a single
    title-header-data block spanning df rows [header_row, block_end). Shared
    by both extract_ytd_workbook() (one block = the whole sheet) and
    extract_multi_block_ytd_workbook() (each of a sheet's several stacked,
    independently-titled blocks, e.g. Tax Notes 1-2's "Tax Note 1" and
    "Tax Note 2" tables). A row with a label but no numeric value in any
    recognized column (e.g. a section heading) naturally produces zero
    rows - no special-casing needed, since every column lookup is
    individually None-checked.
    """
    rows: list[dict] = []
    combined_header, data_start = _combined_header_and_data_start(df, header_row)
    col_meta = parse_header_row(combined_header, df.shape[1], sheet=sheet, quarantine=quarantine)

    for row_idx in range(data_start, block_end):
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
                    "cached_copy_path": relative_or_str(path),
                }
            )
    return rows


def extract_ytd_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    """Extract every (row label, YTD monthly value) pair from an MFS
    sibling workbook. Shared by every sibling since all of them share the
    same sheet shape: row 0 = title (skipped), row 1 = per-column header,
    data rows follow (row label in column 0) until a footnote row
    ("(a) ..."). This function only extracts and quarantines; it does not
    write to facts.db or decide which measure_type a label maps to - that
    classification is always the loader's job, against a declarative
    semantics file, never guessed here.
    """
    rows: list[dict] = []
    quarantine: list[dict] = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, header=None)
        if df.shape[0] < 3 or df.shape[1] < 2:
            quarantine.append({"reason": "sheet_too_small", "sheet": sheet})
            continue
        rows.extend(
            _extract_block_rows(
                df, header_row=1, block_end=df.shape[0], sheet=sheet, source_id=source_id,
                path=path, quarantine=quarantine,
            )
        )
    return rows, quarantine


def extract_multi_block_ytd_workbook(
    path: Path, source_id: str, title_re: re.Pattern
) -> tuple[list[dict], list[dict]]:
    """Like extract_ytd_workbook(), but for a sheet shape that stacks
    several independently-titled title-header-data blocks in a single
    sheet (Tax Notes 1-2: "Tax Note 1 - Income Tax" then, further down the
    same sheet, "Tax Note 2 - Indirect Tax", each with its own header row
    and its own footnote-row block terminator - extract_ytd_workbook()'s
    single "stop at the first footnote row" rule would otherwise truncate
    the sheet at Note 1's footnotes and never reach Note 2's data at all).

    Block boundaries are found by title_re matching column 0 of a row -
    never assumed from a fixed row offset, since blocks are not always the
    same length (footnote-row and section-row counts vary by generation).
    Text before the first matched title row is ignored (there is none in
    the real Tax Notes 1-2 file, but a stray/malformed sheet should not
    crash the whole extraction).
    """
    rows: list[dict] = []
    quarantine: list[dict] = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, header=None)
        if df.shape[0] < 3 or df.shape[1] < 2:
            quarantine.append({"reason": "sheet_too_small", "sheet": sheet})
            continue

        title_rows = [
            r for r in range(df.shape[0])
            if isinstance(df.iloc[r, 0], str) and title_re.search(df.iloc[r, 0])
        ]
        if not title_rows:
            quarantine.append({"reason": "no_block_titles_found", "sheet": sheet})
            continue

        for i, title_row in enumerate(title_rows):
            block_end = title_rows[i + 1] if i + 1 < len(title_rows) else df.shape[0]
            rows.extend(
                _extract_block_rows(
                    df, header_row=title_row + 1, block_end=block_end, sheet=sheet, source_id=source_id,
                    path=path, quarantine=quarantine,
                )
            )
    return rows, quarantine


def find_latest_asset(source_id: str) -> Path | None:
    """The most recently acquired .xlsx/.xls asset for a source_id, per its
    latest.json manifest - shared file-discovery logic identical across
    every MFS sibling workbook."""
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

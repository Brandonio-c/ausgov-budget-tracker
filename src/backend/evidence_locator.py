"""Parse Gate 6 source locators and resolve cached evidence files."""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

DEFAULT_RAW_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
RAW_DATA_DIR = Path(os.environ.get("SPENDING_RAW_DATA_PATH", DEFAULT_RAW_DATA_DIR))

MediaType = Literal["spreadsheet", "pdf", "text_chunk", "unsupported"]

CONTENT_TYPES = {
    ".csv": "text/csv; charset=utf-8",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jsonl": "application/x-ndjson",
    ".gz": "application/gzip",
    ".json": "application/json",
}

SPREADSHEET_SUFFIXES = {".csv", ".xls", ".xlsx"}
PDF_SUFFIXES = {".pdf"}
TOKEN_RE = re.compile(r"^([a-zA-Z_]+)\s*:\s*(.+)$")
CELL_RE = re.compile(r"^[A-Za-z]{1,3}\d{1,7}$")


@dataclass(frozen=True)
class ResolvedSourceFile:
    path: Path
    content_type: str
    file_name: str


def _tokens(locator: str) -> dict[str, str]:
    """Split `key:value | key:value` locators into a dict (last key wins)."""
    out: dict[str, str] = {}
    bare: list[str] = []
    for part in (locator or "").split("|"):
        part = part.strip()
        if not part:
            continue
        m = TOKEN_RE.match(part)
        if m:
            out[m.group(1).lower()] = m.group(2).strip()
        else:
            bare.append(part)
    if bare and "text" not in out:
        out["text"] = " | ".join(bare)
    return out


def parse_locator_string(locator: str) -> dict[str, Any]:
    """Turn a Gate 6 locator string into structured viewer fields."""
    tokens = _tokens(locator)
    sheet = tokens.get("sheet")
    cell = tokens.get("cell")
    if cell and not CELL_RE.match(cell):
        cell = None
    page = tokens.get("page")
    page_number = int(page) if page and str(page).isdigit() else None

    row_number: int | None = None
    if "row" in tokens:
        raw_row = tokens["row"]
        # csv:row:N is sometimes stored as locator starting with csv:row:N
        if str(raw_row).isdigit():
            row_number = int(raw_row)

    # Handle `csv:row:951` style where csv is a bare prefix token
    if locator.strip().lower().startswith("csv:") and row_number is None:
        m = re.search(r"csv:row:(\d+)", locator, re.IGNORECASE)
        if m:
            row_number = int(m.group(1))

    unit = tokens.get("unit")
    purpose = tokens.get("purpose") or tokens.get("function")
    fy = tokens.get("fy") or tokens.get("col")
    amount = tokens.get("amount")
    table = tokens.get("table")
    if not table:
        for part in (locator or "").split("|"):
            part = part.strip()
            if re.match(r"^Table\s+\d", part, re.IGNORECASE):
                table = part
                break

    text_bits = [t for t in (table, purpose, amount) if t]
    if tokens.get("text"):
        # Avoid duplicating a bare Table N.N already captured as table
        bare = tokens["text"]
        if not table or bare.lower() != str(table).lower():
            text_bits.append(bare)
    text_anchor = " | ".join(dict.fromkeys(text_bits)) if text_bits else None

    highlight = None
    if cell and CELL_RE.match(cell):
        # Absolute workbook coordinates; row_index/column_index filled later if needed
        highlight = {"cell": cell.upper(), "row_index": None, "column_index": None}

    return {
        "tokens": tokens,
        "sheet_name": sheet,
        "cell": cell.upper() if cell else None,
        "cell_range": cell.upper() if cell else None,
        "page_number": page_number,
        "row_number": row_number,
        "unit": unit,
        "purpose": purpose,
        "financial_year_label": fy,
        "amount_label": amount,
        "text_anchor": text_anchor,
        "highlight": highlight,
        "note": locator,
    }


def media_type_for_path(path: Path | None, parsed: dict[str, Any]) -> MediaType:
    if path is None:
        if parsed.get("page_number"):
            return "pdf"
        if parsed.get("sheet_name") or parsed.get("cell") or parsed.get("row_number"):
            return "spreadsheet"
        return "unsupported"
    suffix = path.suffix.lower()
    # .jsonl.gz → .gz
    name = path.name.lower()
    if name.endswith(".jsonl.gz") or suffix == ".gz":
        return "text_chunk"
    if suffix in SPREADSHEET_SUFFIXES:
        return "spreadsheet"
    if suffix in PDF_SUFFIXES:
        return "pdf"
    if suffix in {".docx", ".txt", ".json", ".jsonl", ".md"}:
        return "text_chunk"
    if parsed.get("page_number"):
        return "pdf"
    return "unsupported"


def remap_cached_path(cached_path: str | None) -> Path | None:
    """Resolve a stored absolute path to a readable file under data/raw."""
    if not cached_path:
        return None
    candidate = Path(cached_path)
    try:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved
    except OSError:
        pass

    parts = candidate.parts
    raw_marker = None
    for i, part in enumerate(parts):
        if part == "raw" and i > 0 and parts[i - 1] == "data":
            raw_marker = i
            break
    if raw_marker is None:
        # Fall back: treat as relative under RAW_DATA_DIR
        remapped = (RAW_DATA_DIR / candidate.name).resolve()
        return remapped if remapped.is_file() else None

    rel = Path(*parts[raw_marker + 1 :])
    remapped = (RAW_DATA_DIR / rel).resolve()
    try:
        remapped.relative_to(RAW_DATA_DIR.resolve())
    except ValueError:
        return None
    return remapped if remapped.is_file() else None


def resolve_fact_source_file(cached_path: str | None) -> ResolvedSourceFile | None:
    path = remap_cached_path(cached_path)
    if path is None:
        return None
    try:
        path.relative_to(RAW_DATA_DIR.resolve())
    except ValueError:
        # Allow files that resolved via absolute host path still under repo data/raw
        default_raw = DEFAULT_RAW_DATA_DIR.resolve()
        try:
            path.relative_to(default_raw)
        except ValueError:
            return None
    content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
    if path.name.lower().endswith(".jsonl.gz"):
        content_type = "application/gzip"
    return ResolvedSourceFile(path=path, content_type=content_type, file_name=path.name)


def _csv_reconstructed(
    path: Path, row_number: int | None, window: int = 5
) -> dict[str, Any]:
    """Return a small CSV window around the cited 1-based data row (header = row 1)."""
    try:
        with path.open(newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
    except OSError:
        return {"columns": [], "rows": [], "note": "Could not read CSV"}

    if not rows:
        return {"columns": [], "rows": [], "note": "Empty CSV"}

    columns = rows[0]
    data_rows = rows[1:]
    highlight = None
    if row_number is None:
        sample = data_rows[: min(10, len(data_rows))]
        return {
            "columns": columns,
            "rows": sample,
            "note": "No csv row locator; showing first rows",
            "highlight": None,
        }

    # Locator row is typically 1-based index into the data file including header,
    # or 1-based data row. Prefer treating as absolute file line (1 = header).
    idx = row_number - 1  # 0-based into full rows
    if idx < 0:
        idx = 0
    if idx >= len(rows):
        idx = len(rows) - 1

    if idx == 0:
        # Cited header — show header + first data rows
        start = 1
        end = min(len(rows), 1 + window)
        window_rows = rows[start:end]
        return {
            "columns": columns,
            "rows": window_rows,
            "note": f"csv row {row_number} (header)",
            "highlight": None,
        }

    data_idx = idx - 1  # 0-based into data_rows
    start = max(0, data_idx - window)
    end = min(len(data_rows), data_idx + window + 1)
    window_rows = data_rows[start:end]
    highlight_row = data_idx - start
    # Prefer amount-like column for highlight if present
    amount_cols = [
        i
        for i, c in enumerate(columns)
        if re.search(r"amount|value|total|paid|invoice", str(c), re.I)
    ]
    col_i = amount_cols[0] if amount_cols else min(1, len(columns) - 1) if columns else 0
    highlight = {
        "row_index": highlight_row,
        "column_index": col_i,
        "cell": f"R{row_number}C{col_i + 1}",
    }
    return {
        "columns": columns,
        "rows": window_rows,
        "note": f"csv rows around line {row_number}",
        "highlight": highlight,
    }


def build_reconstructed(
    path: Path | None,
    media: MediaType,
    parsed: dict[str, Any],
) -> dict[str, Any] | None:
    if path is None:
        return {
            "columns": ["locator"],
            "rows": [[parsed.get("note") or ""]],
            "note": "Cached file unavailable",
            "highlight": None,
        }
    if path.suffix.lower() == ".csv":
        return _csv_reconstructed(path, parsed.get("row_number"))
    if media in {"text_chunk", "unsupported"}:
        return {
            "columns": ["field", "value"],
            "rows": [
                [k, v]
                for k, v in [
                    ("sheet", parsed.get("sheet_name")),
                    ("cell", parsed.get("cell")),
                    ("page", parsed.get("page_number")),
                    ("row", parsed.get("row_number")),
                    ("purpose", parsed.get("purpose")),
                    ("fy", parsed.get("financial_year_label")),
                    ("unit", parsed.get("unit")),
                    ("locator", parsed.get("note")),
                ]
                if v is not None
            ],
            "note": "Structured locator fields (file format not rendered inline)",
            "highlight": None,
        }
    # Spreadsheet / PDF: lightweight metadata table until the binary viewer loads
    rows = [
        [k, v]
        for k, v in [
            ("sheet", parsed.get("sheet_name")),
            ("cell", parsed.get("cell")),
            ("page", parsed.get("page_number")),
            ("row", parsed.get("row_number")),
            ("purpose", parsed.get("purpose")),
            ("fy", parsed.get("financial_year_label")),
            ("unit", parsed.get("unit")),
            ("text_anchor", parsed.get("text_anchor")),
        ]
        if v is not None
    ]
    return {
        "columns": ["field", "value"],
        "rows": rows,
        "note": parsed.get("note"),
        "highlight": None,
    }


def parse_source_locator_json(raw: str | None) -> tuple[dict[str, Any], str | None, str]:
    """Return (locator_obj, cached_path, locator_string)."""
    locator_obj: dict[str, Any] = {}
    try:
        locator_obj = json.loads(raw or "{}")
    except json.JSONDecodeError:
        locator_obj = {"raw": raw}

    cached = locator_obj.get("cached_copy_path")
    locator = locator_obj.get("locator") or ""
    if isinstance(locator, dict):
        locator = json.dumps(locator)
    return locator_obj, cached if isinstance(cached, str) else None, str(locator)

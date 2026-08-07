#!/usr/bin/env python3
"""Extract the selected modern Queensland MYFER key-aggregates cluster.

The adapter publishes only five stable General Government Sector rows and
only the current-edition MYFER/revised-estimate column. Older UPF layouts and
borrowing/debt rows are intentionally outside this adapter's boundary.
"""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = (
    REPO_ROOT
    / "data/raw/state/qld_report_on_state_finances_actuals/snapshots/20260724T190604Z/files"
)
SEMANTICS_PATH = REPO_ROOT / "config/measure-semantics/qld_myfer.yaml"
SOURCE_ID = "qld_myfer"

EDITIONS: list[dict[str, str]] = [
    {"financial_year": "2015-16", "filename": "mid-year-review-2015-16.pdf", "publication_date": "2015-12-15"},
    {"financial_year": "2016-17", "filename": "mid-year-review-2016-17.pdf", "publication_date": "2016-12-13"},
    {"financial_year": "2017-18", "filename": "2017-18MYFER.pdf", "publication_date": "2017-12-21"},
    {"financial_year": "2018-19", "filename": "Mid-Year-Fiscal-and-Economic-Review-2018-19-Downloadable-PDF_3.pdf", "publication_date": "2019-01-14"},
    {"financial_year": "2019-20", "filename": "Mid-Year-Fiscal-and-Economic-Review-2019-20.pdf", "publication_date": "2019-12-12"},
    {"financial_year": "2025-26", "filename": "mid-year-fiscal-and-economic-review-2025-26.pdf", "publication_date": "2025-12-15"},
]

NUMBER_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _repair_split_thousands(text: str) -> str:
    """Repair real PDF extraction artifacts such as ``54,9 53``."""
    previous = None
    while text != previous:
        previous = text
        text = re.sub(r"(?<=\d),(\d{1,2})\s+(?=\d{2,3}(?:\D|$))", r",\1", text)
        text = re.sub(r"(?<=\d),\s+(?=\d{3}(?:\D|$))", ",", text)
    return text


def parse_number(token: str) -> float:
    negative = token.startswith("(") and token.endswith(")")
    cleaned = token.strip("()").replace(",", "")
    value = float(cleaned)
    return -value if negative else value


def _combined_lines(text: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    combined: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lower() == "net operating" and i + 1 < len(lines) and lines[i + 1].lower().startswith("balance"):
            line = f"{line} {lines[i + 1]}"
            i += 1
            if not NUMBER_RE.search(line) and i + 1 < len(lines) and NUMBER_RE.search(lines[i + 1]):
                line = f"{line} {lines[i + 1]}"
                i += 1
        elif line.lower() == "capital" and i + 1 < len(lines) and lines[i + 1].lower().startswith("purchases "):
            line = f"{line} {lines[i + 1]}"
            i += 1
        combined.append(_repair_split_thousands(line))
        i += 1
    return combined


def _measure_labels(semantics: dict) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for measure_type, spec in semantics["measures"].items():
        for label in spec["source_labels"]:
            result.append((label, measure_type))
    return sorted(result, key=lambda pair: len(pair[0]), reverse=True)


def _parse_expected_rows(text: str, semantics: dict) -> tuple[dict[str, dict], list[dict]]:
    found: dict[str, dict] = {}
    quarantine: list[dict] = []
    lines = _combined_lines(text)
    table_start = next(
        (i for i, line in enumerate(lines) if "key fiscal agg" in line.lower()),
        0,
    )
    table_end = next(
        (i for i, line in enumerate(lines[table_start + 1 :], table_start + 1) if line.lower().startswith("notes:")),
        len(lines),
    )
    for line in lines[table_start:table_end]:
        for label, measure_type in _measure_labels(semantics):
            if not line.lower().startswith(label.lower()):
                continue
            suffix = line[len(label):]
            if suffix and not (suffix[0].isspace() or suffix[0].isdigit()):
                continue
            tokens = NUMBER_RE.findall(suffix)
            if len(tokens) == 7 and len(tokens[0].strip("()")) == 1:
                # Superscript footnote extracted inline: ``PNFA3 ...`` or
                # ``PNFA 3 ...``. It is not a data column.
                tokens = tokens[1:]
            if len(tokens) != 6:
                quarantine.append(
                    {
                        "reason": "unexpected_numeric_column_count",
                        "measure_type": measure_type,
                        "raw_line": line,
                        "numeric_column_count": len(tokens),
                    }
                )
                break
            found[measure_type] = {
                "row_label": line[: len(label)],
                "raw_line": line,
                "values": [parse_number(token) for token in tokens],
            }
            break
    return found, quarantine


def _find_table_page(reader: PdfReader, semantics: dict) -> tuple[str, int, str, dict[str, dict], list[dict]] | None:
    candidates: list[tuple[int, int, str, str, dict[str, dict], list[dict]]] = []
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        low = text.lower()
        if "key fiscal agg" not in low or "revenue" not in low or "expenses" not in low:
            continue
        rows, quarantine = _parse_expected_rows(text, semantics)
        if not rows:
            continue
        table_title = (
            "Table 2: Key fiscal aggregates"
            if "table 2: key fiscal aggregates" in low
            else "Table 3: General Government Sector - key fiscal aggregates"
        )
        candidates.append((len(rows), -len(quarantine), text, table_title, rows, quarantine))
    if not candidates:
        return None
    best = max(enumerate(candidates), key=lambda pair: (pair[1][0], pair[1][1], -pair[0]))
    candidate_index, (_, _, text, title, rows, quarantine) = best
    matching_pages = []
    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        low = page_text.lower()
        if "key fiscal agg" in low and "revenue" in low and "expenses" in low:
            parsed, _ = _parse_expected_rows(page_text, semantics)
            if parsed:
                matching_pages.append(page_idx)
    return text, matching_pages[candidate_index], title, rows, quarantine


def extract_pdf_edition(
    path: Path,
    financial_year: str,
    publication_date: str,
    *,
    source_id: str = SOURCE_ID,
) -> tuple[list[dict], list[dict]]:
    semantics = load_semantics()
    reader = PdfReader(path)
    found = _find_table_page(reader, semantics)
    if found is None:
        return [], [{"reason": "selected_table_not_found", "financial_year": financial_year, "filename": path.name}]

    _, page_idx, table_title, parsed_rows, quarantine = found
    selected_index = semantics["family"]["selected_cluster"]["selected_column_index"]
    rows: list[dict] = []
    expected = set(semantics["measures"])
    for missing in sorted(expected - set(parsed_rows)):
        quarantine.append({"reason": "expected_measure_missing", "financial_year": financial_year, "measure_type": missing})
    if expected - set(parsed_rows):
        return [], quarantine

    for measure_type in semantics["measures"]:
        parsed = parsed_rows[measure_type]
        rows.append(
            {
                "source_id": source_id,
                "source_budget_year": financial_year,
                "financial_year": financial_year,
                "publication_date": publication_date,
                "measure_type": measure_type,
                "estimate_status": "revised_estimate",
                "amount_million_aud": parsed["values"][selected_index],
                "row_label": parsed["row_label"],
                "column_header_original": "MYFER" if financial_year != "2015-16" else "Revised",
                "locator": (
                    f"source_id:{source_id} | file:{path.name} | page:{page_idx + 1} | "
                    f"table:{table_title} | row:{parsed['row_label']} | "
                    f"column:{'MYFER' if financial_year != '2015-16' else 'Revised'} | "
                    f"source_budget_year:{financial_year} | fy:{financial_year}"
                ),
                "cached_copy_path": _relative_or_str(path),
            }
        )
    return rows, quarantine


def extract_all_editions(
    source_id: str = SOURCE_ID, snapshot_dir: Path = SNAPSHOT_DIR
) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    for edition in EDITIONS:
        path = snapshot_dir / edition["filename"]
        if not path.is_file():
            quarantine.append({"reason": "edition_file_missing_on_disk", **edition})
            continue
        edition_rows, edition_quarantine = extract_pdf_edition(
            path,
            edition["financial_year"],
            edition["publication_date"],
            source_id=source_id,
        )
        rows.extend(edition_rows)
        quarantine.extend(edition_quarantine)
    return rows, quarantine

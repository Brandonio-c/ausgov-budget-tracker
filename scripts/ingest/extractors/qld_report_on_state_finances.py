#!/usr/bin/env python3
"""Extractor for 7 editions of the Queensland Treasury's "Report on
State Finances" that share a stable "Key UPF Financial Aggregates"
table shape - see
ops/reports/qld-corpus-inventory-20260807T142208Z.md for the full
page-level inventory this is built from.

Genuinely different shape from every other extractor in this repo: a
6-numeric-column table (3 sector-pairs: General Government Sector,
Public Non-financial Corporations Sector, Non-financial Public
Sector), of which only the FIRST pair (General Government Sector) is
ever extracted - confirmed reliably first in every edition by
cross-referencing each edition's own narrative Overview text against
the table's first-pair values (see the inventory report).

The table's absolute page number shifts year to year (report length
varies), so the page is located by content, not a fixed index: the
row label "Borrowing with QTC" is distinctive (a table row header
unlikely to appear elsewhere in the document's narrative prose) and is
used as the page anchor - the first page containing it is the target
table page.

Number parsing: values use a comma as a thousands separator (e.g.
"60,068" = 60,068) and parenthesized negatives (e.g. "(2,677)" =
-2,677) - simpler than TAS's space/nbsp separator, no in-number-vs-
column-separator ambiguity. Some Public Non-financial Corporations/
Non-financial Public Sector columns use a bare "-" placeholder for nil
values - this never affects General Government Sector extraction, but
means a row's total token count is not fixed at 6, so only AT LEAST 2
numeric tokens are required (enough for the GGS pair). A bare
"Revenue" narrative-heading line (zero trailing numbers) is naturally
quarantined by this same rule.

This module only extracts and quarantines; it does not write to
facts.db. See config/measure-semantics/qld_report_on_state_finances.yaml
for which row labels map to which measure_type, and
scripts/ingest/reload_qld_report_on_state_finances.py for
classification/validation/loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"

EDITIONS: list[tuple[str, str]] = [
    ("2018-19", "2018-19-Report-on-State-Finances.pdf"),
    ("2019-20", "20-077-FG-Report-on-State-Finances-2019-20-Full.pdf"),
    ("2020-21", "Report-on-State-Finances-2020-21.pdf"),
    ("2021-22", "Report-on-State-Finances-2021-22.pdf"),
    ("2022-23", "Report-on-State-Finances-2022-23.pdf"),
    ("2023-24", "Report-on-State-Finances-2023-24.pdf"),
    ("2024-25", "Report-on-State-Finances-2024-25.pdf"),
]
SNAPSHOT_DIR = REPO_ROOT / "data/raw/state/qld_report_on_state_finances_actuals/snapshots/20260724T190604Z/files"

PAGE_ANCHOR = "Borrowing with QTC"
ROW_LABEL_TO_MEASURE = {
    "Revenue": "qld_rsf_revenue",
    "Expenses": "qld_rsf_expense",
    "Net operating balance": "qld_rsf_net_operating_balance",
    "Capital purchases": "qld_rsf_capital_purchases",
    "Fiscal balance": "qld_rsf_fiscal_balance",
    "Borrowing with QTC": "qld_rsf_borrowing_qtc",
    "Leases and similar arrangements": "qld_rsf_leases",
    "Securities and derivatives": "qld_rsf_securities_derivatives",
}

NUMBER_TOKEN_RE = re.compile(r"\(?-?[\d,]+(?:\.\d+)?\)?")


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _parse_number_token(token: str) -> float | None:
    is_negative = token.startswith("(") and token.endswith(")")
    cleaned = token
    if cleaned.startswith("("):
        cleaned = cleaned[1:]
    if cleaned.endswith(")"):
        cleaned = cleaned[:-1]
    cleaned = cleaned.replace(",", "")
    if not cleaned or cleaned == "-":
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if is_negative else value


def _find_table_page(reader: PdfReader) -> tuple[str, int] | None:
    for page_idx in range(len(reader.pages)):
        text = reader.pages[page_idx].extract_text()
        if PAGE_ANCHOR in text:
            return text, page_idx
    return None


def _extract_first_two_tokens(line: str, label: str) -> list[float] | None:
    stripped = line.strip()
    if not stripped.startswith(label):
        return None
    remainder = stripped[len(label):]
    matches = [m.group(0) for m in NUMBER_TOKEN_RE.finditer(remainder)]
    values: list[float] = []
    for tok in matches:
        parsed = _parse_number_token(tok)
        if parsed is not None:
            values.append(parsed)
        if len(values) == 2:
            break
    if len(values) < 2:
        return None
    return values


def extract_pdf_edition(path: Path, source_id: str, financial_year: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []

    reader = PdfReader(path)

    found = _find_table_page(reader)
    if found is None:
        quarantine.append({"reason": "table_page_not_found", "financial_year": financial_year})
        return rows, quarantine

    text, page_idx = found
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        matched_label = None
        for label in ROW_LABEL_TO_MEASURE:
            if stripped.startswith(label):
                matched_label = label
                break
        if matched_label is None:
            continue

        values = _extract_first_two_tokens(stripped, matched_label)
        if values is None:
            quarantine.append(
                {
                    "reason": "unparseable_or_insufficient_tokens",
                    "financial_year": financial_year,
                    "raw_line": stripped,
                }
            )
            continue

        estimated_actual, actual = values
        measure_type = ROW_LABEL_TO_MEASURE[matched_label]
        for estimate_status, amount in [("estimated_actual", estimated_actual), ("actual", actual)]:
            rows.append(
                {
                    "source_id": source_id,
                    "financial_year": financial_year,
                    "measure_type": measure_type,
                    "estimate_status": estimate_status,
                    "amount_million_aud": amount,
                    "row_label": matched_label,
                    "locator": (
                        f"source_id:{source_id} | file:{path.name} | page:{page_idx + 1} | "
                        f"table:Key UPF Financial Aggregates | row:{matched_label} | "
                        f"fy:{financial_year} | estimate_status:{estimate_status}"
                    ),
                    "cached_copy_path": _relative_or_str(path),
                }
            )

    return rows, quarantine


def extract_all_editions(source_id: str, snapshot_dir: Path = SNAPSHOT_DIR) -> tuple[list[dict], list[dict]]:
    all_rows: list[dict] = []
    all_quarantine: list[dict] = []
    for financial_year, filename in EDITIONS:
        path = snapshot_dir / filename
        if not path.is_file():
            all_quarantine.append({"reason": "edition_file_missing_on_disk", "financial_year": financial_year, "filename": filename})
            continue
        rows, quarantine = extract_pdf_edition(path, source_id, financial_year)
        all_rows.extend(rows)
        all_quarantine.extend(quarantine)
    return all_rows, all_quarantine


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", default="qld_report_on_state_finances_actuals")
    args = parser.parse_args()

    rows, quarantine = extract_all_editions(args.source_id)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE_DIR / "qld_report_on_state_finances_extract_quarantine.jsonl", "w", encoding="utf-8") as fh:
        for q in quarantine:
            fh.write(json.dumps(q) + "\n")

    print(json.dumps({"rows_extracted": len(rows), "rows_quarantined": len(quarantine)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

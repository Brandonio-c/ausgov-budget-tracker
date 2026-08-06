#!/usr/bin/env python3
"""Extractor for 3 editions of the Tasmanian Treasurer's Annual
Financial Report (TAFR) that share a stable tabular Executive Summary
shape - see ops/reports/pdf-ocr-family-inventory-20260806T185946Z.md
for the full page-level inventory this is built from.

Genuinely different shape from every other extractor in this repo:
source is a real PDF (text-extractable, no OCR needed), not a
workbook. Two tables per edition are targeted, both General Government
Sector only (the Total State Sector's own parallel tables are
explicitly excluded):

  - "Key Financial Indicators" (page 6 in all 3 editions): both the
    General Government Sector and Total State Sector blocks appear on
    the SAME page, separated by their own section headings within the
    page's text - the GGS block is isolated by slicing lines between
    the "General Government Sector" and "Total State Sector" markers.
  - "Summary of Operating Result" (page 7 for 2010-11, page 8 for
    2011-12/2012-13): the GGS and Total State variants are on
    DIFFERENT pages. Naive title-text matching fails for the 2010-11
    edition (its heading wraps across a line break, so the substring
    "general government sector summary of operating result" never
    appears contiguously) - the reliable rule instead is that the GGS
    table always appears on a strictly earlier page than the Total
    State table, confirmed across all 3 editions. The extractor takes
    the FIRST page (lowest index) containing the row label "Revenue
    from transactions".

Number parsing: values use a plain space as a thousands separator
(e.g. "13 130" = 13,130) and parenthesized negatives (e.g. "(220)" =
-220). A stray trailing ")" with no matching leading "(" appears on
some tokens as a pypdf text-extraction artifact and must not be
mistaken for a negative-sign marker. Given the confirmed value range
in this population (all under 20,000 $m), a number token has at most
one internal space (one thousands-separator group of exactly 3
digits) - this assumption is scoped to these 3 known editions, not a
general-purpose parser.

This module only extracts and quarantines; it does not write to
facts.db. See config/measure-semantics/tas_tafr_pdf_backfill.yaml for
which row labels map to which measure_type, and
scripts/ingest/reload_tas_tafr_pdf_backfill.py for classification/
validation/loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"

EDITIONS: list[tuple[str, str]] = [
    ("2010-11", "TAF-2010-11.pdf"),
    ("2011-12", "2011-12-Treasurers-Annual-Financial-Report.pdf"),
    ("2012-13", "2012-13-Treasurers-Annual-Financial-Report.pdf"),
]
SNAPSHOT_DIR = REPO_ROOT / "data/raw/state/tas_treasurer_annual_financial_reports/snapshots/20260724T170239Z/files"

KFI_HEADING = "key financial indicators"
GGS_SECTOR_MARKER = "general government sector"
TOTAL_STATE_SECTOR_MARKER = "total state sector"
EXCLUDED_UNDERLYING_LABEL = "Underlying Net Operating Surplus/(Deficit)"

KFI_LABEL_TO_MEASURE = {
    "Net Operating Surplus/(Deficit)": "tas_ggs_net_operating_balance",
    "Fiscal Surplus/(Deficit)": "tas_ggs_fiscal_balance",
    "Net Debt": "tas_ggs_net_debt",
    "Net Worth": "tas_ggs_net_worth",
    "Net Financial Liabilities": "tas_ggs_net_financial_liabilities",
}
OPRES_LABEL_TO_MEASURE = {
    "Revenue from transactions": "tas_ggs_revenue",
    "Expenses from transactions": "tas_ggs_expense",
    "Expense from transactions": "tas_ggs_expense",
    "Net Operating Balance – Surplus/(Deficit)": "tas_ggs_net_operating_balance",
    "Equals Fiscal Balance – Surplus/(Deficit)": "tas_ggs_fiscal_balance",
}

NUMBER_TOKEN_RE = re.compile(r"\(?\d{1,3}(?: \d{3})?(?:\.\d+)?\)?")


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
    cleaned = cleaned.replace(" ", "")
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if is_negative else value


def _extract_row_tokens(line: str, label: str) -> list[float] | None:
    stripped = line.strip()
    if not stripped.startswith(label):
        return None
    remainder = stripped[len(label):]
    matches = [m.group(0) for m in NUMBER_TOKEN_RE.finditer(remainder)]
    values: list[float] = []
    for tok in matches:
        parsed = _parse_number_token(tok)
        if parsed is None:
            return None
        values.append(parsed)
    return values


def _find_kfi_ggs_lines(reader: PdfReader) -> tuple[list[str], int] | None:
    for page_idx in range(4, min(12, len(reader.pages))):
        text = reader.pages[page_idx].extract_text()
        if KFI_HEADING in text.lower():
            lines = text.split("\n")
            start_idx = end_idx = None
            for i, line in enumerate(lines):
                low = line.strip().lower()
                if start_idx is None and low == GGS_SECTOR_MARKER:
                    start_idx = i + 1
                    continue
                if start_idx is not None and low == TOTAL_STATE_SECTOR_MARKER:
                    end_idx = i
                    break
            if start_idx is None or end_idx is None:
                return None
            return lines[start_idx:end_idx], page_idx
    return None


def _find_opres_ggs_page(reader: PdfReader) -> tuple[str, int] | None:
    for page_idx in range(4, min(12, len(reader.pages))):
        text = reader.pages[page_idx].extract_text()
        if "Revenue from transactions" in text:
            return text, page_idx
    return None


def extract_pdf_edition(path: Path, source_id: str, financial_year: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []

    reader = PdfReader(path)

    kfi_result = _find_kfi_ggs_lines(reader)
    if kfi_result is None:
        quarantine.append({"reason": "kfi_table_not_found", "financial_year": financial_year})
    else:
        kfi_lines, kfi_page = kfi_result
        for line in kfi_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(EXCLUDED_UNDERLYING_LABEL):
                quarantine.append(
                    {
                        "reason": "excluded_underlying_measure",
                        "financial_year": financial_year,
                        "raw_line": stripped,
                    }
                )
                continue
            matched_label = None
            for label in KFI_LABEL_TO_MEASURE:
                if stripped.startswith(label):
                    matched_label = label
                    break
            if matched_label is None:
                continue
            values = _extract_row_tokens(stripped, matched_label)
            if values is None or len(values) != 3:
                quarantine.append(
                    {
                        "reason": "unparseable_or_unexpected_token_count",
                        "financial_year": financial_year,
                        "table": "Key Financial Indicators",
                        "raw_line": stripped,
                    }
                )
                continue
            budget, actual, _prior_year_actual = values
            measure_type = KFI_LABEL_TO_MEASURE[matched_label]
            for estimate_status, amount in [("budget", budget), ("actual", actual)]:
                rows.append(
                    {
                        "source_id": source_id,
                        "financial_year": financial_year,
                        "measure_type": measure_type,
                        "estimate_status": estimate_status,
                        "amount_million_aud": amount,
                        "source_table": "Key Financial Indicators",
                        "row_label": matched_label,
                        "locator": (
                            f"source_id:{source_id} | file:{path.name} | page:{kfi_page + 1} | "
                            f"table:Key Financial Indicators | row:{matched_label} | "
                            f"fy:{financial_year} | estimate_status:{estimate_status}"
                        ),
                        "cached_copy_path": _relative_or_str(path),
                    }
                )

    opres_result = _find_opres_ggs_page(reader)
    if opres_result is None:
        quarantine.append({"reason": "operating_result_table_not_found", "financial_year": financial_year})
    else:
        opres_text, opres_page = opres_result
        for line in opres_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            matched_label = None
            for label in OPRES_LABEL_TO_MEASURE:
                if stripped.startswith(label):
                    matched_label = label
                    break
            if matched_label is None:
                continue
            values = _extract_row_tokens(stripped, matched_label)
            if values is None or len(values) != 4:
                quarantine.append(
                    {
                        "reason": "unparseable_or_unexpected_token_count",
                        "financial_year": financial_year,
                        "table": "Summary of Operating Result",
                        "raw_line": stripped,
                    }
                )
                continue
            budget, actual, _variation, _variation_pct = values
            measure_type = OPRES_LABEL_TO_MEASURE[matched_label]
            for estimate_status, amount in [("budget", budget), ("actual", actual)]:
                rows.append(
                    {
                        "source_id": source_id,
                        "financial_year": financial_year,
                        "measure_type": measure_type,
                        "estimate_status": estimate_status,
                        "amount_million_aud": amount,
                        "source_table": "Summary of Operating Result",
                        "row_label": matched_label,
                        "locator": (
                            f"source_id:{source_id} | file:{path.name} | page:{opres_page + 1} | "
                            f"table:Summary of Operating Result | row:{matched_label} | "
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
    parser.add_argument("--source-id", default="tas_treasurer_annual_financial_reports")
    args = parser.parse_args()

    rows, quarantine = extract_all_editions(args.source_id)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE_DIR / "tas_tafr_pdf_backfill_extract_quarantine.jsonl", "w", encoding="utf-8") as fh:
        for q in quarantine:
            fh.write(json.dumps(q) + "\n")

    print(json.dumps({"rows_extracted": len(rows), "rows_quarantined": len(quarantine)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

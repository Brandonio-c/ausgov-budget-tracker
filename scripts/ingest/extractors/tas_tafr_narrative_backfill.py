#!/usr/bin/env python3
"""Extract the safe 2007-08--2009-10 TAS TAFR transition cluster."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = REPO_ROOT / "data/raw/state/tas_treasurer_annual_financial_reports/snapshots/20260724T170239Z/files"
SOURCE_ID = "tas_treasurer_annual_financial_reports"

NUMBER_RE = re.compile(r"\(?\d{1,3}(?: \d{3})*(?:\.\d+)?\)?")

EDITION_SPECS = {
    "2007-08": {
        "file": "TAF-Report-2007-08.pdf",
        "publication_date": "2008-10-29",
        "operating_page": 16,
        "operating_columns": {"budget": 1, "actual": 2},
        "operating_count": 3,
        "debt_page": 7,
        "debt_columns": {"budget": 1, "actual": 2},
        "debt_count": 3,
        "debt_label": "Net Debt",
        "labels": {
            "tas_ggs_revenue": "Revenue from transactions",
            "tas_ggs_expense": "Expenses from transactions",
            "tas_ggs_net_operating_balance": "equals NET OPERATING BALANCE",
            "tas_ggs_fiscal_balance": "equals FISCAL BALANCE",
        },
    },
    "2008-09": {
        "file": "2008-09-TAFR.pdf",
        "publication_date": "2009-10-28",
        "operating_page": 14,
        "operating_columns": {"budget": 0, "actual": 1},
        "operating_count": 5,
        "debt_page": 7,
        "debt_columns": {"budget": 1, "actual": 2},
        "debt_count": 3,
        "debt_label": "Net Debt",
        "labels": {
            "tas_ggs_revenue": "Revenue from transactions",
            "tas_ggs_expense": "Expenses from transactions",
            "tas_ggs_net_operating_balance": "NET OPERATING BALANCE",
            "tas_ggs_fiscal_balance": "Equals FISCAL BALANCE",
        },
    },
    "2009-10": {
        "file": "2009-10-TAFR.pdf",
        "publication_date": "2010-10-26",
        "operating_page": 7,
        "operating_columns": {"budget": 1, "actual": 5},
        "operating_count": 6,
        "debt_page": 11,
        "debt_columns": {"budget": 1, "actual": 2},
        "debt_count": 3,
        "debt_label": "General Government Sector to remain Net Debt free",
        "labels": {
            "tas_ggs_revenue": "Revenue from transactions",
            "tas_ggs_expense": "Expenses from transactions",
            "tas_ggs_net_operating_balance": "Net Operating Balance",
            "tas_ggs_fiscal_balance": "Equals Fiscal Balance",
        },
    },
}


def parse_number(token: str) -> float:
    negative = token.startswith("(") and token.endswith(")")
    cleaned = token.strip("()").replace(" ", "")
    value = float(cleaned)
    return -value if negative else value


def _values_after_label(lines: list[str], label: str, expected_count: int) -> list[float] | None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        normalized_label = re.sub(r"\s+", " ", label.strip())
        label_pattern = re.sub(r"\\ ", r"\\s+", re.escape(normalized_label))
        match = re.match(label_pattern, stripped, flags=re.IGNORECASE)
        if match is None:
            continue
        remainder = stripped[match.end():]
        tokens = NUMBER_RE.findall(remainder)
        if len(tokens) == expected_count:
            return [parse_number(token) for token in tokens]
        # In the 2007-08 Operating Statement, section totals are on an
        # unlabelled numeric-only line after the component rows. Notes such as
        # "1.6(a)" contain letters and therefore cannot be mistaken for it.
        for candidate in lines[index + 1:index + 16]:
            candidate_tokens = NUMBER_RE.findall(candidate)
            if len(candidate_tokens) == expected_count and not re.search(r"[A-Za-z]", candidate):
                return [parse_number(token) for token in candidate_tokens]
        return [parse_number(token) for token in tokens]
    return None


def _cached_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def extract_page_texts(
    *, path: Path, financial_year: str, spec: dict, page_texts: dict[int, str]
) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    operating_lines = page_texts.get(spec["operating_page"], "").splitlines()
    debt_lines = page_texts.get(spec["debt_page"], "").splitlines()

    for measure_type, label in spec["labels"].items():
        values = _values_after_label(operating_lines, label, spec["operating_count"])
        if values is None or len(values) != spec["operating_count"]:
            quarantine.append({
                "reason": "missing_expected_row" if values is None else "unexpected_numeric_column_count",
                "financial_year": financial_year,
                "measure_type": measure_type,
                "page": spec["operating_page"] + 1,
                "observed_count": None if values is None else len(values),
            })
            continue
        for status, column in spec["operating_columns"].items():
            rows.append(_row(path, financial_year, spec, measure_type, label, status, values[column], spec["operating_page"]))

    debt_values = _values_after_label(debt_lines, spec["debt_label"], spec["debt_count"])
    if debt_values is None or len(debt_values) < spec["debt_count"]:
        quarantine.append({
            "reason": "missing_expected_row" if debt_values is None else "unexpected_numeric_column_count",
            "financial_year": financial_year,
            "measure_type": "tas_ggs_net_debt",
            "page": spec["debt_page"] + 1,
            "observed_count": None if debt_values is None else len(debt_values),
        })
    else:
        debt_values = debt_values[: spec["debt_count"]]
        for status, column in spec["debt_columns"].items():
            rows.append(_row(path, financial_year, spec, "tas_ggs_net_debt", "Net Debt", status, debt_values[column], spec["debt_page"]))
    return rows, quarantine


def _row(path: Path, fy: str, spec: dict, measure: str, label: str, status: str, amount: float, page: int) -> dict:
    return {
        "source_id": SOURCE_ID,
        "financial_year": fy,
        "publication_date": spec["publication_date"],
        "measure_type": measure,
        "estimate_status": status,
        "amount_million_aud": amount,
        "row_label": label,
        "locator": f"source_id:{SOURCE_ID} | file:{path.name} | page:{page + 1} | row:{label} | fy:{fy} | estimate_status:{status}",
        "cached_copy_path": _cached_path(path),
    }


def extract_edition(path: Path, financial_year: str, spec: dict) -> tuple[list[dict], list[dict]]:
    reader = PdfReader(path)
    required_pages = {spec["operating_page"], spec["debt_page"]}
    if any(page >= len(reader.pages) for page in required_pages):
        return [], [{"reason": "missing_exact_pdf_page", "financial_year": financial_year}]
    texts = {page: reader.pages[page].extract_text() for page in required_pages}
    return extract_page_texts(path=path, financial_year=financial_year, spec=spec, page_texts=texts)


def extract_all_editions(snapshot_dir: Path = SNAPSHOT_DIR) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    for financial_year, spec in EDITION_SPECS.items():
        path = snapshot_dir / spec["file"]
        if not path.is_file():
            quarantine.append({"reason": "edition_file_missing_on_disk", "financial_year": financial_year, "file": spec["file"]})
            continue
        extracted, deferred = extract_edition(path, financial_year, spec)
        rows.extend(extracted)
        quarantine.extend(deferred)
    return rows, quarantine

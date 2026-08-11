#!/usr/bin/env python3
"""Bounded, source-specific extractor for the 2026-27 National Disability
Insurance Agency Portfolio Budget Statements (plan item 5.5).

The generalized federal_pbs_programs_all.py adapter yields zero published
facts for this source: its layout (single entity, no Administered/
Departmental split, "Revenue from Government" resourcing lines, "Total for
Program N" totals, and an "Outcome 1 totals by resource type" cross-program
reconciliation section) does not match the multi-portfolio Table 2.1
assumptions that adapter is tuned for, and its cross-document dedupe keys
by (portfolio, program_label, fy, status, amount) with NDIA's assigned
portfolio ("Health Disability and Ageing") shared by an unrelated, larger
document - silently discarding every NDIA row as an apparent duplicate.

This adapter is bounded to exactly one document, one entity, one outcome
and two programs (Table 2.1.1: Budgeted expenses for Outcome 1), verified
against the real PDF text before being written.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = "federal_pbs_2026_27_ndia"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "federal"
OUT_PATH = REPO_ROOT / "data" / "staging" / "breakdowns" / f"{SOURCE_ID}.csv"
LANDING_URL = "https://budget.gov.au/content/pbs/index.htm"
RESOURCE_URL = (
    "https://www.health.gov.au/sites/default/files/2026-06/"
    "budget_2026-27_national_disability_insurance_agency_2026-27_health_pbs.pdf"
)
ENTITY = "National Disability Insurance Agency"
OUTCOME = "1"

YEARS = ("2025-26", "2026-27", "2027-28", "2028-29", "2029-30")
STATUSES = (
    "estimated_actual",
    "budget",
    "forward_estimate",
    "forward_estimate",
    "forward_estimate",
)

TOKEN = r"(?:\(?-?\d{1,3}(?:,\d{3})*\)?|-)"
TOTAL_RE = re.compile(r"^Total for Program\s+(?P<number>\d+\.\d+)", re.I)
PROGRAM_RE = re.compile(r"^Program\s+(?P<number>\d+\.\d+)\s*[:\-–]\s*(?P<name>.+)$", re.I)
OUTCOME_TOTALS_RE = re.compile(r"^Outcome\s+\d+\s+totals by resource type$", re.I)
BARE_AMOUNTS_RE = re.compile(rf"^{TOKEN}(?:\s+{TOKEN}){{4}}$")


def _norm(value: str) -> str:
    value = value.replace("’", "'").replace("–", "-")
    return re.sub(r"\s+", " ", value).strip(" .")


def _parse_amount_tokens(text: str) -> list[int]:
    amounts = []
    for token in text.split():
        if token == "-":
            amounts.append(0)
        else:
            negative = token.startswith("(") and token.endswith(")")
            value = int(token.strip("()").replace(",", "")) * 1000
            amounts.append(-value if negative else value)
    return amounts


def _amount_line(line: str) -> tuple[str, list[int]] | None:
    match = re.match(rf"^(?P<label>.*?)(?P<nums>(?:\s+{TOKEN}){{5}})\s*$", line)
    if match and _norm(match.group("label")):
        return _norm(match.group("label")), _parse_amount_tokens(match.group("nums"))
    if BARE_AMOUNTS_RE.match(line):
        return "", _parse_amount_tokens(line)
    return None


def _latest_pdf() -> Path:
    manifest = RAW_ROOT / SOURCE_ID / "latest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assets = [asset for asset in data.get("assets", []) if asset.get("detected_type") == "pdf"]
    if len(assets) != 1:
        raise ValueError(f"{SOURCE_ID}: expected one PDF, found {len(assets)}")
    pdf = REPO_ROOT / "data" / assets[0]["stored_path"]
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    return pdf


@dataclass(frozen=True)
class _Row:
    fy: str
    amount: int
    category: str
    program_number: str
    program_label: str
    component_label: str | None
    estimate_status: str
    row_kind: str
    page_no: int


def _rows(
    *,
    page_no: int,
    program_number: str,
    program_name: str,
    component: str | None,
    amounts: list[int],
) -> list[_Row]:
    program = f"Program {program_number} - {program_name}"
    base = f"{ENTITY} / Outcome {OUTCOME} / {program}"
    category = base if component is None else f"{base} / {component}"
    row_kind = "program" if component is None else "component"
    return [
        _Row(
            fy=year,
            amount=amount,
            category=category,
            program_number=program_number,
            program_label=program,
            component_label=component,
            estimate_status=status,
            row_kind=row_kind,
            page_no=page_no,
        )
        for year, status, amount in zip(YEARS, STATUSES, amounts)
    ]


def extract(pdf: Path | None = None) -> list[dict]:
    source_pdf = pdf or _latest_pdf()
    rows: list[_Row] = []
    program_number: str | None = None
    program_names: dict[str, str] = {}
    pending: list[str] = []
    in_table = False

    for page_no, page in enumerate(PdfReader(str(source_pdf)).pages, start=1):
        lines = [_norm(line) for line in (page.extract_text() or "").splitlines() if _norm(line)]
        if any(re.match(r"^Table\s+2\.1\.1\s*:?.*Budgeted expenses for Outcome", line, re.I) for line in lines):
            in_table = True

        for line in lines:
            if re.match(r"^Section 3", line, re.I) or OUTCOME_TOTALS_RE.match(line):
                in_table = False
                program_number = None
                pending = []
                continue
            program_match = PROGRAM_RE.match(line)
            if in_table and program_match:
                program_number = program_match.group("number")
                program_names[program_number] = _norm(program_match.group("name"))
                pending = []
                continue
            if not in_table or not program_number:
                continue
            if re.match(r"^Revenue from Government$", line, re.I):
                pending = []
                continue
            parsed = _amount_line(line)
            if parsed is None:
                if re.match(r"^(?:20\d\d|Estimated|Budget|Forward|\$'?000)", line, re.I):
                    continue
                if len(pending) < 3:
                    pending.append(line)
                continue
            label_part, amounts = parsed
            label = _norm(" ".join([*pending, label_part])) if pending else label_part
            pending = []
            if not label:
                continue
            total_match = TOTAL_RE.match(label)
            if total_match:
                number = total_match.group("number")
                name = program_names.get(number)
                if not name:
                    raise ValueError(f"{SOURCE_ID} page {page_no}: missing name for program {number}")
                rows.extend(
                    _rows(page_no=page_no, program_number=number, program_name=name, component=None, amounts=amounts)
                )
                continue
            if label.lower().startswith("average staffing level"):
                continue
            name = program_names[program_number]
            rows.extend(
                _rows(
                    page_no=page_no,
                    program_number=program_number,
                    program_name=name,
                    component=label,
                    amounts=amounts,
                )
            )

    keys = [(row.fy, row.category, row.estimate_status) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{SOURCE_ID}: duplicate year/category/status rows")

    out_rows = []
    for row in rows:
        out_rows.append(
            {
                "fy": row.fy,
                "amount": row.amount,
                "category": row.category,
                "entity": ENTITY,
                "outcome": f"Outcome {OUTCOME}",
                "program_number": row.program_number,
                "program_label": row.program_label,
                "component_label": row.component_label,
                "estimate_status": row.estimate_status,
                "row_kind": row.row_kind,
                "source_id_origin": SOURCE_ID,
                "cached_copy_path": str(source_pdf.resolve().relative_to(REPO_ROOT)),
                "locator": (
                    f"source_id:{SOURCE_ID} | pdf:{source_pdf.name} | page:{row.page_no} | "
                    f"entity:{ENTITY} | outcome:{OUTCOME} | program:{row.program_number} | "
                    f"row:{row.component_label or 'program total'} | fy:{row.fy} | unit:$000"
                ),
                "landing_url": LANDING_URL,
                "resource_url": RESOURCE_URL,
            }
        )
    return out_rows


def write_csv(rows: list[dict], output: Path = OUT_PATH) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return output


def main() -> int:
    rows = extract()
    path = write_csv(rows)
    print(
        json.dumps(
            {
                "source_id": SOURCE_ID,
                "rows": len(rows),
                "programs": len({r["category"] for r in rows if r["row_kind"] == "program"}),
                "path": str(path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

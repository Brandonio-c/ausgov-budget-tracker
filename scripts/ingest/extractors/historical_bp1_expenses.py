#!/usr/bin/env python3
"""Extract edition-bounded historical BP1 expenses and component tables.

March 2022-23 calls the expenses statement "Statement 5" and uses Table 5A.1;
the October 2022-23 and 2023-24 editions use Statement 6 and Table 6A.1.
This adapter makes those layout and vintage differences explicit.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "federal"
OUT_ROOT = REPO_ROOT / "data" / "staging" / "breakdowns"

FUNCTION_HEADERS = (
    "General public services",
    "Defence",
    "Public order and safety",
    "Education",
    "Health",
    "Social security and welfare",
    "Housing and community amenities",
    "Recreation and culture",
    "Fuel and energy",
    "Agriculture, forestry and fishing",
    "Mining, manufacturing and construction",
    "Transport and communication",
    "Other economic affairs",
    "Other purposes",
)
NUM = r"-?\d{1,3}(?:,\d{3})*"


@dataclass(frozen=True)
class Edition:
    source_id: str
    publication_edition: str
    publication_vintage: str
    statement_number: int
    appendix_table: str
    years: tuple[str, ...]
    statuses: tuple[str, ...]
    landing_url: str
    resource_url: str

    @property
    def output_path(self) -> Path:
        return OUT_ROOT / f"{self.source_id}.csv"


EDITIONS = (
    Edition(
        source_id="federal_budget_statement_6_2022_23_march",
        publication_edition="2022-23 March Budget",
        publication_vintage="2022-03",
        statement_number=5,
        appendix_table="5A.1",
        years=("2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"),
        statuses=("actual", "estimated_actual", "budget", "forward_estimate", "forward_estimate", "forward_estimate"),
        landing_url="https://archive.budget.gov.au/2022-23/",
        resource_url="https://archive.budget.gov.au/2022-23/bp1/download/bp1_2022-23.pdf",
    ),
    Edition(
        source_id="federal_budget_statement_6_2022_23_october",
        publication_edition="2022-23 October Budget",
        publication_vintage="2022-10",
        statement_number=6,
        appendix_table="6A.1",
        years=("2021-22", "2022-23", "2023-24", "2024-25", "2025-26"),
        statuses=("actual", "budget", "forward_estimate", "forward_estimate", "forward_estimate"),
        landing_url="https://archive.budget.gov.au/2022-23-october/",
        resource_url="https://archive.budget.gov.au/2022-23-october/bp1/download/bp1_2022-23.pdf",
    ),
    Edition(
        source_id="federal_budget_statement_6_2023_24",
        publication_edition="2023-24 Budget",
        publication_vintage="2023-05",
        statement_number=6,
        appendix_table="6A.1",
        years=("2021-22", "2022-23", "2023-24", "2024-25", "2025-26", "2026-27"),
        statuses=("actual", "estimated_actual", "budget", "forward_estimate", "forward_estimate", "forward_estimate"),
        landing_url="https://archive.budget.gov.au/2023-24/index.htm",
        resource_url="https://archive.budget.gov.au/2023-24/bp1/download/bp1_2023-24.pdf",
    ),
)


def _norm(value: str) -> str:
    value = value.replace("–", "-").replace("’", "'")
    return re.sub(r"\s+", " ", value).strip(" .")


def _latest_pdf(source_id: str) -> Path:
    manifest = RAW_ROOT / source_id / "latest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assets = [asset for asset in data.get("assets", []) if asset.get("detected_type") == "pdf"]
    if len(assets) != 1:
        raise ValueError(f"{source_id}: expected one acquired PDF, found {len(assets)}")
    path = REPO_ROOT / "data" / assets[0]["stored_path"]
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _amount_pattern(column_count: int) -> re.Pattern[str]:
    return re.compile(rf"^(?P<label>.*?)(?P<nums>(?:\s+(?:{NUM})){{{column_count}}})\s*$")


def _parse_amount_line(line: str, column_count: int) -> tuple[str, list[int]] | None:
    match = _amount_pattern(column_count).match(line.strip())
    if not match:
        return None
    label = _norm(match.group("label"))
    if not label:
        return None
    amounts = [int(token.replace(",", "")) * 1_000_000 for token in match.group("nums").split()]
    return label, amounts


def _function(label: str) -> str | None:
    normalized = _norm(re.sub(r"\s*\(continued\)\s*", "", label, flags=re.I)).lower()
    for function in FUNCTION_HEADERS:
        if normalized == function.lower():
            return function
    return None


def _skip_line(line: str, edition: Edition) -> bool:
    low = _norm(line).lower()
    return (
        not low
        or low in {"actual", "estimates", "(continued)"}
        or low.startswith("budget paper no. 1")
        or low.startswith("page ")
        or low.startswith(f"statement {edition.statement_number}:")
        or low.startswith("appendix a:")
        or low.startswith("table ")
        or low.startswith("$m")
        or bool(re.fullmatch(r"(?:\d{4}-\d{2}\s*)+", low))
    )


def _rows_for_values(
    edition: Edition,
    *,
    page_no: int,
    table_id: str,
    category: str,
    row_kind: str,
    amounts: list[int],
    source_pdf: Path,
) -> list[dict]:
    rows = []
    for financial_year, status, amount in zip(edition.years, edition.statuses, amounts):
        # Historical actuals belong to the audited FBO branch. This Budget-paper
        # adapter publishes only estimates so measure_type remains truthful.
        if status == "actual":
            continue
        rows.append(
            {
                "fy": financial_year,
                "amount": amount,
                "category": category,
                "estimate_status": status,
                "row_kind": row_kind,
                "publication_edition": edition.publication_edition,
                "publication_vintage": edition.publication_vintage,
                "locator": (
                    f"pdf:{source_pdf.name} | page:{page_no} | Table {table_id} | "
                    f"row:{category} | col:{financial_year} | unit:$m | "
                    f"edition:{edition.publication_edition}"
                ),
                "landing_url": edition.landing_url,
                "resource_url": edition.resource_url,
            }
        )
    return rows


def extract_appendix(edition: Edition, pdf: Path) -> list[dict]:
    rows: list[dict] = []
    current_function: str | None = None
    pending: list[str] = []
    active = False

    for page_no, page in enumerate(PdfReader(str(pdf)).pages, start=1):
        text = page.extract_text() or ""
        if f"Table {edition.appendix_table}:" in text or (
            active and "Total expenses" not in " ".join(pending)
        ):
            active = True
        if not active:
            continue
        for raw in text.splitlines():
            line = _norm(raw)
            if _skip_line(line, edition):
                continue
            parsed = _parse_amount_line(line, len(edition.years))
            if parsed is None:
                function = _function(line)
                if function:
                    current_function = function
                    pending = []
                elif not re.match(r"^\(?[a-z]\)", line, re.I):
                    pending.append(line)
                continue

            label_part, amounts = parsed
            label = _norm(" ".join([*pending, label_part])) if pending else label_part
            pending = []
            if label.lower() == "total expenses":
                rows.extend(
                    _rows_for_values(
                        edition,
                        page_no=page_no,
                        table_id=edition.appendix_table,
                        category="Total expenses",
                        row_kind="grand_total",
                        amounts=amounts,
                        source_pdf=pdf,
                    )
                )
                active = False
                break

            total_match = re.match(r"^Total\s+(.+)$", label, re.I)
            total_function = _function(total_match.group(1)) if total_match else None
            direct_function = _function(label)
            if total_function:
                current_function = total_function
                category = total_function
                row_kind = "function"
            elif direct_function:
                current_function = direct_function
                category = direct_function
                row_kind = "function"
            elif current_function:
                category = f"{current_function} / {label}"
                row_kind = "subfunction"
            else:
                raise ValueError(f"{edition.source_id} page {page_no}: row without function: {label}")

            rows.extend(
                _rows_for_values(
                    edition,
                    page_no=page_no,
                    table_id=edition.appendix_table,
                    category=category,
                    row_kind=row_kind,
                    amounts=amounts,
                    source_pdf=pdf,
                )
            )
        if not active:
            break
    if active:
        raise ValueError(f"{edition.source_id}: appendix table did not reach Total expenses")
    return rows


def _component_parent(title: str, appendix_rows: list[dict]) -> str:
    normalized = _norm(title)
    normalized = re.sub(r"^.*?Trends in the major components of (?:the )?", "", normalized, flags=re.I)
    normalized = re.sub(r"\s+sub-function expenses?$", "", normalized, flags=re.I)
    normalized = re.sub(r"\s+expenses?$", "", normalized, flags=re.I)
    candidates = []
    for row in appendix_rows:
        if row["fy"] != appendix_rows[0]["fy"] or row["row_kind"] == "grand_total":
            continue
        leaf = row["category"].split(" / ")[-1]
        if _norm(leaf).lower() == normalized.lower():
            candidates.append(row["category"])
    if len(candidates) != 1:
        raise ValueError(f"component parent {normalized!r} matched {candidates}")
    return candidates[0]


def extract_components(edition: Edition, pdf: Path, appendix_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    table_prefix = str(edition.statement_number)
    table_re = re.compile(rf"^Table ({table_prefix}\.\d+\.\d+):\s+Trends in the major components", re.I)

    for page_no, page in enumerate(PdfReader(str(pdf)).pages, start=1):
        lines = [_norm(line) for line in (page.extract_text() or "").splitlines()]
        starts = [index for index, line in enumerate(lines) if table_re.match(line)]
        for start in starts:
            table_id = table_re.match(lines[start]).group(1)  # type: ignore[union-attr]
            title_parts = [lines[start]]
            cursor = start + 1
            while cursor < len(lines) and not lines[cursor].lower().startswith("component"):
                if lines[cursor] and not re.match(r"^(?:actual|estimates|\d{4})", lines[cursor], re.I):
                    title_parts.append(lines[cursor])
                cursor += 1
            if cursor >= len(lines):
                continue
            parent = _component_parent(" ".join(title_parts), appendix_rows)
            pending: list[str] = []
            cursor += 1
            while cursor < len(lines):
                line = lines[cursor]
                cursor += 1
                if not line or _skip_line(line, edition):
                    continue
                if line.startswith("Table ") or re.match(r"^\(?[a-z]\)", line, re.I):
                    break
                parsed = _parse_amount_line(line, len(edition.years) - (1 if len(edition.years) == 6 else 0))
                if parsed is None:
                    if not re.match(r"^(?:component|actual|estimates|\d{4})", line, re.I):
                        pending.append(line)
                    continue
                label_part, amounts = parsed
                label = _norm(" ".join([*pending, label_part])) if pending else label_part
                pending = []
                label = re.sub(r"\s*\([a-z]\)\s*$", "", label, flags=re.I)
                if label.lower().startswith("total"):
                    continue
                # Six-column appendix editions have five-column component tables;
                # their component years omit the old actual column.
                component_edition = edition
                if len(amounts) != len(edition.years):
                    component_edition = Edition(
                        **{
                            **edition.__dict__,
                            "years": edition.years[1:],
                            "statuses": edition.statuses[1:],
                        }
                    )
                rows.extend(
                    _rows_for_values(
                        component_edition,
                        page_no=page_no,
                        table_id=table_id,
                        category=f"{parent} / {label}",
                        row_kind="component",
                        amounts=amounts,
                        source_pdf=pdf,
                    )
                )
    return rows


def extract_edition(edition: Edition, pdf: Path | None = None) -> list[dict]:
    source_pdf = pdf or _latest_pdf(edition.source_id)
    appendix = extract_appendix(edition, source_pdf)
    return appendix + extract_components(edition, source_pdf, appendix)


def write_csv(rows: list[dict], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "fy",
        "amount",
        "category",
        "estimate_status",
        "row_kind",
        "publication_edition",
        "publication_vintage",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return output


def main() -> int:
    for edition in EDITIONS:
        rows = extract_edition(edition)
        output = write_csv(rows, edition.output_path)
        print({"source_id": edition.source_id, "rows": len(rows), "path": str(output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extract entity-aware program expense paths from historical Treasury PBS PDFs."""

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
TOKEN = r"(?:\(?-?\d{1,3}(?:,\d{3})*\)?|-)"
TOTAL_RE = re.compile(r"^Total expenses for program\s+(?P<number>\d+(?:\.\d+)?)", re.I)
PROGRAM_RE = re.compile(
    r"^Program\s+(?P<number>\d+(?:\.\d+)?)\s*[:\-–]\s*(?P<name>.+)$",
    re.I,
)
OUTCOME_RE = re.compile(r"Budgeted expenses for Outcome\s+(?P<number>\d+)", re.I)
OUTCOME_TOTALS_RE = re.compile(r"^Outcome\s+\d+\s+Totals by appropriation type$", re.I)

# Standard PGPA Act appropriation-type headings used verbatim across every
# entity/program table. Several of these introduce more than one indented
# line item (e.g. "Ordinary annual services" often lists two-plus specific
# appropriations), so the heading must persist across siblings rather than
# being consumed by only the first one.
KNOWN_HEADINGS = {
    "ordinary annual services (appropriation bill no. 1)": "Ordinary annual services (Appropriation Bill No. 1)",
    "other services (appropriation bill no. 2)": "Other services (Appropriation Bill No. 2)",
    "special appropriations": "Special appropriations",
    "special accounts": "Special accounts",
}
# This scope-wide memo line always appears standalone, never nested beneath
# one of the appropriation-type headings above.
STANDALONE_LABEL_PREFIXES = ("expenses not requiring appropriation",)


def _heading_prefix(label: str) -> str | None:
    lowered = label.lower()
    for key, canonical in KNOWN_HEADINGS.items():
        if lowered.startswith(key):
            return canonical
    return None


@dataclass(frozen=True)
class PbsEdition:
    source_id: str
    publication_edition: str
    publication_vintage: str
    years: tuple[str, ...]
    statuses: tuple[str, ...]
    landing_url: str
    resource_url: str

    @property
    def output_path(self) -> Path:
        return OUT_ROOT / f"{self.source_id}.csv"


EDITIONS = (
    PbsEdition(
        "federal_pbs_2022_23_march_treasury",
        "2022-23 March Budget",
        "2022-03",
        ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26"),
        ("estimated_actual", "budget", "forward_estimate", "forward_estimate", "forward_estimate"),
        "https://archive.budget.gov.au/2022-23/",
        "https://treasury.gov.au/sites/default/files/2022-03/tsy_pbs_2022-23.pdf",
    ),
    PbsEdition(
        "federal_pbs_2022_23_october_treasury",
        "2022-23 October Budget",
        "2022-10",
        ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26"),
        ("estimated_actual", "budget", "forward_estimate", "forward_estimate", "forward_estimate"),
        "https://archive.budget.gov.au/2022-23-october/",
        "https://treasury.gov.au/sites/default/files/2022-10/tsy_pbs_october-2022-23.pdf",
    ),
    PbsEdition(
        "federal_pbs_2023_24_treasury",
        "2023-24 Budget",
        "2023-05",
        ("2022-23", "2023-24", "2024-25", "2025-26", "2026-27"),
        ("estimated_actual", "budget", "forward_estimate", "forward_estimate", "forward_estimate"),
        "https://archive.budget.gov.au/2023-24/index.htm",
        "https://treasury.gov.au/sites/default/files/2023-07/tsy_pbs_2023-24_230727.pdf",
    ),
)


def _norm(value: str) -> str:
    value = value.replace("’", "'").replace("–", "-")
    return re.sub(r"\s+", " ", value).strip(" .")


def _latest_pdf(source_id: str) -> Path:
    manifest = RAW_ROOT / source_id / "latest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assets = [asset for asset in data.get("assets", []) if asset.get("detected_type") == "pdf"]
    if len(assets) != 1:
        raise ValueError(f"{source_id}: expected one PDF, found {len(assets)}")
    pdf = REPO_ROOT / "data" / assets[0]["stored_path"]
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    return pdf


def _entity_from_page(lines: list[str]) -> str | None:
    candidates: list[str] = []
    for line in lines:
        for pattern in (
            r"^Page\s+\d+\s*\|\s*(.+)$",
            r"^(.+?)\s*\|\s*Page\s+\d+$",
        ):
            match = re.match(pattern, line, re.I)
            if match:
                candidates.append(_norm(match.group(1)))
    excluded = ("portfolio budget statements", "budget paper", "section ")
    usable = [
        value
        for value in candidates
        if value and not any(part in value.lower() for part in excluded)
    ]
    return usable[0] if usable else None


BARE_AMOUNTS_RE = re.compile(rf"^{TOKEN}(?:\s+{TOKEN}){{4}}$")


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
        # A label wrapped onto enough physical lines that its five year
        # columns land on a separate, label-free line entirely.
        return "", _parse_amount_tokens(line)
    return None


def _merge_wrapped_amount_lines(lines: list[str]) -> list[str]:
    """Reassemble rows whose five year columns pypdf split across more than
    one physical line (observed for a small number of long-label rows, e.g.
    ATO "Taxation Administration Act 1953 - section 16 (Non-refund items)").

    Only a line that does NOT already satisfy the normal five-token row
    pattern is a merge candidate, and only pure numeric continuation lines
    are absorbed, so ordinary single-line rows are never touched.
    """
    merged: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _amount_line(line) is not None:
            merged.append(line)
            i += 1
            continue
        match = re.match(rf"^(?P<label>.+?)(?P<nums>(?:\s+{TOKEN}){{1,4}})\s*$", line)
        if match and _norm(match.group("label")):
            nums = match.group("nums").split()
            j = i + 1
            while len(nums) < 5 and j < len(lines):
                tail_tokens = lines[j].split()
                if not tail_tokens or not all(re.fullmatch(TOKEN, t) for t in tail_tokens):
                    break
                if len(nums) + len(tail_tokens) > 5:
                    break
                nums.extend(tail_tokens)
                j += 1
            if len(nums) == 5:
                merged.append(_norm(f"{match.group('label')} {' '.join(nums)}"))
                i = j
                continue
        merged.append(line)
        i += 1
    return merged


def _rows(
    edition: PbsEdition,
    *,
    pdf: Path,
    page_no: int,
    entity: str,
    outcome: str,
    program_number: str,
    program_name: str,
    scope: str | None,
    component: str | None,
    amounts: list[int],
) -> list[dict]:
    program = f"Program {program_number} - {program_name}"
    base = f"Treasury / {entity} / Outcome {outcome} / {program}"
    category = base if component is None else f"{base} / {scope or 'Unscoped'} / {component}"
    row_kind = "program" if component is None else "component"
    return [
        {
            "fy": year,
            "amount": amount,
            "category": category,
            "portfolio": "Treasury",
            "entity": entity,
            "outcome": f"Outcome {outcome}",
            "program_number": program_number,
            "program_label": program,
            "component_label": component,
            "estimate_status": status,
            "row_kind": row_kind,
            "publication_edition": edition.publication_edition,
            "publication_vintage": edition.publication_vintage,
            "source_id_origin": edition.source_id,
            "cached_copy_path": str(pdf.resolve().relative_to(REPO_ROOT)),
            "locator": (
                f"source_id:{edition.source_id} | pdf:{pdf.name} | page:{page_no} | "
                f"entity:{entity} | outcome:{outcome} | program:{program_number} | "
                f"row:{component or 'program total'} | fy:{year} | unit:$000 | "
                f"edition:{edition.publication_edition}"
            ),
            "landing_url": edition.landing_url,
            "resource_url": edition.resource_url,
        }
        for year, status, amount in zip(edition.years, edition.statuses, amounts)
    ]


def extract_edition(edition: PbsEdition, pdf: Path | None = None) -> list[dict]:
    source_pdf = pdf or _latest_pdf(edition.source_id)
    rows: list[dict] = []
    entity: str | None = None
    outcome: str | None = None
    program_number: str | None = None
    program_names: dict[tuple[str, str], str] = {}
    scope: str | None = None
    heading: str | None = None
    pending: list[str] = []
    in_outcome_table = False

    for page_no, page in enumerate(PdfReader(str(source_pdf)).pages, start=1):
        lines = [_norm(line) for line in (page.extract_text() or "").splitlines() if _norm(line)]
        lines = _merge_wrapped_amount_lines(lines)
        page_entity = _entity_from_page(lines)
        if page_entity:
            entity = page_entity
        page_outcomes = [match.group("number") for line in lines if (match := OUTCOME_RE.search(line))]
        if page_outcomes:
            outcome = page_outcomes[-1]
        if any(re.match(r"^Table\s+2\.\s*1(?:\.\d+)?\s*:?.*Budgeted expenses for Outcome", line, re.I) for line in lines):
            in_outcome_table = True

        for line in lines:
            if re.match(r"^(?:Section 3|Budgeted financial statements|Movement of administered)", line, re.I):
                # "Movement of administered funds between years" is a
                # distinct reconciliation memo table, not program expense
                # detail; its rows must not be attributed to a program.
                in_outcome_table = False
                program_number = None
                heading = None
                pending = []
                continue
            program_match = PROGRAM_RE.match(line)
            if in_outcome_table and program_match and entity:
                program_number = program_match.group("number")
                program_names[(entity, program_number)] = _norm(program_match.group("name"))
                scope = None
                heading = None
                pending = []
                continue
            if not in_outcome_table or not entity or not outcome or not program_number:
                continue
            if re.match(r"^Administered expenses$", line, re.I):
                scope = "Administered"
                heading = None
                pending = []
                continue
            if re.match(r"^Departmental expenses$", line, re.I):
                scope = "Departmental"
                heading = None
                pending = []
                continue
            if OUTCOME_TOTALS_RE.match(line):
                # Cross-program outcome reconciliation table, not a program
                # component; stop attributing lines to the previous program.
                program_number = None
                scope = None
                heading = None
                pending = []
                continue
            parsed = _amount_line(line)
            if parsed is None:
                if re.match(r"^(?:Actual|Estimated|Budget|Forward|\$'?000|Table\s+2)", line, re.I):
                    continue
                if len(pending) < 3:
                    pending.append(line)
                continue
            label_part, amounts = parsed
            label = _norm(" ".join([*pending, label_part])) if pending else label_part
            pending = []
            if not label:
                continue
            is_total_line = (
                TOTAL_RE.match(label) is not None
                or label.lower().endswith(" total")
                or re.match(r"^Total expenses for Outcome", label, re.I) is not None
            )
            if is_total_line:
                # Program/scope/outcome summary rows always stand alone and
                # end the current appropriation-type grouping.
                heading = None
            else:
                heading_here = _heading_prefix(label)
                if heading_here:
                    heading = heading_here
                elif label.lower().startswith(STANDALONE_LABEL_PREFIXES):
                    heading = None
                elif heading and not label.lower().startswith(heading.lower()):
                    label = _norm(f"{heading} {label}")
            total_match = TOTAL_RE.match(label)
            if total_match:
                number = total_match.group("number")
                name = program_names.get((entity, number))
                if not name:
                    raise ValueError(f"{edition.source_id} page {page_no}: missing name for {entity} program {number}")
                rows.extend(
                    _rows(
                        edition,
                        pdf=source_pdf,
                        page_no=page_no,
                        entity=entity,
                        outcome=outcome,
                        program_number=number,
                        program_name=name,
                        scope=None,
                        component=None,
                        amounts=amounts,
                    )
                )
                continue
            if label.lower().endswith(" total") or re.match(r"^Total expenses for Outcome", label, re.I):
                continue
            if re.match(r"^(?:Average staffing level|Program\s+\d|Outcome\s+\d)", label, re.I):
                continue
            name = program_names[(entity, program_number)]
            rows.extend(
                _rows(
                    edition,
                    pdf=source_pdf,
                    page_no=page_no,
                    entity=entity,
                    outcome=outcome,
                    program_number=program_number,
                    program_name=name,
                    scope=scope,
                    component=label,
                    amounts=amounts,
                )
            )

    keys = [(row["fy"], row["category"], row["estimate_status"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{edition.source_id}: duplicate year/category/status rows")
    return rows


def write_csv(rows: list[dict], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return output


def main() -> int:
    for edition in EDITIONS:
        rows = extract_edition(edition)
        print(
            {
                "source_id": edition.source_id,
                "rows": len(rows),
                "programs": len({row["category"] for row in rows if row["row_kind"] == "program"}),
                "path": str(write_csv(rows, edition.output_path)),
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

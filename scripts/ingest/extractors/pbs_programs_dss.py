#!/usr/bin/env python3
"""Extract SSW program rows from Statement 6 Table 6.1.3 as PBS-bridge programs."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors import SKIP_LINE, YEARS, iter_pdf_pages, parse_amount_token  # noqa: E402

BRIDGE_PDF = (
    REPO_ROOT
    / "data/raw/federal/federal_budget_statement_6_2026_27/snapshots/20260720T215815Z/files/bp1_bs-6.pdf"
)
OUT = REPO_ROOT / "data/staging/breakdowns/pbs_programs_dss.csv"
LANDING = "https://www.dss.gov.au/budget-and-additional-estimates-statements/budget-2026-27"
RESOURCE = (
    "https://www.dss.gov.au/system/files/documents/2026-05/"
    "portfolio-budget-statements-2026-27-social-services.pdf"
)

STATUS_BY_FY = {
    "2025-26": "estimated_actual",
    "2026-27": "budget",
    "2027-28": "forward_estimate",
    "2028-29": "forward_estimate",
    "2029-30": "forward_estimate",
}

# Programs marked SSW in Table 6.1.3 Top 20
SSW_PROGRAMS = {
    "Support for Seniors": "Social security and welfare / Assistance to the aged",
    "National Disability Insurance Scheme": "Social security and welfare / Assistance to people with disabilities",
    "Aged Care Services": "Social security and welfare / Assistance to the aged",
    "Financial Support for People with Disability": "Social security and welfare / Assistance to people with disabilities",
    "Job Seeker Income Support": "Social security and welfare / Assistance to the unemployed and the sick",
    "Support for Families": "Social security and welfare / Assistance to families with children",
    "Child Care Subsidy": "Social security and welfare / Assistance to families with children",
    "Financial Support for Carers": "Social security and welfare / Assistance to people with disabilities",
}

FIVE_TAIL = re.compile(
    r"^(?P<label>.*?)(?P<nums>(?:\s+-?\d{1,3}(?:,\d{3})+|\s+-?\d+){5})\s*$"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract(pdf: Path = BRIDGE_PDF) -> list[dict]:
    rows: list[dict] = []
    capturing = False
    pending: list[str] = []
    estimate_years = YEARS[1:]

    for page_no, text in iter_pdf_pages(pdf):
        if "Table 6.1.3" in text and "Top 20 programs" in text:
            capturing = True
        if not capturing:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if capturing and line.startswith("Table 6.") and "6.1.3" not in line:
                capturing = False
                break
            if SKIP_LINE.match(line) or line.startswith("Program"):
                continue
            m = FIVE_TAIL.match(line)
            if not m:
                pending.append(_norm(line))
                continue
            label_part = _norm(m.group("label"))
            # Strip trailing function codes like SSW / Health
            label_part = re.sub(r"\s+SSW\s*$", "", label_part)
            label_part = re.sub(r"\s+Health\s*$", "", label_part)
            label_part = re.sub(r"\s+Education\s*$", "", label_part)
            label_part = re.sub(r"\s+Defence\s*$", "", label_part)
            label_part = re.sub(r"\s+Other purposes.*$", "", label_part)
            label = _norm(" ".join(pending + [label_part])) if pending else label_part
            pending = []
            label = re.sub(r"\s*\(b\)\s*$", "", label)
            label = re.sub(r"\s*\(c\)\s*$", "", label)
            parent = None
            for prog, path in SSW_PROGRAMS.items():
                if label.lower().startswith(prog.lower()) or prog.lower() in label.lower():
                    parent = path
                    label = prog
                    break
            if not parent:
                continue
            nums = [parse_amount_token(t) for t in m.group("nums").split()]
            category = f"{parent} / {label}"
            for fy, amount in zip(estimate_years, nums):
                rows.append(
                    {
                        "fy": fy,
                        "amount": amount,
                        "category": category,
                        "estimate_status": STATUS_BY_FY[fy],
                        "row_kind": "program",
                        "locator": (
                            f"pdf:bp1_bs-6.pdf | page:{page_no} | Table 6.1.3 | "
                            f"program:{label} | col:{fy} | unit:$m | "
                            f"bridge:dss_pbs"
                        ),
                        "landing_url": LANDING,
                        "resource_url": RESOURCE,
                    }
                )
    return rows


def write_csv(rows: list[dict], path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "fy",
        "amount",
        "category",
        "estimate_status",
        "row_kind",
        "locator",
        "landing_url",
        "resource_url",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def extract_dss_outcome_programs(
    pdf: Path | None = None,
) -> list[dict]:
    """Total expenses for Program X.Y rows from DSS PBS Outcome 1 tables."""
    pdf = pdf or (
        REPO_ROOT
        / "data/raw/federal/federal_dss_pbs_2026_27/snapshots/manual-20260722T043829Z/files/"
        "portfolio-budget-statements-2026-27-social-services.pdf"
    )
    if not pdf.is_file():
        return []

    program_paths = {
        "Support for Families": "Social security and welfare / Assistance to families with children",
        "Paid Parental Leave": "Social security and welfare / Assistance to families with children",
        "Support for Seniors": "Social security and welfare / Assistance to the aged",
        "Income Support for People with Disability": (
            "Social security and welfare / Assistance to people with disabilities"
        ),
        "Income Support for Carers": (
            "Social security and welfare / Assistance to people with disabilities"
        ),
        "Working Age Payments": (
            "Social security and welfare / Assistance to the unemployed and the sick"
        ),
        "Student Payments": "Social security and welfare / Other welfare programs",
        "Disability Employment Services": (
            "Social security and welfare / Assistance to people with disabilities"
        ),
    }
    prog_header = re.compile(
        r"^Program\s+(?P<code>\d+\.\d+)\s+[–\-]\s+(?P<title>.+)$", re.I
    )
    total_line = re.compile(
        r"^Total expenses for Program\s+(?P<code>\d+\.\d+)\s+"
        r"(?P<nums>(?:\s*-?\d{1,3}(?:,\d{3})+|\s*-?\d+){5})\s*$",
        re.I,
    )
    rows: list[dict] = []
    current_title: str | None = None
    current_code: str | None = None
    capturing = False
    estimate_years = YEARS[1:]

    for page_no, text in iter_pdf_pages(pdf):
        if "Budgeted expenses for Outcome 1" in text or "Table 2.1.1" in text:
            capturing = True
        if not capturing:
            continue
        if "Outcome 2:" in text and "Outcome 1:" not in text and "Table 2.1.1" not in text:
            capturing = False
            break
        for raw in text.splitlines():
            line = _norm(raw)
            if not line:
                continue
            hm = prog_header.match(line)
            if hm:
                current_code = hm.group("code")
                current_title = _norm(hm.group("title"))
                continue
            tm = total_line.match(line)
            if not tm:
                continue
            code = tm.group("code")
            title = current_title if current_code == code else None
            if not title:
                continue
            parent = None
            for key, path in program_paths.items():
                if key.lower() == title.lower() or key.lower() in title.lower():
                    parent = path
                    title = key
                    break
            if not parent:
                continue
            # PBS Outcome tables are in $'000 — do NOT use parse_amount_token
            # (that helper assumes Statement 6 $m and multiplies by 1e6).
            nums_k = [int(t.replace(",", "")) for t in tm.group("nums").split()]
            category = f"{parent} / {title}"
            for fy, amount_k in zip(estimate_years, nums_k):
                rows.append(
                    {
                        "fy": fy,
                        "amount": amount_k * 1000,  # $'000 → AUD
                        "category": category,
                        "estimate_status": STATUS_BY_FY[fy],
                        "row_kind": "pbs_program",
                        "locator": (
                            f"pdf:portfolio-budget-statements-2026-27-social-services.pdf | "
                            f"page:{page_no} | Table 2.1.1 | program:{code} {title} | "
                            f"col:{fy} | unit:$'000"
                        ),
                        "landing_url": LANDING,
                        "resource_url": RESOURCE,
                    }
                )
    return rows


def main() -> int:
    bridge = extract()
    outcome = extract_dss_outcome_programs()
    by_key: dict[tuple[str, str], dict] = {}
    for r in bridge:
        by_key[(r["category"].lower(), r["fy"])] = r
    for r in outcome:
        by_key[(r["category"].lower(), r["fy"])] = r
    rows = list(by_key.values())
    path = write_csv(rows)
    print(
        {
            "rows": len(rows),
            "bridge": len(bridge),
            "outcome": len(outcome),
            "path": str(path),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

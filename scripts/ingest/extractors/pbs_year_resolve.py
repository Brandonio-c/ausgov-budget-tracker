"""Header-aware PBS financial-year resolution (no fixed-year column guessing)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

FY_TOKEN = re.compile(
    # \xad (soft hyphen) is the character pypdf actually extracts for the
    # hyphen in "20XX-XX" year ranges in several PBS documents (same
    # character used elsewhere in these PDFs for wrapped words like
    # "non\xadfinancial") - without it here, every such header line fails to
    # match at all, silently forcing every row in the table onto the coarser
    # source_layout_template fallback (or quarantine) instead of the
    # accurate table_header_exact resolution. Confirmed on
    # federal_pbs_2024_25_climate_change_energy_the_environment_and_water.
    r"(?P<fy>(?:20\d{2})\s*[–\-\xad/]\s*(?:\d{2}|20\d{2}))",
    re.I,
)
STATUS_HINTS = [
    (re.compile(r"estimated\s+actual|est\.?\s*actual", re.I), "estimated_actual"),
    (re.compile(r"forward\s+estimate", re.I), "forward_estimate"),
    (re.compile(r"revised", re.I), "revised_estimate"),
    (re.compile(r"\bbudget\b", re.I), "budget"),
    (re.compile(r"\bactual\b|outcome", re.I), "actual"),
]


@dataclass(frozen=True)
class YearColumn:
    financial_year: str
    estimate_status: str
    column_header_original: str
    inference_method: str
    confidence: str  # high | medium | low | quarantine


def normalize_fy(raw: str) -> str:
    raw = raw.replace("–", "-").replace("\xad", "-")
    digits = re.findall(r"\d+", raw)
    if len(digits) >= 2:
        y1 = digits[0]
        y2 = digits[1]
        if len(y1) == 4 and len(y2) == 2:
            return f"{y1}-{y2}"
        if len(y1) == 4 and len(y2) == 4:
            return f"{y1}-{y2[-2:]}"
    return re.sub(r"\s+", "", raw)


def parse_year_header_line(line: str) -> list[YearColumn] | None:
    """Extract ordered FY columns from a table header row."""
    matches = list(FY_TOKEN.finditer(line))
    if len(matches) < 2:
        return None
    cols: list[YearColumn] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        span = line[max(0, start - 24) : end]
        fy = normalize_fy(m.group("fy"))
        status = "budget"
        for rx, st in STATUS_HINTS:
            if rx.search(span):
                status = st
                break
        # Heuristic fallback by position when labels sparse
        if status == "budget" and i == 0 and "actual" in line.lower():
            status = "actual"
        cols.append(
            YearColumn(
                financial_year=fy,
                estimate_status=status,
                column_header_original=span.strip()[:120],
                inference_method="table_header",
                confidence="high" if STATUS_HINTS[0][0].search(span) or "20" in span else "medium",
            )
        )
    return cols


def resolve_years_for_nums(
    nums: Sequence[str],
    *,
    header_cols: list[YearColumn] | None,
    source_budget_year: str | None,
    layout_template: list[YearColumn] | None = None,
) -> tuple[list[YearColumn] | None, str]:
    """
    Map numeric columns to year metadata.

    Returns (columns, reason). columns is None → quarantine.
    Priority: header → template → quarantine (never fixed global slice).
    """
    n = len(nums)
    if n < 2:
        return None, "too_few_numeric_columns"

    if header_cols and len(header_cols) == n:
        return header_cols, "table_header_exact"
    if header_cols and len(header_cols) > n:
        # Align to rightmost years (common when label column eats space)
        return header_cols[-n:], "table_header_right_align"
    if header_cols and len(header_cols) < n:
        return None, "header_column_count_mismatch"

    if layout_template and len(layout_template) == n:
        return layout_template, "source_layout_template"
    if layout_template and len(layout_template) > n:
        return layout_template[-n:], "source_layout_template_right_align"

    if source_budget_year:
        # Document metadata alone is insufficient to assign N unlabeled columns.
        return None, "missing_year_header_quarantine"

    return None, "no_year_evidence_quarantine"


def template_for_budget_year(source_budget_year: str) -> list[YearColumn]:
    """Declared layout for a PBS budget year when headers are absent but known."""
    # Explicit templates only — callers must opt in per source_id.
    y = normalize_fy(source_budget_year)
    m = re.match(r"(20\d{2})-(\d{2})", y)
    if not m:
        return []
    start = int(m.group(1))
    # Classic 6-col PBS: prior actual, est actual, budget, FE1, FE2, FE3
    years = [
        f"{start - 1}-{str(start)[2:]}",
        f"{start}-{m.group(2)}",
        f"{start}-{m.group(2)}",
        f"{start + 1}-{str(start + 2)[2:]}",
        f"{start + 2}-{str(start + 3)[2:]}",
        f"{start + 3}-{str(start + 4)[2:]}",
    ]
    statuses = [
        "actual",
        "estimated_actual",
        "budget",
        "forward_estimate",
        "forward_estimate",
        "forward_estimate",
    ]
    return [
        YearColumn(
            financial_year=fy,
            estimate_status=st,
            column_header_original=f"template:{source_budget_year}:{fy}:{st}",
            inference_method="source_layout_template",
            confidence="medium",
        )
        for fy, st in zip(years, statuses)
    ]

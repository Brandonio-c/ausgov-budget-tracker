"""Shared helpers for Statement 6 PDF text extraction."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

# Optional leading minus for contingency reserve
NUM = r"-?\d{1,3}(?:,\d{3})+|-?\d+"
LINE_AMOUNT_TAIL = re.compile(
    rf"^(?P<label>.*?)(?P<nums>(?:\s+(?:{NUM})){{6}})\s*$"
)

YEARS = ["2024-25", "2025-26", "2026-27", "2027-28", "2028-29", "2029-30"]

SKIP_LINE = re.compile(
    r"^(?:\|?\s*Budget Paper|Page \d+|Statement 6|Appendix|Table A\.6\.1|"
    r"Actual|Estimates|\$m|\d{4}-\d{2}|a\)\s|This page)",
    re.I,
)


def parse_amount_token(tok: str) -> int:
    return int(tok.replace(",", "")) * 1_000_000


def iter_pdf_pages(path: Path):
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages):
        yield i + 1, page.extract_text() or ""


def parse_amount_line(line: str) -> tuple[str, list[int]] | None:
    m = LINE_AMOUNT_TAIL.match(line.strip())
    if not m:
        return None
    label = re.sub(r"\s+", " ", m.group("label")).strip()
    nums = [parse_amount_token(t) for t in m.group("nums").split()]
    if len(nums) != 6 or not label:
        return None
    return label, nums

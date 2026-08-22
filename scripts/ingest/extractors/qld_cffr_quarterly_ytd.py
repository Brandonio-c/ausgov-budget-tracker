#!/usr/bin/env python3
"""Extractor for Queensland Treasury's quarterly Consolidated Fund
Financial Report (CFFR) "Quarterly Statement" editions - item 7.4's
quarterly slice, the cumulative "Statement of Receipts and Payments for
the <N> Months Ended <date>" (Year-to-Date) table only.

Scope of this pass: the 26 confirmed-tractable, confirmed-clean editions
FY2016-17 Q3 through FY2025-26 Q3 (Sep/Dec/Mar quarters, 2017 onward -
see _EDITIONS below and
ops/reports/qld-cffr-quarterly-scoping-20260819T194500Z.md). Every
edition's own reported "At <date>, the Consolidated Fund had a
balance..." sentence was directly checked against its assumed
(financial_year, quarter) before being added here - never inferred from
the filename alone. `cffr-sept-2025.pdf` (FY2025-26 Q1) was found to
have ZERO extractable text on any page via both pypdf and `pdftotext`
(a genuinely unreadable/image-only PDF, not a text-layout problem) and
is deliberately excluded, not force-included. The pre-2017 era
(FY2008-09 Q1 through FY2016-17 Q2) is deferred to its own future pass -
`consolidated-fund-2012-march.pdf` in that era is already known to have
real OCR-quality character corruption (see the scoping report), and the
remaining ~24 pre-2017 files have not yet been individually re-verified
with the same rigor as this slice.

Each quarterly file contains one or two tables depending on the quarter:
  - September editions (Q1): a single table (the quarter's own 3-month
    flow and the fiscal year's Year-to-Date are identical at that
    point, since Q1 starts on 1 July, the financial year start).
  - December editions (Q2) and March editions (Q3): TWO tables - a
    3-month-only "Quarter Ended" flow (opens with "Balance as at 1
    October" or "Balance as at 1 January" respectively) and the
    cumulative "<N> Months Ended" Year-to-Date table (always opens with
    "Balance as at 1 July", the financial year start, regardless of
    quarter). This module deliberately extracts ONLY the Year-to-Date
    table - the quarter-only flow is a genuinely different vintage
    (never summed with, or blended with, cumulative YTD or full-year
    annual figures) and is out of scope this pass.

Because every genuine Year-to-Date block (and every September edition's
single block, since Year-to-Date coincides with the quarter there) opens
with "Balance as at 1 July", the exact same block-location technique
already proven for the annual editions
(scripts/ingest/extractors/qld_cffr_annual.py's `_extract_year_ended_block`,
`text.rfind("Balance as at 1 July")`) works unchanged here - the
Quarter-Ended-only table (present for Dec/Mar editions) never carries
that label, so `rfind` always lands on the genuine YTD block.

Column layout is identical to the annual editions: Operating Account |
Investment Account | Total (current period) | Total (same period, prior
year) - only the 3rd column ("Total", current period) is ever extracted,
the same "Total only, never the Operating/Investment split" convention
already established for the annual editions. Values are in $'000
(confirmed directly against every edition's own column header) and
scaled to real AUD here, never left as thousands.

This module only extracts and quarantines; loading (measure_type
classification against config/measure-semantics/qld_cffr_quarterly.yaml)
is load_qld_cffr_quarterly_ytd.py's job, not this one's.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "qld_cffr_quarterly_ytd"

_RAW_DIR = (
    REPO_ROOT
    / "data"
    / "raw"
    / "state"
    / "qld_report_on_state_finances_actuals"
    / "snapshots"
    / "20260724T190604Z"
    / "files"
)

# (financial_year, quarter [1=Sep, 2=Dec, 3=Mar], filename) - only the
# confirmed-tractable years, each directly verified against its own
# reported "At <date>..." sentence before being added here (see module
# docstring and the scoping report). The pre-2017 era and the unreadable
# cffr-sept-2025.pdf are deliberately excluded, not guessed at.
_EDITIONS: list[tuple[str, int, str]] = [
    ("2016-17", 3, "Consolidated-Fund-Financial-Report-March-2017.pdf"),
    ("2017-18", 1, "Consolidated-Fund-Financial-Report-September-2017.pdf"),
    ("2017-18", 2, "Consolidated-Fund-Financial-Report-December-2017.pdf"),
    ("2017-18", 3, "CFFR-March-Qtr-2018-attachment.pdf"),
    ("2018-19", 1, "CFFR-Sept-2018.pdf"),
    ("2018-19", 2, "CFFR-Dec-2018.pdf"),
    ("2018-19", 3, "01978-2019-ATTACHMENT-CFFR-March-2019.pdf"),
    ("2019-20", 1, "01978-2019-Attachment-CFFR-Sep-2019.pdf"),
    ("2019-20", 2, "CFFR-December-2019-Quarter.pdf"),
    ("2019-20", 3, "CFFR-March-2020-publish.pdf"),
    ("2020-21", 1, "CFFR-Sept-2020-Tables.pdf"),
    ("2020-21", 2, "CFFR-Dec-2020.pdf"),
    ("2020-21", 3, "CFFR-March-21.pdf"),
    ("2021-22", 1, "CFFR-Sep-2021.pdf"),
    ("2021-22", 2, "CFFR-Dec-2021.pdf"),
    ("2021-22", 3, "CFFR_March_22.pdf"),
    ("2022-23", 1, "CFFR-Sept-2022.pdf"),
    ("2022-23", 2, "CFFR-Dec-22.pdf"),
    ("2022-23", 3, "CFFR-March-2023.pdf"),
    ("2023-24", 1, "CFFR-September-2023.pdf"),
    ("2023-24", 2, "CFFR_Dec_2023.pdf"),
    ("2023-24", 3, "CFFR-Mar-2024.pdf"),
    ("2024-25", 1, "CFFR-Sep-24.pdf"),
    ("2024-25", 2, "CFFR-Dec-24.pdf"),
    ("2024-25", 3, "CFFR-March-2025.pdf"),
    ("2025-26", 3, "quarterly-statement-consolidated-fund-march2026.pdf"),
]
# quarterly-statement-consolidated-fund-dec2025.pdf (FY2025-26 Q2) is
# deliberately excluded, not force-included: its labels and numbers
# render in two entirely separate text blocks rather than interleaved
# per row (confirmed by direct inspection of the raw extraction), a
# fundamentally different layout the simple sequential regex approach
# below cannot safely parse - needs a positional/columnar extraction
# approach in a future pass, see the scoping report.

_QUARTER_END_MONTH_DAY = {1: (9, 30), 2: (12, 31), 3: (3, 31)}

# label -> measure_key. Same 4-numeric-column layout as the annual
# editions (Operating | Investment | Total-current | Total-prior);
# group(3) is the Total (current period) column.
_NUM = r"(\(?-?[\d,]+(?:\.\d+)?\)?|-)"
_LABEL_PATTERNS: list[tuple[str, str]] = [
    (r"Balance as at 1\s*July", "opening_balance"),
    (r"Collections received from [Dd]epartments", "collections_from_departments"),
    (r"Investment [Ii]nterest", "investment_interest"),
    (r"Dividends and [Ii]ncome [Tt]ax [Ee]quivalents", "dividends_income_tax_equivalents"),
    (r"Non-[Aa]ppropriated [Ee]quity [Aa]djustments", "non_appropriated_equity_adjustments"),
    (
        r"Superannuation,\s*[Ll]ong [Ss]ervice [Ll]eave,?\s*(?:and\s*)?Queensland\s*"
        r"(?:-\s*)?Government Insurance Fund and ALCS [Cc]ontributions",
        "superannuation_lsl_qgif_alcs_contributions",
    ),
    (r"Other [Rr]eceipts", "other_receipts"),
    (r"Appropriations provided to [Dd]epartments", "appropriations_provided_to_departments"),
    (r"Consolidated Fund Balance as at \d{1,2} \w+", "closing_balance"),
]


_BALANCE_1_JULY_RE = re.compile(r"Balance as at 1\s*July")


def _extract_ytd_block(text: str) -> str | None:
    """The genuine Year-to-Date block always opens with "Balance as at 1
    July" (the financial year start), regardless of quarter - the
    quarter-only "Quarter Ended" table present for Dec/Mar editions
    opens with a different label ("Balance as at 1 October"/"1
    January") and is never matched here. Mirrors
    qld_cffr_annual.py's `_extract_year_ended_block`, but tolerant of a
    missing space ("1July" - confirmed present in at least 3 real
    files' own text extraction, e.g. CFFR-Sept-2020-Tables.pdf)."""
    matches = list(_BALANCE_1_JULY_RE.finditer(text))
    if not matches:
        return None
    idx = matches[-1].start()
    end = text.find("Notes:", idx)
    return text[idx : end if end != -1 else None]


def extract_edition(path: Path, financial_year: str, quarter: int, original_filename: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        quarantine.append({"reason": "unreadable_pdf", "file": original_filename, "error": str(exc)})
        return rows, quarantine

    block = None
    page_num = None
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        candidate = _extract_ytd_block(text)
        if candidate:
            block = candidate
            page_num = i + 1
            break
    if block is None:
        quarantine.append({"reason": "ytd_table_not_found", "file": original_filename})
        return rows, quarantine

    for label_re, measure_key in _LABEL_PATTERNS:
        m = re.search(
            rf"{label_re}\s*\d?\s*{_NUM}\s*{_NUM}\s*{_NUM}\s*{_NUM}",
            block,
            re.S,
        )
        if not m:
            quarantine.append(
                {
                    "reason": "label_not_found_in_ytd_block",
                    "file": original_filename,
                    "fy": financial_year,
                    "quarter": quarter,
                    "measure_key": measure_key,
                }
            )
            continue
        total_current_raw = m.group(3)
        value = _parse_number(total_current_raw)
        if value is None:
            quarantine.append(
                {
                    "reason": "unparseable_total_value",
                    "file": original_filename,
                    "fy": financial_year,
                    "quarter": quarter,
                    "measure_key": measure_key,
                    "raw": total_current_raw,
                }
            )
            continue
        value *= 1_000  # $'000 -> real AUD, confirmed against every edition's own header
        rows.append(
            {
                "fy": financial_year,
                "quarter": quarter,
                "amount": value,
                "measure_key": measure_key,
                "locator": (
                    f"source_id:{SOURCE_ID} | file:{original_filename} | page:{page_num} | "
                    f"row:{measure_key} | column:Total (Year to Date)"
                ),
                "cached_copy_path": _relative_or_str(path),
            }
        )
    return rows, quarantine


def _parse_number(raw: str) -> float | None:
    raw = raw.strip()
    if raw == "-" or not raw:
        return 0.0
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = raw.strip("()").replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _relative_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def extract_all(raw_dir: Path = _RAW_DIR) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    quarantine: list[dict] = []
    for fy, quarter, filename in _EDITIONS:
        path = raw_dir / filename
        if not path.is_file():
            quarantine.append({"reason": "edition_file_missing_on_disk", "fy": fy, "quarter": quarter, "filename": filename})
            continue
        edition_rows, edition_quarantine = extract_edition(path, fy, quarter, filename)
        rows.extend(edition_rows)
        quarantine.extend(edition_quarantine)
    return rows, quarantine


def main() -> int:
    rows, quarantine = extract_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "qld_cffr_quarterly_ytd.csv"
    if rows:
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    if quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        qpath = QUARANTINE_DIR / f"{SOURCE_ID}_extract_quarantine.jsonl"
        with qpath.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "rows": len(rows),
                "quarantined": len(quarantine),
                "distinct_measure_keys": sorted({r["measure_key"] for r in rows}),
                "editions": len(_EDITIONS),
                "out": str(out),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

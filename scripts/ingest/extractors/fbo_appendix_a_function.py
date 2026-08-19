#!/usr/bin/env python3
"""Extractor for the pre-2019 Final Budget Outcome (FBO) "Appendix A/B:
Expenses by Function and Sub-function" table - item 8.1, every
confirmed-tractable year: FY1999-00 through FY2018-19. FY1998-99
predates accrual/functional expense reporting entirely (confirmed via
its own full table of contents) and is permanently excluded, not a gap
to fill later.

Four distinct, individually-verified column layouts are covered, never
assumed uniform across years - each edition in _EDITIONS carries its own
verified (numeric_column_count, estimate_at_outcome_column_index,
needs_shift_decode) triple, never inferred or guessed:
  - FY1999-00/FY2000-01: 2 numeric columns (next-year Budget | current-
    year Estimate at Outcome) - no prior-year comparative column at
    all. Estimate at Outcome is column 2.
  - FY2001-02/FY2002-03/FY2003-04: 3 numeric columns (prior-year Outcome
    | next-year Budget | current-year Estimate at Outcome) - Estimate
    at Outcome is column 3, not 2. A blind column-2 read here would
    load the *next* year's Budget forecast as an actual - the same
    class of trap independently caught for FY2017-19 below, verified
    separately for this earlier era via direct page inspection.
  - FY2004-05 through FY2011-12: 3 numeric columns (prior-year Outcome |
    current-year Estimate at Outcome | next-year Budget) - Estimate at
    Outcome moves back to column 2.
  - FY2012-13 through FY2016-17: 4 numeric columns (prior-year Outcome |
    current-year Estimate at Outcome | next-year Budget | "Change on
    Budget") - Estimate at Outcome is still column 2. FY2014-15..
    FY2016-17 were originally flagged by the scoping pass as having
    "different header wording" and excluded; a direct re-check with
    this module's own (already case-insensitive) anchor regex found
    they use the identical layout and anchor as FY2012-13/FY2013-14 -
    the original finding predated the case-insensitivity fix, not a
    real layout difference.
  - FY2017-18/FY2018-19: 5 numeric columns (prior-year Outcome |
    current-year Budget | next-year Budget | current-year Estimate at
    Outcome | "Change on Budget") - a genuinely different column ORDER,
    not just an added trailing column: Estimate at Outcome moves to
    column 4. Blindly reusing column 2 here would silently load a
    Budget forecast as if it were an actual - caught by directly
    inspecting both editions' real page text and cross-validating
    against the published Total other purposes/Total expenses rows
    (both matched exactly once column 4 was used) before writing any
    loader-facing code.
Only the "Estimate at Outcome" column is ever extracted, at whatever
position that edition's own header genuinely places it - never assumed
to be a fixed position across sub-generations.

FY1999-00/FY2001-02/FY2002-03 additionally require needs_shift_decode
(see _decode_shift29): pypdf cannot read these 3 files' embedded font
at all (raw glyph IDs, e.g. "/G1A/G18"); `pdftotext` extracts a
substitute character per glyph that recovers correctly with a fixed
+29 ASCII-code shift, verified against multiple independently-decoded
words. FY2004-05/FY2005-06/FY2006-07/FY2000-01/FY2001-02/FY2002-03/
FY2003-04/FY1999-00 title the table "Appendix B"/"Table B1" (the
anchor regex accepts either letter, plus a 2nd alternative that catches
FY2000-01's continuation pages, which omit the "Appendix B:" line
entirely and repeat only "Table B1: ..."). FY2007-08 onward use
"Appendix A"/"Table A1".

Two genuine, confirmed-real data absences are deliberately left
unmatched rather than force-fit, documented in
config/measure-semantics/fbo_appendix_a_function.yaml's global_rules:
`mining_manufacturing_construction` is out of scope for FY1999-00
through FY2002-03 (those editions scope the function narrower,
excluding fuels - a real scope difference, not a label variant), and
`nominal_superannuation_interest` has no line item at all in FY1999-00.
FY2000-01/FY2001-02 also have a genuine, real 6th "Other purposes" line
item ("Asset sales") this workbook does not model as its own measure -
phased out by FY2002-03, confirmed absent there.

The existing broad `fbo_appendix_a.extract()` is confirmed unsafe to
reuse (it latches onto unrelated tables earlier in each consolidated FBO,
e.g. "Table 5: ... expenses by function", a function-level-ONLY summary
table with no sub-function detail and a different page/column shape -
see ops/reports/fbo-historical-archive-triage-20260807T175900Z.md). This
module locates the genuine Appendix A ("Table A1") page range directly,
using a title anchor confirmed present in two different physical forms
across these editions (a chapter-heading form on the section's very
first page, and a running-header form on every continuation page - see
ops/reports/fbo-appendix-a-page-anchor-scoping-20260818T160000Z.md).

Scope: function-level totals only (13 COFOG-style functions + 5 "Other
purposes" line items + "Total other purposes" + "Total expenses" = 20
measures), deliberately NOT the individual sub-function line items
beneath each function - the same granularity choice already made for
the MFS Note 3 workbook (item 7.1), and for the same reason: the ~60+
sub-function labels are a much larger surface with more real drift risk
across editions, not attempted this pass.

Each function is either:
  - "total-terminated": several sub-function rows followed by a
    "Total <function>" row (e.g. "Total general public services") - the
    total row's own middle numeric column is extracted, never
    recomputed by summing the sub-function rows; or
  - "single-line": the bare function-name row itself already carries
    the 3 numeric columns directly (no separate Total row exists,
    verified directly - e.g. "Defence", "Fuel and energy", "Public debt
    interest") - some of these also have informational sub-items listed
    below them (e.g. "Public debt interest" is followed by "Interest on
    Australian Government's behalf", a near-identical restatement), but
    those sub-items are never separately extracted or summed here.

Only the middle numeric column ("<FY> Estimate at Outcome" - FBO's own
term for its best current estimate of the actual final outcome, the
figure this whole database treats as the "actual" for consistency with
every other measure family) is extracted - never the leading prior-year-
outcome comparative column (independently extracted from that prior
year's own edition) or the trailing next-year Budget forecast column (a
forecast, never an actual, per this program's standing rule).

This module only extracts and quarantines; loading is
load_fbo_appendix_a_function.py's job, not this one's.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "fbo_appendix_a_function"

_RAW_BASE = (
    REPO_ROOT / "data" / "raw" / "federal" / "federal_budget_archive_function_series" / "snapshots"
)
# Default snapshot for the FY2010-11..FY2018-19 editions; the pre-2010-11
# editions were acquired into different snapshot folders (see _EDITIONS'
# own per-edition snapshot field) and are resolved relative to _RAW_BASE.
_RAW_DIR = _RAW_BASE / "20260723T033445Z" / "files"

# (financial_year, snapshot_dir_or_None, filename, numeric_column_count,
# estimate_at_outcome_column_index) - only the confirmed-tractable
# years/layouts (see the page-anchor scoping report and the
# data-remediation-progress.md item 8.1 milestone entries).
# snapshot_dir_or_None resolves relative to _RAW_BASE; None means the
# default _RAW_DIR (20260723T033445Z). FY2014-15 through FY2016-17 were
# re-checked directly against the anchor logic below (not re-derived
# from the original scoping pass's narrower, exact-case check) and
# found to use the SAME 4-column layout and the same case-insensitive-
# matchable anchor as FY2012-13/FY2013-14 - the original "different
# header wording" finding predates this module's case-insensitive
# anchor fix. FY2017-18/FY2018-19 use a genuinely different 5-column
# layout where Estimate at Outcome is column 4, not column 2 -
# confirmed by direct page inspection and an exact match on both the
# Total other purposes and Total expenses cross-checks for both years
# (see the item 8.1 milestone entry). FY2007-08/FY2008-09/FY2009-10 use
# the identical 3-column/column-2 layout as FY2010-11..FY2016-17 (still
# titled "Appendix A"/"Table A1", unlike FY2000-01..FY2006-07's
# "Appendix B"), confirmed by direct page inspection and an exact/near-
# exact match on both cross-checks once a real PDF-text-extraction
# defect (a stray space inserted inside a large number, e.g. "5, 926"
# for "5,926" in the 2008-09 file) was found and fixed in the shared
# _NUM pattern - re-verified this fix changes 0 values across every
# already-loaded year before being applied. FY2004-05/FY2005-06/
# FY2006-07 also use the identical 3-column/column-2 layout, but titled
# "Appendix B"/"Table B1" (the anchor regex accepts either letter) -
# confirmed by direct page inspection; extraction unchanged for every
# other already-loaded year after widening the anchor (re-verified: 0
# value changes). FY2000-01/FY2003-04 use a 2-column and a 3-column-
# with-Estimate-at-Outcome-in-column-3 layout respectively (see
# outcome_column_index below); FY1999-00/FY2001-02/FY2002-03 use the
# same layouts but require the needs_shift_decode flag (see
# _decode_shift29 below - a real, consistent +29 ASCII-code font
# substitution found in these 3 files' embedded fonts, confirmed by
# decoding multiple independent words correctly). FY1998-99 has no such
# table at all (predates accrual/functional reporting) and is
# permanently excluded, not a gap to fill later. See
# ops/reports/fbo-pre-2010-scoping-20260819T182500Z.md.
# Tuple: (financial_year, snapshot_dir_or_None, filename,
#         numeric_column_count, estimate_at_outcome_column_index,
#         needs_shift_decode)
_EDITIONS: list[tuple[str, str | None, str, int, int, bool]] = [
    ("1999-00", "20260723T031046Z", "FBO_1999-00.pdf", 2, 2, True),
    ("2000-01", "20260723T033738Z", "2000-01_fbo.pdf", 2, 2, False),
    ("2001-02", "20260723T033738Z", "2001-02_fbo.pdf", 3, 3, True),
    ("2002-03", "20260723T033738Z", "2002-03_fbo.pdf", 3, 3, True),
    ("2003-04", "20260723T033738Z", "2003-04_FBO_2003_04.pdf", 3, 3, False),
    ("2004-05", "20260723T031046Z", "FBO_2004-05.pdf", 3, 2, False),
    ("2005-06", "20260723T033738Z", "2005-06_fbo.pdf", 3, 2, False),
    ("2006-07", "20260723T031046Z", "FBO_2006-07.pdf", 3, 2, False),
    ("2007-08", "20260723T033738Z", "2007-08_FBO_2007_08.pdf", 3, 2, False),
    ("2008-09", "20260723T031046Z", "2008-09_2008_09_FBO.pdf", 3, 2, False),
    ("2009-10", "20260723T031046Z", "2009-10_2009_10_FBO.pdf", 3, 2, False),
    ("2010-11", None, "FBO_2010-11_Consolidated.pdf", 3, 2, False),
    ("2011-12", None, "FBO_2011-12_Consolidated.pdf", 3, 2, False),
    ("2012-13", None, "2012-13_FBO_Consolidated.pdf", 4, 2, False),
    ("2013-14", None, "2013-14_FBO_Consolidated.pdf", 4, 2, False),
    ("2014-15", None, "FBO-2014-15-Consolidated.pdf", 4, 2, False),
    ("2015-16", None, "FBO-2015-16-Consolidated.pdf.pdf", 4, 2, False),
    ("2016-17", None, "FBO-2016-17.pdf", 4, 2, False),
    ("2017-18", None, "FBO_2017-18_Combined.pdf", 5, 4, False),
    ("2018-19", None, "FBO_2018-19_web.pdf", 5, 4, False),
]

# FY2000-01..FY2006-07 title this table "Appendix B" (not "A") - see
# ops/reports/fbo-pre-2010-scoping-20260819T182500Z.md. Confirmed no
# already-loaded year has an unrelated "Appendix B: Expenses by
# Function..." string that this widening could false-positive on.
#
# The 2nd alternative catches FY2000-01's continuation pages, which omit
# the "Appendix B:" line entirely and repeat only "Table B1: ... expenses
# by function and sub-function" - verified this does NOT match FY1999-00's
# unrelated "Table A1: ... cash revenue, outlays and surplus" (a different
# appendix's historical-fiscal-data table, checked directly).
_ANCHOR_RE = re.compile(
    r"appendix [ab]:\s*expenses by function and\s*sub-function"
    r"|table [ab]1:?.{0,100}?function and\s*sub-function",
    re.I | re.S,
)
# Digit-group-aware, not a bare [\d,]+ run: some editions' PDF text
# extraction inserts a stray space right after a thousands comma (e.g.
# "5, 926" for "5,926" - confirmed in the 2008-09 file's "Total other
# economic affairs" row), which a bare [\d,]+ run would silently split
# into two separate tokens and shift every subsequent column by one.
# Requiring each comma-separated group to be exactly 3 digits (with an
# optional stray space tolerated after the comma) rejects that split.
_NUM = r"(\(?-?\d{1,3}(?:,\s?\d{3})*(?:\.\d+)?\)?|-)"

# measure_key -> (search_label_regex_fragment, is_total_terminated)
# is_total_terminated=True means the search text is a "Total <label>" row;
# False means the bare function-name row itself carries the numbers.
_LABEL_PATTERNS: list[tuple[str, str, bool]] = [
    ("general_public_services", r"Total general public services", True),
    ("defence", r"Defence", False),
    ("public_order_safety", r"Total public order and safety", True),
    ("education", r"Total education", True),
    ("health", r"Total health", True),
    ("social_security_welfare", r"Total social security and welfare", True),
    ("housing_community_amenities", r"Total housing and community\s+amenities", True),
    ("recreation_culture", r"Total recreation and culture", True),
    ("fuel_energy", r"Fuel and energy", False),
    (
        "agriculture_forestry_fishing",
        r"Total agriculture,\s*(?:forestry and\s+fishing|fisheries and\s+forestry)",
        True,
    ),
    ("mining_manufacturing_construction", r"Mining, manufacturing (?:and|&)\s+construction", False),
    ("transport_communication", r"Total transport and communication", True),
    ("other_economic_affairs", r"Total other economic affairs", True),
    ("public_debt_interest", r"Public debt interest", False),
    ("nominal_superannuation_interest", r"Nominal superannuation interest", False),
    ("general_purpose_intergovt_transactions", r"General purpose inter-government\s+transactions", False),
    ("natural_disaster_relief", r"Natural disaster relief", False),
    ("contingency_reserve", r"Contingency reserve", False),
    ("total_other_purposes", r"Total other purposes", True),
    ("total_expenses", r"Total expenses", True),
]


def _decode_shift29(text: str) -> str:
    """Undoes a consistent +29 ASCII-code font substitution found in 3
    pre-2004 FBO files (1999-00, 2001-02, 2002-03) - their embedded font
    has no usable ToUnicode map for pypdf, but `pdftotext` extracts a
    substitute character per glyph that decodes correctly with this
    fixed shift. Verified against multiple independent words decoding
    to real English (e.g. "7DEOH" -> "Table", "&RPPRQZHDOWK" ->
    "Commonwealth") - see ops/reports/fbo-pre-2010-scoping-20260819T182500Z.md.
    Spaces and newlines pass through unchanged; the shift is only valid
    for these 3 specific files, never assumed for any other broken-font
    PDF found elsewhere in this project."""
    out = []
    for c in text:
        if c in (" ", "\n"):
            out.append(c)
        else:
            out.append(chr((ord(c) - 32 + 29) % 95 + 32))
    return "".join(out)


def _pdftotext_page(path: Path, page_num: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-f", str(page_num), "-l", str(page_num), "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def _page_text(reader: PdfReader, path: Path, page_num: int, needs_shift_decode: bool) -> str:
    if needs_shift_decode:
        return _decode_shift29(_pdftotext_page(path, page_num))
    return reader.pages[page_num - 1].extract_text() or ""


def _find_appendix_a_pages(reader: PdfReader, path: Path | None = None, needs_shift_decode: bool = False) -> list[int]:
    """The genuine Appendix A/B page range, never a Table-of-Contents
    mention (which always appears well before page 50 in every edition
    checked - see the scoping report). needs_shift_decode routes text
    extraction through pdftotext + _decode_shift29 instead of pypdf's
    own (unusable, for these 3 files) extract_text()."""
    pages = []
    npages = len(reader.pages)
    for i in range(npages):
        page_num = i + 1
        if page_num <= 50:
            continue
        text = _page_text(reader, path, page_num, needs_shift_decode).replace("\n", " ")
        if _ANCHOR_RE.search(text):
            pages.append(page_num)
    return pages


def extract_edition(
    path: Path,
    financial_year: str,
    original_filename: str,
    num_columns: int = 3,
    outcome_column_index: int = 2,
    needs_shift_decode: bool = False,
) -> tuple[list[dict], list[dict]]:
    """num_columns is the edition's own verified numeric-column count;
    outcome_column_index (1-indexed) is the position of "Estimate at
    Outcome" within those columns - column 2 for most layouts, column 3
    for FY2001-02/FY2002-03/FY2003-04, column 4 for FY2017-18/FY2018-19
    (see _EDITIONS - never assume a fixed position across
    sub-generations). needs_shift_decode is True only for the 3 files
    whose embedded font pypdf cannot decode (see _decode_shift29)."""
    rows: list[dict] = []
    quarantine: list[dict] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        quarantine.append({"reason": "unreadable_pdf", "file": original_filename, "error": str(exc)})
        return rows, quarantine

    pages = _find_appendix_a_pages(reader, path, needs_shift_decode)
    if not pages:
        quarantine.append({"reason": "appendix_a_pages_not_found", "file": original_filename})
        return rows, quarantine

    block = "\n".join(_page_text(reader, path, p, needs_shift_decode) for p in pages)
    num_pattern = r"\s+".join([_NUM] * num_columns)

    for measure_key, label_re, _is_total in _LABEL_PATTERNS:
        # Case-insensitive (some editions title-case a label, e.g. "Total
        # Transport and Communication") and tolerant of an optional
        # footnote-letter marker in either of 2 real forms found across
        # different editions: directly attached with no space (e.g.
        # "Defence(a)", "Contingency reserve(c)") or a bare letter with a
        # space and no parentheses (e.g. "Total health a", "Fuel and
        # energy a", found in the 2002-03 file's decoded text) - both
        # confirmed by direct inspection, not guessed at.
        m = re.search(rf"{label_re}(?:\([a-z]\)|\s[a-z](?=\s))?\s+{num_pattern}", block, re.I | re.S)
        if not m:
            quarantine.append({"reason": "label_not_found", "file": original_filename, "measure_key": measure_key})
            continue
        raw_value = m.group(outcome_column_index)
        value = _parse_number(raw_value)
        if value is None:
            quarantine.append(
                {"reason": "unparseable_value", "file": original_filename, "measure_key": measure_key, "raw": raw_value}
            )
            continue
        rows.append(
            {
                "fy": financial_year,
                "amount": value,
                "measure_key": measure_key,
                "locator": (
                    f"source_id:{SOURCE_ID} | file:{original_filename} | pages:{pages[0]}-{pages[-1]} | "
                    f"row:{measure_key} | column:Estimate at Outcome"
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
    # A captured token may include a stray space the _NUM pattern
    # deliberately tolerates after a thousands comma (e.g. "5, 926") -
    # strip all internal whitespace too, not just leading/trailing.
    cleaned = re.sub(r"\s+", "", raw.strip("()").replace(",", ""))
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
    for fy, snapshot_dir, filename, num_columns, outcome_column_index, needs_shift_decode in _EDITIONS:
        edition_dir = raw_dir if snapshot_dir is None else (_RAW_BASE / snapshot_dir / "files")
        path = edition_dir / filename
        if not path.is_file():
            quarantine.append({"reason": "edition_file_missing_on_disk", "fy": fy, "filename": filename})
            continue
        edition_rows, edition_quarantine = extract_edition(
            path, fy, filename, num_columns, outcome_column_index, needs_shift_decode
        )
        rows.extend(edition_rows)
        quarantine.extend(edition_quarantine)
    return rows, quarantine


def main() -> int:
    rows, quarantine = extract_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "fbo_appendix_a_function.csv"
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

#!/usr/bin/env python3
"""Extractor for the Australian Government Monthly Financial Statements'
'Note 1 - Income Tax' and 'Note 2 - Indirect Tax' workbook
(federal_mfs_tax_notes_1_2), item 7.1's fourth MFS sibling workbook.

Unlike every other MFS sibling (one title-header-data block per sheet),
this workbook stacks TWO independently-titled blocks in each of its 21
year-sheets ("... Tax Note 1 - Income Tax" then, further down the same
sheet, "... Tax Note 2 - Indirect Tax") - handled by mfs_common.py's new
extract_multi_block_ytd_workbook(), added here because
extract_ytd_workbook()'s single "stop at the first footnote row" rule
would otherwise truncate a sheet at Note 1's footnotes and never reach
Note 2's data.

Verified directly against all 21 real sheets (FY2005-06..FY2025-26) before
writing any label mapping - two real, genuine multi-generation composition
changes were found and are deliberately NOT loaded as their naive single
label would suggest (loading them would risk exactly the same-label-
different-value collision already documented for the Operating Statement
workbook):

  - Note 1's petroleum/minerals resource rent tax line is reported as a
    single "Petroleum resource rent tax" row in FY2005-06..FY2011-12, then
    as a single COMBINED "Resource rent taxes (a)" row in FY2012-13 (per
    that year's own footnote: combined specifically to avoid breaching tax
    secrecy provisions), then in FY2013-14 the SAME "Resource rent taxes"
    label becomes a subtotal with two child rows ("Minerals resource rent
    tax", "Petroleum resource rent tax"), then FY2014-15..FY2016-17 reverts
    to a single combined "Resource rent taxes" row again (MRRT phasing
    out), then FY2017-18 onward reverts to a standalone
    "Petroleum resource rent tax" row (MRRT repealed). A single measure_type
    spanning all years would silently mix "PRRT alone" and "PRRT+MRRT
    combined" under one label - not loaded here, left for a dedicated
    future pass;
  - Note 1's grand total ("Total Income tax" FY2005-06, renamed
    "Total income taxation revenue" from FY2006-07) has a documented,
    source-footnoted composition change even within a single year: FY2005-06
    excludes Fringe Benefits tax entirely (reported as a separate line
    after the total); FY2006-07's own footnote states FBT was excluded from
    the total for July-October then included from November onward; every
    year from FY2007-08 includes it consistently. Not loaded here;
  - Note 2's "Other indirect tax" line has an analogous mid-year defect:
    FY2008-09's own footnote states GST was bundled into this row for
    July-November, then reported separately (as its own "Goods and
    services tax" row) from December onward - the same row label spans two
    different real compositions within one sheet. Not loaded here.

Every other line item in both notes is stable in identity across all 21
years (verified directly, not assumed) and is loaded: Note 1's
Gross income tax withholding, Gross other individuals, less Refunds,
Total individuals and other withholding taxation (subtotal), Company tax,
Superannuation fund(s) (taxes), Fringe Benefits tax (the raw line-item
figure only, never claiming anything about its inclusion in a total); and
Note 2's Excise duty, Customs duty, Goods and services tax (introduced
partway through FY2008-09, naturally absent before - never backfilled),
Wine equalisation tax and Luxury car tax (introduced FY2009-10, naturally
absent before), Carbon pricing mechanism (present FY2012-13 and FY2013-14
only, naturally absent elsewhere), and Total indirect taxation revenue
(the source's own literal total for each year - not recomputed here, so
its normal, disclosed year-over-year composition change as taxes are
added/repealed is not the same defect class as Note 1's within-generation
FBT ambiguity).

"Petroleum resource rent tax" is also loaded, but NOT for every year the
label appears: verified directly, FY2005-06..FY2011-12 and FY2017-18
onward both report a clean, standalone PRRT figure under this exact
label, but FY2013-14 reports the SAME label as an incomplete child
breakdown of that year's combined "Resource rent taxes" row (missing
July/August entirely, per that year's own footnote: "The breakdown was
not publicly released in July and August") - the load_mfs_tax_notes_1_2.py
loader's only_published_financial_years gate (config/measure-semantics/mfs.yaml)
admits the 16 clean years and quarantines FY2013-14's occurrence, rather
than either losing all 16 good years to a blanket exclusion or silently
mixing the clean and incomplete-child-breakdown figures under one series.

This module only extracts and quarantines; loading (measure_type
classification against config/measure-semantics/mfs.yaml) is
load_mfs_tax_notes_1_2.py's job, not this one's.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mfs_common import extract_multi_block_ytd_workbook, find_latest_asset  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "staging" / "breakdowns"
QUARANTINE_DIR = REPO_ROOT / "data" / "staging" / "quarantine"
SOURCE_ID = "federal_mfs_tax_notes_1_2"

TITLE_RE = re.compile(r"Tax Note \d - ")

# Labels with a genuine multi-generation composition ambiguity, verified
# directly against all 21 real sheets (see module docstring) - deliberately
# excluded from the published output so a downstream loader can never
# accidentally treat them as one continuous, comparable series.
_AMBIGUOUS_LABELS = {
    "Resource rent taxes",
    "Minerals resource rent tax",
    "Total Income tax",
    "Total income taxation revenue",
    "Other indirect tax",
    "Other indirect tax (including GST)",
}


def extract_workbook(path: Path, source_id: str) -> tuple[list[dict], list[dict]]:
    rows, quarantine = extract_multi_block_ytd_workbook(path, source_id, TITLE_RE)
    published: list[dict] = []
    for row in rows:
        if row["measure_label"] in _AMBIGUOUS_LABELS:
            quarantine.append(
                {
                    "reason": "known_multi_generation_composition_ambiguity",
                    "sheet": row["sheet"],
                    "label": row["measure_label"],
                }
            )
            continue
        published.append(row)
    return published, quarantine


def main() -> int:
    path = find_latest_asset(SOURCE_ID)
    if path is None:
        print(json.dumps({"error": f"no asset found for {SOURCE_ID}"}))
        return 1

    rows, quarantine = extract_workbook(path, SOURCE_ID)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "mfs_tax_notes_1_2.csv"
    if rows:
        with out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    if quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        qpath = QUARANTINE_DIR / f"mfs_quarantine_{SOURCE_ID}.jsonl"
        with qpath.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    distinct_labels = sorted({r["measure_label"] for r in rows})
    print(
        json.dumps(
            {
                "source_id": SOURCE_ID,
                "path": str(path),
                "rows": len(rows),
                "quarantined": len(quarantine),
                "distinct_measure_labels": distinct_labels,
                "out": str(out),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a before/after PBS reprocessing report.

Read-only: runs extract_pdf() per discovered PBS PDF (does not touch
facts.db), compares raw row counts against the pre-reprocessing inventory
(ops/reports/pbs-inventory-*.csv), and records per-source outcome
(rows produced / quarantined / zero-yield reason).
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extractors.pbs_programs_all import discover_pbs_pdfs, extract_pdf  # noqa: E402

STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
INVENTORY = sorted((REPO_ROOT / "ops/reports").glob("pbs-inventory-*.csv"))[-1]
QUARANTINE_DIR = REPO_ROOT / "data/staging/quarantine"


def _before_counts() -> dict[str, dict]:
    before = {}
    with INVENTORY.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            before[row["source_id"]] = row
    return before


def main() -> int:
    before = _before_counts()
    results = []
    total_rows = 0
    total_quarantine = 0
    for portfolio, source_id, pdf, url in discover_pbs_pdfs():
        qpath = QUARANTINE_DIR / f"pbs_quarantine_{source_id}.jsonl"
        if qpath.exists():
            qpath.unlink()
        try:
            rows = extract_pdf(pdf, portfolio=portfolio, source_id=source_id, source_url=url)
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "source_id": source_id,
                    "portfolio": portfolio,
                    "pdf": pdf.name,
                    "before_fact_count": before.get(source_id, {}).get("current_fact_count"),
                    "after_raw_rows": 0,
                    "after_quarantine_rows": 0,
                    "outcome": "error",
                    "detail": str(exc),
                }
            )
            continue
        qcount = 0
        if qpath.exists():
            qcount = sum(1 for _ in qpath.open(encoding="utf-8"))
        total_rows += len(rows)
        total_quarantine += qcount
        outcome = "facts" if rows else ("quarantine_only" if qcount else "zero_yield")
        detail = ""
        if outcome == "zero_yield":
            detail = "no rows and no quarantine entries - no matching table content found"
        results.append(
            {
                "source_id": source_id,
                "portfolio": portfolio,
                "pdf": pdf.name,
                "before_fact_count": before.get(source_id, {}).get("current_fact_count"),
                "after_raw_rows": len(rows),
                "after_quarantine_rows": qcount,
                "outcome": outcome,
                "detail": detail,
            }
        )

    out_csv = REPO_ROOT / f"ops/reports/pbs-reprocessing-{STAMP}.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    zero_yield = [r for r in results if r["outcome"] == "zero_yield"]
    out_md = REPO_ROOT / f"ops/reports/pbs-reprocessing-{STAMP}.md"
    with out_md.open("w", encoding="utf-8") as fh:
        fh.write(f"# PBS reprocessing report — {STAMP}\n\n")
        fh.write(f"Sources processed: {len(results)}\n\n")
        fh.write(f"Total raw rows (pre cross-document dedupe): {total_rows}\n\n")
        fh.write(f"Total quarantined rows: {total_quarantine}\n\n")
        fh.write(f"Sources with zero rows and zero quarantine: {len(zero_yield)}\n\n")
        if zero_yield:
            fh.write("## Zero-yield sources (require follow-up)\n\n")
            for r in zero_yield:
                fh.write(f"- `{r['source_id']}` ({r['portfolio']}) — {r['pdf']}\n")
            fh.write("\n")
        fh.write("## Per-source detail\n\n")
        fh.write("| source_id | portfolio | before_fact_count | after_raw_rows | after_quarantine_rows | outcome |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for r in sorted(results, key=lambda x: -x["after_raw_rows"]):
            fh.write(
                f"| {r['source_id']} | {r['portfolio']} | {r['before_fact_count']} | "
                f"{r['after_raw_rows']} | {r['after_quarantine_rows']} | {r['outcome']} |\n"
            )

    print(json.dumps({"csv": str(out_csv), "md": str(out_md), "sources": len(results),
                       "total_raw_rows": total_rows, "total_quarantine_rows": total_quarantine,
                       "zero_yield": len(zero_yield)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

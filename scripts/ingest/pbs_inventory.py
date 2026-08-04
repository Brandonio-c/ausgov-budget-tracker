#!/usr/bin/env python3
"""Build a machine-readable inventory of every acquired PBS PDF (Task 3.1).

Read-only: does not touch facts.db beyond SELECTs, does not write staging
breakdowns. Cross-references data/raw/**/latest.json against source_documents/
facts/facts_pending_attribution in facts.db.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from extractors.pbs_programs_all import _budget_year_from_source, discover_pbs_pdfs  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
OUT_CSV = REPO_ROOT / "ops" / "reports" / "pbs-inventory-{stamp}.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def page_count_and_extractable(path: Path) -> tuple[int | None, bool, str | None]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = len(reader.pages)
        sample_text = ""
        for page in reader.pages[: min(3, pages)]:
            sample_text += page.extract_text() or ""
        return pages, bool(sample_text.strip()), None
    except Exception as error:  # noqa: BLE001
        return None, False, f"{type(error).__name__}: {error}"


def db_counts() -> dict[str, dict]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        by_source: dict[str, dict] = {}
        rows = conn.execute(
            """
            SELECT sd.source_key, COUNT(f.id) AS fact_count
            FROM source_documents sd
            LEFT JOIN facts f ON f.source_document_id = sd.id
            GROUP BY sd.source_key
            """
        ).fetchall()
        for source_key, fact_count in rows:
            by_source[source_key] = {"fact_count": fact_count, "in_source_documents": True}
        return by_source
    finally:
        conn.close()


def quarantine_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    qdir = REPO_ROOT / "data" / "staging" / "quarantine"
    if not qdir.is_dir():
        return counts
    for path in qdir.glob("pbs_quarantine_*.jsonl"):
        source_id = path.stem.replace("pbs_quarantine_", "")
        n = sum(1 for _ in path.open("r", encoding="utf-8"))
        counts[source_id] = n
    return counts


def main() -> int:
    from datetime import datetime, timezone

    fact_counts = db_counts()
    quarantine = quarantine_counts()

    rows = []
    for portfolio, source_id, pdf, url in discover_pbs_pdfs():
        pages, extractable, error = page_count_and_extractable(pdf)
        budget_year = _budget_year_from_source(source_id, pdf.stem)
        db_info = fact_counts.get(source_id, {"fact_count": 0, "in_source_documents": False})
        rows.append(
            {
                "source_id": source_id,
                "portfolio": portfolio,
                "budget_year": budget_year or "unknown",
                "file_path": str(pdf.relative_to(REPO_ROOT)),
                "file_sha256": sha256_file(pdf),
                "page_count": pages,
                "text_extractable": extractable,
                "read_error": error,
                "current_fact_count": db_info["fact_count"],
                "in_source_documents_table": db_info["in_source_documents"],
                "current_quarantine_count": quarantine.get(source_id, 0),
                "landing_or_source_url": url,
            }
        )

    rows.sort(key=lambda r: (r["portfolio"], r["budget_year"], r["source_id"]))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(str(OUT_CSV).format(stamp=stamp))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    portfolios = sorted({r["portfolio"] for r in rows})
    budget_years = sorted({r["budget_year"] for r in rows})
    print(json.dumps({
        "total_pdfs": len(rows),
        "portfolios": len(portfolios),
        "budget_years": budget_years,
        "zero_fact_count": sum(1 for r in rows if r["current_fact_count"] == 0),
        "non_extractable": sum(1 for r in rows if not r["text_extractable"]),
        "out": str(out_path.relative_to(REPO_ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

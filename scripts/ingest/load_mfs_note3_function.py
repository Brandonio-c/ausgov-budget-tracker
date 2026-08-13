#!/usr/bin/env python3
"""Load Federal Monthly Financial Statements (MFS) Note 3 - Total expense
by function data into data/facts.db (item 7.1, second of five MFS sibling
workbooks - federal_mfs_aggregates was the first, done previously).

Mirrors load_mfs_aggregates.py's structure and discipline exactly: reads
the unmodified scripts/ingest/extractors/mfs_note3_function.py extraction,
classifies every row against the declarative semantic model in
config/measure-semantics/mfs.yaml, validates it, and publishes it under
one of the 20 dedicated mfs_note3_* measure types/compatibility_groups
(see scripts/ingest/migrations/020_mfs_note3_measures.sql) - none of which
can ever share a compatibility_group with an annual GFS/PBS actual or
budget measure, nor with any mfs_ytd_*/mfs_stock_* Aggregates measure.

Revision policy: identical to the Aggregates loader - a fact_key is
identity-complete (source family + financial year + reporting month +
measure_type + accounting_basis + estimate_status + jurisdiction); if a
future re-acquisition ever produces a different amount for the same
identity, apply() below detects it explicitly and REFUSES to silently
overwrite, quarantining it pending an explicit revision-policy decision.

Usage:
    python3 scripts/ingest/load_mfs_note3_function.py --dry-run   (default)
    python3 scripts/ingest/load_mfs_note3_function.py --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import yaml  # noqa: E402
from mfs_common import find_latest_asset  # noqa: E402
from mfs_note3_function import extract_workbook  # noqa: E402
from schema_migrate import migrate  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "mfs.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "mfs_note3_function_load_quarantine.jsonl"
SOURCE_ID = "federal_mfs_note3_function"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Department of Finance",
    "title": "Australian Government Monthly Financial Statements - Note 3, Total expense by function",
    "jurisdiction": "Commonwealth",
    "government_level": "federal",
    "source_family": "mfs_note3_function",
}

_MONTH_NUM = {
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
}
_MONTH_DAYS = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def month_to_period_end(fy: str, month: str) -> str:
    y1, y2 = fy.split("-")
    year1 = int(y1)
    year2 = int("20" + y2) if len(y2) == 2 else int(y2)
    month_num = _MONTH_NUM[month]
    year = year1 if month_num >= 7 else year2
    last_day = 29 if month_num == 2 and _is_leap(year) else _MONTH_DAYS[month_num]
    return f"{year:04d}-{month_num:02d}-{last_day:02d}"


def financial_year_start(fy: str) -> str:
    return f"{fy.split('-')[0]}-07-01"


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_label_index(semantics: dict) -> dict[str, str]:
    """Only mfs_note3_* measures participate - this loader must never
    accidentally claim an Aggregates-workbook label (or vice versa), even
    though both share one semantics file."""
    index: dict[str, str] = {}
    for measure_type, spec in semantics["measures"].items():
        if not measure_type.startswith("mfs_note3_"):
            continue
        for label in spec.get("source_label_variants") or []:
            if label in index and index[label] != measure_type:
                raise ValueError(f"label {label!r} claimed by both {index[label]!r} and {measure_type!r}")
            index[label] = measure_type
    return index


def build_fact_key(
    *, source_family: str, financial_year: str, reporting_month: str, measure_type: str,
    accounting_basis: str, estimate_status: str, jurisdiction: str,
) -> str:
    return (
        f"{source_family}|{financial_year}|{reporting_month}|{measure_type}|"
        f"{accounting_basis}|{estimate_status}|{jurisdiction}"
    )


def classify_and_validate(row: dict, semantics: dict, label_index: dict[str, str]) -> tuple[dict | None, str]:
    """Returns (prepared_fact_dict_or_None, quarantine_reason_or_empty)."""
    measure_type = label_index.get(row["measure_label"])
    if measure_type is None:
        return None, "unrecognized_label"

    spec = semantics["measures"][measure_type]
    only_years = spec.get("only_published_financial_years")
    if only_years and row["fy"] not in only_years:
        return None, "outside_only_published_financial_years"

    if row["month"] not in _MONTH_NUM:
        return None, "invalid_reporting_month"

    try:
        period_end = month_to_period_end(row["fy"], row["month"])
    except (KeyError, ValueError):
        return None, "period_end_undeterminable"
    period_start = financial_year_start(row["fy"])
    if not period_end or not period_start:
        return None, "missing_period_bounds"

    if row["unit"] not in ("$m", "$b"):
        return None, "unit_undeterminable"

    if not row.get("locator") or not row.get("cached_copy_path"):
        return None, "missing_source_cell"
    source_file = REPO_ROOT / row["cached_copy_path"]
    if not source_file.is_file():
        return None, "source_file_missing_on_disk"

    jurisdiction = SOURCE_DOCUMENT_META["jurisdiction"]
    accounting_basis = spec["accounting_basis"]
    estimate_status = row["estimate_status"]

    fact_key = build_fact_key(
        source_family=SOURCE_ID,
        financial_year=row["fy"],
        reporting_month=row["month"],
        measure_type=measure_type,
        accounting_basis=accounting_basis,
        estimate_status=estimate_status,
        jurisdiction=jurisdiction,
    )

    return (
        {
            "fact_key": fact_key,
            "financial_year": row["fy"],
            "period_start": period_start,
            "period_end": period_end,
            "period_granularity": "month",
            "measure_type": measure_type,
            "accounting_basis": accounting_basis,
            "estimate_status": estimate_status,
            "amount_aud": row["amount"],
            "reporting_month": row["month"],
            "source_unit": row["unit"],
            "locator": row["locator"],
            "cached_copy_path": row["cached_copy_path"],
        },
        "",
    )


def ensure_source_document(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = ?", (SOURCE_DOCUMENT_META["source_key"],)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """
        INSERT INTO source_documents (source_key, publisher, title, jurisdiction, government_level, source_family)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            SOURCE_DOCUMENT_META["source_key"],
            SOURCE_DOCUMENT_META["publisher"],
            SOURCE_DOCUMENT_META["title"],
            SOURCE_DOCUMENT_META["jurisdiction"],
            SOURCE_DOCUMENT_META["government_level"],
            SOURCE_DOCUMENT_META["source_family"],
        ),
    )
    return cur.lastrowid


def ensure_measure_node(conn: sqlite3.Connection, doc_id: int, measure_type: str, label: str) -> int:
    canonical_key = f"{SOURCE_ID}|node|{measure_type}"
    row = conn.execute("SELECT id FROM nodes WHERE canonical_key = ?", (canonical_key,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """
        INSERT INTO nodes (canonical_key, node_type, name, jurisdiction, government_level, source_document_id)
        VALUES (?, 'category', ?, ?, ?, ?)
        """,
        (canonical_key, label, SOURCE_DOCUMENT_META["jurisdiction"], SOURCE_DOCUMENT_META["government_level"], doc_id),
    )
    return cur.lastrowid


def run(conn: sqlite3.Connection, *, apply: bool, quarantine_path: Path = QUARANTINE_PATH) -> dict:
    semantics = load_semantics()
    label_index = build_label_index(semantics)

    path = find_latest_asset(SOURCE_ID)
    if path is None:
        raise FileNotFoundError(f"no acquired asset found for {SOURCE_ID}")

    extracted_rows, extractor_quarantine = extract_workbook(path, SOURCE_ID)

    quarantine: list[dict] = [{"reason": q.get("reason", ""), **q} for q in extractor_quarantine]
    prepared: list[dict] = []
    for row in extracted_rows:
        fact, reason = classify_and_validate(row, semantics, label_index)
        if fact is None:
            quarantine.append({"reason": reason, "raw_label": row["measure_label"], "fy": row["fy"], "month": row["month"]})
        else:
            prepared.append(fact)

    to_insert: list[dict] = []
    superseded_conflicts: list[dict] = []
    for fact in prepared:
        existing = conn.execute(
            "SELECT id, amount_aud FROM facts WHERE fact_key = ?", (fact["fact_key"],)
        ).fetchone()
        if existing is None:
            to_insert.append(fact)
            continue
        existing_amount = existing[1]
        if existing_amount is not None and abs(float(existing_amount) - float(fact["amount_aud"])) < 0.01:
            continue  # already loaded, identical - idempotent no-op
        superseded_conflicts.append(
            {
                "reason": "amount_conflict_with_existing_fact",
                "fact_key": fact["fact_key"],
                "existing_amount_aud": existing_amount,
                "new_amount_aud": fact["amount_aud"],
            }
        )

    result = {
        "source_id": SOURCE_ID,
        "rows_extracted": len(extracted_rows),
        "rows_quarantined_by_extractor": len(extractor_quarantine),
        "rows_validated_publishable": len(prepared),
        "rows_quarantined_by_loader": len(quarantine) - len(extractor_quarantine),
        "facts_already_present_idempotent_skip": len(prepared) - len(to_insert) - len(superseded_conflicts),
        "facts_to_insert": len(to_insert),
        "revision_conflicts_quarantined": len(superseded_conflicts),
        "nodes_inserted": 0,
        "mode": "apply" if apply else "dry-run",
    }
    quarantine.extend(superseded_conflicts)

    if apply and to_insert:
        doc_id = ensure_source_document(conn)
        measure_labels = {m: semantics["measures"][m] for m in {f["measure_type"] for f in to_insert}}
        node_ids = {}
        nodes_before = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        for measure_type in measure_labels:
            row = conn.execute(
                "SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)
            ).fetchone()
            label = row[0] if row else measure_type
            node_ids[measure_type] = ensure_measure_node(conn, doc_id, measure_type, label)
        nodes_after = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        result["nodes_inserted"] = nodes_after - nodes_before

        for fact in to_insert:
            locator_json = json.dumps(
                {"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]}
            )
            cur = conn.execute(
                """
                INSERT INTO facts (
                    fact_key, financial_year, period_start, period_end, period_granularity,
                    measure_type, accounting_basis, estimate_status, amount_aud, unit, currency,
                    source_document_id, source_locator_json, retrieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'AUD', 'AUD', ?, ?, datetime('now'))
                """,
                (
                    fact["fact_key"], fact["financial_year"], fact["period_start"], fact["period_end"],
                    fact["period_granularity"], fact["measure_type"], fact["accounting_basis"],
                    fact["estimate_status"], fact["amount_aud"], doc_id, locator_json,
                ),
            )
            fact_id = cur.lastrowid
            conn.execute(
                "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
                (fact_id, node_ids[fact["measure_type"]]),
            )
        conn.commit()

    if quarantine:
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        with quarantine_path.open("w", encoding="utf-8") as fh:
            for item in quarantine:
                fh.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Default behavior; explicit no-op flag.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    migrate(args.db)
    conn = sqlite3.connect(str(args.db))
    result = run(conn, apply=args.apply)
    conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

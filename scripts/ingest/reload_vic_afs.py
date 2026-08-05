#!/usr/bin/env python3
"""Load the Victorian DTF Annual Financial Statements (2024-25) into
data/facts.db (adapter-repair-followup milestone, Task 3/4).

Reads scripts/ingest/extractors/vic_afs.py's extraction, classifies every
row against the declarative semantic model in
config/measure-semantics/vic_afs.yaml, validates it, and publishes it
under one of 11 dedicated vic_afs_* measure types/compatibility_groups
(see scripts/ingest/migrations/008_vic_afs_measures.sql) - none of which
can ever share a compatibility_group with any annual GFS/PBS actual or
budget measure, nor with any other VIC state-level family. A row is
published only if every one of these holds:

  - its row label matches exactly one measure_type's
    source_label_variants (and is not an explicitly excluded duplicate
    label - "Net worth" restates "Net assets" verbatim; the extractor
    already stops before the sheet's other duplicate-by-design notes
    sections);
  - the row's sheet matches that measure_type's declared source_sheet
    (defensive cross-sheet check);
  - a source cell locator and an on-disk cached copy of the source
    workbook both resolve;
  - the $ thousand -> AUD scale conversion is applied exactly once.

Anything that fails any of these is written to
data/staging/quarantine/vic_afs_load_quarantine.jsonl, never to
facts.db.

Revision policy: vic_annual_financial_statements_2024_25 has exactly one
acquired snapshot today - there is no competing prior edition to
reconcile. The stable fact_key below is identity-complete (source_id +
financial_year + measure_type + accounting_basis + estimate_status +
jurisdiction), so if a future re-acquisition (e.g. a 2025-26 edition,
which will re-present 2024-25 as its own comparative column) ever
produces a different amount for the same identity, apply() below
detects it explicitly (reason=amount_conflict_with_existing_fact) and
REFUSES to silently overwrite - it is quarantined pending an explicit
revision-policy decision, matching the MFS-aggregates milestone's
established pattern.

Usage:
    python3 scripts/ingest/reload_vic_afs.py --dry-run   (default)
    python3 scripts/ingest/reload_vic_afs.py --apply
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
from schema_migrate import migrate  # noqa: E402
from vic_afs import extract_workbook  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "vic_afs.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "vic_afs_load_quarantine.jsonl"
SOURCE_ID = "vic_annual_financial_statements_2024_25"
SOURCE_FILE = (
    REPO_ROOT
    / "data/raw/state/vic_annual_financial_statements_2024_25/snapshots/20260724T190604Z/files/Annual-financial-statements-2024-25.xlsx"
)

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Victorian Department of Treasury and Finance",
    "title": "Victoria Department of Treasury and Finance Annual Financial Statements 2024-25",
    "jurisdiction": "VIC",
    "government_level": "state",
    "source_family": "handoff_actuals_state",
}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_label_index(semantics: dict) -> dict[str, str]:
    index: dict[str, str] = {}
    for measure_type, spec in semantics["measures"].items():
        for label in spec.get("source_label_variants") or []:
            if label in index and index[label] != measure_type:
                raise ValueError(f"label {label!r} claimed by both {index[label]!r} and {measure_type!r}")
            index[label] = measure_type
    return index


def build_excluded_label_set(semantics: dict) -> set[str]:
    excluded: set[str] = set()
    for spec in semantics["measures"].values():
        excluded.update(spec.get("excluded_label_variants") or [])
    return excluded


def build_fact_key(
    *, source_id: str, financial_year: str, measure_type: str, accounting_basis: str,
    estimate_status: str, jurisdiction: str,
) -> str:
    return f"{source_id}|{financial_year}|{measure_type}|{accounting_basis}|{estimate_status}|{jurisdiction}"


def classify_and_validate(
    row: dict, semantics: dict, label_index: dict[str, str], excluded_labels: set[str]
) -> tuple[dict | None, str]:
    """Returns (prepared_fact_dict_or_None, quarantine_reason_or_empty)."""
    if row["row_label"] in excluded_labels:
        return None, "excluded_duplicate_label"

    measure_type = label_index.get(row["row_label"])
    if measure_type is None:
        return None, "unrecognized_label"

    spec = semantics["measures"][measure_type]
    if row["sheet"] != spec["source_sheet"]:
        return None, "sheet_mismatch"

    if not row.get("locator") or not row.get("cached_copy_path"):
        return None, "missing_source_cell"
    source_file = REPO_ROOT / row["cached_copy_path"]
    if not source_file.is_file():
        return None, "source_file_missing_on_disk"

    scale_factor = spec.get("scale_factor", 1)
    amount_aud = row["amount_thousand_aud"] * scale_factor

    jurisdiction = SOURCE_DOCUMENT_META["jurisdiction"]
    accounting_basis = spec["accounting_basis"]
    estimate_status = spec["estimate_status"]

    fact_key = build_fact_key(
        source_id=SOURCE_ID,
        financial_year=row["financial_year"],
        measure_type=measure_type,
        accounting_basis=accounting_basis,
        estimate_status=estimate_status,
        jurisdiction=jurisdiction,
    )

    return (
        {
            "fact_key": fact_key,
            "financial_year": row["financial_year"],
            "period_start": None if spec["flow_or_stock"] in ("stock", "stock_balance") else f"{row['financial_year'][:4]}-07-01",
            "period_end": f"{'20' + row['financial_year'][-2:]}-06-30",
            "period_granularity": "financial_year",
            "measure_type": measure_type,
            "accounting_basis": accounting_basis,
            "estimate_status": estimate_status,
            "amount_aud": amount_aud,
            "flow_or_stock": spec["flow_or_stock"],
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
    excluded_labels = build_excluded_label_set(semantics)

    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"no acquired asset found at {SOURCE_FILE}")

    extracted_rows, extractor_quarantine = extract_workbook(SOURCE_FILE, SOURCE_ID)

    quarantine: list[dict] = [{"reason": q.get("reason", ""), **q} for q in extractor_quarantine]
    prepared: list[dict] = []
    for row in extracted_rows:
        fact, reason = classify_and_validate(row, semantics, label_index, excluded_labels)
        if fact is None:
            quarantine.append(
                {"reason": reason, "raw_label": row["row_label"], "sheet": row["sheet"], "fy": row["financial_year"]}
            )
        else:
            prepared.append(fact)

    # Revision-conflict detection: if a fact_key already exists with a
    # materially different amount, refuse to overwrite - quarantine for
    # explicit review rather than letting insertion order decide.
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
        measure_types_touched = {f["measure_type"] for f in to_insert}
        node_ids = {}
        nodes_before = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        for measure_type in measure_types_touched:
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

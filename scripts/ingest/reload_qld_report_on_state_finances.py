#!/usr/bin/env python3
"""Load 7 editions of the Queensland Treasury's "Report on State
Finances" into data/facts.db (QLD PDF population milestone - Task
5/6).

Reads scripts/ingest/extractors/qld_report_on_state_finances.py's
extraction, classifies every row against the declarative semantic
model in config/measure-semantics/qld_report_on_state_finances.yaml,
validates it, and publishes it under one of 8 NEW qld_rsf_* measure
types/compatibility_groups (see scripts/ingest/migrations/
012_qld_rsf_measures.sql) - a genuinely new family (Queensland
currently has zero Treasury-published-own fiscal-aggregate coverage in
this dashboard).

A row is published only if every one of these holds:

  - its financial year and measure_type were resolved by the extractor
    (which already performed row-label matching and General-
    Government-Sector-only column disambiguation - always the first
    pair of 2 numbers per row);
  - its estimate_status is 'estimated_actual' or 'actual' (the only
    two vintages this table produces - 'estimated_actual' is NOT the
    same concept as TAS's 'budget', see the semantic model's revision
    policy);
  - a source cell locator and an on-disk cached copy of the source PDF
    both resolve;
  - the $ million -> AUD scale conversion is applied exactly once.

Anything that fails any of these is written to
data/staging/quarantine/qld_report_on_state_finances_load_quarantine.jsonl,
never to facts.db.

Revision policy: each of the 7 target editions is Queensland
Treasury's own final, audited report for its stated financial year -
there is no competing prior edition of the SAME year to reconcile
against today. The stable fact_key below is identity-complete
(source_id + financial_year + measure_type + accounting_basis +
estimate_status + jurisdiction), so if a future re-acquisition of any
edition ever produces a different amount for the same identity,
apply() below detects it explicitly (reason=amount_conflict_with_
existing_fact) and REFUSES to silently overwrite - it is quarantined
pending an explicit revision-policy decision.

Usage:
    python3 scripts/ingest/reload_qld_report_on_state_finances.py --dry-run   (default)
    python3 scripts/ingest/reload_qld_report_on_state_finances.py --apply
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
from qld_report_on_state_finances import extract_all_editions  # noqa: E402
from schema_migrate import migrate  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "qld_report_on_state_finances.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "qld_report_on_state_finances_load_quarantine.jsonl"
SOURCE_ID = "qld_report_on_state_finances_actuals"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Queensland Treasury",
    "title": "Queensland Report on State Finances",
    "jurisdiction": "QLD",
    "government_level": "state",
    "source_family": "handoff_actuals_state",
}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_fact_key(
    *, source_id: str, financial_year: str, measure_type: str, accounting_basis: str,
    estimate_status: str, jurisdiction: str,
) -> str:
    return f"{source_id}|{financial_year}|{measure_type}|{accounting_basis}|{estimate_status}|{jurisdiction}"


def classify_and_validate(row: dict, semantics: dict) -> tuple[dict | None, str]:
    """Returns (prepared_fact_dict_or_None, quarantine_reason_or_empty)."""
    measure_type = row["measure_type"]
    spec = semantics["measures"].get(measure_type)
    if spec is None:
        return None, "unrecognized_measure_type"

    if row["estimate_status"] not in ("estimated_actual", "actual"):
        return None, "unexpected_estimate_status"

    if not row.get("locator") or not row.get("cached_copy_path"):
        return None, "missing_source_cell"
    source_file = REPO_ROOT / row["cached_copy_path"]
    if not source_file.is_file():
        return None, "source_file_missing_on_disk"

    scale_factor = spec.get("scale_factor", 1)
    amount_aud = row["amount_million_aud"] * scale_factor

    jurisdiction = SOURCE_DOCUMENT_META["jurisdiction"]
    accounting_basis = spec["accounting_basis"]
    estimate_status = row["estimate_status"]

    fact_key = build_fact_key(
        source_id=SOURCE_ID,
        financial_year=row["financial_year"],
        measure_type=measure_type,
        accounting_basis=accounting_basis,
        estimate_status=estimate_status,
        jurisdiction=jurisdiction,
    )

    is_stock = spec["flow_or_stock"] in ("stock", "stock_balance")
    return (
        {
            "fact_key": fact_key,
            "financial_year": row["financial_year"],
            "period_start": None if is_stock else f"{row['financial_year'][:4]}-07-01",
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

    extracted_rows, extractor_quarantine = extract_all_editions(SOURCE_ID)

    quarantine: list[dict] = [{"reason": q.get("reason", ""), **q} for q in extractor_quarantine]
    prepared: list[dict] = []
    for row in extracted_rows:
        fact, reason = classify_and_validate(row, semantics)
        if fact is None:
            quarantine.append(
                {
                    "reason": reason,
                    "measure_type": row.get("measure_type"),
                    "fy": row["financial_year"],
                    "estimate_status": row.get("estimate_status"),
                }
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

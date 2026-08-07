#!/usr/bin/env python3
"""Validate and idempotently load the safe TAS TAFR transition cluster."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest/extractors"))

from schema_migrate import migrate  # noqa: E402
from tas_tafr_narrative_backfill import SOURCE_ID, extract_all_editions  # noqa: E402

DB_PATH = REPO_ROOT / "data/facts.db"
SEMANTICS_PATH = REPO_ROOT / "config/measure-semantics/tas_tafr_narrative_backfill.yaml"
QUARANTINE_PATH = REPO_ROOT / "data/staging/quarantine/tas_tafr_narrative_backfill.jsonl"

SOURCE_META = {
    "source_key": SOURCE_ID,
    "publisher": "Tasmanian Department of Treasury and Finance",
    "title": "Tasmanian Treasurer's Annual Financial Reports",
    "jurisdiction": "TAS",
    "government_level": "state",
    "source_family": "handoff_actuals_state",
}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def classify(row: dict, semantics: dict) -> tuple[dict | None, str]:
    spec = semantics["measures"].get(row.get("measure_type"))
    if spec is None:
        return None, "unrecognized_measure_type"
    if row.get("estimate_status") not in semantics["family"]["allowed_estimate_statuses"]:
        return None, "unexpected_estimate_status"
    if row.get("financial_year") not in semantics["family"]["selected_years"]:
        return None, "edition_outside_selected_cluster"
    if not row.get("locator") or not (REPO_ROOT / row.get("cached_copy_path", "")).is_file():
        return None, "missing_source_locator_or_file"
    fy = row["financial_year"]
    is_stock = spec["flow_or_stock"] == "stock"
    amount = row["amount_million_aud"] * semantics["family"]["scale_factor"]
    fact_key = f"{SOURCE_ID}|{fy}|{row['measure_type']}|accrual|{row['estimate_status']}|TAS"
    return ({
        "fact_key": fact_key,
        "financial_year": fy,
        "period_start": None if is_stock else f"{fy[:4]}-07-01",
        "period_end": f"20{fy[-2:]}-06-30",
        "period_granularity": "financial_year",
        "measure_type": row["measure_type"],
        "accounting_basis": "accrual",
        "estimate_status": row["estimate_status"],
        "amount_aud": amount,
        "publication_date": row["publication_date"],
        "source_budget_year": fy,
        "column_header_original": "Original Budget" if row["estimate_status"] == "budget" else "Actual",
        "locator": row["locator"],
        "cached_copy_path": row["cached_copy_path"],
    }, "")


def _source_document(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM source_documents WHERE source_key = ?", (SOURCE_ID,)).fetchone()
    if row:
        return int(row[0])
    cur = conn.execute(
        "INSERT INTO source_documents (source_key,publisher,title,jurisdiction,government_level,source_family) VALUES (?,?,?,?,?,?)",
        tuple(SOURCE_META[key] for key in ("source_key", "publisher", "title", "jurisdiction", "government_level", "source_family")),
    )
    return int(cur.lastrowid)


def _node(conn: sqlite3.Connection, doc_id: int, measure_type: str) -> int:
    key = f"{SOURCE_ID}|node|{measure_type}"
    row = conn.execute("SELECT id FROM nodes WHERE canonical_key = ?", (key,)).fetchone()
    if row:
        return int(row[0])
    label_row = conn.execute("SELECT label FROM measure_definitions WHERE measure_type = ?", (measure_type,)).fetchone()
    label = label_row[0] if label_row else measure_type
    cur = conn.execute(
        "INSERT INTO nodes (canonical_key,node_type,name,jurisdiction,government_level,source_document_id,source_locator_json) VALUES (?,'category',?,'TAS','state',?,'{}')",
        (key, label, doc_id),
    )
    return int(cur.lastrowid)


def run(conn: sqlite3.Connection, *, apply: bool, quarantine_path: Path = QUARANTINE_PATH) -> dict:
    semantics = load_semantics()
    extracted, quarantine = extract_all_editions()
    prepared: list[dict] = []
    for row in extracted:
        fact, reason = classify(row, semantics)
        if fact is None:
            quarantine.append({"reason": reason, "financial_year": row.get("financial_year"), "measure_type": row.get("measure_type")})
        else:
            prepared.append(fact)

    to_insert: list[dict] = []
    idempotent = 0
    conflicts = 0
    for fact in prepared:
        existing = conn.execute("SELECT amount_aud FROM facts WHERE fact_key = ?", (fact["fact_key"],)).fetchone()
        if existing is None:
            to_insert.append(fact)
        elif existing[0] is not None and abs(float(existing[0]) - fact["amount_aud"]) < 0.01:
            idempotent += 1
        else:
            conflicts += 1
            quarantine.append({"reason": "amount_conflict_with_existing_fact", "fact_key": fact["fact_key"], "existing_amount_aud": existing[0], "new_amount_aud": fact["amount_aud"]})

    result = {
        "source_id": SOURCE_ID,
        "rows_extracted": len(extracted),
        "rows_published": len(prepared) - conflicts,
        "rows_quarantined": len(quarantine),
        "facts_inserted": 0,
        "facts_updated": 0,
        "facts_superseded": 0,
        "facts_to_insert": len(to_insert),
        "facts_already_present_idempotent_skip": idempotent,
        "nodes_inserted": 0,
        "edges_inserted": 0,
        "semantic_changes": 0,
        "revision_conflicts_quarantined": conflicts,
        "mode": "apply" if apply else "dry-run",
    }

    if apply and to_insert:
        doc_id = _source_document(conn)
        before_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        nodes = {measure: _node(conn, doc_id, measure) for measure in {fact["measure_type"] for fact in to_insert}}
        result["nodes_inserted"] = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] - before_nodes
        for fact in to_insert:
            locator_json = json.dumps({"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]})
            cur = conn.execute(
                """INSERT INTO facts (
                    fact_key,financial_year,period_start,period_end,period_granularity,
                    measure_type,accounting_basis,estimate_status,amount_aud,unit,currency,
                    source_document_id,source_locator_json,retrieved_at,publication_date,
                    source_budget_year,column_header_original,quality_status,view_family
                ) VALUES (?,?,?,?,?,?,?,?,?,'AUD','AUD',?,?,datetime('now'),?,?,?,'published','state_annual_fiscal')""",
                (fact["fact_key"], fact["financial_year"], fact["period_start"], fact["period_end"],
                 fact["period_granularity"], fact["measure_type"], fact["accounting_basis"],
                 fact["estimate_status"], fact["amount_aud"], doc_id, locator_json,
                 fact["publication_date"], fact["source_budget_year"], fact["column_header_original"]),
            )
            conn.execute("INSERT INTO fact_nodes (fact_id,node_id,dimension_role) VALUES (?,?,'primary')", (cur.lastrowid, nodes[fact["measure_type"]]))
        conn.commit()
        result["facts_inserted"] = len(to_insert)

    if quarantine:
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        with quarantine_path.open("w", encoding="utf-8") as handle:
            for item in quarantine:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    migrate(args.db)
    conn = sqlite3.connect(args.db)
    try:
        result = run(conn, apply=args.apply)
    finally:
        conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

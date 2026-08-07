#!/usr/bin/env python3
"""Validate and idempotently load VIC DTF output-cost performance rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest/extractors"))

from schema_migrate import migrate  # noqa: E402
from vic_output_performance import SOURCE_ID, extract_workbook  # noqa: E402

DB_PATH = REPO_ROOT / "data/facts.db"
SEMANTICS_PATH = REPO_ROOT / "config/measure-semantics/vic_output_performance.yaml"
QUARANTINE_PATH = REPO_ROOT / "data/staging/quarantine/vic_output_performance.jsonl"
SOURCE_META = {
    "source_key": SOURCE_ID,
    "publisher": "Victorian Department of Treasury and Finance",
    "title": "Victoria Output Performance Measures 2024-25",
    "jurisdiction": "VIC",
    "government_level": "state",
    "source_family": "handoff_actuals_state",
    "landing_url": "https://www.dtf.vic.gov.au/2024-25-annual-report",
    "canonical_resource_url": "https://www.dtf.vic.gov.au/sites/default/files/2025-10/Output-performance-measures-2024-25.xlsx",
}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return base or hashlib.sha1(value.encode()).hexdigest()[:12]


def classify(row: dict, semantics: dict) -> tuple[dict | None, str]:
    family = semantics["family"]
    if row.get("measure_type") != semantics["measure"]["measure_type"]:
        return None, "unexpected_measure_type"
    if row.get("financial_year") != family["financial_year"]:
        return None, "unexpected_financial_year"
    if row.get("estimate_status") not in ("actual", "budget"):
        return None, "unexpected_estimate_status"
    if not row.get("locator") or not (REPO_ROOT / row.get("cached_copy_path", "")).is_file():
        return None, "missing_source_locator_or_file"
    output_slug = _slug(row["output_name"])
    return ({
        "fact_key": f"{SOURCE_ID}|2024-25|{output_slug}|vic_output_total_cost|{row['estimate_status']}|VIC",
        "financial_year": "2024-25",
        "period_start": "2024-07-01",
        "period_end": "2025-06-30",
        "measure_type": "vic_output_total_cost",
        "estimate_status": row["estimate_status"],
        "amount_aud": row["amount_million_aud"] * family["scale_factor"],
        "output_name": row["output_name"],
        "output_slug": output_slug,
        "publication_date": row["publication_date"],
        "column_header_original": row["column_header_original"],
        "locator": row["locator"],
        "cached_copy_path": row["cached_copy_path"],
    }, "")


def _source(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM source_documents WHERE source_key=?", (SOURCE_ID,)).fetchone()
    if row:
        conn.execute(
            "UPDATE source_documents SET landing_url=?, canonical_resource_url=? WHERE id=?",
            (SOURCE_META["landing_url"], SOURCE_META["canonical_resource_url"], row[0]),
        )
        return int(row[0])
    cur = conn.execute(
        "INSERT INTO source_documents (source_key,publisher,title,jurisdiction,government_level,source_family,landing_url,canonical_resource_url) VALUES (?,?,?,?,?,?,?,?)",
        tuple(SOURCE_META[key] for key in ("source_key", "publisher", "title", "jurisdiction", "government_level", "source_family", "landing_url", "canonical_resource_url")),
    )
    return int(cur.lastrowid)


def _node(conn: sqlite3.Connection, doc_id: int, fact: dict) -> int:
    key = f"{SOURCE_ID}|output|{fact['output_slug']}"
    row = conn.execute("SELECT id FROM nodes WHERE canonical_key=?", (key,)).fetchone()
    if row:
        return int(row[0])
    cur = conn.execute(
        "INSERT INTO nodes (canonical_key,node_type,name,jurisdiction,government_level,source_document_id,source_locator_json) VALUES (?,'program',?,'VIC','state',?,'{}')",
        (key, fact["output_name"], doc_id),
    )
    return int(cur.lastrowid)


def run(conn: sqlite3.Connection, *, apply: bool, quarantine_path: Path = QUARANTINE_PATH) -> dict:
    extracted, quarantine = extract_workbook()
    semantics = load_semantics()
    prepared = []
    for row in extracted:
        fact, reason = classify(row, semantics)
        if fact is None:
            quarantine.append({"reason": reason, "output_name": row.get("output_name")})
        else:
            prepared.append(fact)
    to_insert, idempotent = [], 0
    conflicts = 0
    for fact in prepared:
        existing = conn.execute("SELECT amount_aud FROM facts WHERE fact_key=?", (fact["fact_key"],)).fetchone()
        if existing is None:
            to_insert.append(fact)
        elif existing[0] is not None and abs(float(existing[0]) - fact["amount_aud"]) < 0.01:
            idempotent += 1
        else:
            conflicts += 1
            quarantine.append({"reason": "amount_conflict_with_existing_fact", "fact_key": fact["fact_key"]})
    result = {
        "source_id": SOURCE_ID, "rows_extracted": len(extracted),
        "rows_published": len(prepared) - conflicts, "rows_quarantined": len(quarantine),
        "facts_inserted": 0, "facts_updated": 0, "facts_superseded": 0,
        "facts_to_insert": len(to_insert), "facts_already_present_idempotent_skip": idempotent,
        "nodes_inserted": 0, "edges_inserted": 0, "semantic_changes": 0,
        "revision_conflicts_quarantined": conflicts, "mode": "apply" if apply else "dry-run",
    }
    doc_id = _source(conn) if apply else None
    if apply and to_insert:
        assert doc_id is not None
        before_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        nodes = {fact["output_slug"]: _node(conn, doc_id, fact) for fact in to_insert}
        result["nodes_inserted"] = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] - before_nodes
        for fact in to_insert:
            locator = json.dumps({"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]})
            cur = conn.execute(
                """INSERT INTO facts (
                    fact_key,financial_year,period_start,period_end,period_granularity,
                    measure_type,accounting_basis,estimate_status,amount_aud,unit,currency,
                    source_document_id,source_locator_json,retrieved_at,publication_date,
                    source_budget_year,column_header_original,quality_status,view_family
                ) VALUES (?,?,?,?,?,'vic_output_total_cost','accrual',?,?,'AUD','AUD',?,?,datetime('now'),?,'2024-25',?,'published','vic_output_performance')""",
                (fact["fact_key"], fact["financial_year"], fact["period_start"], fact["period_end"],
                 "financial_year", fact["estimate_status"], fact["amount_aud"], doc_id, locator,
                 fact["publication_date"], fact["column_header_original"]),
            )
            conn.execute("INSERT INTO fact_nodes (fact_id,node_id,dimension_role) VALUES (?,?,'primary')", (cur.lastrowid, nodes[fact["output_slug"]]))
        conn.commit()
        result["facts_inserted"] = len(to_insert)
    elif apply:
        conn.commit()
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

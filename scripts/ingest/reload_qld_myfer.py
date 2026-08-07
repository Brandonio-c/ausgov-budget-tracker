#!/usr/bin/env python3
"""Validate and idempotently load the selected Queensland MYFER cluster."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest/extractors"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))

import yaml  # noqa: E402
from qld_myfer import SOURCE_ID, extract_all_editions  # noqa: E402
from schema_migrate import migrate  # noqa: E402

DB_PATH = REPO_ROOT / "data/facts.db"
SEMANTICS_PATH = REPO_ROOT / "config/measure-semantics/qld_myfer.yaml"
QUARANTINE_PATH = REPO_ROOT / "data/staging/quarantine/qld_myfer_load_quarantine.jsonl"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Queensland Treasury",
    "title": "Queensland Mid-Year Fiscal and Economic Review",
    "jurisdiction": "QLD",
    "government_level": "state",
    "source_family": "handoff_actuals_state",
    "native_unit": "AUD million",
    "notes": "Selected MYFER cluster from qld_report_on_state_finances_actuals; revised estimates, not audited RSF actuals.",
}


def load_semantics() -> dict:
    return yaml.safe_load(SEMANTICS_PATH.read_text(encoding="utf-8"))


def build_fact_key(
    *, source_id: str, source_budget_year: str, financial_year: str,
    measure_type: str, accounting_basis: str, estimate_status: str,
    jurisdiction: str,
) -> str:
    return (
        f"{source_id}|vintage:{source_budget_year}|fy:{financial_year}|"
        f"{measure_type}|{accounting_basis}|{estimate_status}|{jurisdiction}"
    )


def classify_and_validate(row: dict, semantics: dict) -> tuple[dict | None, str]:
    spec = semantics["measures"].get(row.get("measure_type"))
    if spec is None:
        return None, "unrecognized_measure_type"
    if row.get("estimate_status") != semantics["family"]["estimate_status"]:
        return None, "unexpected_estimate_status"
    if row.get("source_budget_year") != row.get("financial_year"):
        return None, "selected_column_period_mismatch"
    if not row.get("locator") or not row.get("cached_copy_path"):
        return None, "missing_pdf_locator"
    if not (REPO_ROOT / row["cached_copy_path"]).is_file():
        return None, "source_file_missing_on_disk"

    family = semantics["family"]
    scale_factor = family["scale_factor"]
    amount_aud = row["amount_million_aud"] * scale_factor
    financial_year = row["financial_year"]
    period_end = f"20{financial_year[-2:]}-06-30"
    fact_key = build_fact_key(
        source_id=SOURCE_ID,
        source_budget_year=row["source_budget_year"],
        financial_year=financial_year,
        measure_type=row["measure_type"],
        accounting_basis=family["accounting_basis"],
        estimate_status=row["estimate_status"],
        jurisdiction=family["jurisdiction"],
    )
    return (
        {
            "fact_key": fact_key,
            "financial_year": financial_year,
            "period_start": f"{financial_year[:4]}-07-01",
            "period_end": period_end,
            "period_granularity": family["period_granularity"],
            "measure_type": row["measure_type"],
            "accounting_basis": family["accounting_basis"],
            "estimate_status": row["estimate_status"],
            "amount_aud": amount_aud,
            "source_budget_year": row["source_budget_year"],
            "publication_date": row["publication_date"],
            "column_header_original": row["column_header_original"],
            "locator": row["locator"],
            "cached_copy_path": row["cached_copy_path"],
            "flow_or_stock": spec["flow_or_stock"],
        },
        "",
    )


def ensure_source_document(conn: sqlite3.Connection) -> int:
    existing = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = ?", (SOURCE_ID,)
    ).fetchone()
    if existing:
        return existing[0]
    cur = conn.execute(
        """
        INSERT INTO source_documents (
            source_key, publisher, title, jurisdiction, government_level,
            source_family, native_unit, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        tuple(SOURCE_DOCUMENT_META[key] for key in (
            "source_key", "publisher", "title", "jurisdiction",
            "government_level", "source_family", "native_unit", "notes",
        )),
    )
    return int(cur.lastrowid)


def ensure_measure_node(
    conn: sqlite3.Connection, doc_id: int, measure_type: str, label: str
) -> int:
    canonical_key = f"{SOURCE_ID}|node|{measure_type}"
    existing = conn.execute(
        "SELECT id FROM nodes WHERE canonical_key = ?", (canonical_key,)
    ).fetchone()
    if existing:
        return existing[0]
    cur = conn.execute(
        """
        INSERT INTO nodes (
            canonical_key, node_type, name, jurisdiction, government_level,
            source_document_id, source_locator_json
        ) VALUES (?, 'category', ?, 'QLD', 'state', ?, '{}')
        """,
        (canonical_key, label, doc_id),
    )
    return int(cur.lastrowid)


def run(
    conn: sqlite3.Connection,
    *,
    apply: bool,
    quarantine_path: Path = QUARANTINE_PATH,
) -> dict:
    semantics = load_semantics()
    extracted, extractor_quarantine = extract_all_editions(SOURCE_ID)
    quarantine = list(extractor_quarantine)
    prepared: list[dict] = []
    for row in extracted:
        fact, reason = classify_and_validate(row, semantics)
        if fact is None:
            quarantine.append(
                {
                    "reason": reason,
                    "financial_year": row.get("financial_year"),
                    "measure_type": row.get("measure_type"),
                }
            )
        else:
            prepared.append(fact)

    to_insert: list[dict] = []
    citation_updates: list[tuple[str, int]] = []
    conflicts: list[dict] = []
    idempotent_skips = 0
    for fact in prepared:
        existing = conn.execute(
            "SELECT id, amount_aud, source_locator_json FROM facts WHERE fact_key = ?",
            (fact["fact_key"],),
        ).fetchone()
        if existing is None:
            to_insert.append(fact)
            continue
        if abs(float(existing[1]) - float(fact["amount_aud"])) >= 0.01:
            conflicts.append(
                {
                    "reason": "amount_conflict_with_existing_fact",
                    "fact_key": fact["fact_key"],
                    "existing_amount_aud": existing[1],
                    "new_amount_aud": fact["amount_aud"],
                }
            )
            continue
        expected_locator = json.dumps(
            {"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]}
        )
        if existing[2] == expected_locator:
            idempotent_skips += 1
        else:
            citation_updates.append((expected_locator, existing[0]))

    quarantine.extend(conflicts)
    result = {
        "source_id": SOURCE_ID,
        "rows_extracted": len(extracted),
        "rows_published": len(prepared) - len(conflicts),
        "rows_quarantined": len(quarantine),
        "facts_inserted": len(to_insert) if apply else 0,
        "facts_to_insert": len(to_insert),
        "facts_updated": len(citation_updates) if apply else 0,
        "facts_superseded": 0,
        "facts_already_present_idempotent_skip": idempotent_skips,
        "nodes_inserted": 0,
        "edges_inserted": 0,
        "semantic_changes": 0,
        "revision_conflicts_quarantined": len(conflicts),
        "mode": "apply" if apply else "dry-run",
    }

    if apply:
        doc_id = ensure_source_document(conn)
        nodes_before = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        node_ids: dict[str, int] = {}
        for measure_type in sorted({fact["measure_type"] for fact in prepared}):
            label = conn.execute(
                "SELECT label FROM measure_definitions WHERE measure_type = ?",
                (measure_type,),
            ).fetchone()[0]
            node_ids[measure_type] = ensure_measure_node(conn, doc_id, measure_type, label)
        result["nodes_inserted"] = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] - nodes_before

        for fact in to_insert:
            locator_json = json.dumps(
                {"locator": fact["locator"], "cached_copy_path": fact["cached_copy_path"]}
            )
            cur = conn.execute(
                """
                INSERT INTO facts (
                    fact_key, financial_year, period_start, period_end,
                    period_granularity, measure_type, accounting_basis,
                    estimate_status, amount_aud, unit, currency,
                    source_document_id, source_locator_json, retrieved_at,
                    publication_date, source_budget_year,
                    column_header_original, quality_status, view_family, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'AUD', 'AUD', ?, ?,
                          datetime('now'), ?, ?, ?, 'validated', 'qld_myfer', ?)
                """,
                (
                    fact["fact_key"], fact["financial_year"], fact["period_start"],
                    fact["period_end"], fact["period_granularity"],
                    fact["measure_type"], fact["accounting_basis"],
                    fact["estimate_status"], fact["amount_aud"], doc_id,
                    locator_json, fact["publication_date"],
                    fact["source_budget_year"], fact["column_header_original"],
                    f"MYFER {fact['flow_or_stock']}; revised estimate; isolated from audited RSF actuals.",
                ),
            )
            conn.execute(
                "INSERT INTO fact_nodes (fact_id, node_id, dimension_role) VALUES (?, ?, 'primary')",
                (cur.lastrowid, node_ids[fact["measure_type"]]),
            )
        if citation_updates:
            conn.executemany(
                "UPDATE facts SET source_locator_json = ? WHERE id = ?",
                citation_updates,
            )
        conn.commit()

    if quarantine:
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        with quarantine_path.open("w", encoding="utf-8") as handle:
            for item in quarantine:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    elif apply and quarantine_path.exists():
        quarantine_path.unlink()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Explicit no-op; the default mode.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    if args.apply:
        migrate(args.db)
    conn = sqlite3.connect(str(args.db))
    try:
        result = run(conn, apply=args.apply)
    finally:
        conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

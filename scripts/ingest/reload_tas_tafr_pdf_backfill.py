#!/usr/bin/env python3
"""Load 3 editions of the Tasmanian Treasurer's Annual Financial
Report (TAFR) PDF into data/facts.db (PDF/OCR-focused milestone - Task
5/6).

Reads scripts/ingest/extractors/tas_tafr_pdf_backfill.py's extraction,
classifies every row against the declarative semantic model in
config/measure-semantics/tas_tafr_pdf_backfill.yaml, validates it, and
publishes it under one of 7 ALREADY-SHIPPED tas_ggs_* measure types/
compatibility_groups (see scripts/ingest/migrations/011_tas_ggs_key_
fiscal_measures.sql) - this is a backward EXTENSION of the tas_ggs_*
family (2010-11 to 2012-13), not a new family, and no new migration is
needed. scripts/ingest/reload_tas_ggs_key_fiscal_measures.py (the
existing, already-shipped xlsx loader) is NOT modified by this file -
a new, separate loader is built instead, mirroring the pattern already
established for VIC BPO SOCE/Admin.

A row is published only if every one of these holds:

  - its financial year and measure_type were resolved by the extractor
    (which already performed row-label matching and General-
    Government-Sector-only page/line disambiguation);
  - its estimate_status is 'budget' or 'actual' (the only two vintages
    this PDF sub-shape produces - see the semantic model's revision
    policy for why 'budget' is distinct from the xlsx's
    'revised_estimate');
  - a source cell locator and an on-disk cached copy of the source PDF
    both resolve;
  - the $ million -> AUD scale conversion is applied exactly once.

Net Operating Balance and Fiscal Balance each appear in BOTH target
tables per edition (Key Financial Indicators and Summary of Operating
Result) - both extractions resolve to the SAME fact_key, so the
existing idempotent-skip logic below (not a new mechanism) naturally
absorbs the expected duplication as a no-op on the second occurrence.

Anything that fails any of these is written to
data/staging/quarantine/tas_tafr_pdf_backfill_load_quarantine.jsonl,
never to facts.db.

Revision policy: this adapter covers financial years 2010-11 to
2012-13 - disjoint from the GGS xlsx's 2013-14-onward coverage, so no
overlap exists today. The stable fact_key below is identity-complete
(source_id + financial_year + measure_type + accounting_basis +
estimate_status + jurisdiction) and shared with the xlsx loader's own
scheme - if a future re-acquisition of either source ever produces an
overlapping year with a different amount for the same identity,
apply() below detects it explicitly (reason=amount_conflict_with_
existing_fact) and REFUSES to silently overwrite - it is quarantined
pending an explicit revision-policy decision.

Usage:
    python3 scripts/ingest/reload_tas_tafr_pdf_backfill.py --dry-run   (default)
    python3 scripts/ingest/reload_tas_tafr_pdf_backfill.py --apply
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
from tas_tafr_pdf_backfill import extract_all_editions  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
SEMANTICS_PATH = REPO_ROOT / "config" / "measure-semantics" / "tas_tafr_pdf_backfill.yaml"
QUARANTINE_PATH = REPO_ROOT / "data" / "staging" / "quarantine" / "tas_tafr_pdf_backfill_load_quarantine.jsonl"
SOURCE_ID = "tas_treasurer_annual_financial_reports"

SOURCE_DOCUMENT_META = {
    "source_key": SOURCE_ID,
    "publisher": "Tasmanian Department of Treasury and Finance",
    "title": "Tasmania General Government Key Fiscal Measures Time Series",
    "jurisdiction": "TAS",
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

    if row["estimate_status"] not in ("actual", "budget"):
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
    # explicit review rather than letting insertion order decide. This
    # also naturally absorbs the expected same-value duplication from
    # Net Operating Balance/Fiscal Balance appearing in both tables.
    to_insert: list[dict] = []
    idempotent_skips = 0
    superseded_conflicts: list[dict] = []
    seen_fact_keys: dict[str, float] = {}
    for fact in prepared:
        if fact["fact_key"] in seen_fact_keys:
            if abs(seen_fact_keys[fact["fact_key"]] - fact["amount_aud"]) < 0.01:
                idempotent_skips += 1
                continue
            superseded_conflicts.append(
                {
                    "reason": "amount_conflict_within_same_load",
                    "fact_key": fact["fact_key"],
                    "first_amount_aud": seen_fact_keys[fact["fact_key"]],
                    "second_amount_aud": fact["amount_aud"],
                }
            )
            continue
        seen_fact_keys[fact["fact_key"]] = fact["amount_aud"]

        existing = conn.execute(
            "SELECT id, amount_aud FROM facts WHERE fact_key = ?", (fact["fact_key"],)
        ).fetchone()
        if existing is None:
            to_insert.append(fact)
            continue
        existing_amount = existing[1]
        if existing_amount is not None and abs(float(existing_amount) - float(fact["amount_aud"])) < 0.01:
            idempotent_skips += 1
            continue
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
        "facts_already_present_idempotent_skip": idempotent_skips,
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

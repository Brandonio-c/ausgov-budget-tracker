#!/usr/bin/env python3
"""Upsert publishable facts and quarantine incomplete rows into facts.db."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from canonical_lineage import canonical_dataset_for_source
from duckdb_etl import build_fact_key
from validate import RowDecision

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_source_document(conn: sqlite3.Connection, mapping: dict[str, Any]) -> int:
    source_key = mapping["source_id"]
    row = conn.execute(
        "SELECT id FROM source_documents WHERE source_key = ?", (source_key,)
    ).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO source_documents
            (source_key, publisher, title, jurisdiction, government_level,
             source_family, landing_url, canonical_resource_url, native_unit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_key,
            mapping.get("publisher", source_key),
            mapping.get("title", source_key),
            mapping.get("jurisdiction", "unknown"),
            mapping.get("government_level", "federal"),
            mapping.get("source_family", "unknown"),
            mapping.get("attribution", {}).get("landing_url"),
            mapping.get("attribution", {}).get("original_resource_url"),
            mapping.get("native_unit"),
        ),
    )
    return int(cur.lastrowid)


def ensure_retrieval(
    conn: sqlite3.Connection,
    source_document_id: int,
    row: dict[str, Any],
) -> int:
    sha = row["_sha256"]
    existing = conn.execute(
        """
        SELECT id FROM source_retrievals
        WHERE source_document_id = ? AND sha256 = ?
        """,
        (source_document_id, sha),
    ).fetchone()
    if existing:
        return int(existing["id"])
    cur = conn.execute(
        """
        INSERT INTO source_retrievals
            (source_document_id, retrieved_at, resolved_url, http_status,
             content_type, byte_size, sha256, local_path, retrieval_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_document_id,
            row["_retrieved_at"],
            row.get("original_resource_url") or row["_local_path"],
            200,
            "text/csv",
            Path(row["_cached_copy_path"]).stat().st_size
            if Path(row["_cached_copy_path"]).is_file()
            else None,
            sha,
            row["_cached_copy_path"],
            "ok",
        ),
    )
    return int(cur.lastrowid)


def ensure_node(
    conn: sqlite3.Connection,
    mapping: dict[str, Any],
    row: dict[str, Any],
    source_document_id: int,
) -> int:
    name = str(row.get("node_name") or row.get("category")).strip()
    canonical_key = f"{mapping['source_id']}|node|{name}"
    existing = conn.execute(
        "SELECT id FROM nodes WHERE canonical_key = ?", (canonical_key,)
    ).fetchone()
    if existing:
        return int(existing["id"])
    locator = json.dumps({"locator": row.get("locator")})
    cur = conn.execute(
        """
        INSERT INTO nodes
            (canonical_key, node_type, name, jurisdiction, government_level,
             source_document_id, source_locator_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            canonical_key,
            "category",
            name,
            mapping.get("jurisdiction", "unknown"),
            mapping.get("government_level", "federal"),
            source_document_id,
            locator,
        ),
    )
    return int(cur.lastrowid)


def upsert_fact(
    conn: sqlite3.Connection,
    mapping: dict[str, Any],
    decision: RowDecision,
    source_document_id: int,
    retrieval_id: int,
    node_id: int,
) -> str:
    row = decision.row
    fact_key = build_fact_key(mapping, row)
    locator_payload = {
        "locator": row.get("locator"),
        "landing_url": row.get("landing_url"),
        "original_resource_url": row.get("original_resource_url"),
        "cached_copy_path": row.get("_cached_copy_path"),
    }
    def _jsonable(value: Any) -> Any:
        if value is None or value == "":
            return None
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                return str(value)
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    for key in (
        "observation_date",
        "publication_date",
        "valuation_basis",
        "amount_granularity",
        "isin",
        "maturity_date",
        "coupon",
        "authority",
        "numerator_fact_key",
        "denominator_fact_key",
    ):
        if row.get(key) not in (None, ""):
            locator_payload[key] = _jsonable(row[key])
    locator_json = json.dumps(locator_payload, sort_keys=True)
    amount = float(row["amount_aud"])
    observation_date = _jsonable(
        row.get("observation_date") or row.get("_observation_date")
    )
    publication_date = _jsonable(
        row.get("publication_date") or row.get("_publication_date")
    )
    valuation_basis = row.get("valuation_basis") or mapping.get("valuation_basis")
    amount_granularity = row.get("amount_granularity") or mapping.get("amount_granularity")
    canonical_dataset_id = canonical_dataset_for_source(mapping["source_id"])
    conn.execute(
        """
        INSERT INTO facts (
            fact_key, financial_year, period_granularity, measure_type,
            accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_retrieval_id, source_locator_json,
            retrieved_at, observation_date, publication_date,
            valuation_basis, amount_granularity, canonical_dataset_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'AUD', 'AUD', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fact_key) DO UPDATE SET
            amount_aud = excluded.amount_aud,
            source_retrieval_id = excluded.source_retrieval_id,
            source_locator_json = excluded.source_locator_json,
            retrieved_at = excluded.retrieved_at,
            observation_date = COALESCE(excluded.observation_date, facts.observation_date),
            publication_date = COALESCE(excluded.publication_date, facts.publication_date),
            valuation_basis = COALESCE(excluded.valuation_basis, facts.valuation_basis),
            amount_granularity = COALESCE(excluded.amount_granularity, facts.amount_granularity),
            canonical_dataset_id = excluded.canonical_dataset_id
        """,
        (
            fact_key,
            str(row["financial_year"]).strip(),
            mapping["period_granularity"],
            mapping["measure_type"],
            mapping["accounting_basis"],
            row.get("_estimate_status") or mapping["estimate_status"],
            amount,
            source_document_id,
            retrieval_id,
            locator_json,
            row["_retrieved_at"],
            observation_date,
            publication_date,
            valuation_basis,
            amount_granularity,
            canonical_dataset_id,
        ),
    )
    fact_id = conn.execute(
        "SELECT id FROM facts WHERE fact_key = ?", (fact_key,)
    ).fetchone()["id"]
    conn.execute(
        """
        INSERT OR IGNORE INTO fact_nodes (fact_id, node_id, dimension_role)
        VALUES (?, ?, 'primary')
        """,
        (fact_id, node_id),
    )
    # clear quarantine twin if previously incomplete
    conn.execute(
        "DELETE FROM facts_pending_attribution WHERE fact_key = ?", (fact_key,)
    )
    return fact_key


def quarantine_fact(
    conn: sqlite3.Connection,
    mapping: dict[str, Any],
    decision: RowDecision,
    source_document_id: int | None,
) -> str:
    row = decision.row
    fact_key = build_fact_key(mapping, row)
    locator_json = json.dumps(
        {
            "locator": row.get("locator"),
            "landing_url": row.get("landing_url"),
            "original_resource_url": row.get("original_resource_url"),
            "cached_copy_path": row.get("_cached_copy_path"),
        },
        sort_keys=True,
    )
    amount = None
    try:
        amount = float(row["amount_aud"]) if row.get("amount_aud") is not None else None
    except (TypeError, ValueError):
        amount = None
    if amount is None:
        amount = 0.0  # satisfy CHECK; reason captures real failure
    conn.execute(
        """
        INSERT INTO facts_pending_attribution (
            fact_key, financial_year, period_granularity, measure_type,
            accounting_basis, estimate_status, amount_aud, unit, currency,
            source_document_id, source_locator_json, retrieved_at,
            is_publishable, quarantine_reason, quarantined_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'AUD', 'AUD', ?, ?, ?, 0, ?, ?)
        ON CONFLICT(fact_key) DO UPDATE SET
            quarantine_reason = excluded.quarantine_reason,
            quarantined_at = excluded.quarantined_at,
            source_locator_json = excluded.source_locator_json,
            amount_aud = excluded.amount_aud
        """,
        (
            fact_key,
            str(row.get("financial_year") or "0000-00"),
            mapping.get("period_granularity", "financial_year"),
            mapping["measure_type"],
            mapping["accounting_basis"],
            row.get("_estimate_status") or mapping["estimate_status"],
            amount,
            source_document_id,
            locator_json,
            row.get("_retrieved_at") or _utc_now(),
            decision.quarantine_reason or "unknown",
            _utc_now(),
        ),
    )
    return fact_key


def load_decisions(
    mapping: dict[str, Any],
    decisions: list[RowDecision],
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    conn = _connect(db_path)
    published = 0
    quarantined = 0
    replaced_existing = 0
    try:
        source_document_id = ensure_source_document(conn, mapping)
        if mapping.get("replace_on_reload"):
            # fact_key includes derived label text, which legitimately changes
            # as extractor logic improves (e.g. a bug-fixed label or year
            # resolution) - without this, a fact from a fixed extraction run
            # gets a different fact_key than its pre-fix predecessor and the
            # old, wrong row is never overwritten, just silently duplicated
            # alongside the corrected one. Opt-in only: every other mapping's
            # behaviour (ON CONFLICT upsert against the existing fact_key) is
            # unchanged. facts.fact_nodes/lineage_edges cascade on delete.
            cur = conn.execute(
                "DELETE FROM facts WHERE source_document_id = ?", (source_document_id,)
            )
            replaced_existing = cur.rowcount
            conn.execute(
                "DELETE FROM facts_pending_attribution WHERE source_document_id = ?",
                (source_document_id,),
            )
        for decision in decisions:
            row = decision.row
            if decision.publishable:
                retrieval_id = ensure_retrieval(conn, source_document_id, row)
                node_id = ensure_node(conn, mapping, row, source_document_id)
                upsert_fact(
                    conn, mapping, decision, source_document_id, retrieval_id, node_id
                )
                published += 1
            else:
                quarantine_fact(conn, mapping, decision, source_document_id)
                quarantined += 1
        conn.commit()
    finally:
        conn.close()
    return {
        "published": published,
        "quarantined": quarantined,
        "replaced_existing": replaced_existing,
    }

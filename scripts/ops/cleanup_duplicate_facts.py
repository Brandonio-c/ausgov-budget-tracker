#!/usr/bin/env python3
"""Idempotent cleanup for confirmed true-duplicate facts (Task 4 of the
database-hygiene-and-CI-hardening milestone).

Resolves ONLY the specific fact pairs declared in
config/audit/confirmed_duplicate_deletions.yaml - each one individually
investigated against its raw source rows (see
ops/reports/duplicate-fact-investigation-*.md). This is deliberately not
a generic "delete every duplicate_facts() hit" tool: a new or unreviewed
duplicate candidate is left untouched (and still reported as a hard
failure by scripts/ops/task9_sql_integrity_checks.py) until it goes
through the same investigation and gets its own declarative entry.

Usage:
    python3 scripts/ops/cleanup_duplicate_facts.py --dry-run   (default)
    python3 scripts/ops/cleanup_duplicate_facts.py --apply
    python3 scripts/ops/cleanup_duplicate_facts.py --apply --report path.json

Safety checks performed for every entry, live against the database,
before any deletion:
  - the fact_key to retain still exists;
  - the fact_key to delete still exists (if not: already resolved, a
    no-op - this is what makes a second run idempotent);
  - both facts share the entry's declared node/financial_year/
    measure_type/estimate_status/amount identity (guards against a
    reload or edit silently invalidating a stale config entry);
  - the fact to delete has zero lineage_edges references (as parent or
    child) and zero reconciliations references (as either side) - a fact
    with any such reference is never deleted by this script, even if
    listed, because that would risk losing unique lineage or breaking a
    reconciliation.
Only if every check passes is the fact (and its fact_nodes rows) deleted,
inside a single transaction, in --apply mode.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "facts.db"
CONFIG_PATH = REPO_ROOT / "config" / "audit" / "confirmed_duplicate_deletions.yaml"


def load_confirmed_deletions(path: Path = CONFIG_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("confirmed_duplicate_deletions") or [])


def _fact_identity(conn: sqlite3.Connection, fact_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT f.id, f.financial_year, f.measure_type, f.estimate_status,
               f.amount_aud, fn.node_id, n.name AS node_path, sd.source_key
        FROM facts f
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        JOIN source_documents sd ON sd.id = f.source_document_id
        WHERE f.fact_key = ?
        """,
        (fact_key,),
    ).fetchone()
    if row is None:
        return None
    return {
        "fact_id": row[0],
        "financial_year": row[1],
        "measure_type": row[2],
        "estimate_status": row[3],
        "amount_aud": row[4],
        "node_id": row[5],
        "node_path": row[6],
        "source_key": row[7],
    }


def _reference_counts(conn: sqlite3.Connection, fact_id: int) -> dict[str, int]:
    return {
        "lineage_as_parent": conn.execute(
            "SELECT COUNT(*) FROM lineage_edges WHERE parent_fact_id = ?", (fact_id,)
        ).fetchone()[0],
        "lineage_as_child": conn.execute(
            "SELECT COUNT(*) FROM lineage_edges WHERE child_fact_id = ?", (fact_id,)
        ).fetchone()[0],
        "reconciliation_left": conn.execute(
            "SELECT COUNT(*) FROM reconciliations WHERE left_fact_id = ?", (fact_id,)
        ).fetchone()[0],
        "reconciliation_right": conn.execute(
            "SELECT COUNT(*) FROM reconciliations WHERE right_fact_id = ?", (fact_id,)
        ).fetchone()[0],
    }


def plan(conn: sqlite3.Connection, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for entry in entries:
        outcome: dict[str, Any] = {
            "source_key": entry["source_key"],
            "node_path": entry["node_path"],
            "financial_year": entry["financial_year"],
            "retain_fact_key": entry["retain_fact_key"],
            "delete_fact_key": entry["delete_fact_key"],
        }
        delete_identity = _fact_identity(conn, entry["delete_fact_key"])
        if delete_identity is None:
            outcome["status"] = "already_resolved"
            outcome["detail"] = "delete_fact_key no longer present - nothing to do"
            results.append(outcome)
            continue

        retain_identity = _fact_identity(conn, entry["retain_fact_key"])
        if retain_identity is None:
            outcome["status"] = "error"
            outcome["detail"] = (
                "retain_fact_key not found in the database - refusing to delete "
                "the other fact without a surviving retained record"
            )
            results.append(outcome)
            continue

        expected = (
            str(entry["financial_year"]),
            str(entry["measure_type"]),
            str(entry["estimate_status"]),
            float(entry["amount_aud"]),
            str(entry["node_path"]),
            str(entry["source_key"]),
        )
        for identity, label in ((delete_identity, "delete"), (retain_identity, "retain")):
            live = (
                str(identity["financial_year"]),
                str(identity["measure_type"]),
                str(identity["estimate_status"]),
                float(identity["amount_aud"]),
                str(identity["node_path"]),
                str(identity["source_key"]),
            )
            if live != expected:
                outcome["status"] = "error"
                outcome["detail"] = (
                    f"{label} fact's live identity {live} does not match the "
                    f"config entry's declared identity {expected} - config is "
                    "stale relative to the database, refusing to act"
                )
                results.append(outcome)
                break
        else:
            if retain_identity["node_id"] != delete_identity["node_id"]:
                outcome["status"] = "error"
                outcome["detail"] = (
                    "retain and delete facts are attached to different node_ids "
                    "- refusing to delete (would risk orphaning the node)"
                )
                results.append(outcome)
                continue

            refs = _reference_counts(conn, delete_identity["fact_id"])
            if any(refs.values()):
                outcome["status"] = "error"
                outcome["detail"] = f"delete fact has references, refusing to delete: {refs}"
                results.append(outcome)
                continue

            outcome["status"] = "would_delete"
            outcome["delete_fact_id"] = delete_identity["fact_id"]
            outcome["retain_fact_id"] = retain_identity["fact_id"]
            outcome["shared_node_id"] = retain_identity["node_id"]
            results.append(outcome)
    return results


def apply(conn: sqlite3.Connection, planned: list[dict[str, Any]]) -> list[dict[str, Any]]:
    applied = []
    for outcome in planned:
        if outcome["status"] != "would_delete":
            applied.append(outcome)
            continue
        fact_id = outcome["delete_fact_id"]
        conn.execute("DELETE FROM fact_nodes WHERE fact_id = ?", (fact_id,))
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        done = dict(outcome)
        done["status"] = "deleted"
        applied.append(done)
    conn.commit()
    return applied


def write_reports(results: list[dict[str, Any]], report_path: Path, apply_mode: bool) -> None:
    json_path = report_path.with_suffix(".json")
    md_path = report_path.with_suffix(".md")
    payload = {"mode": "apply" if apply_mode else "dry_run", "entries": results}
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Duplicate-fact cleanup report",
        "",
        f"Mode: **{'apply' if apply_mode else 'dry-run'}**",
        "",
        "| source_key | node_path | financial_year | status | detail |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        detail = r.get("detail", "")
        if r["status"] == "would_delete":
            detail = f"would delete fact_id {r['delete_fact_id']}, retain {r['retain_fact_id']}"
        elif r["status"] == "deleted":
            detail = f"deleted fact_id {r['delete_fact_id']}, retained {r['retain_fact_id']}"
        lines.append(
            f"| {r['source_key']} | {r['node_path']} | {r['financial_year']} | "
            f"{r['status']} | {detail} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="default: plan only, no writes")
    mode.add_argument("--apply", action="store_true", help="perform the confirmed deletions")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="base path for the .json/.md report (default: print summary only)",
    )
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args(argv)

    apply_mode = bool(args.apply)

    conn = sqlite3.connect(str(args.db))
    entries = load_confirmed_deletions(args.config)
    planned = plan(conn, entries)

    if apply_mode:
        results = apply(conn, planned)
    else:
        results = planned
    conn.close()

    if args.report:
        write_reports(results, args.report, apply_mode)

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(json.dumps({"mode": "apply" if apply_mode else "dry_run", "counts": counts}, indent=2))
    return 1 if counts.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())

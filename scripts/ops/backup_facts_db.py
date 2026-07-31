#!/usr/bin/env python3
"""Safe, consistent backup of data/facts.db using the SQLite backup API.

Uses sqlite3's connection.backup() (page-level, transactionally consistent
copy) rather than a naive file copy, so it produces a correct snapshot even
while the production read-only API server has the database open. Stores the
backup outside the Git-tracked repo tree and records baseline counts + hashes
alongside it.

Usage:
    python scripts/ops/backup_facts_db.py [--db PATH] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
DEFAULT_OUT_DIR = Path("/home/vibe-server/backups/ausgov-budget-tracker")

COUNT_QUERIES = {
    "fact_count": "SELECT COUNT(*) FROM facts",
    "source_document_count": "SELECT COUNT(*) FROM source_documents",
    "node_count": "SELECT COUNT(*) FROM nodes",
    "edge_count": "SELECT COUNT(*) FROM node_edges",
    "lineage_edge_count": "SELECT COUNT(*) FROM lineage_edges",
    "quarantine_count": "SELECT COUNT(*) FROM facts_pending_attribution",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        counts = {}
        for key, query in COUNT_QUERIES.items():
            try:
                counts[key] = conn.execute(query).fetchone()[0]
            except sqlite3.OperationalError as error:
                counts[key] = f"error: {error}"
        return counts
    finally:
        conn.close()


def backup(db_path: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = out_dir / f"facts-{stamp}.db"

    counts_before = record_counts(db_path)

    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    dest = sqlite3.connect(str(backup_path))
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    db_sha256 = sha256_file(db_path)
    backup_sha256 = sha256_file(backup_path)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_db_path": str(db_path),
        "backup_path": str(backup_path),
        "source_db_sha256": db_sha256,
        "backup_sha256": backup_sha256,
        "backup_matches_source_bytes": db_sha256 == backup_sha256,
        "counts": counts_before,
        "source_db_size_bytes": db_path.stat().st_size,
        "backup_size_bytes": backup_path.stat().st_size,
    }
    report_path = out_dir / f"facts-{stamp}.backup-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not args.db.is_file():
        print(f"no such database: {args.db}")
        return 1

    report = backup(args.db, args.out_dir)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run one mapping through extract → validate → load."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from duckdb_etl import extract_rows, load_mapping  # noqa: E402
from load_facts import load_decisions  # noqa: E402
from schema_migrate import migrate  # noqa: E402
from validate import validate_batch  # noqa: E402

DEFAULT_DB = REPO_ROOT / "data" / "facts.db"


def run_mapping(mapping_path: Path, db_path: Path = DEFAULT_DB) -> dict:
    migrate(db_path)
    mapping = load_mapping(mapping_path)
    rows = extract_rows(mapping, REPO_ROOT)
    decisions = validate_batch(mapping, rows)
    stats = load_decisions(mapping, decisions, db_path)
    return {
        "source_id": mapping["source_id"],
        "input_rows": len(rows),
        **stats,
        "gate6_quarantine": sum(
            1
            for d in decisions
            if (not d.publishable)
            and d.quarantine_reason
            and "Gate 6" in d.quarantine_reason
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest one mapping YAML")
    parser.add_argument("mapping", type=Path, help="Path to mapping YAML")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    summary = run_mapping(args.mapping, args.db)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

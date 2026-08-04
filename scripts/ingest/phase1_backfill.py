#!/usr/bin/env python3
"""Export Phase 1 spending.db rows to CSV + ingest into facts.db (read-only spending)."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from reconcile import reconcile_source  # noqa: E402
from run import run_mapping  # noqa: E402

SPENDING_DB = REPO_ROOT / "data" / "processed" / "spending.db"
EXPORT_DIR = REPO_ROOT / "data" / "staging" / "phase1"
MAPPINGS = REPO_ROOT / "config" / "mappings"

SOURCE_META = {
    "federal_expense_by_function": {
        "level": "federal",
        "jurisdiction": "Commonwealth",
        "landing_url": "https://data.gov.au/data/dataset/2b690e28-8239-48c6-a71d-2658f37d51d7",
        "cached_copy_path": "data/raw/federal/federal_expense_by_function/federal_expense_by_function.xlsx",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "actual",
        "government_level": "federal",
        "publisher": "Department of Finance",
        "title": "GGS Note 3 Function Statement (Phase 1 backfill)",
        "source_family": "federal_actuals",
    },
    "sa_gfs_by_function": {
        "level": "state",
        "jurisdiction": "SA",
        "landing_url": "https://data.sa.gov.au/data/dataset/e77f59d9-3df9-43ad-acf0-b7f8928ee827",
        "cached_copy_path": "data/raw/state/sa_gfs_by_function/sa_gfs_by_function.xlsx",
        "measure_type": "gfs_expense",
        "accounting_basis": "gfs",
        "estimate_status": "actual",
        "government_level": "state",
        "publisher": "Government of South Australia",
        "title": "SA GFS expenses by function (Phase 1 backfill)",
        "source_family": "state_actuals",
    },
    "vic_local_govt_financial": {
        "level": "local",
        "jurisdiction": "VIC",
        "landing_url": "https://www.audit.vic.gov.au/report/results-2018-19-audits-local-government",
        "cached_copy_path": "data/raw/local/vic_local_govt_financial/vic_local_govt_financial.xlsx",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "audited_actual",
        "government_level": "local",
        "publisher": "Victorian Auditor-General's Office",
        "title": "VIC local government financial dashboard (Phase 1 backfill)",
        "source_family": "local_actuals",
    },
}


def _infer_source_id(level: str, jurisdiction: str) -> str | None:
    for sid, meta in SOURCE_META.items():
        if meta["level"] != level:
            continue
        if meta["jurisdiction"] == jurisdiction:
            return sid
        # VIC local rows use "VIC — <council>" jurisdiction strings
        if meta["jurisdiction"] == "VIC" and jurisdiction.startswith("VIC"):
            return sid
    return None


def _locator_from_context(ctx: dict) -> str:
    if not ctx:
        return ""
    highlight = ctx.get("highlight") or {}
    parts = []
    if ctx.get("sheet_name"):
        parts.append(f"sheet:{ctx['sheet_name']}")
    if highlight.get("cell"):
        parts.append(f"cell:{highlight['cell']}")
    elif ctx.get("cell_range"):
        parts.append(f"range:{ctx['cell_range']}")
    if ctx.get("unit"):
        parts.append(f"unit:{ctx['unit']}")
    return " | ".join(parts) if parts else json.dumps(ctx, sort_keys=True)[:240]


def export_csvs(spending_db: Path = SPENDING_DB, export_dir: Path = EXPORT_DIR) -> dict[str, Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(spending_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM spending").fetchall()
    conn.close()

    buckets: dict[str, list[dict]] = {k: [] for k in SOURCE_META}
    skipped = 0
    for r in rows:
        sid = _infer_source_id(r["level_of_government"], r["jurisdiction"])
        if not sid:
            skipped += 1
            continue
        ctx = {}
        try:
            ctx = json.loads(r["source_context_json"] or "{}")
        except json.JSONDecodeError:
            ctx = {}
        locator = _locator_from_context(ctx)
        node = r["category"] or "Uncategorized"
        if r["subcategory"]:
            node = f"{node} / {r['subcategory']}"
        if r["department"]:
            node = f"{node} / {r['department']}"
        buckets[sid].append(
            {
                "fy": r["financial_year"],
                "amount": r["amount_aud"],
                "category": node,
                "locator": locator,
                "landing_url": SOURCE_META[sid]["landing_url"],
                "resource_url": r["source_url"],
                "legacy_id": r["id"],
            }
        )

    out_paths: dict[str, Path] = {}
    fieldnames = [
        "fy",
        "amount",
        "category",
        "locator",
        "landing_url",
        "resource_url",
        "legacy_id",
    ]
    for sid, items in buckets.items():
        path = export_dir / f"{sid}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(items)
        out_paths[sid] = path
        print(f"exported {sid}: {len(items)} rows -> {path}")
    if skipped:
        print(f"skipped_unmapped={skipped}")
    return out_paths


def write_mapping_yamls(export_paths: dict[str, Path]) -> list[Path]:
    written = []
    for sid, meta in SOURCE_META.items():
        rel_csv = export_paths[sid].relative_to(REPO_ROOT).as_posix()
        import yaml

        doc = {
            "source_id": sid,
            "title": meta["title"],
            "publisher": meta["publisher"],
            "jurisdiction": meta["jurisdiction"],
            "government_level": meta["government_level"],
            "source_family": meta["source_family"],
            "measure_type": meta["measure_type"],
            "accounting_basis": meta["accounting_basis"],
            "estimate_status": meta["estimate_status"],
            "period_granularity": "financial_year",
            "input": {"path": rel_csv, "format": "csv"},
            "columns": {
                "financial_year": "fy",
                "amount_aud": "amount",
                "node_name": "category",
                "locator": "locator",
                "landing_url": "landing_url",
                "original_resource_url": "resource_url",
                "legacy_id": "legacy_id",
            },
            "attribution": {
                "landing_url_column": "landing_url",
                "original_resource_url_column": "resource_url",
                "cached_copy_path": meta["cached_copy_path"],
            },
            "fact_key_template": (
                "{source_id}|{financial_year}|{node_name}|{measure_type}|"
                "{estimate_status}|{legacy_id}"
            ),
        }
        path = MAPPINGS / f"{sid}.yaml"
        path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spending-db", type=Path, default=SPENDING_DB)
    parser.add_argument("--facts-db", type=Path, default=REPO_ROOT / "data" / "facts.db")
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args(argv)

    paths = export_csvs(args.spending_db)
    maps = write_mapping_yamls(paths)
    if args.export_only:
        return 0

    summaries = []
    for mpath in maps:
        summaries.append(run_mapping(mpath, args.facts_db))

    recon = []
    for sid, meta in SOURCE_META.items():
        kwargs = {
            "facts_db": args.facts_db,
            "spending_db": args.spending_db,
        }
        if sid == "vic_local_govt_financial":
            kwargs["jurisdiction_prefix"] = "VIC"
        else:
            kwargs["jurisdiction"] = meta["jurisdiction"]
        recon.extend(reconcile_source(sid, **kwargs))

    # attribution completeness
    conn = sqlite3.connect(str(args.facts_db))
    pub = conn.execute(
        """
        SELECT COUNT(*) FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        WHERE d.source_key IN (?, ?, ?)
        """,
        tuple(SOURCE_META.keys()),
    ).fetchone()[0]
    pend = conn.execute(
        """
        SELECT COUNT(*) FROM facts_pending_attribution
        WHERE fact_key LIKE 'federal_expense_by_function|%'
           OR fact_key LIKE 'sa_gfs_by_function|%'
           OR fact_key LIKE 'vic_local_govt_financial|%'
        """
    ).fetchone()[0]
    conn.close()
    print(json.dumps({"ingest": summaries, "reconcile_count": len(recon), "published": pub, "quarantined": pend}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

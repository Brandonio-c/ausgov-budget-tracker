#!/usr/bin/env python3
"""Task 2 of the MFS-aggregates milestone: inventory every acquired Federal
Monthly Financial Statements workbook and identify its distinct
workbook/table shape. Read-only - inspects data/raw/federal/federal_mfs_*
(and the legacy, pre-split federal_monthly_financial_statements bulk
acquisition) directly; writes nothing to data/facts.db.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_FEDERAL = REPO_ROOT / "data" / "raw" / "federal"

# Maps each acquired source_id to the workbook "shape" it represents, per
# the mission's Task 2 required taxonomy.
SHAPE_BY_SOURCE_ID = {
    "federal_mfs_aggregates": "Aggregates",
    "federal_mfs_operating_statement": "Operating Statement",
    "federal_mfs_balance_sheet": "Balance Sheet",
    "federal_mfs_note3_function": "Notes or supplementary schedules (functional expense breakdown)",
    "federal_mfs_tax_notes_1_2": "Notes or supplementary schedules (taxation revenue detail)",
    "federal_mfs_monthly_profiles": "Monthly Profiles",
    # Legacy bulk acquisition, pre-dating the per-file split above. Kept only
    # to identify the one shape (Cash Flow Statement) not yet re-acquired
    # under its own dedicated source_id, and to document that the rest of
    # its assets are superseded duplicates of the sources above.
    "federal_monthly_financial_statements": "legacy bulk acquisition (pre-split)",
}

EXTRACTOR_SUPPORT = {
    "federal_mfs_aggregates": "supported (scripts/ingest/extractors/mfs_aggregates.py) - this milestone's load target",
    "federal_mfs_operating_statement": "not supported - no extractor; out of scope for this milestone's load",
    "federal_mfs_balance_sheet": "not supported - no extractor; out of scope for this milestone's load",
    "federal_mfs_note3_function": "not supported - no extractor; out of scope for this milestone's load",
    "federal_mfs_tax_notes_1_2": "not supported - no extractor; out of scope for this milestone's load",
    "federal_mfs_monthly_profiles": "not supported - no extractor; out of scope for this milestone's load",
    "federal_monthly_financial_statements": "not supported - superseded by the per-file sources above (except cash flow statement, which has no dedicated source_id yet); the 288-fact stray preload from this source was removed in Task 1",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_snapshot_dir(source_dir: Path) -> Path | None:
    latest = source_dir / "latest.json"
    if not latest.is_file():
        return None
    data = json.loads(latest.read_text(encoding="utf-8"))
    assets = data.get("assets") or []
    if not assets:
        return None
    stored = assets[0].get("stored_path")
    if not stored:
        return None
    # stored_path is relative to data/ (e.g. "raw/federal/.../files/x.xlsx")
    return (REPO_ROOT / "data" / stored).parent.parent


def inspect_workbook(path: Path) -> list[dict]:
    """One row per sheet: shape, header sample, financial-year/month guess."""
    rows = []
    try:
        xl = pd.ExcelFile(path)
    except Exception as exc:
        return [{"sheet": None, "error": str(exc)}]
    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet, header=None, nrows=5)
        except Exception as exc:
            rows.append({"sheet": sheet, "error": str(exc)})
            continue
        n_rows_full = None
        try:
            full = xl.parse(sheet, header=None)
            n_rows_full = full.shape[0]
        except Exception:
            pass
        header_row_1 = [str(v) for v in (df.iloc[1].tolist() if df.shape[0] > 1 else [])]
        title_row_0 = [str(v) for v in (df.iloc[0].tolist() if df.shape[0] > 0 else [])]
        rows.append(
            {
                "sheet": sheet,
                "n_rows": n_rows_full if n_rows_full is not None else df.shape[0],
                "n_cols": df.shape[1],
                "title_row_sample": " | ".join(t for t in title_row_0 if t and t != "nan")[:200],
                "header_row_sample": " | ".join(h for h in header_row_1 if h and h != "nan")[:300],
            }
        )
    return rows


def main() -> int:
    out_rows = []
    for source_id in SHAPE_BY_SOURCE_ID:
        source_dir = RAW_FEDERAL / source_id
        if not source_dir.is_dir():
            continue
        latest = json.loads((source_dir / "latest.json").read_text(encoding="utf-8"))
        for asset in latest.get("assets") or []:
            stored = asset.get("stored_path")
            if not stored:
                continue
            file_path = REPO_ROOT / "data" / stored
            if not file_path.is_file():
                out_rows.append(
                    {
                        "source_id": source_id,
                        "shape": SHAPE_BY_SOURCE_ID[source_id],
                        "source_file": str(stored),
                        "error": "file_missing_on_disk",
                    }
                )
                continue
            digest = sha256_file(file_path)
            sheets = inspect_workbook(file_path)
            for sheet_row in sheets:
                out_rows.append(
                    {
                        "source_id": source_id,
                        "shape": SHAPE_BY_SOURCE_ID[source_id],
                        "source_file": str(stored),
                        "source_sha256": digest,
                        "original_filename": asset.get("original_filename"),
                        "landing_url": asset.get("landing_url") or asset.get("final_url"),
                        "extractor_support_status": EXTRACTOR_SUPPORT[source_id],
                        **sheet_row,
                    }
                )
    fieldnames = [
        "source_id", "shape", "source_file", "source_sha256", "original_filename",
        "landing_url", "extractor_support_status", "sheet", "n_rows", "n_cols",
        "title_row_sample", "header_row_sample", "error",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in out_rows:
        writer.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

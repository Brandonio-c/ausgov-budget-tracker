from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from duckdb_etl import extract_rows  # noqa: E402


def test_extract_rows_assigns_cached_copy_by_financial_year(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["fy", "amount", "category"])
        writer.writeheader()
        writer.writerow({"fy": "2022-23", "amount": "1", "category": "One"})
        writer.writerow({"fy": "2023-24", "amount": "2", "category": "Two"})
    first = tmp_path / "2022-23.pdf"
    second = tmp_path / "2023-24.pdf"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    mapping = {
        "source_id": "test",
        "measure_type": "actual_accrual_expense",
        "accounting_basis": "accrual",
        "estimate_status": "audited_actual",
        "period_granularity": "financial_year",
        "input": {"path": str(source), "format": "csv"},
        "columns": {
            "financial_year": "fy",
            "amount_aud": "amount",
            "node_name": "category",
        },
        "attribution": {
            "cached_copy_path_by_financial_year": {
                "2022-23": str(first),
                "2023-24": str(second),
            }
        },
    }
    rows = extract_rows(mapping, tmp_path)
    assert [Path(row["_cached_copy_path"]).name for row in rows] == [
        "2022-23.pdf",
        "2023-24.pdf",
    ]
    assert rows[0]["_sha256"] != rows[1]["_sha256"]

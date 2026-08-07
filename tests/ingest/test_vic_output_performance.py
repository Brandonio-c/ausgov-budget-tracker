from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts/ingest/extractors"))

import reload_vic_output_performance as loader  # noqa: E402
import vic_output_performance as extractor  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def test_real_workbook_selects_only_seven_cost_rows():
    rows, quarantine = extractor.extract_workbook()
    assert quarantine == []
    assert len(rows) == 14
    assert {row["estimate_status"] for row in rows} == {"actual", "budget"}
    assert {row["output_name"] for row in rows} == set(extractor.EXPECTED_SHEETS)
    assert all(row["row_label"] == "Total output cost" for row in rows)


def test_non_dollar_rows_are_not_coerced(tmp_path):
    path = tmp_path / "output.xlsx"
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet in extractor.EXPECTED_SHEETS:
        ws = workbook.create_sheet(sheet)
        ws.append(["Performance measures", "Unit of measure", "2024-25 actual", "2024-25 target"])
        ws.append(["Customer satisfaction", "per cent", 91, 80])
        ws.append(["Total output cost", "$ million", 9, 9.2])
    workbook.save(path)
    rows, quarantine = extractor.extract_workbook(path)
    assert quarantine == []
    assert len(rows) == 14
    assert not any(row["row_label"] == "Customer satisfaction" for row in rows)


def test_scale_period_and_output_identity():
    row = extractor.extract_workbook()[0][0]
    fact, reason = loader.classify(row, loader.load_semantics())
    assert reason == ""
    assert fact["period_start"] == "2024-07-01"
    assert fact["period_end"] == "2025-06-30"
    assert fact["amount_aud"] == row["amount_million_aud"] * 1_000_000
    assert fact["output_slug"] in fact["fact_key"]


def test_loader_idempotency(tmp_path):
    db = tmp_path / "facts.db"
    migrate(db)
    conn = sqlite3.connect(db)
    first = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")
    second = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")
    assert first["facts_inserted"] == 14
    assert first["nodes_inserted"] == 7
    assert second["facts_inserted"] == 0
    assert second["nodes_inserted"] == 0
    assert second["facts_already_present_idempotent_skip"] == 14
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 14
    conn.close()

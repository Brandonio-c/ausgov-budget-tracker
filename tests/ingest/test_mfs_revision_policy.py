"""MFS revision/duplicate policy (Task 6 of the MFS-aggregates milestone).

federal_mfs_aggregates has exactly one acquired snapshot in the real
corpus (Task 2's inventory) - there is no real overlapping/revised
edition to test against. These synthetic fixtures exercise the policy
directly: reloading identical source data is a no-op (idempotent);
reloading source data whose amount for an already-loaded fact_key has
changed is refused and quarantined, never silently overwritten - the
loader must never let processing order decide which value wins.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

import load_mfs_aggregates as loader  # noqa: E402
from schema_migrate import migrate  # noqa: E402


def _write_workbook(path: Path, revenue_amount: float) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2023-24 Aggregates", None],
                [None, "ACTUAL\n2023-2024\nYTD July\n$m"],
                ["Revenue", revenue_amount],
            ]
        )
        sheet.to_excel(writer, sheet_name="2023-24", header=False, index=False)


@pytest.fixture
def fixture_db(tmp_path: Path) -> Path:
    db = tmp_path / "facts.db"
    migrate(db)
    return db


def _run_apply(monkeypatch, db_path: Path, workbook_path: Path) -> dict:
    monkeypatch.setattr(loader, "_find_latest_asset", lambda source_id: workbook_path)
    quarantine_path = workbook_path.parent / "quarantine.jsonl"
    conn = sqlite3.connect(str(db_path))
    result = loader.run(conn, apply=True, quarantine_path=quarantine_path)
    conn.close()
    result["_quarantine_path"] = quarantine_path
    return result


def test_reload_of_identical_data_is_idempotent(monkeypatch, fixture_db: Path, tmp_path: Path):
    workbook = tmp_path / "aggregates.xlsx"
    _write_workbook(workbook, 100.0)

    first = _run_apply(monkeypatch, fixture_db, workbook)
    assert first["facts_to_insert"] == 1
    assert first["revision_conflicts_quarantined"] == 0

    second = _run_apply(monkeypatch, fixture_db, workbook)
    assert second["facts_to_insert"] == 0
    assert second["facts_already_present_idempotent_skip"] == 1
    assert second["revision_conflicts_quarantined"] == 0
    assert second["nodes_inserted"] == 0

    conn = sqlite3.connect(str(fixture_db))
    n = conn.execute("SELECT COUNT(*) FROM facts WHERE measure_type = 'mfs_ytd_revenue'").fetchone()[0]
    conn.close()
    assert n == 1, "second identical load must not create a duplicate fact"


def test_reload_with_changed_amount_is_quarantined_not_silently_overwritten(
    monkeypatch, fixture_db: Path, tmp_path: Path
):
    workbook = tmp_path / "aggregates.xlsx"
    _write_workbook(workbook, 100.0)
    first = _run_apply(monkeypatch, fixture_db, workbook)
    assert first["facts_to_insert"] == 1

    # A later "edition" reports a different Revenue figure for the exact
    # same identity (financial_year=2023-24, month=July, same measure).
    revised_workbook = tmp_path / "aggregates_revised.xlsx"
    _write_workbook(revised_workbook, 250.0)
    second = _run_apply(monkeypatch, fixture_db, revised_workbook)

    assert second["facts_to_insert"] == 0
    assert second["revision_conflicts_quarantined"] == 1

    conn = sqlite3.connect(str(fixture_db))
    rows = conn.execute(
        "SELECT amount_aud FROM facts WHERE measure_type = 'mfs_ytd_revenue'"
    ).fetchall()
    conn.close()
    assert len(rows) == 1, "a conflicting revision must never create a second fact either"
    assert rows[0][0] == pytest.approx(100_000_000), (
        "the original value must be preserved - conflicting data is quarantined, never silently overwritten"
    )

    quarantine_path = second["_quarantine_path"]
    assert quarantine_path.is_file()
    lines = [json.loads(line) for line in quarantine_path.read_text(encoding="utf-8").splitlines()]
    conflict_entries = [r for r in lines if r.get("reason") == "amount_conflict_with_existing_fact"]
    assert len(conflict_entries) == 1
    assert conflict_entries[0]["existing_amount_aud"] == pytest.approx(100_000_000)
    assert conflict_entries[0]["new_amount_aud"] == pytest.approx(250_000_000)


def test_reload_with_new_additional_month_inserts_only_the_new_fact(
    monkeypatch, fixture_db: Path, tmp_path: Path
):
    """A genuinely new reporting month (not a revision of an existing one)
    must be inserted cleanly, without disturbing the already-loaded fact."""
    workbook = tmp_path / "aggregates.xlsx"
    _write_workbook(workbook, 100.0)
    first = _run_apply(monkeypatch, fixture_db, workbook)
    assert first["facts_to_insert"] == 1

    workbook2 = tmp_path / "aggregates2.xlsx"
    with pd.ExcelWriter(workbook2, engine="openpyxl") as writer:
        sheet = pd.DataFrame(
            [
                ["2023-24 Aggregates", None, None],
                [None, "ACTUAL\n2023-2024\nYTD July\n$m", "ACTUAL\n2023-2024\nYTD August\n$m"],
                ["Revenue", 100.0, 210.0],
            ]
        )
        sheet.to_excel(writer, sheet_name="2023-24", header=False, index=False)
    second = _run_apply(monkeypatch, fixture_db, workbook2)

    assert second["facts_to_insert"] == 1
    assert second["facts_already_present_idempotent_skip"] == 1
    assert second["revision_conflicts_quarantined"] == 0

    conn = sqlite3.connect(str(fixture_db))
    n = conn.execute("SELECT COUNT(*) FROM facts WHERE measure_type = 'mfs_ytd_revenue'").fetchone()[0]
    conn.close()
    assert n == 2

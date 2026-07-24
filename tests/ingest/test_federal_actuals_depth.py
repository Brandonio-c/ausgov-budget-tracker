"""Unit checks for Defence PBS heuristics and FBO function nesting."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))


def test_defence_start_markers_and_table_keep() -> None:
    from extractors.pbs_programs_all import _is_start_page, _should_stop_table

    assert _is_start_page("Budget Expenses and Performance for Outcome 1")
    assert _is_start_page("Cost Summary for Program 2.5")
    assert not _should_stop_table("Table 13: Cost Summary for Program 2.5 Navy")
    assert _should_stop_table("Table 3: Budgeted Financial Statements")


def test_defence_clean_program_total_label() -> None:
    from extractors.pbs_programs_all import _clean_defence_program_label

    label = _clean_defence_program_label(
        "Program 2.5 Navy Capabilities Total funded expenditure"
    )
    assert label is not None
    assert "Program 2.5 Navy Capabilities" in label
    assert _clean_defence_program_label("Employees") is None


def test_defence_extract_joins_label_and_numeric_line() -> None:
    from extractors import pbs_programs_all as mod

    snippet = (
        "Budget Expenses and Performance\n"
        "Program 2.5 Navy Capabilities Total funded expenditure\n"
        "1,234,567 2,345,678 3,456,789 4,000,000 5,000,000\n"
        "Employees 100,000 100,000 100,000 100,000 100,000\n"
    )
    with patch.object(mod, "iter_pdf_pages", return_value=[(1, snippet)]):
        rows = mod.extract_pdf(
            Path("fake-defence.pdf"),
            portfolio="Defence",
            source_id="federal_pbs_defence",
        )
    totals = [
        r
        for r in rows
        if "Program 2.5" in r.get("program_label", "")
        or "Program 2.5" in r.get("category", "")
    ]
    assert len(totals) >= 1
    assert not any(
        r.get("program_label", "").startswith("Employees") for r in rows
    )


def test_fbo_does_not_nest_defence_under_gps() -> None:
    from extractors.fbo_appendix_a import FUNCTION_HEADERS, _match_function

    assert _match_function("Defence") == "Defence"
    assert "Defence" in FUNCTION_HEADERS
    assert "General public services" in FUNCTION_HEADERS

    staging = (
        REPO_ROOT
        / "data"
        / "staging"
        / "breakdowns"
        / "federal_fbo_2024_25_function_subfunction.csv"
    )
    if staging.is_file():
        text = staging.read_text(encoding="utf-8", errors="replace")
        assert "General public services / Defence" not in text
        assert "\nDefence," in text or ",Defence," in text or text.endswith("Defence")

    import sqlite3

    db = REPO_ROOT / "data" / "facts.db"
    if not db.is_file():
        return
    conn = sqlite3.connect(str(db))
    n = conn.execute(
        """
        SELECT COUNT(*) FROM nodes n
        JOIN source_documents d ON d.id = n.source_document_id
        WHERE d.source_key = 'federal_fbo_2024_25_function_subfunction'
          AND n.name LIKE 'General public services / Defence%'
        """
    ).fetchone()[0]
    conn.close()
    assert n == 0
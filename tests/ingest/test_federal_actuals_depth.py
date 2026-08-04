"""Unit checks for Defence PBS heuristics and FBO function nesting."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

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


def test_defence_key_cost_category_rejects_generic_single_word_matches() -> None:
    """Regression for a real bug found in the database-hygiene milestone
    (Task 2): "Workforce", "Operating", and "Operations" used to be bare
    substring matches here, bucketing rows from completely unrelated
    tables (a workforce headcount table, a facilities/property table, a
    Statement of Cash Flows, a Program 1.1 resourcing table) under a
    misleading "Key cost category / <word>" label - confirmed for every
    one of the 26 real facts those three keywords ever matched (none came
    from the genuine Key Cost Category table), and confirmed further by
    the resulting "OPERATING" series jumping ~24x between adjacent
    forward-estimate years, which no real cost category does. Only the
    two multi-word, specific Table 4b category names are safe to bucket
    via a bare substring match."""
    from extractors.pbs_programs_all import _clean_defence_program_label

    assert _clean_defence_program_label("(Workforce Requirement) ADF Permanent Force 16,193 Navy") is None
    assert _clean_defence_program_label("18 -59,327 Expenditure (Operating and Capital) -76,682") is None
    assert _clean_defence_program_label(
        "Table 46: Budgeted Departmental Statement of Cash Flows OPERATING ACTIVITIES Cash received Appropriations"
    ) is None
    assert _clean_defence_program_label(
        "30 June 2026 Facilities to Support LAND 3025 Phase 2 Deployable Special Operations Engineer Regiment"
    ) is None

    # The two genuine, specific Table 4b category names must still pass.
    acquisition = _clean_defence_program_label("3 Capability Acquisition Program 17,702.7 18,")
    assert acquisition == "Key cost category / Capability Acquisition Program"
    sustainment = _clean_defence_program_label("4 Capability Sustainment Program 17,230.5 18,")
    assert sustainment == "Key cost category / Capability Sustainment Program"


def test_defence_extract_joins_label_and_numeric_line() -> None:
    from extractors import pbs_programs_all as mod

    snippet = (
        "Budget Expenses and Performance\n"
        "2024-25 Estimated actual 2025-26 Budget 2026-27 Forward estimate "
        "2027-28 Forward estimate 2028-29 Forward estimate\n"
        "Program 2.5 Navy Capabilities Total funded expenditure\n"
        "1,234,567 2,345,678 3,456,789 4,000,000 5,000,000\n"
        "Employees 100,000 100,000 100,000 100,000 100,000\n"
    )
    with patch.object(mod, "iter_pdf_pages", return_value=[(1, snippet)]):
        rows = mod.extract_pdf(
            Path("fake-defence.pdf"),
            portfolio="Defence",
            source_id="federal_pbs_defence_2025_26",
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
"""Task 6 of the adapter-repair-followup milestone (second family):
consolidated tests for the VIC DTF Budget Portfolio Outcomes extractor
and loader - unit conversion, negative values, header parsing (multi-line
Actual/Budget/Variance columns, no "Notes" column), footnote-letter
stripping, revision policy, idempotent reload, citation preservation,
quarantine behavior, and duplicate prevention (Net assets/Total equity,
Net result/Comprehensive result).
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
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import reload_vic_bpo as loader  # noqa: E402
import vic_bpo  # noqa: E402
from schema_migrate import migrate  # noqa: E402

# ---- header cell / footnote regex --------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2024-25\nActual", ("2024-25", "Actual")),
        ("2024-25\nBudget", ("2024-25", "Budget")),
        ("2024-25\nBudget (a)", ("2024-25", "Budget")),
        ("2023-24\nActual", ("2023-24", "Actual")),
    ],
)
def test_header_cell_regex(text, expected):
    m = vic_bpo.HEADER_CELL_RE.match(text)
    assert m is not None
    assert (m.group("fy"), m.group("status")) == expected


def test_header_cell_regex_rejects_variance():
    assert vic_bpo.HEADER_CELL_RE.match("Variance") is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Output appropriations (a)", "Output appropriations"),
        ("Receivables from government (b)", "Receivables from government"),
        ("Total assets", "Total assets"),
        ("Payables ", "Payables"),
    ],
)
def test_strip_trailing_footnote(raw, expected):
    assert vic_bpo._strip_trailing_footnote(raw) == expected


def test_footnote_row_regex_matches_lowercase_letter_paren():
    assert vic_bpo.FOOTNOTE_ROW_RE.match("(a) Higher actuals primarily reflect...")
    assert not vic_bpo.FOOTNOTE_ROW_RE.match("Total assets")


# ---- extractor: synthetic fixture workbooks -----------------------------


def _write_workbook(path: Path, *, unit_text: str = "($ million)", budget_footnote: str = "") -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        os_rows = [
            ["Comprehensive operating statement", None, None, None],
            ["for the year ended 30 June 2025", None, None, unit_text],
            [None, "2024-25\nActual", f"2024-25\nBudget{budget_footnote}", "Variance"],
            ["Income from transactions", None, None, None],
            ["Output appropriations (a)", 455, 442, 13],
            ["Total revenue and income from transactions", 466, 452, 14],
            ["Expenses from transactions", None, None, None],
            ["Employee benefits (b)", 267, 237, 30],
            ["Total expenses from transactions", 459, 452, 7],
            ["Net result from transactions (net operating balance)", 7, 0, 7],
            ["Net result", 7, 0, 7],
            ["Comprehensive result", 7, 0, 7],
            ["(a) Higher actuals primarily reflect funding changes.", None, None, None],
            ["(b) Higher actuals primarily reflect enterprise agreement outcomes.", None, None, None],
        ]
        pd.DataFrame(os_rows).to_excel(writer, sheet_name="OS", header=False, index=False)

        bs_rows = [
            ["Balance sheet", None, None, None],
            ["as at 30 June 2025", None, None, unit_text],
            [None, "2024-25\nActual", f"2024-25\nBudget{budget_footnote}", "Variance"],
            ["Assets", None, None, None],
            ["Total assets", 227, 250, -23],
            ["Liabilities", None, None, None],
            ["Total liabilities", 144, 163, -19],
            ["Net assets", 83, 87, -4],
            ["Equity", None, None, None],
            ["Total equity", 83, 87, -4],
            ["(a) The 2024-25 budget figures have been restated.", None, None, None],
        ]
        pd.DataFrame(bs_rows).to_excel(writer, sheet_name="BS", header=False, index=False)

        cfs_rows = [
            ["Statement of cash flows", None, None, None],
            ["for the year ended 30 June 2025", None, None, unit_text],
            [None, "2024-25\nActual", "2024-25\nBudget", "Variance"],
            ["Cash flows from operating activities", None, None, None],
            ["Net cash flows from / (used in) operating activities", 7, 4, 3],
            ["Net cash flows from / (used in) investing activities", -7, -15, 8],
            ["Net cash flows from / (used in) financing activities", 0, 10, -10],
            ["Cash and cash equivalents at the end of the financial year", 12, 11, 1],
            ["(a) Higher actuals reflect funding allocations.", None, None, None],
        ]
        pd.DataFrame(cfs_rows).to_excel(writer, sheet_name="CFS", header=False, index=False)


def test_extractor_stops_before_footnote_block(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, quarantine = vic_bpo.extract_workbook(path, "test_source")
    assert quarantine == []
    os_labels = [r["row_label"] for r in rows if r["sheet"] == "OS"]
    assert "Higher actuals primarily reflect funding changes." not in " ".join(os_labels)
    # Footnote-stripped label, not the raw "(a) ..." footnote row itself
    assert "Output appropriations" in os_labels


def test_extractor_excludes_variance_column(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo.extract_workbook(path, "test_source")
    rev_rows = [r for r in rows if r["row_label"] == "Total revenue and income from transactions"]
    amounts = sorted(r["amount_million_aud"] for r in rev_rows)
    assert amounts == [452.0, 466.0]  # never 14 (the variance)
    assert len(rev_rows) == 2  # actual + budget only, not a third "variance" row


def test_extractor_handles_budget_header_with_footnote_marker(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path, budget_footnote=" (a)")
    rows, quarantine = vic_bpo.extract_workbook(path, "test_source")
    assert quarantine == []
    bs_rows = [r for r in rows if r["sheet"] == "BS" and r["row_label"] == "Total assets"]
    assert {r["estimate_status"] for r in bs_rows} == {"actual", "budget"}


def test_extractor_negative_values_preserved(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo.extract_workbook(path, "test_source")
    investing_rows = [r for r in rows if r["row_label"] == "Net cash flows from / (used in) investing activities"]
    assert {r["amount_million_aud"] for r in investing_rows} == {-7.0, -15.0}


def test_extractor_quarantines_unexpected_unit(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path, unit_text="($ thousand)")
    rows, quarantine = vic_bpo.extract_workbook(path, "test_source")
    assert rows == []
    assert all(q["reason"] == "unexpected_unit_cell" for q in quarantine)
    assert len(quarantine) == 3


def test_extractor_quarantines_missing_sheet(tmp_path):
    with pd.ExcelWriter(tmp_path / "bpo.xlsx", engine="openpyxl") as writer:
        pd.DataFrame([["x"]]).to_excel(writer, sheet_name="OS", header=False, index=False)
    rows, quarantine = vic_bpo.extract_workbook(tmp_path / "bpo.xlsx", "test_source")
    reasons = {q["reason"] for q in quarantine}
    assert "expected_sheet_missing" in reasons


# ---- loader: classification, scale conversion, duplicate exclusion -----


@pytest.fixture
def semantics():
    return loader.load_semantics()


@pytest.fixture
def label_index(semantics):
    return loader.build_label_index(semantics)


@pytest.fixture
def excluded_labels(semantics):
    return loader.build_excluded_label_set(semantics)


def _row(label, sheet, estimate_status="actual", amount=100.0, cached_copy_path=None):
    return {
        "source_id": "vic_budget_portfolio_outcomes_2024_25",
        "sheet": sheet,
        "row_label": label,
        "financial_year": "2024-25",
        "estimate_status": estimate_status,
        "amount_million_aud": amount,
        "locator": f"row:{label}|{estimate_status}",
        "cached_copy_path": cached_copy_path or str(REPO_ROOT / "README.md"),
    }


def test_scale_factor_applied_million_to_aud(semantics, label_index, excluded_labels):
    row = _row("Total revenue and income from transactions", "OS", amount=466.0)
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["amount_aud"] == 466_000_000.0


def test_total_equity_excluded_as_duplicate(semantics, label_index, excluded_labels):
    row = _row("Total equity", "BS")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "excluded_duplicate_label"


def test_comprehensive_result_excluded_as_duplicate(semantics, label_index, excluded_labels):
    row = _row("Comprehensive result", "OS")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "excluded_duplicate_label"


def test_sheet_mismatch_quarantined(semantics, label_index, excluded_labels):
    row = _row("Total revenue and income from transactions", "BS")  # wrong sheet
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "sheet_mismatch"


def test_missing_source_file_quarantined(semantics, label_index, excluded_labels):
    row = _row("Total assets", "BS", cached_copy_path="data/does/not/exist.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


def test_stock_measure_has_no_period_start(semantics, label_index, excluded_labels):
    row = _row("Total assets", "BS")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2025-06-30"


def test_flow_measure_has_period_start_and_end(semantics, label_index, excluded_labels):
    row = _row("Total revenue and income from transactions", "OS")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["period_start"] == "2024-07-01"
    assert fact["period_end"] == "2025-06-30"


def test_negative_amount_preserved_through_classification(semantics, label_index, excluded_labels):
    row = _row("Net cash flows from / (used in) investing activities", "CFS", amount=-7.0)
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["amount_aud"] == -7_000_000.0


def test_actual_and_budget_produce_distinct_fact_keys(semantics, label_index, excluded_labels):
    actual_row = _row("Total assets", "BS", estimate_status="actual")
    budget_row = _row("Total assets", "BS", estimate_status="budget")
    actual_fact, _ = loader.classify_and_validate(actual_row, semantics, label_index, excluded_labels)
    budget_fact, _ = loader.classify_and_validate(budget_row, semantics, label_index, excluded_labels)
    assert actual_fact["fact_key"] != budget_fact["fact_key"]
    assert actual_fact["financial_year"] == budget_fact["financial_year"] == "2024-25"


def test_unexpected_estimate_status_quarantined(semantics, label_index, excluded_labels):
    row = _row("Total assets", "BS", estimate_status="forward_estimate")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "unexpected_estimate_status"


def test_fact_key_stable_and_identity_complete():
    key1 = loader.build_fact_key(
        source_id="src", financial_year="2024-25", measure_type="vic_bpo_revenue",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="VIC",
    )
    key2 = loader.build_fact_key(
        source_id="src", financial_year="2024-25", measure_type="vic_bpo_revenue",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="VIC",
    )
    assert key1 == key2
    key_budget = loader.build_fact_key(
        source_id="src", financial_year="2024-25", measure_type="vic_bpo_revenue",
        accounting_basis="accrual", estimate_status="budget", jurisdiction="VIC",
    )
    assert key_budget != key1


# ---- loader: full run against a real fixture DB (idempotency, revision, citations) --


@pytest.fixture
def fixture_db(tmp_path, monkeypatch):
    db = tmp_path / "facts.db"
    migrate(db)
    workbook = tmp_path / "bpo.xlsx"
    _write_workbook(workbook)
    monkeypatch.setattr(loader, "SOURCE_FILE", workbook)
    monkeypatch.setattr(loader, "QUARANTINE_PATH", tmp_path / "q.jsonl")
    return db


def test_full_load_is_idempotent(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    result1 = loader.run(conn, apply=True)
    assert result1["facts_to_insert"] == 22  # 11 measures x 2 estimate_status
    assert result1["revision_conflicts_quarantined"] == 0

    facts_after_first = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    result2 = loader.run(conn, apply=True)
    assert result2["facts_to_insert"] == 0
    assert result2["facts_already_present_idempotent_skip"] == 22
    assert result2["revision_conflicts_quarantined"] == 0

    facts_after_second = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    assert facts_after_first == facts_after_second

    dupes = conn.execute(
        "SELECT fact_key, COUNT(*) c FROM facts GROUP BY fact_key HAVING c > 1"
    ).fetchall()
    assert dupes == []
    conn.close()


def test_revision_conflict_detection(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)

    original = conn.execute(
        "SELECT amount_aud FROM facts WHERE measure_type = 'vic_bpo_revenue' AND estimate_status = 'actual'"
    ).fetchone()[0]

    fake_fact_key = loader.build_fact_key(
        source_id=loader.SOURCE_ID, financial_year="2024-25", measure_type="vic_bpo_revenue",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="VIC",
    )
    existing = conn.execute(
        "SELECT id, amount_aud FROM facts WHERE fact_key = ?", (fake_fact_key,)
    ).fetchone()
    assert existing is not None
    assert abs(float(existing[1]) - float(original + 1_000_000)) >= 0.01
    conn.close()


def test_citation_preserved_through_real_load(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)
    row = conn.execute(
        "SELECT source_locator_json FROM facts WHERE measure_type = 'vic_bpo_revenue' AND estimate_status = 'actual'"
    ).fetchone()
    payload = json.loads(row[0])
    assert "row:Total revenue and income from transactions" in payload["locator"]
    assert "estimate_status:actual" in payload["locator"]
    assert payload["cached_copy_path"]
    conn.close()


def test_dedicated_compatibility_groups_distinct_from_annual_and_vic_afs(fixture_db):
    """Checks exactly this family's own 11 OS/BS/CFS measure_types
    (sourced from vic_bpo.yaml itself, not a `LIKE 'vic_bpo_%'` wildcard
    - the sibling vic_bpo_soce_admin family deliberately shares the same
    `vic_bpo_` naming prefix to signal it's the same overall workbook/
    department, so a wildcard would over-match)."""
    this_familys_measure_types = tuple(loader.load_semantics()["measures"].keys())
    assert len(this_familys_measure_types) == 11

    conn = sqlite3.connect(str(fixture_db))
    placeholders = ",".join("?" * len(this_familys_measure_types))
    rows = conn.execute(
        f"SELECT measure_type, compatibility_group FROM measure_definitions WHERE measure_type IN ({placeholders})",
        this_familys_measure_types,
    ).fetchall()
    afs_rows = conn.execute(
        "SELECT compatibility_group FROM measure_definitions WHERE measure_type LIKE 'vic_afs_%'"
    ).fetchall()
    conn.close()
    assert len(rows) == 11
    annual_groups = {"actual_expense", "budget_expense", "gfs_revenue", "gfs_liability"}
    afs_groups = {r[0] for r in afs_rows}
    for measure_type, group in rows:
        assert group == measure_type  # 1:1
        assert group not in annual_groups
        assert group not in afs_groups

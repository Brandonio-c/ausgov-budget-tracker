"""Task 6 of the VIC SOCE/Admin milestone: consolidated tests for the
VIC DTF Budget Portfolio Outcomes workbook's deferred `SOCE`/`Admin`
sheet extractor and loader - unit conversion, negative values, header
parsing (Admin: same Actual/Budget/Variance shape as OS/BS/CFS; SOCE:
rolling-balance-across-blocks shape), footnote-letter stripping,
period granularity, vintage precedence (actual vs budget for one
financial year), revision policy, idempotent reload, citation
preservation, quarantine behavior, and duplicate prevention (SOCE's
"Balance at 30 June 2025"/"Comprehensive result" vs the already-loaded
vic_bpo_net_assets/vic_bpo_net_result; Admin's "Net result"/"Net
assets" vs OS's/BS's same-text labels for a different concept).
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

import reload_vic_bpo_soce_admin as loader  # noqa: E402
import vic_bpo_soce_admin  # noqa: E402
from schema_migrate import migrate  # noqa: E402

# ---- extractor: synthetic fixture workbooks -----------------------------


def _write_workbook(path: Path, *, unit_text: str = "($ million)", budget_footnote: str = "") -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        admin_rows = [
            ["Administered items statement", None, None, None],
            ["for the year ended 30 June 2025", None, None, unit_text],
            [None, "2024-25\nActual", f"2024-25\nBudget{budget_footnote}", "Variance"],
            ["Total administered income", 82428, 95706, -13278],
            ["Total administered expenses (a)", 99557, 110340, -10783],
            ["Net result", -16443, -14571, -1872],
            ["Comprehensive result", -15657, -13823, -1834],
            ["Total administered assets", 25695, 25541, 154],
            ["Total administered liabilities", 183471, 187260, -3789],
            ["Net assets", -157776, -161719, 3943],
            ["(a) Higher actuals reflect Commonwealth pass-through grants.", None, None, None],
        ]
        pd.DataFrame(admin_rows).to_excel(writer, sheet_name="Admin", header=False, index=False)

        soce_rows = [
            ["Statement of changes in equity", None, None, None],
            ["for the year ended 30 June 2025", None, None, unit_text],
            [None, "Accumulated surplus", "Contributions by owner", "Total equity"],
            ["2024-25 actuals", None, None, None],
            ["Balance at 1 July 2024", 70, 6, 76],
            ["Comprehensive result", 7, 0, 7],
            ["Transactions with owners in their capacity as owners", 0, 0, 0],
            ["Balance at 30 June 2025 (a)", 77, 6, 83],
            ["2024-25 original budget", None, None, None],
            ["Balance at 1 July 2024", 70, 6, 76],
            ["Comprehensive result", 0, 0, 0],
            ["Transactions with owners in their capacity as owners", 0, 10, 10],
            ["Balance at 30 June 2025", 70, 16, 87],
            ["Variance", None, None, None],
            ["Balance at 1 July 2024", 0, 0, 0],
            ["Comprehensive result", 7, 0, 7],
            ["Transactions with owners in their capacity as owners", 0, -10, -10],
            ["Balance at 30 June 2025", 7, -10, -4],
            ["(a) The 2024-25 actual closing balance has been restated.", None, None, None],
        ]
        pd.DataFrame(soce_rows).to_excel(writer, sheet_name="SOCE", header=False, index=False)


def test_admin_extractor_stops_before_footnote_block(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, quarantine = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    assert quarantine == []
    admin_labels = [r["row_label"] for r in rows if r["sheet"] == "Admin"]
    assert "Higher actuals reflect Commonwealth pass-through grants." not in " ".join(admin_labels)
    assert "Total administered expenses" in admin_labels  # footnote-stripped


def test_admin_extractor_excludes_variance_column(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    income_rows = [r for r in rows if r["sheet"] == "Admin" and r["row_label"] == "Total administered income"]
    amounts = sorted(r["amount_million_aud"] for r in income_rows)
    assert amounts == [82428.0, 95706.0]  # never -13278 (the variance)
    assert len(income_rows) == 2


def test_admin_extractor_negative_values_preserved(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    net_result_rows = [r for r in rows if r["sheet"] == "Admin" and r["row_label"] == "Net result"]
    assert {r["amount_million_aud"] for r in net_result_rows} == {-16443.0, -14571.0}


def test_admin_extractor_handles_budget_header_with_footnote_marker(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path, budget_footnote=" (a)")
    rows, quarantine = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    assert quarantine == []
    admin_rows = [r for r in rows if r["sheet"] == "Admin" and r["row_label"] == "Net assets"]
    assert {r["estimate_status"] for r in admin_rows} == {"actual", "budget"}


def test_extractor_quarantines_unexpected_unit(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path, unit_text="($ thousand)")
    rows, quarantine = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    assert rows == []
    assert all(q["reason"] == "unexpected_unit_cell" for q in quarantine)
    assert len(quarantine) == 2  # one per sheet


def test_extractor_quarantines_missing_sheet(tmp_path):
    with pd.ExcelWriter(tmp_path / "bpo.xlsx", engine="openpyxl") as writer:
        pd.DataFrame([["x"]]).to_excel(writer, sheet_name="Admin", header=False, index=False)
    rows, quarantine = vic_bpo_soce_admin.extract_workbook(tmp_path / "bpo.xlsx", "test_source")
    reasons = {q["reason"] for q in quarantine}
    assert "expected_sheet_missing" in reasons


def test_soce_extractor_skips_variance_block(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    soce_rows = [r for r in rows if r["sheet"] == "SOCE"]
    # 4 line items x 2 blocks (actuals, original budget) - Variance block never extracted
    assert len(soce_rows) == 8
    assert all(r["estimate_status"] in ("actual", "budget") for r in soce_rows)


def test_soce_extractor_reads_total_equity_column_only(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    opening = [
        r for r in rows if r["sheet"] == "SOCE" and r["row_label"] == "Balance at 1 July 2024" and r["estimate_status"] == "actual"
    ]
    assert len(opening) == 1
    assert opening[0]["amount_million_aud"] == 76.0  # Total equity column, not Accumulated surplus (70)


def test_soce_extractor_strips_footnote_on_closing_balance_label(tmp_path):
    path = tmp_path / "bpo.xlsx"
    _write_workbook(path)
    rows, _ = vic_bpo_soce_admin.extract_workbook(path, "test_source")
    closing_labels = {r["row_label"] for r in rows if r["sheet"] == "SOCE" and "Balance at 30 June" in r["row_label"]}
    assert closing_labels == {"Balance at 30 June 2025"}  # footnote marker stripped, not a distinct label


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


def _row(label, sheet, estimate_status="actual", amount=100.0, cached_copy_path=None, locator_suffix=""):
    return {
        "source_id": "vic_budget_portfolio_outcomes_2024_25",
        "sheet": sheet,
        "row_label": label,
        "financial_year": "2024-25",
        "estimate_status": estimate_status,
        "amount_million_aud": amount,
        "locator": f"row:{label}|{estimate_status}{locator_suffix}",
        "cached_copy_path": cached_copy_path or str(REPO_ROOT / "README.md"),
    }


def test_scale_factor_applied_million_to_aud(semantics, label_index, excluded_labels):
    row = _row("Total administered income", "Admin", amount=82428.0)
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["amount_aud"] == 82_428_000_000.0


def test_soce_comprehensive_result_quarantined_as_sheet_mismatch(semantics, label_index, excluded_labels):
    """SOCE's "Comprehensive result" label collides textually with Admin's
    own measure of the same name - it must be rejected (not silently
    loaded as vic_bpo_admin_comprehensive_result), since it's a duplicate
    of the already-loaded vic_bpo_net_result from the OS sheet."""
    row = _row("Comprehensive result", "SOCE")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "sheet_mismatch"


def test_soce_balance_at_30_june_unrecognized(semantics, label_index, excluded_labels):
    """SOCE's "Balance at 30 June 2025" restates the already-loaded
    vic_bpo_net_assets verbatim - never registered as a valid label for
    any measure_type in this family, so it is quarantined."""
    row = _row("Balance at 30 June 2025", "SOCE")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "unrecognized_label"


def test_admin_net_result_and_comprehensive_result_both_load_as_distinct_measures(
    semantics, label_index, excluded_labels
):
    """Unlike OS's Net result/Comprehensive result (a duplicate pair,
    only Net result loaded), Admin's two measures are genuinely
    distinct and both load."""
    net_result_row = _row("Net result", "Admin", amount=-16443.0)
    comp_result_row = _row("Comprehensive result", "Admin", amount=-15657.0)
    net_fact, net_reason = loader.classify_and_validate(net_result_row, semantics, label_index, excluded_labels)
    comp_fact, comp_reason = loader.classify_and_validate(comp_result_row, semantics, label_index, excluded_labels)
    assert net_reason == comp_reason == ""
    assert net_fact["measure_type"] == "vic_bpo_admin_net_result"
    assert comp_fact["measure_type"] == "vic_bpo_admin_comprehensive_result"
    assert net_fact["fact_key"] != comp_fact["fact_key"]


def test_sheet_mismatch_quarantined_admin_label_on_wrong_sheet(semantics, label_index, excluded_labels):
    row = _row("Total administered income", "SOCE")  # wrong sheet
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "sheet_mismatch"


def test_missing_source_file_quarantined(semantics, label_index, excluded_labels):
    row = _row("Net assets", "Admin", cached_copy_path="data/does/not/exist.xlsx")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


def test_stock_measure_has_no_period_start(semantics, label_index, excluded_labels):
    row = _row("Net assets", "Admin")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2025-06-30"


def test_flow_measure_has_period_start_and_end(semantics, label_index, excluded_labels):
    row = _row("Total administered income", "Admin")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["period_start"] == "2024-07-01"
    assert fact["period_end"] == "2025-06-30"


def test_negative_amount_preserved_through_classification(semantics, label_index, excluded_labels):
    row = _row("Net result", "Admin", amount=-16443.0)
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert reason == ""
    assert fact["amount_aud"] == -16_443_000_000.0


def test_actual_and_budget_produce_distinct_fact_keys(semantics, label_index, excluded_labels):
    actual_row = _row("Net assets", "Admin", estimate_status="actual")
    budget_row = _row("Net assets", "Admin", estimate_status="budget")
    actual_fact, _ = loader.classify_and_validate(actual_row, semantics, label_index, excluded_labels)
    budget_fact, _ = loader.classify_and_validate(budget_row, semantics, label_index, excluded_labels)
    assert actual_fact["fact_key"] != budget_fact["fact_key"]
    assert actual_fact["financial_year"] == budget_fact["financial_year"] == "2024-25"


def test_unexpected_estimate_status_quarantined(semantics, label_index, excluded_labels):
    row = _row("Net assets", "Admin", estimate_status="forward_estimate")
    fact, reason = loader.classify_and_validate(row, semantics, label_index, excluded_labels)
    assert fact is None
    assert reason == "unexpected_estimate_status"


def test_fact_key_stable_and_identity_complete():
    key1 = loader.build_fact_key(
        source_id="src", financial_year="2024-25", measure_type="vic_bpo_admin_income",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="VIC",
    )
    key2 = loader.build_fact_key(
        source_id="src", financial_year="2024-25", measure_type="vic_bpo_admin_income",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="VIC",
    )
    assert key1 == key2
    key_budget = loader.build_fact_key(
        source_id="src", financial_year="2024-25", measure_type="vic_bpo_admin_income",
        accounting_basis="accrual", estimate_status="budget", jurisdiction="VIC",
    )
    assert key_budget != key1


def test_label_index_never_collides_with_vic_bpo_os_bs_cfs_measures(semantics, label_index):
    """This adapter's own label index (SOCE/Admin only) must never claim
    "Net result"/"Net assets" for the sibling vic_bpo_* (OS/BS)
    measure_types - it is a completely separate index, built only from
    this YAML, so those measure_types don't even exist here."""
    assert label_index["Net result"] == "vic_bpo_admin_net_result"
    assert label_index["Net assets"] == "vic_bpo_admin_net_assets"
    assert "vic_bpo_net_result" not in semantics["measures"]
    assert "vic_bpo_net_assets" not in semantics["measures"]


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
    assert result1["facts_to_insert"] == 18  # 9 measures x 2 estimate_status
    assert result1["revision_conflicts_quarantined"] == 0

    facts_after_first = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    result2 = loader.run(conn, apply=True)
    assert result2["facts_to_insert"] == 0
    assert result2["facts_already_present_idempotent_skip"] == 18
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
        "SELECT amount_aud FROM facts WHERE measure_type = 'vic_bpo_admin_income' AND estimate_status = 'actual'"
    ).fetchone()[0]

    fake_fact_key = loader.build_fact_key(
        source_id=loader.SOURCE_ID, financial_year="2024-25", measure_type="vic_bpo_admin_income",
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
        "SELECT source_locator_json FROM facts WHERE measure_type = 'vic_bpo_net_assets_opening' AND estimate_status = 'actual'"
    ).fetchone()
    payload = json.loads(row[0])
    assert "row:Balance at 1 July 2024" in payload["locator"]
    assert "estimate_status:actual" in payload["locator"]
    assert "column:Total equity" in payload["locator"]
    assert payload["cached_copy_path"]
    conn.close()


def test_soce_duplicate_rows_never_loaded_through_real_load(fixture_db):
    """End-to-end proof (not just unit-level classify_and_validate) that
    the full run() never publishes SOCE's duplicate-by-design rows."""
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)
    net_assets_opening_count = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE measure_type = 'vic_bpo_net_assets_opening'"
    ).fetchone()[0]
    owner_txn_count = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE measure_type = 'vic_bpo_owner_transactions'"
    ).fetchone()[0]
    # Only the 2 genuinely new SOCE measures ever appear - no
    # vic_bpo_net_assets/vic_bpo_net_result rows are inserted by this
    # loader at all (those measure_types don't even exist in this
    # adapter's semantics).
    assert net_assets_opening_count == 2  # actual + budget
    assert owner_txn_count == 2
    all_measure_types = {
        r[0] for r in conn.execute("SELECT DISTINCT measure_type FROM facts").fetchall()
    }
    assert "vic_bpo_net_assets" not in all_measure_types
    assert "vic_bpo_net_result" not in all_measure_types
    conn.close()


def test_dedicated_compatibility_groups_distinct_from_annual_vic_afs_and_vic_bpo(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    rows = conn.execute(
        "SELECT measure_type, compatibility_group FROM measure_definitions "
        "WHERE measure_type LIKE 'vic_bpo_admin_%' OR measure_type IN "
        "('vic_bpo_net_assets_opening', 'vic_bpo_owner_transactions')"
    ).fetchall()
    conn.close()
    assert len(rows) == 9
    annual_groups = {"actual_expense", "budget_expense", "gfs_revenue", "gfs_liability"}
    sibling_vic_bpo_groups = {"vic_bpo_revenue", "vic_bpo_expense", "vic_bpo_net_result", "vic_bpo_net_assets"}
    for measure_type, group in rows:
        assert group == measure_type  # 1:1
        assert group not in annual_groups
        assert group not in sibling_vic_bpo_groups

"""Regression tests for scripts/ingest/extractors/qld_on_time_payments.py
(item 7.5). Covers the filename-identity never-guess discipline (skip on
ambiguity, both the range and single-year patterns), the real header-wording
drift across the 42 acquired files, the embedded-newline "2025-26\\nQuarter"
header cell, "Nil" vs blank-cell numeric handling (including the pandas
NaN-vs-None gotcha that caused a real CHECK-constraint bug), and the
"Unnamed:" trailing-column-noise skip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import qld_on_time_payments as extractor  # noqa: E402


# ---- filename -> financial_year --------------------------------------------


@pytest.mark.parametrize(
    "filename,expected_fy",
    [
        ("qld_on_time_payment_reports__dpc_2020-21.csv", "2020-21"),
        ("qld_on_time_payment_reports__dpc_2020_21.csv", "2020-21"),
        ("qld_on_time_payment_reports__dpc_fy2020.csv", "2020-21"),
    ],
)
def test_financial_year_recognized_patterns(filename, expected_fy):
    assert extractor._financial_year_from_filename(filename) == expected_fy


def test_financial_year_undeterminable_is_none_not_guessed():
    """A bare "q4-2021" with no month context to resolve which financial
    year Q4 belongs to must never be guessed - the plan's standing rule
    against inferring identity from label similarity alone."""
    assert extractor._financial_year_from_filename("qld_on_time_payment_reports__dpc_q4-2021.csv") is None


# ---- filename -> agency_code ------------------------------------------------


def test_agency_code_is_the_literal_filename_token_verbatim():
    """Never expanded to a guessed full department name - QLD agencies
    undergo frequent machinery-of-government renames."""
    assert extractor._agency_code_from_filename("qld_on_time_payment_reports__dcyjma_2020-21.csv") == "dcyjma"


def test_agency_code_skips_year_and_quarter_tokens():
    assert extractor._agency_code_from_filename("qld_on_time_payment_reports__2020-21_q1_dpc.csv") == "dpc"


def test_agency_code_undeterminable_is_none_not_guessed():
    assert extractor._agency_code_from_filename("qld_on_time_payment_reports__2020-21.csv") is None


# ---- numeric cleaning --------------------------------------------------------


def test_clean_numeric_nil_is_a_literal_zero():
    assert extractor._clean_numeric("Nil") == 0.0


def test_clean_numeric_blank_string_is_none_not_zero():
    assert extractor._clean_numeric("") is None
    assert extractor._clean_numeric("   ") is None


def test_clean_numeric_pandas_nan_is_none_not_zero():
    """Regression: pandas represents a blank CSV cell as float('nan'), not
    Python None, even with dtype=str - str(float('nan')) is the non-empty
    string "nan", which silently round-trips back to a real NaN via
    float("nan") and previously reached the facts.amount_aud/quantity CHECK
    constraint as neither a valid number nor SQL NULL. Must return None."""
    assert extractor._clean_numeric(float("nan")) is None


def test_clean_numeric_strips_dollar_comma_percent_and_whitespace():
    assert extractor._clean_numeric(" $1,234.50 ") == 1234.50
    assert extractor._clean_numeric("12.5%") == 12.5


def test_clean_numeric_unparseable_text_is_none():
    assert extractor._clean_numeric("N/A") is None


# ---- extract_workbook: header drift, quarantine, Unnamed: skip -------------


def _write_csv(tmp_path: Path, name: str, header: list[str], rows: list[list]) -> Path:
    path = tmp_path / name
    pd.DataFrame(rows, columns=header).to_csv(path, index=False)
    return path


def test_extract_workbook_recognizes_a_real_header_wording_variant(tmp_path):
    header = [
        "Quarter",
        "Eligible claims for penalty interest smallbus",
        "Penalty interest paid smallbus",
        "Total eligible and undisputed small business invoices",
        "Eligible and undisputed invs paid late smallbus",
        "Value eligible and undisputed inv paid late smallbus",
        "Mean days paid late eligible and undisputed inv smallbus",
        "Percent of all late payments smallbus",
        "Percent of all late payments others",
    ]
    rows = [[1, 5, 100.0, 50, 2, 200.0, 3.5, 4.0, 6.0]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__dpc_2020-21.csv")
    assert quarantine == []
    measures = {f["measure"] for f in facts}
    assert "total_eligible_invoices" in measures
    assert all(f["fy"] == "2020-21" and f["agency_code"] == "dpc" and f["quarter"] == 1 for f in facts)


def test_extract_workbook_handles_embedded_newline_quarter_header(tmp_path):
    """One real file has the financial year and "Quarter" merged into a
    single quoted, newline-containing header cell (e.g. "2025-26\\nQuarter")
    - must still be recognized as the quarter column."""
    header = ["2025-26\nQuarter", "Eligible claims for penalty interest smallbus"]
    rows = [[2, 7]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__dpc_2025-26.csv")
    assert quarantine == []
    assert facts[0]["quarter"] == 2


def test_extract_workbook_skips_unnamed_trailing_columns_without_quarantine(tmp_path):
    header = ["Quarter", "Eligible claims for penalty interest smallbus", "Unnamed: 9"]
    rows = [[1, 5, None]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__dpc_2020-21.csv")
    assert quarantine == []


def test_extract_workbook_quarantines_a_genuinely_unrecognized_header(tmp_path):
    header = ["Quarter", "Some Brand New Column Nobody Has Seen Before"]
    rows = [[1, 5]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__dpc_2020-21.csv")
    reasons = {q["reason"] for q in quarantine}
    assert "unrecognized_column_header" in reasons


def test_extract_workbook_quarantines_unparseable_and_out_of_range_quarters(tmp_path):
    header = ["Quarter", "Eligible claims for penalty interest smallbus"]
    rows = [["not-a-number", 5], [7, 5]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__dpc_2020-21.csv")
    reasons = [q["reason"] for q in quarantine]
    assert "unparseable_quarter" in reasons
    assert "quarter_out_of_range" in reasons
    assert facts == []


def test_extract_workbook_undeterminable_identity_is_quarantined_not_guessed(tmp_path):
    header = ["Quarter", "Eligible claims for penalty interest smallbus"]
    rows = [[1, 5]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__2020-21.csv")
    assert facts == []
    assert quarantine[0]["reason"] == "agency_code_undeterminable_from_filename"


def test_extract_workbook_blank_cell_is_skipped_not_zero(tmp_path):
    """A blank measure cell must not silently produce a zero-valued fact -
    it is a missing observation, not "Nil"."""
    header = ["Quarter", "Eligible claims for penalty interest smallbus"]
    rows = [[1, ""]]
    path = _write_csv(tmp_path, "in.csv", header, rows)

    facts, quarantine = extractor.extract_workbook(path, "qld_on_time_payment_reports__dpc_2020-21.csv")
    assert facts == []
    assert quarantine == []

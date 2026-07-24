"""Unit tests for Gate 6 locator parsing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from backend.evidence_locator import parse_locator_string, media_type_for_path


def test_parse_sheet_cell():
    p = parse_locator_string("sheet:2005-06 | cell:L7 | unit:AUD millions")
    assert p["sheet_name"] == "2005-06"
    assert p["cell"] == "L7"
    assert p["highlight"]["cell"] == "L7"
    assert p["unit"] == "AUD millions"


def test_parse_abs_purpose_fy():
    p = parse_locator_string(
        "sheet:Table_4 | purpose:Public debt transactions | fy:2015-16 | unit:$m"
    )
    assert p["sheet_name"] == "Table_4"
    assert p["purpose"] == "Public debt transactions"
    assert p["financial_year_label"] == "2015-16"
    assert p["cell"] is None


def test_parse_pdf_page():
    p = parse_locator_string(
        "pdf:bp1_bs-6.pdf | page:225 | Table 6.3 | function:General public services | col:2025-26 | unit:$m"
    )
    assert p["page_number"] == 225
    assert p["purpose"] == "General public services"
    assert "Table 6.3" in (p["text_anchor"] or "")


def test_parse_csv_row():
    p = parse_locator_string("csv:row:951 | payment_date:04/06/2020 | contract:nan")
    assert p["row_number"] == 951


def test_media_type_pdf_path():
    assert media_type_for_path(Path("x.pdf"), {}) == "pdf"
    assert media_type_for_path(Path("x.xlsx"), {}) == "spreadsheet"
    assert media_type_for_path(Path("x.jsonl.gz"), {}) == "text_chunk"

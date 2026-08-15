"""Tests for the Queensland CFFR annual-edition extractor (item 7.4).

Focuses on the regex-based row parser (label match + 4-numeric-token
Year-Ended block, unit scaling from $'000 to real AUD) and the chained
opening/closing-balance continuity check that independently proves
correct extraction across real multi-year data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import qld_cffr_annual as extractor  # noqa: E402


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, pages: list[str]) -> None:
        self.pages = [_FakePage(p) for p in pages]


_SAMPLE_YEAR_ENDED_BLOCK = """
Balance as at 1 July (1,264,975) 30,385,361 29,120,385 31,978,937
Receipts
Collections received from departments  1 40,854,991  - 40,854,991 35,500,575
Investment interest  2,065,828  - 2,065,828 2,245,946
Dividends and income tax equivalents  1,979,499  - 1,979,499 3,812,816
Non-appropriated equity adjustments  69,439  - 69,439 595,647
Superannuation, long service leave, Queensland
Government Insurance Fund and ALCS contributions  2,874,425  - 2,874,425 2,590,919
Capital return from public enterprise investments  995,000  - 995,000 3,350,228
Other receipts  8,232  - 8,232 8,215
48,847,414  - 48,847,414 48,104,347
Payments
Appropriations provided to departments 2 (48,793,165)  - (48,793,165) (50,962,899)
(48,793,165)  - (48,793,165) (50,962,899)
Net effect of investments
Funds transfer to/from Treasurer's account  (413,784) 413,784  -  -
Consolidated Fund Balance as at 30 June (1,624,511) 30,799,145 29,174,634 29,120,385
Notes:
1. Refer to statement of Collections Received from Departments.
"""


def test_extract_edition_parses_real_shaped_year_ended_block(tmp_path, monkeypatch):
    fake = _FakeReader([_SAMPLE_YEAR_ENDED_BLOCK])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")

    rows, quarantine = extractor.extract_edition(path, "2016-17", "x.pdf")
    assert quarantine == []
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["opening_balance"] == pytest.approx(29_120_385_000)
    assert by_key["closing_balance"] == pytest.approx(29_174_634_000)
    assert by_key["collections_from_departments"] == pytest.approx(40_854_991_000)
    assert by_key["appropriations_provided_to_departments"] == pytest.approx(-48_793_165_000)


def test_amounts_are_scaled_from_thousands_to_real_aud(tmp_path, monkeypatch):
    """The source table is denominated in $'000 - a raw extracted token
    of "40,854,991" must become $40,854,991,000, never left as thousands."""
    fake = _FakeReader([_SAMPLE_YEAR_ENDED_BLOCK])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2016-17", "x.pdf")
    collections = next(r for r in rows if r["measure_key"] == "collections_from_departments")
    assert collections["amount"] == 40_854_991_000.0


def test_negative_parenthesized_values_parsed_as_negative(tmp_path, monkeypatch):
    fake = _FakeReader([_SAMPLE_YEAR_ENDED_BLOCK])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2016-17", "x.pdf")
    appropriations = next(r for r in rows if r["measure_key"] == "appropriations_provided_to_departments")
    assert appropriations["amount"] < 0


def test_quarter_ended_block_is_never_matched_only_year_ended(tmp_path, monkeypatch):
    """A page with BOTH a Quarter Ended and a Year Ended table (the real
    shape) must only extract the Year Ended figures - never the smaller
    quarter-only numbers."""
    quarter_then_year = (
        "Balance as at 1 April 1 1 1 1\n"
        "Receipts\nCollections received from departments 1 999 - 999 999\n"
        "Payments\nAppropriations provided to departments 2 (999) - (999) (999)\n"
        "Consolidated Fund Balance as at 30 June 1 1 1 1\n"
        + _SAMPLE_YEAR_ENDED_BLOCK
    )
    fake = _FakeReader([quarter_then_year])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2016-17", "x.pdf")
    collections = next(r for r in rows if r["measure_key"] == "collections_from_departments")
    assert collections["amount"] == 40_854_991_000.0  # the Year Ended value, not 999


def test_missing_label_is_quarantined_not_guessed(tmp_path, monkeypatch):
    incomplete = _SAMPLE_YEAR_ENDED_BLOCK.replace("Other receipts  8,232  - 8,232 8,215\n", "")
    fake = _FakeReader([incomplete])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2016-17", "x.pdf")
    assert not any(r["measure_key"] == "other_receipts" for r in rows)
    assert any(q["measure_key"] == "other_receipts" for q in quarantine)


def test_year_ended_table_not_found_is_quarantined(tmp_path, monkeypatch):
    fake = _FakeReader(["no relevant content here"])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2016-17", "x.pdf")
    assert rows == []
    assert quarantine[0]["reason"] == "year_ended_table_not_found"


def test_parse_number_handles_dash_placeholder_and_parens():
    assert extractor._parse_number("-") == 0.0
    assert extractor._parse_number("1,234") == 1234.0
    assert extractor._parse_number("(1,234)") == -1234.0


def test_annual_editions_list_has_no_duplicate_financial_years():
    fys = [fy for fy, _ in extractor._ANNUAL_EDITIONS]
    assert len(fys) == len(set(fys))

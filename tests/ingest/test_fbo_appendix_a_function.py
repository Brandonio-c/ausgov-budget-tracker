"""Tests for the pre-2019 FBO Appendix A: Expenses by Function and
Sub-function extractor (item 8.1, first two sub-generations).

Focuses on the page-anchor page-range detection (case-insensitive, both
physical heading forms, Table-of-Contents exclusion), the middle
("Estimate at Outcome") column selection out of both the 3-numeric-
column (FY2010-11/FY2011-12) and 4-numeric-column (FY2012-13/FY2013-14)
layouts, and negative/quarantine handling.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import fbo_appendix_a_function as extractor  # noqa: E402


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, pages: list[str]) -> None:
        self.pages = [_FakePage(p) for p in pages]


_SAMPLE_BLOCK = """
Appendix A: Expenses by Function and Sub-function

                                              2009-10    2010-11    2011-12
                                              Outcome    Estimate   Budget
                                                         at Outcome
General public services
Total general public services                 20,000     21,239     22,000
Defence                                        19,500     20,136     21,000
Public debt interest                            5,100      5,300      5,500
Contingency reserve                                 -     (1,468)         -
Total other purposes                           63,000     64,692     66,000
Total expenses                                340,000    350,803    360,000
"""


_SAMPLE_BLOCK_4COL = """
Appendix A: Expenses by Function and Sub-function

                                              2011-12    2012-13    2012-13    Change on
                                              Outcome    Estimate   2013-14    2013-14
                                                         at Outcome Budget     Budget

General public services
Total general public services                 23,419     25,555     25,956        401
Defence                                        21,692     21,122     21,146         24
Public debt interest                           11,421     12,209     12,521        312
Contingency reserve                                 0     (1,301)         0      1,301
Total other purposes                           70,253     70,741     72,623      1,830
Total expenses                                378,005    381,439    382,644      1,205
"""


def _toc_page(text: str = "Appendix A: Expenses by Function and Sub-function .......... 105") -> str:
    return text


def test_extract_edition_parses_real_shaped_block_and_takes_middle_column(tmp_path, monkeypatch):
    # Real editions never have Appendix A within the first 50 pages, so the
    # sample page must be placed after that boundary to be found.
    pages = ["front matter"] * 60 + [_SAMPLE_BLOCK]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")

    rows, quarantine = extractor.extract_edition(path, "2010-11", "x.pdf")
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["general_public_services"] == pytest.approx(21_239.0)
    assert by_key["defence"] == pytest.approx(20_136.0)
    assert by_key["public_debt_interest"] == pytest.approx(5_300.0)
    assert by_key["total_expenses"] == pytest.approx(350_803.0)


def test_negative_parenthesized_values_parsed_as_negative(tmp_path, monkeypatch):
    pages = ["front matter"] * 60 + [_SAMPLE_BLOCK]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")

    rows, _ = extractor.extract_edition(path, "2010-11", "x.pdf")
    contingency = next(r for r in rows if r["measure_key"] == "contingency_reserve")
    assert contingency["amount"] == -1_468.0


def test_table_of_contents_mention_before_page_50_is_never_matched():
    pages = [_toc_page()] * 5 + ["front matter"] * 55 + [_SAMPLE_BLOCK]
    fake = _FakeReader(pages)
    found = extractor._find_appendix_a_pages(fake)
    assert found == [61]  # only the real table page, never the page-5 TOC mention
    assert all(p > 50 for p in found)


def test_case_insensitive_anchor_matches_both_heading_forms(tmp_path, monkeypatch):
    """The genuine first page uses an all-caps chapter-heading form; every
    continuation page uses a title-case running-header form."""
    chapter_heading = _SAMPLE_BLOCK.replace(
        "Appendix A: Expenses by Function and Sub-function",
        "APPENDIX A: EXPENSES BY FUNCTION AND SUB-FUNCTION",
    )
    pages = ["front matter"] * 60 + [chapter_heading]
    fake = _FakeReader(pages)
    found = extractor._find_appendix_a_pages(fake)
    assert found == [61]


def test_appendix_a_pages_not_found_is_quarantined(tmp_path, monkeypatch):
    fake = _FakeReader(["no relevant content here"] * 60)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2010-11", "x.pdf")
    assert rows == []
    assert quarantine[0]["reason"] == "appendix_a_pages_not_found"


def test_missing_label_is_quarantined_not_guessed(tmp_path, monkeypatch):
    incomplete = _SAMPLE_BLOCK.replace("Contingency reserve                                 -     (1,468)         -\n", "")
    pages = ["front matter"] * 60 + [incomplete]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2010-11", "x.pdf")
    assert not any(r["measure_key"] == "contingency_reserve" for r in rows)
    assert any(q["measure_key"] == "contingency_reserve" for q in quarantine)


def test_parse_number_handles_dash_placeholder_and_parens():
    assert extractor._parse_number("-") == 0.0
    assert extractor._parse_number("1,234") == 1234.0
    assert extractor._parse_number("(1,234)") == -1234.0


def test_editions_list_is_only_the_confirmed_tractable_seven_year_slice():
    fys = [fy for fy, _, _ in extractor._EDITIONS]
    assert fys == ["2010-11", "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17"]
    assert len(fys) == len(set(fys))


def test_editions_carry_their_own_verified_column_count():
    by_fy = {fy: n for fy, _, n in extractor._EDITIONS}
    assert by_fy["2010-11"] == 3
    assert by_fy["2011-12"] == 3
    assert by_fy["2012-13"] == 4
    assert by_fy["2013-14"] == 4
    assert by_fy["2014-15"] == 4
    assert by_fy["2015-16"] == 4
    assert by_fy["2016-17"] == 4


def test_four_column_layout_still_extracts_the_second_estimate_at_outcome_column(tmp_path, monkeypatch):
    """FY2012-13/FY2013-14 add a trailing 4th "Change on Budget" column -
    the extractor must still take the 2nd numeric column, never the
    trailing one, and never be thrown off by the extra column."""
    pages = ["front matter"] * 60 + [_SAMPLE_BLOCK_4COL]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")

    rows, quarantine = extractor.extract_edition(path, "2012-13", "x.pdf", num_columns=4)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["general_public_services"] == pytest.approx(25_555.0)
    assert by_key["defence"] == pytest.approx(21_122.0)
    assert by_key["public_debt_interest"] == pytest.approx(12_209.0)
    assert by_key["contingency_reserve"] == pytest.approx(-1_301.0)
    assert by_key["total_other_purposes"] == pytest.approx(70_741.0)
    assert by_key["total_expenses"] == pytest.approx(381_439.0)

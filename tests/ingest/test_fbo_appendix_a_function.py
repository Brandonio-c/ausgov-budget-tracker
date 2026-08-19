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


_SAMPLE_BLOCK_5COL = """
Appendix A: Expenses by Function and Sub-function

                                              2016-17    2017-18    2018-19    2017-18    Change on
                                              Outcome    Budget     Budget     Estimate   2017-18
                                                                                at Outcome Budget

General public services
Total general public services                 26,280     20,703     24,975     24,521      3,818
Defence                                        28,051     30,051     30,982     29,288       -763
Public debt interest                           16,076     17,154     17,047     17,025       -129
Contingency reserve                                 0     (1,301)         0    (2,500)      -2,500
Total other purposes                           93,057     94,000     95,000     93,057          0
Total expenses                                460,282    461,000    462,000    460,282          0
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


def test_five_column_layout_extracts_column_four_not_column_two(tmp_path, monkeypatch):
    """FY2017-18/FY2018-19 have a genuinely different column ORDER -
    "Estimate at Outcome" is column 4, not column 2. Column 2 in this
    layout is a Budget forecast; blindly reusing the earlier years'
    column-2 convention here would silently load a forecast as an
    actual, so this must be a distinct, explicit assertion."""
    pages = ["front matter"] * 60 + [_SAMPLE_BLOCK_5COL]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")

    rows, quarantine = extractor.extract_edition(
        path, "2017-18", "x.pdf", num_columns=5, outcome_column_index=4
    )
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["general_public_services"] == pytest.approx(24_521.0)
    assert by_key["defence"] == pytest.approx(29_288.0)
    assert by_key["contingency_reserve"] == pytest.approx(-2_500.0)  # not -1,301 (column 2)
    assert by_key["total_expenses"] == pytest.approx(460_282.0)  # not 461,000 (column 2)


def test_editions_list_is_only_the_confirmed_tractable_twenty_year_slice():
    fys = [fy for fy, _, _, _, _, _ in extractor._EDITIONS]
    assert fys == [
        "1999-00", "2000-01", "2001-02", "2002-03", "2003-04",
        "2004-05", "2005-06", "2006-07", "2007-08", "2008-09", "2009-10", "2010-11",
        "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17", "2017-18", "2018-19",
    ]
    assert len(fys) == len(set(fys))
    assert "1998-99" not in fys  # predates accrual/functional reporting - permanently excluded


def test_editions_carry_their_own_verified_column_count_and_outcome_index():
    by_fy = {fy: (n, idx) for fy, _, _, n, idx, _ in extractor._EDITIONS}
    assert by_fy["1999-00"] == (2, 2)
    assert by_fy["2000-01"] == (2, 2)
    assert by_fy["2001-02"] == (3, 3)
    assert by_fy["2002-03"] == (3, 3)
    assert by_fy["2003-04"] == (3, 3)
    assert by_fy["2004-05"] == (3, 2)
    assert by_fy["2005-06"] == (3, 2)
    assert by_fy["2006-07"] == (3, 2)
    assert by_fy["2007-08"] == (3, 2)
    assert by_fy["2008-09"] == (3, 2)
    assert by_fy["2009-10"] == (3, 2)
    assert by_fy["2010-11"] == (3, 2)
    assert by_fy["2011-12"] == (3, 2)
    assert by_fy["2012-13"] == (4, 2)
    assert by_fy["2013-14"] == (4, 2)
    assert by_fy["2014-15"] == (4, 2)
    assert by_fy["2015-16"] == (4, 2)
    assert by_fy["2016-17"] == (4, 2)
    assert by_fy["2017-18"] == (5, 4)
    assert by_fy["2018-19"] == (5, 4)


def test_editions_needs_shift_decode_only_for_the_three_broken_font_files():
    by_fy = {fy: shift for fy, _, _, _, _, shift in extractor._EDITIONS}
    assert by_fy["1999-00"] is True
    assert by_fy["2001-02"] is True
    assert by_fy["2002-03"] is True
    assert by_fy["2000-01"] is False
    assert by_fy["2003-04"] is False
    assert by_fy["2010-11"] is False


def test_editions_pre_2010_11_resolve_to_their_own_snapshot_directory():
    by_fy = {fy: snap for fy, snap, _, _, _, _ in extractor._EDITIONS}
    assert by_fy["2007-08"] == "20260723T033738Z"
    assert by_fy["2008-09"] == "20260723T031046Z"
    assert by_fy["2009-10"] == "20260723T031046Z"
    assert by_fy["2010-11"] is None


def test_decode_shift29_recovers_real_words():
    assert extractor._decode_shift29("7DEOH") == "Table"
    assert extractor._decode_shift29("&RPPRQZHDOWK") == "Commonwealth"
    assert extractor._decode_shift29("hello world") != "hello world"  # non-space chars do shift


def test_two_column_layout_has_no_prior_year_comparative(tmp_path, monkeypatch):
    """FY1999-00/FY2000-01 have only 2 numeric columns (next-year Budget
    then current-year Estimate at Outcome) - no prior-year column at
    all, unlike every other loaded sub-generation."""
    block = """
Appendix B: Expenses by Function and Sub-function

                                    2000-01    1999-00
                                    Budget     Outcome

General public services
Total general public services         600        573
Defence                            10,500     9,956
Total expenses                    148,000    145,000
"""
    pages = ["front matter"] * 60 + [block]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "1999-00", "x.pdf", num_columns=2, outcome_column_index=2)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["general_public_services"] == pytest.approx(573.0)
    assert by_key["defence"] == pytest.approx(9_956.0)


def test_three_column_layout_with_outcome_in_column_three_not_two(tmp_path, monkeypatch):
    """FY2001-02/FY2002-03/FY2003-04 have Estimate at Outcome in column
    3 (prior-year Outcome | next-year Budget | current-year Estimate at
    Outcome) - a blind column-2 read would load the next year's Budget
    forecast as an actual."""
    block = """
Appendix B: Expenses by Function and Sub-function

                                    2000-01    2002-03    2001-02
                                    Outcome    Budget     Outcome

General public services
Total general public services         600        650        778
Defence                             9,956     11,200     12,017
Total expenses                    145,000    150,000    148,000
"""
    pages = ["front matter"] * 60 + [block]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2001-02", "x.pdf", num_columns=3, outcome_column_index=3)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["general_public_services"] == pytest.approx(778.0)  # column 3, not column 2 (650)
    assert by_key["defence"] == pytest.approx(12_017.0)


def test_bare_letter_footnote_with_no_parentheses_is_tolerated(tmp_path, monkeypatch):
    """The 2002-03 file's decoded text has footnote markers as a bare
    space-separated letter with no parentheses (e.g. "Total health a"),
    a different real form from "Defence(a)"."""
    block_with_bare_footnote = _SAMPLE_BLOCK_4COL.replace(
        "Total other purposes", "Total other purposes a"
    )
    pages = ["front matter"] * 60 + [block_with_bare_footnote]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2012-13", "x.pdf", num_columns=4)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["total_other_purposes"] == pytest.approx(70_741.0)


def test_agriculture_label_accepts_the_reordered_1999_00_wording(tmp_path, monkeypatch):
    """FY1999-00 words this label "Total agriculture, fisheries and
    forestry" - the same concept, reordered - not "...forestry and
    fishing" used everywhere else."""
    block = _SAMPLE_BLOCK_4COL.replace(
        "Total other purposes", "Total agriculture, fisheries and forestry"
    )
    pages = ["front matter"] * 60 + [block]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "1999-00", "x.pdf", num_columns=4)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["agriculture_forestry_fishing"] == pytest.approx(70_741.0)


def test_defence_and_contingency_reserve_tolerate_a_footnote_marker(tmp_path, monkeypatch):
    """FY2007-08's real file has "Defence(a)" and "Contingency reserve(c)"
    - a footnote letter directly attached with no space - which the
    label regex must still match."""
    block_with_footnotes = _SAMPLE_BLOCK_4COL.replace("Defence", "Defence(a)").replace(
        "Contingency reserve", "Contingency reserve(c)"
    )
    pages = ["front matter"] * 60 + [block_with_footnotes]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2012-13", "x.pdf", num_columns=4)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["defence"] == pytest.approx(21_122.0)
    assert by_key["contingency_reserve"] == pytest.approx(-1_301.0)


def test_label_matching_is_case_insensitive(tmp_path, monkeypatch):
    """The 2004-05 file has "Total Transport and Communication"
    (title-cased) where every other edition uses lowercase - the label
    regex must still match regardless of case."""
    block = _SAMPLE_BLOCK_4COL.replace(
        "Total other purposes", "TOTAL OTHER PURPOSES"
    )
    pages = ["front matter"] * 60 + [block]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2012-13", "x.pdf", num_columns=4)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["total_other_purposes"] == pytest.approx(70_741.0)


def test_mining_manufacturing_construction_tolerates_an_ampersand(tmp_path, monkeypatch):
    """Pre-2007-08 editions use "Mining, manufacturing & construction"
    (an ampersand) instead of "...and construction"."""
    block = _SAMPLE_BLOCK_4COL.replace(
        "Total other purposes", "Mining, manufacturing & construction"
    )
    pages = ["front matter"] * 60 + [block]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2012-13", "x.pdf", num_columns=4)
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["mining_manufacturing_construction"] == pytest.approx(70_741.0)


def test_num_pattern_rejects_a_stray_space_inside_a_thousands_group(tmp_path, monkeypatch):
    """A real PDF-text-extraction defect found in the 2008-09 file: a
    stray space inserted right after a thousands comma (e.g. "5, 926"
    for "5,926") must not be read as two separate numbers - each comma
    group must be exactly 3 digits."""
    block = _SAMPLE_BLOCK.replace("21,239", "21, 239")
    pages = ["front matter"] * 60 + [block]
    fake = _FakeReader(pages)
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2010-11", "x.pdf")
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["general_public_services"] == pytest.approx(21_239.0)


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

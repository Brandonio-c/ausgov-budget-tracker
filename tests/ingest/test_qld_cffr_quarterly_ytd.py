"""Tests for the Queensland CFFR quarterly Year-to-Date extractor (item
7.4, quarterly slice).

Focuses on the shared block-location technique (always the LAST "Balance
as at 1 July" occurrence, which is the genuine Year-to-Date block for
every quarter type - the quarter-only "Quarter Ended" table present for
Dec/Mar editions opens with a different label and is never matched),
the missing-space tolerance found in 3 real September editions, and the
same $'000 scaling / negative-parenthesized-value handling already
proven for the annual editions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import qld_cffr_quarterly_ytd as extractor  # noqa: E402


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, pages: list[str]) -> None:
        self.pages = [_FakePage(p) for p in pages]


_SAMPLE_YTD_BLOCK = """
Balance as at 1 July (4,287,355) 33,267,758 28,980,403 26,621,065
Receipts
Collections received from departments 1 54,188,970 - 54,188,970 43,005,475
Investment interest 1,653,355 - 1,653,355 1,431,974
Dividends and income tax equivalents 758,250 - 758,250 1,078,239
Non-appropriated equity adjustments 2,555,758 - 2,555,758 2,821,426
Superannuation, long service leave, Queensland
Government Insurance Fund and ALCS contributions 3,039,690 - 3,039,690 2,761,892
Capital return from public enterprise investments 90,000 - 90,000 99,600
Other receipts 960 - 960 1,053
62,286,983 - 62,286,983 51,199,659
Payments
Appropriations provided to departments 2 (52,833,589) - (52,833,589) (48,765,872)
(52,833,589) - (52,833,589) (48,765,872)
Net effect of investments
Funds transfer to/from Treasurer's account (5,491,229) 5,491,229 - -
Consolidated Fund Balance as at 31 March (325,190) 38,758,987 38,433,797 29,054,852
Notes:
1. Refer to statement of Collections Received from Departments.
"""


def test_extract_edition_parses_real_shaped_ytd_block(tmp_path, monkeypatch):
    fake = _FakeReader([_SAMPLE_YTD_BLOCK])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")

    rows, quarantine = extractor.extract_edition(path, "2022-23", 3, "x.pdf")
    assert quarantine == []
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["opening_balance"] == pytest.approx(28_980_403_000)
    assert by_key["closing_balance"] == pytest.approx(38_433_797_000)
    assert by_key["collections_from_departments"] == pytest.approx(54_188_970_000)
    assert by_key["appropriations_provided_to_departments"] == pytest.approx(-52_833_589_000)


def test_amounts_are_scaled_from_thousands_to_real_aud(tmp_path, monkeypatch):
    fake = _FakeReader([_SAMPLE_YTD_BLOCK])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2022-23", 3, "x.pdf")
    collections = next(r for r in rows if r["measure_key"] == "collections_from_departments")
    assert collections["amount"] == 54_188_970_000.0


def test_negative_parenthesized_values_parsed_as_negative(tmp_path, monkeypatch):
    fake = _FakeReader([_SAMPLE_YTD_BLOCK])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2022-23", 3, "x.pdf")
    appropriations = next(r for r in rows if r["measure_key"] == "appropriations_provided_to_departments")
    assert appropriations["amount"] < 0


def test_quarter_only_table_is_never_matched_only_year_to_date(tmp_path, monkeypatch):
    """A page with BOTH a Quarter Ended (opening with "Balance as at 1
    January") and a Year-to-Date table (opening with "Balance as at 1
    July") - the real shape for March editions - must only extract the
    Year-to-Date figures, never the smaller quarter-only numbers."""
    quarter_then_ytd = (
        "Balance as at 1 January 1 1 1 1\n"
        "Receipts\nCollections received from departments 1 999 - 999 999\n"
        "Payments\nAppropriations provided to departments 2 (999) - (999) (999)\n"
        "Consolidated Fund Balance as at 31 March 1 1 1 1\n"
        + _SAMPLE_YTD_BLOCK
    )
    fake = _FakeReader([quarter_then_ytd])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, _ = extractor.extract_edition(path, "2022-23", 3, "x.pdf")
    collections = next(r for r in rows if r["measure_key"] == "collections_from_departments")
    assert collections["amount"] == 54_188_970_000.0  # the YTD value, not 999


def test_missing_space_before_july_is_tolerated(tmp_path, monkeypatch):
    """3 real September editions render "Balance as at 1July" with no
    space - confirmed directly in CFFR-Sept-2020-Tables.pdf and others."""
    no_space_block = _SAMPLE_YTD_BLOCK.replace("Balance as at 1 July", "Balance as at 1July")
    fake = _FakeReader([no_space_block])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2020-21", 1, "x.pdf")
    by_key = {r["measure_key"]: r["amount"] for r in rows}
    assert by_key["opening_balance"] == pytest.approx(28_980_403_000)


def test_missing_label_is_quarantined_not_guessed(tmp_path, monkeypatch):
    incomplete = _SAMPLE_YTD_BLOCK.replace("Other receipts 960 - 960 1,053\n", "")
    fake = _FakeReader([incomplete])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2022-23", 3, "x.pdf")
    assert not any(r["measure_key"] == "other_receipts" for r in rows)
    assert any(q["measure_key"] == "other_receipts" for q in quarantine)


def test_ytd_table_not_found_is_quarantined(tmp_path, monkeypatch):
    fake = _FakeReader(["no relevant content here"])
    monkeypatch.setattr(extractor, "PdfReader", lambda _path: fake)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2022-23", 3, "x.pdf")
    assert rows == []
    assert quarantine[0]["reason"] == "ytd_table_not_found"


def test_unreadable_pdf_is_quarantined_not_silently_skipped(tmp_path, monkeypatch):
    def _raise(_path):
        raise ValueError("no text layer")

    monkeypatch.setattr(extractor, "PdfReader", _raise)
    path = tmp_path / "x.pdf"
    path.write_bytes(b"stub")
    rows, quarantine = extractor.extract_edition(path, "2025-26", 1, "x.pdf")
    assert rows == []
    assert quarantine[0]["reason"] == "unreadable_pdf"


def test_parse_number_handles_dash_placeholder_and_parens():
    assert extractor._parse_number("-") == 0.0
    assert extractor._parse_number("1,234") == 1234.0
    assert extractor._parse_number("(1,234)") == -1234.0


def test_editions_list_has_no_duplicate_financial_year_quarter_pairs():
    keys = [(fy, q) for fy, q, _ in extractor._EDITIONS]
    assert len(keys) == len(set(keys))


def test_editions_list_excludes_known_unreadable_and_incompatible_files():
    filenames = [f for _, _, f in extractor._EDITIONS]
    assert "cffr-sept-2025.pdf" not in filenames  # zero extractable text
    assert "quarterly-statement-consolidated-fund-dec2025.pdf" not in filenames  # positionally broken
    assert "consolidated-fund-2012-march.pdf" not in filenames  # OCR-corrupted, pre-2017 era

    fys = [fy for fy, _, _ in extractor._EDITIONS]
    assert min(fys) >= "2016-17"  # 2017+ slice only, per the scoping report

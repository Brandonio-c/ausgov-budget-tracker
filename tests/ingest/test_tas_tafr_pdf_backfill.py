"""Task 5/8 of the PDF/OCR-focused milestone: consolidated tests for
the TAS TAFR PDF backfill extractor and loader - page/table
disambiguation (General Government Sector only, never Total State
Sector), space-thousands-separator and parenthesized-negative number
parsing, stray-parenthesis-artifact handling, excluded "Underlying"
measure, cross-table duplicate absorption (Net Operating Balance /
Fiscal Balance), period granularity, revision policy (disjoint years
from the xlsx family, 'budget' vs 'revised_estimate'), idempotent
reload, citation preservation, and quarantine behavior.

Uses synthetic fixture PDFs built with reportlab-free raw pypdf/
pdfwriter text placement is avoided - instead we monkeypatch the
extractor's own page-reading entry points isn't necessary either: we
build minimal real PDFs whose extracted text reproduces the exact line
shapes the real editions have, using the `fpdf`-free simplest approach
available in this repo's dependencies - reuse of `pypdf`'s writer is
overkill for text-only fixtures, so a tiny handwritten single-page PDF
content stream is used instead, keeping the fixture minimal and
dependency-free.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest" / "extractors"))

import reload_tas_tafr_pdf_backfill as loader  # noqa: E402
import tas_tafr_pdf_backfill as extractor  # noqa: E402
from schema_migrate import migrate  # noqa: E402

# ---- number / token parsing ---------------------------------------------


@pytest.mark.parametrize(
    "token,expected",
    [
        ("134", 134.0),
        ("(220)", -220.0),
        ("13 130", 13130.0),
        ("(409)", -409.0),
        ("4 638", 4638.0),
    ],
)
def test_parse_number_token(token, expected):
    assert extractor._parse_number_token(token) == expected


def test_parse_number_token_strips_stray_trailing_paren_as_noise():
    # A lone trailing ")" with no matching leading "(" is a pypdf
    # text-extraction artifact, not a negative-sign marker.
    assert extractor._parse_number_token("69)") == 69.0


def test_extract_row_tokens_returns_none_for_non_matching_line():
    assert extractor._extract_row_tokens("Some other line", "Net Debt") is None


def test_extract_row_tokens_parses_three_columns():
    values = extractor._extract_row_tokens("Net Worth 13 130  11 792  11 066  ", "Net Worth")
    assert values == [13130.0, 11792.0, 11066.0]


def test_extract_row_tokens_parses_mixed_sign_row():
    # Real 2012-13 data: Budget positive, Actual/Prior negative.
    values = extractor._extract_row_tokens("Net Debt 134  (220) (409) ", "Net Debt")
    assert values == [134.0, -220.0, -409.0]


# ---- fixture PDF construction ---------------------------------------------


def _esc_to_winansi_bytes(s: str) -> bytes:
    """Encodes to cp1252 (WinAnsiEncoding-compatible, including the
    en-dash at 0x96 used by the real source PDFs) and escapes PDF
    string-literal special characters at the byte level."""
    raw = s.encode("cp1252")
    escaped = raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return escaped


def _make_pdf_bytes(page_texts: list[str]) -> bytes:
    """Builds a minimal multi-page PDF whose Tj-per-line content
    stream reproduces the given plain-text lines exactly as pypdf
    would extract them (one BT/Tj/ET per line, left-aligned). The font
    declares /Encoding /WinAnsiEncoding so non-ASCII characters (the
    en-dash used by the real source PDFs) round-trip correctly."""
    objects: list[bytes] = []

    page_ids = []
    content_ids = []
    n = len(page_texts)
    catalog_id = 1
    pages_id = 2
    font_id = 3
    first_page_obj_id = 4
    for i in range(n):
        page_ids.append(first_page_obj_id + i * 2)
        content_ids.append(first_page_obj_id + i * 2 + 1)

    objects.append(f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R >>\nendobj\n".encode())
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(
        f"{pages_id} 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {n} >>\nendobj\n".encode()
    )
    objects.append(
        (
            f"{font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            f"/Encoding /WinAnsiEncoding >>\nendobj\n"
        ).encode()
    )

    for i, text in enumerate(page_texts):
        page_id = page_ids[i]
        content_id = content_ids[i]
        lines = text.split("\n")
        stream_lines: list[bytes] = [b"BT", b"/F1 10 Tf", b"12 TL", b"50 750 Td"]
        for j, line in enumerate(lines):
            if j > 0:
                stream_lines.append(b"T*")
            stream_lines.append(b"(" + _esc_to_winansi_bytes(line) + b") Tj")
        stream_lines.append(b"ET")
        stream = b"\n".join(stream_lines)
        objects.append(
            (
                f"{page_id} 0 obj\n<< /Type /Page /Parent {pages_id} 0 R "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/MediaBox [0 0 612 792] /Contents {content_id} 0 R >>\nendobj\n"
            ).encode()
        )
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode()
            + stream
            + b"\nendstream\nendobj\n"
        )

    header = b"%PDF-1.4\n"
    body = b""
    offsets = [0]
    pos = len(header)
    for obj in objects:
        offsets.append(pos)
        body += obj
        pos += len(obj)
    xref_start = len(header) + len(body)
    all_ids = [catalog_id, pages_id, font_id] + page_ids + content_ids
    max_id = max(all_ids)
    xref_lines = ["0000000000 65535 f \n"]
    offset_by_id = {}
    running = len(header)
    for obj in objects:
        obj_id = int(obj.split(b" ")[0])
        offset_by_id[obj_id] = running
        running += len(obj)
    for oid in range(1, max_id + 1):
        if oid in offset_by_id:
            xref_lines.append(f"{offset_by_id[oid]:010d} 00000 n \n")
        else:
            xref_lines.append("0000000000 65535 f \n")
    xref = f"xref\n0 {max_id + 1}\n".encode() + "".join(xref_lines).encode()
    trailer = (
        f"trailer\n<< /Size {max_id + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_start}\n%%EOF"
    ).encode()
    return header + body + xref + trailer


def _write_edition_pdf(path: Path) -> None:
    """A 7-page fixture reproducing the real editions' page layout:
    pages 0-5 filler, page 6 = Key Financial Indicators (GGS then Total
    State), page 7 = Summary of Operating Result (GGS only, kept
    minimal - Total State's own page is omitted since only the FIRST
    match is ever taken)."""
    filler = "Filler page"
    kfi_page = (
        "Table 2.1: Key Financial Indicators\n"
        "General Government Sector\n"
        "Net Operating Surplus/(Deficit) (65) (23) 18 \n"
        "Fiscal Surplus/(Deficit) (530) (446) (291) \n"
        "Net Debt (309) (416) (748) \n"
        "Net Worth 14 211 12 492  13 065 \n"
        "Net Financial Liabilities 3 487 4 146  3 814 \n"
        "Total State Sector\n"
        "Net Operating Surplus/(Deficit) 69) 132  192 \n"
        "Net Debt 1 669  1 309  962 \n"
    )
    opres_page = (
        "GENERAL GOVERNMENT OUTCOME\n"
        "Table 2.2: General Government Sector Summary of Operating\n"
        "Result\n"
        "Revenue from transactions 4 563  4 767  204  4 \n"
        "Expenses from transactions 4 627  4 790  163  4 \n"
        "Net Operating Balance – Surplus/(Deficit) (65) (23) 42  65 \n"
        "Equals Fiscal Balance – Surplus/(Deficit) (530) (446) 84  16 \n"
        "Revenue from transactions was $4  767 million in narrative text that also starts with the row label\n"
    )
    pages = [filler] * 6 + [kfi_page, opres_page]
    path.write_bytes(_make_pdf_bytes(pages))


def _write_edition_pdf_with_underlying(path: Path) -> None:
    filler = "Filler page"
    kfi_page = (
        "Table 2.1: Key Financial Indicators\n"
        "General Government Sector\n"
        "Net Operating Surplus/(Deficit) (114) (186) (23) \n"
        "Underlying Net Operating Surplus/(Deficit) (269) (348) (557) \n"
        "Fiscal Surplus/(Deficit) (359) (262) (446) \n"
        "Net Debt (53) (409) (416) \n"
        "Net Worth 13 755  11 066  12 492 \n"
        "Net Financial Liabilities 4 795  6 123  4 146 \n"
        "Total State Sector\n"
        "Net Operating Surplus/(Deficit) 21  1  132 \n"
    )
    opres_page = (
        "General Government Outcome\n"
        "Table 2.3: General Government Summary Operating Result\n"
        "Revenue from transactions 4 618  4 690  72  2 \n"
        "Expense from transactions 4 732  4 876  144  3 \n"
        "Net Operating Balance – Surplus/(Deficit) (114) (186) (72) (63) \n"
        "Equals Fiscal Balance – Surplus/(Deficit) (359) (262) 97  27 \n"
    )
    pages = [filler] * 6 + [kfi_page, opres_page]
    path.write_bytes(_make_pdf_bytes(pages))


# ---- extractor: fixture PDFs ------------------------------------------


def test_extractor_finds_ggs_only_kfi_block(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2010-11")
    net_debt_rows = [r for r in rows if r["measure_type"] == "tas_ggs_net_debt"]
    amounts = {r["estimate_status"]: r["amount_million_aud"] for r in net_debt_rows}
    assert amounts == {"budget": -309.0, "actual": -416.0}
    # Total State Sector's own Net Debt row (1 669 / 1 309) must never appear
    assert -1669.0 not in [r["amount_million_aud"] for r in rows]
    assert 1669.0 not in [r["amount_million_aud"] for r in rows]


def test_extractor_excludes_underlying_measure(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf_with_underlying(path)
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2011-12")
    reasons = {q["reason"] for q in quarantine}
    assert "excluded_underlying_measure" in reasons
    amounts = [r["amount_million_aud"] for r in rows]
    assert -269.0 not in amounts and -348.0 not in amounts


def test_extractor_parses_mixed_sign_net_debt(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, _ = extractor.extract_pdf_edition(path, "test_source", "2010-11")
    net_debt = [r for r in rows if r["measure_type"] == "tas_ggs_net_debt"]
    assert {r["amount_million_aud"] for r in net_debt} == {-309.0, -416.0}


def test_extractor_cross_table_duplicate_values_match(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, _ = extractor.extract_pdf_edition(path, "test_source", "2010-11")
    nob_rows = [r for r in rows if r["measure_type"] == "tas_ggs_net_operating_balance" and r["estimate_status"] == "actual"]
    assert len(nob_rows) == 2
    assert nob_rows[0]["amount_million_aud"] == nob_rows[1]["amount_million_aud"] == -23.0
    assert {r["source_table"] for r in nob_rows} == {"Key Financial Indicators", "Summary of Operating Result"}


def test_extractor_quarantines_narrative_false_positive(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    _, quarantine = extractor.extract_pdf_edition(path, "test_source", "2010-11")
    reasons = [q["reason"] for q in quarantine]
    assert "unparseable_or_unexpected_token_count" in reasons


def test_extractor_negative_values_preserved(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, _ = extractor.extract_pdf_edition(path, "test_source", "2010-11")
    fiscal_balance_budget = [
        r for r in rows if r["measure_type"] == "tas_ggs_fiscal_balance" and r["estimate_status"] == "budget"
    ]
    assert all(r["amount_million_aud"] == -530.0 for r in fiscal_balance_budget)


def test_extractor_all_editions(tmp_path):
    ed1 = tmp_path / "TAF-2010-11.pdf"
    ed2 = tmp_path / "2011-12-Treasurers-Annual-Financial-Report.pdf"
    ed3 = tmp_path / "2012-13-Treasurers-Annual-Financial-Report.pdf"
    _write_edition_pdf(ed1)
    _write_edition_pdf_with_underlying(ed2)
    _write_edition_pdf_with_underlying(ed3)
    rows, quarantine = extractor.extract_all_editions("test_source", snapshot_dir=tmp_path)
    fys = {r["financial_year"] for r in rows}
    assert fys == {"2010-11", "2011-12", "2012-13"}


def test_extractor_quarantines_missing_edition_file(tmp_path):
    rows, quarantine = extractor.extract_all_editions("test_source", snapshot_dir=tmp_path)
    assert rows == []
    reasons = {q["reason"] for q in quarantine}
    assert "edition_file_missing_on_disk" in reasons


# ---- loader: classification, scale conversion --------------------------


@pytest.fixture
def semantics():
    return loader.load_semantics()


def _row(measure_type, fy="2010-11", estimate_status="actual", amount=100.0, cached_copy_path=None):
    return {
        "source_id": "tas_treasurer_annual_financial_reports",
        "financial_year": fy,
        "measure_type": measure_type,
        "estimate_status": estimate_status,
        "amount_million_aud": amount,
        "source_table": "Key Financial Indicators",
        "row_label": "Net Debt",
        "locator": f"measure:{measure_type}|{fy}|{estimate_status}",
        "cached_copy_path": cached_copy_path or str(REPO_ROOT / "README.md"),
    }


def test_scale_factor_applied_million_to_aud(semantics):
    row = _row("tas_ggs_net_debt", amount=-416.0)
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["amount_aud"] == -416_000_000.0


def test_unrecognized_measure_type_quarantined(semantics):
    row = _row("not_a_real_measure")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "unrecognized_measure_type"


def test_missing_source_file_quarantined(semantics):
    row = _row("tas_ggs_net_worth", cached_copy_path="data/does/not/exist.pdf")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


def test_stock_measure_has_no_period_start(semantics):
    row = _row("tas_ggs_net_worth")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2011-06-30"


def test_flow_measure_has_period_start_and_end(semantics):
    row = _row("tas_ggs_revenue")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] == "2010-07-01"
    assert fact["period_end"] == "2011-06-30"


def test_budget_and_actual_produce_distinct_fact_keys(semantics):
    budget_row = _row("tas_ggs_net_debt", estimate_status="budget")
    actual_row = _row("tas_ggs_net_debt", estimate_status="actual")
    budget_fact, _ = loader.classify_and_validate(budget_row, semantics)
    actual_fact, _ = loader.classify_and_validate(actual_row, semantics)
    assert budget_fact["fact_key"] != actual_fact["fact_key"]


def test_unexpected_estimate_status_quarantined(semantics):
    row = _row("tas_ggs_net_debt", estimate_status="forward_estimate")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "unexpected_estimate_status"


def test_fact_key_scheme_matches_xlsx_loader_shared_format():
    key = loader.build_fact_key(
        source_id="tas_treasurer_annual_financial_reports", financial_year="2010-11",
        measure_type="tas_ggs_net_debt", accounting_basis="accrual",
        estimate_status="budget", jurisdiction="TAS",
    )
    assert key == "tas_treasurer_annual_financial_reports|2010-11|tas_ggs_net_debt|accrual|budget|TAS"


# ---- loader: full run against a real fixture DB (idempotency, revision, citations) --


@pytest.fixture
def fixture_db(tmp_path, monkeypatch):
    db = tmp_path / "facts.db"
    migrate(db)
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    _write_edition_pdf(snapshot_dir / "TAF-2010-11.pdf")
    _write_edition_pdf_with_underlying(snapshot_dir / "2011-12-Treasurers-Annual-Financial-Report.pdf")
    _write_edition_pdf_with_underlying(snapshot_dir / "2012-13-Treasurers-Annual-Financial-Report.pdf")

    def fake_extract(source_id):
        return extractor.extract_all_editions(source_id, snapshot_dir=snapshot_dir)

    monkeypatch.setattr(loader, "extract_all_editions", fake_extract)
    monkeypatch.setattr(loader, "QUARANTINE_PATH", tmp_path / "q.jsonl")
    return db


def test_full_load_is_idempotent(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    result1 = loader.run(conn, apply=True)
    assert result1["facts_to_insert"] == 42  # 7 measures x 3 editions x 2 estimate_status
    assert result1["revision_conflicts_quarantined"] == 0

    facts_after_first = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    result2 = loader.run(conn, apply=True)
    assert result2["facts_to_insert"] == 0
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
        "SELECT amount_aud FROM facts WHERE measure_type = 'tas_ggs_net_debt' AND financial_year = '2010-11' AND estimate_status = 'actual'"
    ).fetchone()[0]

    fake_fact_key = loader.build_fact_key(
        source_id=loader.SOURCE_ID, financial_year="2010-11", measure_type="tas_ggs_net_debt",
        accounting_basis="accrual", estimate_status="actual", jurisdiction="TAS",
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
        "SELECT source_locator_json FROM facts WHERE measure_type = 'tas_ggs_net_debt' AND financial_year = '2010-11' AND estimate_status = 'actual'"
    ).fetchone()
    payload = json.loads(row[0])
    assert "fy:2010-11" in payload["locator"]
    assert "estimate_status:actual" in payload["locator"]
    assert "row:Net Debt" in payload["locator"]
    assert payload["cached_copy_path"]
    conn.close()


def test_disjoint_years_from_xlsx_family(fixture_db):
    """This adapter must only ever publish years 2010-11 to 2012-13 -
    never overlapping with the xlsx loader's 2013-14-onward coverage."""
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)
    fys = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT financial_year FROM facts WHERE measure_type LIKE 'tas_ggs_%'"
        ).fetchall()
    }
    conn.close()
    assert fys == {"2010-11", "2011-12", "2012-13"}
    assert "2013-14" not in fys


def test_reuses_existing_compatibility_groups_not_new_ones(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)
    rows = conn.execute(
        "SELECT DISTINCT measure_type, compatibility_group FROM measure_definitions "
        "WHERE measure_type IN (SELECT DISTINCT measure_type FROM facts WHERE financial_year IN ('2010-11','2011-12','2012-13'))"
    ).fetchall()
    conn.close()
    assert len(rows) == 7
    for measure_type, group in rows:
        assert group == measure_type  # 1:1, same as the xlsx family

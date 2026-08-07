"""Task 5/8 of the QLD PDF milestone: consolidated tests for the QLD
Report on State Finances extractor and loader - page-location-by-
content, General-Government-Sector-only (first pair) extraction,
comma-thousands-separator and parenthesized-negative number parsing,
bare-hyphen-placeholder tolerance, narrative-false-positive
quarantine, period granularity, vintage semantics ('estimated_actual'
vs 'actual', never 'budget'), revision policy, idempotent reload,
citation preservation, and duplicate prevention.
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

import qld_report_on_state_finances as extractor  # noqa: E402
import reload_qld_report_on_state_finances as loader  # noqa: E402
from schema_migrate import migrate  # noqa: E402

# ---- number / token parsing ---------------------------------------------


@pytest.mark.parametrize(
    "token,expected",
    [
        ("60,068", 60068.0),
        ("(2,677)", -2677.0),
        ("134", 134.0),
        ("(220)", -220.0),
        ("2,623", 2623.0),
    ],
)
def test_parse_number_token(token, expected):
    assert extractor._parse_number_token(token) == expected


def test_parse_number_token_bare_hyphen_returns_none():
    assert extractor._parse_number_token("-") is None


def test_extract_first_two_tokens_returns_none_for_non_matching_line():
    assert extractor._extract_first_two_tokens("Some other line", "Net Debt") is None


def test_extract_first_two_tokens_returns_none_for_bare_label_no_numbers():
    # The narrative-heading false positive: "Revenue" with no numbers.
    assert extractor._extract_first_two_tokens("Revenue", "Revenue") is None


def test_extract_first_two_tokens_takes_only_first_pair():
    values = extractor._extract_first_two_tokens(
        "Revenue 60,068 59,834 13,215 14,256 67,699 68,334", "Revenue"
    )
    assert values == [60068.0, 59834.0]


def test_extract_first_two_tokens_handles_negative_first_pair():
    values = extractor._extract_first_two_tokens(
        "Fiscal balance (2,677) (2,191) 1,446 1,471 (2,868) (2,422)", "Fiscal balance"
    )
    assert values == [-2677.0, -2191.0]


def test_extract_first_two_tokens_tolerates_bare_hyphen_placeholder():
    # Real 2018-19 data: PNFC columns use "-" for nil - GGS pair (first
    # 2) is unaffected and still extracted correctly.
    values = extractor._extract_first_two_tokens(
        "Leases and similar arrangements 2,623 2,612 - - 2,623 2,612",
        "Leases and similar arrangements",
    )
    assert values == [2623.0, 2612.0]


# ---- fixture PDF construction ------------------------------------------


def _esc_to_winansi_bytes(s: str) -> bytes:
    raw = s.encode("cp1252")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _make_pdf_bytes(page_texts: list[str]) -> bytes:
    """Minimal multi-page PDF whose Tj-per-line content stream
    reproduces the given plain-text lines exactly as pypdf would
    extract them."""
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
    objects.append(f"{pages_id} 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {n} >>\nendobj\n".encode())
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
    body = b"".join(objects)
    xref_start = len(header) + len(body)
    all_ids = [catalog_id, pages_id, font_id] + page_ids + content_ids
    max_id = max(all_ids)
    offset_by_id = {}
    running = len(header)
    for obj in objects:
        obj_id = int(obj.split(b" ")[0])
        offset_by_id[obj_id] = running
        running += len(obj)
    xref_lines = ["0000000000 65535 f \n"]
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
    filler = "Filler page"
    table_page = (
        "Outcomes Report - Overview and Analysis\n"
        "Key UPF Financial Aggregates\n"
        "Outlined in the table below are the key aggregates, by sector.\n"
        "General Government Public Non-financial Non-financial Public\n"
        "Sector Corporations Sector Sector\n"
        "Est. Actual Outcome Est. Actual Outcome Est. Actual Outcome\n"
        "$ million $ million $ million $ million $ million $ million\n"
        "Revenue 60,068 59,834 13,215 14,256 67,699 68,334\n"
        "Expenses 59,226 58,842 11,679 12,587 66,965 67,367\n"
        "Net operating balance 841 992 1,536 1,669 734 967\n"
        "Capital purchases 6,060 5,764 2,801 2,687 8,856 8,460\n"
        "Fiscal balance (2,677) (2,191) 1,446 1,471 (2,868) (2,422)\n"
        "Borrowing with QTC 29,933 29,468 38,208 38,108 68,141 67,576\n"
        "Leases and similar arrangements 2,623 2,612 - - 2,623 2,612\n"
        "Securities and derivatives 122 121 549 599 671 720\n"
        "Notes:\n"
        "1. Numbers may not add due to rounding.\n"
        "General Government Sector\n"
        "Revenue\n"
        "Total GGS revenue was $234 million lower than the Budget.\n"
    )
    pages = [filler] * 3 + [table_page]
    path.write_bytes(_make_pdf_bytes(pages))


def _write_edition_pdf_variant(path: Path) -> None:
    filler = "Filler page"
    table_page = (
        "Outcomes Report - Overview and Analysis\n"
        "Key UPF Financial Aggregates\n"
        "General Government Public Non-financial Non-financial Public\n"
        "Sector Corporations Sector Sector\n"
        "Est. Actual Outcome Est. Actual Outcome Est. Actual Outcome\n"
        "$ million $ million $ million $ million $ million $ million\n"
        "Revenue 57,719 57,764 13,623 13,589 66,200 66,156\n"
        "Expenses 63,617 63,498 12,272 12,662 71,825 72,049\n"
        "Net operating balance (5,898) (5,734) 1,351 927 (5,625) (5,893)\n"
        "Capital purchases 6,305 6,291 3,142 3,156 9,447 9,467\n"
        "Fiscal balance (9,318) (9,158) 719 306 (9,678) (9,958)\n"
        "Borrowing with QTC 37,574 37,570 38,904 38,894 76,478 76,464\n"
        "Leases and similar arrangements 6,454 6,499 491 492 6,945 6,991\n"
        "Securities and derivatives 198 198 1,315 1,315 1,513 1,505\n"
        "Notes:\n"
        "1. Numbers may not add due to rounding.\n"
    )
    pages = [filler] * 5 + [table_page]
    path.write_bytes(_make_pdf_bytes(pages))


def _write_older_edition_pdf(path: Path) -> None:
    table_page = (
        "Summary of Key GFS Financial Aggregates\n"
        "General Government Public Non-financial Non-financial Public\n"
        "Sector Corporations Sector Sector\n"
        "Est. Actual Outcome Est. Actual Outcome Est. Actual Outcome\n"
        "$ million $ million $ million $ million $ million $ million\n"
        "Revenue 19,913 20,256 7,335 7,751 24,772 25,423\n"
        "Expenses 20,263 20,241 7,551 7,803 25,337 25,460\n"
        "Net Operating Balance (350) 15 (216) (52) (565) (37)\n"
        "Net Lending/Borrowing (769) (140) (873) (894) (1,640) (1,034)\n"
        "Cash Surplus/(Deficit) 51 645 (583) (722) (530) (78)\n"
        "Gross Fixed Capital Formation 1,779 1,607 1,776 1,948 3,554 3,556\n"
        "Net Worth 58,692 64,894 12,644 12,096 58,692 64,894\n"
        "Net Debt (10,636) (11,260) 10,949 11,479 313 219\n"
    )
    path.write_bytes(_make_pdf_bytes(["Filler", table_page]))


def _write_residual_rows_pdf(path: Path, *, borrowing_label: str = "Borrowing") -> None:
    table_page = (
        "Key UPF Financial Aggregates\n"
        "Revenue 77,000 78,000 10,000 11,000 87,000 89,000\n"
        "Expenses 75,000 76,000 9,000 10,000 84,000 86,000\n"
        "Borrowing with QTC 66,766 64,708 40,000 39,000 106,766 103,708\n"
        "Leases and similar arrangements 8,013 8,100 500 500 8,513 8,600\n"
        "Securities and derivatives 64 57 20 20 84 77\n"
        f"{borrowing_label} 74,843 72,864 40,520 39,520 115,363 112,384\n"
        "Net Debt 22,092 16,727 30,000 28,000 52,092 44,727\n"
    )
    path.write_bytes(_make_pdf_bytes([table_page]))


# ---- extractor: fixture PDFs --------------------------------------------


def test_extractor_finds_table_page_by_content_not_fixed_index(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2018-19")
    assert len(rows) == 16  # 8 measures x 2 estimate_status
    variant_path = tmp_path / "edition_variant.pdf"
    _write_edition_pdf_variant(variant_path)
    rows2, _ = extractor.extract_pdf_edition(variant_path, "test_source", "2019-20")
    assert len(rows2) == 16  # same shape found despite the table being on a different page index


def test_extractor_ggs_only_first_pair(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, _ = extractor.extract_pdf_edition(path, "test_source", "2018-19")
    revenue_rows = [r for r in rows if r["measure_type"] == "qld_rsf_revenue"]
    amounts = {r["estimate_status"]: r["amount_million_aud"] for r in revenue_rows}
    assert amounts == {"estimated_actual": 60068.0, "actual": 59834.0}
    # PNFC/NFPS values (13,215 etc.) must never appear
    all_amounts = [r["amount_million_aud"] for r in rows]
    assert 13215.0 not in all_amounts
    assert 14256.0 not in all_amounts


def test_extractor_negative_values_preserved(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, _ = extractor.extract_pdf_edition(path, "test_source", "2018-19")
    fiscal_balance = [r for r in rows if r["measure_type"] == "qld_rsf_fiscal_balance"]
    amounts = {r["estimate_status"]: r["amount_million_aud"] for r in fiscal_balance}
    assert amounts == {"estimated_actual": -2677.0, "actual": -2191.0}


def test_extractor_tolerates_bare_hyphen_in_pnfc_columns(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2018-19")
    leases = [r for r in rows if r["measure_type"] == "qld_rsf_leases"]
    amounts = {r["estimate_status"]: r["amount_million_aud"] for r in leases}
    assert amounts == {"estimated_actual": 2623.0, "actual": 2612.0}
    assert not any(q["reason"] != "" and "Leases" in q.get("raw_line", "") for q in quarantine)


def test_extractor_quarantines_narrative_revenue_false_positive(tmp_path):
    path = tmp_path / "edition.pdf"
    _write_edition_pdf(path)
    _, quarantine = extractor.extract_pdf_edition(path, "test_source", "2018-19")
    reasons = [q["reason"] for q in quarantine]
    assert "unparseable_or_insufficient_tokens" in reasons
    bad = [q for q in quarantine if q["reason"] == "unparseable_or_insufficient_tokens"]
    assert bad[0]["raw_line"] == "Revenue"


def test_extractor_quarantines_missing_table_page(tmp_path):
    path = tmp_path / "edition.pdf"
    path.write_bytes(_make_pdf_bytes(["No relevant content here"]))
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2018-19")
    assert rows == []
    assert quarantine[0]["reason"] == "table_page_not_found"


def test_older_label_vocabulary_maps_without_conflating_measures(tmp_path):
    path = tmp_path / "older.pdf"
    _write_older_edition_pdf(path)
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2002-03")
    assert quarantine == []
    assert len(rows) == 16
    actual = {r["measure_type"]: r["amount_million_aud"] for r in rows if r["estimate_status"] == "actual"}
    assert actual["qld_rsf_fiscal_balance"] == -140.0
    assert actual["qld_rsf_cash_surplus"] == 645.0
    assert actual["qld_rsf_gross_fixed_capital_formation"] == 1607.0
    assert actual["qld_rsf_net_worth"] == 64894.0
    assert actual["qld_rsf_net_debt"] == -11260.0


@pytest.mark.parametrize(
    "financial_year,present,absent",
    [
        ("2002-03", {"Net Debt"}, {"Borrowing", "Borrowings", "Net Borrowing"}),
        ("2006-07", {"Net debt", "Net Borrowing"}, {"Borrowing", "Borrowings"}),
        ("2011-12", {"Borrowing"}, {"Net Debt", "Net debt", "Net Borrowing"}),
        ("2018-19", set(), {"Borrowing", "Borrowings", "Net Debt", "Net debt"}),
        ("2020-21", {"Net Debt"}, {"Borrowing", "Borrowings"}),
        ("2021-22", {"Borrowing", "Borrowings", "Net Debt"}, {"Net Borrowing"}),
        ("2024-25", {"Borrowing", "Borrowings", "Net Debt"}, {"Net Borrowing"}),
    ],
)
def test_residual_row_mapping_has_explicit_edition_applicability(financial_year, present, absent):
    labels = extractor._row_label_map(financial_year)
    assert present <= labels.keys()
    assert absent.isdisjoint(labels)
    assert labels["Borrowing with QTC"] == "qld_rsf_borrowing_qtc"


def test_newer_residual_stock_rows_are_published_with_exact_values_and_citations(tmp_path):
    path = tmp_path / "Report-on-State-Finances-2024-25.pdf"
    _write_residual_rows_pdf(path)
    rows, quarantine = extractor.extract_pdf_edition(path, "test_source", "2024-25")
    residuals = [r for r in rows if r["measure_type"] in {"qld_rsf_borrowing", "qld_rsf_net_debt"}]
    assert quarantine == []
    assert {(r["measure_type"], r["estimate_status"]): r["amount_million_aud"] for r in residuals} == {
        ("qld_rsf_borrowing", "estimated_actual"): 74843.0,
        ("qld_rsf_borrowing", "actual"): 72864.0,
        ("qld_rsf_net_debt", "estimated_actual"): 22092.0,
        ("qld_rsf_net_debt", "actual"): 16727.0,
    }
    assert all("page:1" in r["locator"] and "fy:2024-25" in r["locator"] for r in residuals)
    assert {r["row_label"] for r in residuals} == {"Borrowing", "Net Debt"}


def test_extractor_all_editions(tmp_path):
    ed1 = tmp_path / "2018-19-Report-on-State-Finances.pdf"
    ed2 = tmp_path / "20-077-FG-Report-on-State-Finances-2019-20-Full.pdf"
    ed3 = tmp_path / "Report-on-State-Finances-2020-21.pdf"
    ed4 = tmp_path / "Report-on-State-Finances-2021-22.pdf"
    ed5 = tmp_path / "Report-on-State-Finances-2022-23.pdf"
    ed6 = tmp_path / "Report-on-State-Finances-2023-24.pdf"
    ed7 = tmp_path / "Report-on-State-Finances-2024-25.pdf"
    for p in (ed1, ed3, ed5, ed7):
        _write_edition_pdf(p)
    for p in (ed2, ed4, ed6):
        _write_edition_pdf_variant(p)
    rows, quarantine = extractor.extract_all_editions("test_source", snapshot_dir=tmp_path)
    fys = {r["financial_year"] for r in rows}
    assert fys == {"2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"}


def test_extractor_quarantines_missing_edition_file(tmp_path):
    rows, quarantine = extractor.extract_all_editions("test_source", snapshot_dir=tmp_path)
    assert rows == []
    reasons = {q["reason"] for q in quarantine}
    assert "edition_file_missing_on_disk" in reasons


# ---- loader: classification, scale conversion --------------------------


@pytest.fixture
def semantics():
    return loader.load_semantics()


def _row(measure_type, fy="2018-19", estimate_status="actual", amount=100.0, cached_copy_path=None):
    return {
        "source_id": "qld_report_on_state_finances_actuals",
        "financial_year": fy,
        "measure_type": measure_type,
        "estimate_status": estimate_status,
        "amount_million_aud": amount,
        "row_label": "Revenue",
        "locator": f"measure:{measure_type}|{fy}|{estimate_status}",
        "cached_copy_path": cached_copy_path or str(REPO_ROOT / "README.md"),
    }


def test_scale_factor_applied_million_to_aud(semantics):
    row = _row("qld_rsf_revenue", amount=59834.0)
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["amount_aud"] == 59_834_000_000.0


def test_unrecognized_measure_type_quarantined(semantics):
    row = _row("not_a_real_measure")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "unrecognized_measure_type"


def test_missing_source_file_quarantined(semantics):
    row = _row("qld_rsf_borrowing_qtc", cached_copy_path="data/does/not/exist.pdf")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "source_file_missing_on_disk"


def test_stock_measure_has_no_period_start(semantics):
    row = _row("qld_rsf_borrowing_qtc")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2019-06-30"


def test_older_stock_measure_has_no_period_start(semantics):
    row = _row("qld_rsf_net_worth", fy="2002-03")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] is None
    assert fact["period_end"] == "2003-06-30"


def test_flow_measure_has_period_start_and_end(semantics):
    row = _row("qld_rsf_revenue")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert reason == ""
    assert fact["period_start"] == "2018-07-01"
    assert fact["period_end"] == "2019-06-30"


def test_estimated_actual_and_actual_produce_distinct_fact_keys(semantics):
    est_row = _row("qld_rsf_revenue", estimate_status="estimated_actual")
    act_row = _row("qld_rsf_revenue", estimate_status="actual")
    est_fact, _ = loader.classify_and_validate(est_row, semantics)
    act_fact, _ = loader.classify_and_validate(act_row, semantics)
    assert est_fact["fact_key"] != act_fact["fact_key"]


def test_budget_estimate_status_rejected_not_used_by_this_family(semantics):
    """QLD's vintage is 'estimated_actual', never 'budget' - confirms
    the semantic distinction from TAS's TAFR adapter is enforced."""
    row = _row("qld_rsf_revenue", estimate_status="budget")
    fact, reason = loader.classify_and_validate(row, semantics)
    assert fact is None
    assert reason == "unexpected_estimate_status"


def test_fact_key_scheme_identity_complete():
    key = loader.build_fact_key(
        source_id="qld_report_on_state_finances_actuals", financial_year="2018-19",
        measure_type="qld_rsf_revenue", accounting_basis="gfs",
        estimate_status="actual", jurisdiction="QLD",
    )
    assert key == "qld_report_on_state_finances_actuals|2018-19|qld_rsf_revenue|gfs|actual|QLD"


# ---- loader: full run against a real fixture DB -------------------------


@pytest.fixture
def fixture_db(tmp_path, monkeypatch):
    db = tmp_path / "facts.db"
    migrate(db)
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    _write_edition_pdf(snapshot_dir / "2018-19-Report-on-State-Finances.pdf")
    _write_edition_pdf_variant(snapshot_dir / "20-077-FG-Report-on-State-Finances-2019-20-Full.pdf")
    _write_edition_pdf(snapshot_dir / "Report-on-State-Finances-2020-21.pdf")
    _write_edition_pdf_variant(snapshot_dir / "Report-on-State-Finances-2021-22.pdf")
    _write_edition_pdf(snapshot_dir / "Report-on-State-Finances-2022-23.pdf")
    _write_edition_pdf_variant(snapshot_dir / "Report-on-State-Finances-2023-24.pdf")
    _write_edition_pdf(snapshot_dir / "Report-on-State-Finances-2024-25.pdf")

    def fake_extract(source_id):
        return extractor.extract_all_editions(source_id, snapshot_dir=snapshot_dir)

    monkeypatch.setattr(loader, "extract_all_editions", fake_extract)
    monkeypatch.setattr(loader, "QUARANTINE_PATH", tmp_path / "q.jsonl")
    return db


def test_full_load_is_idempotent(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    result1 = loader.run(conn, apply=True)
    assert result1["facts_to_insert"] == 112  # 8 measures x 7 editions x 2 estimate_status
    assert result1["revision_conflicts_quarantined"] == 0

    facts_after_first = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    result2 = loader.run(conn, apply=True)
    assert result2["facts_to_insert"] == 0
    assert result2["facts_already_present_idempotent_skip"] == 112
    assert result2["revision_conflicts_quarantined"] == 0

    facts_after_second = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    assert facts_after_first == facts_after_second

    dupes = conn.execute(
        "SELECT fact_key, COUNT(*) c FROM facts GROUP BY fact_key HAVING c > 1"
    ).fetchall()
    assert dupes == []
    conn.close()


def test_residual_rows_reload_is_idempotent_and_preserves_citations(tmp_path, monkeypatch):
    db = tmp_path / "facts.db"
    migrate(db)
    pdf = tmp_path / "Report-on-State-Finances-2024-25.pdf"
    _write_residual_rows_pdf(pdf)
    extracted, extractor_quarantine = extractor.extract_pdf_edition(
        pdf, loader.SOURCE_ID, "2024-25"
    )
    residuals = [
        row
        for row in extracted
        if row["measure_type"] in {"qld_rsf_borrowing", "qld_rsf_net_debt"}
    ]

    monkeypatch.setattr(loader, "extract_all_editions", lambda source_id: (residuals, extractor_quarantine))
    conn = sqlite3.connect(str(db))
    first = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")
    second = loader.run(conn, apply=True, quarantine_path=tmp_path / "q.jsonl")

    assert first["facts_to_insert"] == 4
    assert first["nodes_inserted"] == 2
    assert first["edges_inserted"] == 0
    assert second["facts_to_insert"] == 0
    assert second["facts_updated"] == 0
    assert second["facts_already_present_idempotent_skip"] == 4
    assert second["nodes_inserted"] == 0
    assert second["edges_inserted"] == 0
    assert second["semantic_changes"] == 0
    citations = conn.execute(
        "SELECT source_locator_json FROM facts WHERE measure_type IN ('qld_rsf_borrowing', 'qld_rsf_net_debt')"
    ).fetchall()
    assert len(citations) == 4
    assert all("page:1" in json.loads(row[0])["locator"] for row in citations)
    conn.close()


def test_revision_conflict_detection(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)

    original = conn.execute(
        "SELECT amount_aud FROM facts WHERE measure_type = 'qld_rsf_revenue' AND financial_year = '2018-19' AND estimate_status = 'actual'"
    ).fetchone()[0]

    fake_fact_key = loader.build_fact_key(
        source_id=loader.SOURCE_ID, financial_year="2018-19", measure_type="qld_rsf_revenue",
        accounting_basis="gfs", estimate_status="actual", jurisdiction="QLD",
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
        "SELECT source_locator_json FROM facts WHERE measure_type = 'qld_rsf_revenue' AND financial_year = '2018-19' AND estimate_status = 'actual'"
    ).fetchone()
    payload = json.loads(row[0])
    assert "fy:2018-19" in payload["locator"]
    assert "estimate_status:actual" in payload["locator"]
    assert "row:Revenue" in payload["locator"]
    assert payload["cached_copy_path"]
    conn.close()


def test_citation_locator_repair_is_idempotent(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)
    conn.execute(
        "UPDATE facts SET source_locator_json = ? WHERE fact_key = ?",
        (
            json.dumps({"locator": "stale", "cached_copy_path": "stale"}),
            "qld_report_on_state_finances_actuals|2018-19|qld_rsf_revenue|gfs|actual|QLD",
        ),
    )
    conn.commit()
    repaired = loader.run(conn, apply=True)
    assert repaired["facts_updated"] == 1
    repeated = loader.run(conn, apply=True)
    assert repeated["facts_updated"] == 0
    assert repeated["facts_already_present_idempotent_skip"] == 112
    conn.close()


def test_all_seven_years_load_as_distinct_facts(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    loader.run(conn, apply=True)
    fys = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT financial_year FROM facts WHERE measure_type LIKE 'qld_rsf_%'"
        ).fetchall()
    }
    conn.close()
    assert fys == {"2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"}


def test_dedicated_compatibility_groups_distinct_from_abs_gfs_qld(fixture_db):
    conn = sqlite3.connect(str(fixture_db))
    rows = conn.execute(
        "SELECT DISTINCT measure_type, compatibility_group FROM measure_definitions WHERE measure_type LIKE 'qld_rsf_%'"
    ).fetchall()
    conn.close()
    assert len(rows) == 14
    annual_groups = {"actual_expense", "budget_expense", "gfs_revenue", "gfs_liability"}
    for measure_type, group in rows:
        assert group == measure_type  # 1:1
        assert group not in annual_groups
        assert not group.startswith("abs_gfs_")

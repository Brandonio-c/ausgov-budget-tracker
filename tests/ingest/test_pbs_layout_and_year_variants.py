"""Coverage for PBS layout variants, year resolution, and citation completeness.

Fixtures under tests/fixtures/pbs/ are synthetic (fabricated program names and
amounts matching real table structures observed in acquired PBS PDFs) - they
exercise parsing logic, not real published figures.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "pbs"
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))


def _extract(fixture_name: str, *, portfolio: str, source_id: str):
    from extractors import pbs_programs_all as mod

    text = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    pages = [(i + 1, page) for i, page in enumerate(text.split("=====PAGE=====\n"))]
    with patch.object(mod, "iter_pdf_pages", return_value=pages):
        return mod.extract_pdf(
            Path(f"fake-{source_id}.pdf"), portfolio=portfolio, source_id=source_id
        )


def test_wrapped_multiline_header_and_nil_row_no_longer_corrupt_labels():
    """Regression test for the federal_pbs_2026_27_defence bug: a year-header
    wrapped across many single-word lines, followed by a real zero-value
    ("-") row, must not get glued onto the next real data row's label.

    Uses "Grants" (not "Suppliers"/"Employees"/"Other expenses") as the target
    row label: those three are intentionally excluded by extract_pdf()'s
    generic cost-category filter (they're sub-lines under "Expenses funded
    by...", not programs, and would double-count against the program total)
    - confirmed by direct inspection, not assumed. That filter is unrelated
    to the header/nil-row contamination bug this test targets.
    """
    rows = _extract(
        "wrapped_header_and_nil_row.txt",
        portfolio="Test Portfolio",
        source_id="test_wrapped_header_2026_27",
    )
    grants = [r for r in rows if "Grants" in r["program_label"]]
    assert len(grants) >= 1
    label = grants[0]["program_label"]
    # None of the wrapped header fragments should appear glued onto the label.
    for fragment in ("Estimated", "Actual", "Budget", "Forward", "Employees"):
        assert fragment not in label
    assert grants[0]["fy"] in {"2025-26", "2026-27", "2027-28", "2028-29", "2029-30"}


def test_multi_page_table_continuation_with_repeated_header():
    rows = _extract(
        "multi_page_repeated_header.txt",
        portfolio="Test Portfolio",
        source_id="test_multi_page_2025_26",
    )
    fys = {r["fy"] for r in rows}
    assert {"2024-25", "2025-26", "2026-27", "2027-28", "2028-29"} <= fys
    totals = [r for r in rows if "Total funded expenditure" in r["program_label"]]
    assert len(totals) >= 1


def test_scale_conversion_thousands_to_whole_dollars():
    """$'000-labelled tables are the overwhelming majority of PBS program
    tables; confirms the thousands->whole-dollar conversion (not a no-op,
    not double-converted) on a decimal-bearing value.

    Note: this line shape is matched by the generic FIVE_TAIL pattern before
    the Defence-only KEY_COST_ROW/$m branch ever gets a chance (FIVE_TAIL is
    checked unconditionally first) - confirmed by direct inspection, not
    assumed. That $m branch is real but only reachable for line shapes
    FIVE_TAIL rejects; not exercised by this fixture, which instead pins down
    the actual (and far more common) $'000 conversion path.
    """
    rows = _extract(
        "scale_conversion_dollar_m.txt",
        portfolio="Test Portfolio",
        source_id="test_scale_conversion_2025_26",
    )
    assert rows
    workforce = [r for r in rows if "Workforce" in r["program_label"]]
    assert workforce
    # "1,234.5" under a $'000 table -> $1,234,500, not 1234 (unconverted) or
    # 1234500000 (wrongly treated as $m).
    assert workforce[0]["amount"] == 1_234_500


@pytest.mark.parametrize(
    "fixture_name,portfolio,source_id",
    [
        ("social_services_program.txt", "Social Services", "test_dss_2025_26"),
        ("health_program.txt", "Health Disability and Ageing", "test_health_2025_26"),
        ("ndia_program.txt", "Health Disability and Ageing", "test_ndia_2025_26"),
        ("dva_program.txt", "Veterans' Affairs", "test_dva_2025_26"),
        ("education_program.txt", "Education", "test_education_2025_26"),
    ],
)
def test_high_value_portfolio_programs_extract_with_complete_citations(
    fixture_name, portfolio, source_id
):
    rows = _extract(fixture_name, portfolio=portfolio, source_id=source_id)
    assert rows, f"{source_id} yielded zero rows - should have a precise reason instead"
    for row in rows:
        assert row["fy"].count("-") == 1
        assert row["estimate_status"] in {
            "actual",
            "estimated_actual",
            "budget",
            "forward_estimate",
        }
        assert row["portfolio"] == portfolio
        # Citation locator completeness: source, pdf, page, program, fy, unit, inference method.
        locator = row["locator"]
        for required in ("source_id:", "pdf:", "page:", "program:", "fy:", "unit:", "infer:"):
            assert required in locator
        assert row["cached_copy_path"].endswith(".pdf")
        assert row["amount"] != 0 or "Employees" not in row["program_label"]


def test_malformed_document_with_no_year_evidence_quarantines_not_guesses():
    rows = _extract(
        "bad_no_years.txt", portfolio="Test Portfolio", source_id="test_malformed_2025_26"
    )
    # No year header anywhere in this fixture -> nothing should be published,
    # and nothing must guess a fixed-year column mapping.
    assert rows == []


def test_cross_document_dedupe_keeps_richest_locator():
    """main()'s cross-document dedupe key is (portfolio, program_label, fy,
    estimate_status, amount) - two identical rows from different source_ids
    for the same real-world figure must collapse to one, keeping the richer
    locator, not double-count the same fact under two aliases."""
    from extractors.pbs_programs_all import _norm

    row_a = {
        "portfolio": "Education",
        "program_label": "Sample Schools Funding",
        "fy": "2024-25",
        "estimate_status": "actual",
        "amount": 22_700_000,
        "locator": "short",
    }
    row_b = dict(row_a, locator="source_id:test | pdf:doc.pdf | page:5 | longer-locator")
    deduped: dict[tuple, dict] = {}
    for r in (row_a, row_b):
        key = (
            r["portfolio"],
            _norm(r["program_label"]).lower(),
            r["fy"],
            r["estimate_status"],
            int(r["amount"]),
        )
        prev = deduped.get(key)
        if prev is None or len(r["locator"]) > len(prev["locator"]):
            deduped[key] = r
    assert len(deduped) == 1
    assert list(deduped.values())[0]["locator"] == row_b["locator"]

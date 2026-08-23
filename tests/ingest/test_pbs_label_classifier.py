"""Tests for the deterministic PBS label-quality classifier (Task 5 of the
semantic-defect milestone, scripts/ingest/pbs_label_classifier.py).

Covers every named rejection pattern from the mission verbatim, plus the
category boundaries between table_header/total/financial_statement_line/
narrative_fragment/malformed_concatenated_row, and the explicit "- Other"
review requirement (do not reject every Other row automatically, but a bare
Other with no supporting context is not evidence of a legitimate category).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from pbs_label_classifier import PUBLISHABLE_CLASSES, classify_label  # noqa: E402


def _cls(label: str) -> str:
    return classify_label(label).classification


def test_mission_example_year_and_unit_header_glued_to_expenses_line():
    r = classify_label("000 2028\xad29 000 EXPENSES Employee benefits")
    assert r.classification == "malformed_concatenated_row"
    assert not r.publishable


def test_mission_example_pure_year_sequence_glued_to_suppliers_line():
    r = classify_label("2027\xad28 2028\xad29 2029\xad30 EXPENSES Suppliers")
    assert r.classification == "malformed_concatenated_row"
    assert not r.publishable


def test_mission_example_ndia_concatenated_numeric_row():
    label = (
        "National Disability Insurance Agency Departmental payments 1.1 - "
        "(2,013,602) (7,431,787) (11,830,241) (16,652,205) 1.2 -"
    )
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "three_or_more_embedded_value_tokens"
    assert not r.publishable


def test_mission_example_loss_attributable_narrative_join():
    label = (
        "(loss) attributable to the Australian Government plus: "
        "non-appropriated expenses depreciation/amortisation expenses"
    )
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert not r.publishable


def test_bare_other_is_quarantined_not_auto_accepted():
    for label in ("Other", "- Other", "OTHER"):
        r = classify_label(label)
        assert r.classification == "narrative_fragment"
        assert not r.publishable
        assert r.rejection_reason == "bare_generic_term_no_supporting_context"


def test_other_with_real_numbering_prefix_is_not_auto_rejected():
    """Task 5 explicitly warns against rejecting every "Other" row - one
    with real component/program numbering attached is legitimate."""
    r = classify_label("1.2.3 - Component 3 (Other)")
    assert r.classification == "component"
    assert r.publishable


def test_pure_year_sequence_is_year_header():
    r = classify_label("2027\xad28 2028\xad29 2029\xad30")
    assert r.classification == "year_header"
    assert not r.publishable


def test_bare_unit_marker_is_unit_header():
    r = classify_label("$'000")
    assert r.classification == "unit_header"
    assert not r.publishable


def test_accounting_heading_alone_is_table_header():
    for label in ("EXPENSES", "ASSETS", "LIABILITIES", "OPERATING ACTIVITIES"):
        r = classify_label(label)
        assert r.classification == "table_header", label
        assert not r.publishable


def test_total_and_subtotal_lines():
    assert classify_label("Total expenses").classification == "total"
    assert classify_label("Net cash from/(used by) operating activities").classification == "subtotal"
    assert classify_label("Sub-total transactions with owners").classification == "subtotal"


def test_known_financial_statement_line_items_rejected():
    for label in ("Computer software", "Cash and cash equivalents", "Employee benefits", "Suppliers"):
        r = classify_label(label)
        assert r.classification == "financial_statement_line", label
        assert not r.publishable


def test_narrative_continuation_and_bare_act_citation():
    r = classify_label("plus: depreciation/amortisation expenses for ROU")
    assert r.classification == "narrative_fragment"
    assert r.rejection_reason == "narrative_continuation_lead"

    r2 = classify_label("Law Officers Act 1964")
    assert r2.classification == "narrative_fragment"
    assert r2.rejection_reason == "bare_legislative_citation"


def test_truncated_trailing_numeric_token_rejected():
    r = classify_label("Housing Support Administered payments 1.5 -")
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "truncated_trailing_numeric_token"
    assert not r.publishable


def test_embedded_bare_numeric_run_rejected():
    """Small $'000 values under 1,000 have no thousands separator (e.g.
    "150 150 100") and would otherwise slip past the value-token count -
    found while manually reviewing NDIA rows during Task 6's corpus audit."""
    r = classify_label(
        "National Disability Insurance Scheme - Getting the NDIS back on "
        "track (l) 2.1 Departmental payment - 150 150 100 - National"
    )
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "embedded_bare_numeric_run"


def test_excessive_length_rejected():
    label = "A " + ("very " * 60) + "long label"
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "exceeds_justified_max_length"


def test_repeated_accounting_heading_rejected():
    r = classify_label("EXPENSES Employee benefits ASSETS Cash and cash equivalents")
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "repeated_accounting_heading"


def test_program_outcome_component_numbering_accepted():
    assert classify_label("Program 1.1: Aged Care Quality and Safety").classification == "program"
    assert classify_label("Outcome 1: Improved health outcomes for all Australians").classification == "outcome"
    assert (
        classify_label(
            "1.5.6 – Component 6 (Carer Adjustment Payment) Annual administered expenses"
        ).classification
        == "component"
    )
    assert classify_label("Key cost category / Capability Acquisition Program").classification == "program"


def test_key_cost_category_only_accepts_the_two_verified_safe_names():
    """Regression for a real bug found in the database-hygiene milestone
    (Task 2): "Key cost category / Operations" (and Workforce/Operating/
    OPERATING) used to be accepted here, but a corpus-wide check found
    every one of the 26 real facts under those four generic-word labels
    came from a completely unrelated table (a workforce headcount table,
    a facilities/property table, a Statement of Cash Flows, a Program 1.1
    resourcing table) - never the genuine Key Cost Category table. Only
    the two multi-word, specific Table 4b category names are verified
    safe; anything else with this prefix must be explicitly rejected, not
    silently re-accepted via the generic default clean-shape rule."""
    for bad in (
        "Key cost category / Operations",
        "Key cost category / Workforce",
        "Key cost category / Operating",
        "Key cost category / OPERATING",
    ):
        r = classify_label(bad)
        assert r.publishable is False, bad
        assert r.rejection_reason == "key_cost_category_not_in_verified_whitelist"

    for good in (
        "Key cost category / Capability Acquisition Program",
        "Key cost category / Capability Sustainment Program",
    ):
        r = classify_label(good)
        assert r.classification == "program"
        assert r.publishable is True


def test_component_numbering_beats_accounting_heading_false_positive():
    """A real component description legitimately containing a phrase like
    "administered expenses" must not be misclassified as a bare table
    header just because it contains the word "expenses"."""
    r = classify_label(
        "4.1.1 – Component 1 (Disability and Carers) Annual administered expenses"
    )
    assert r.classification == "component"
    assert r.publishable


def test_clean_unlabelled_title_defaults_to_program_not_unknown():
    """Most genuine PBS program titles reach the classifier with no
    numbering prefix because the extractor already strips bare numbering
    fragments - a clean, well-shaped title with no defect signal must still
    be usable, not stuck in unknown forever."""
    r = classify_label("Inspiring All Australians in STEM")
    assert r.classification == "program"
    assert r.publishable


def test_short_ambiguous_fragment_is_unknown_not_guessed():
    r = classify_label("TBC")
    assert r.classification == "unknown"
    assert not r.publishable


def test_empty_label_is_unknown():
    r = classify_label("")
    assert r.classification == "unknown"
    assert not r.publishable


def test_only_publishable_classes_are_program_outcome_component():
    assert PUBLISHABLE_CLASSES == frozenset({"program", "outcome", "component"})


# --- Item 5.5 classifier precision pass -----------------------------------
# Every label below is a real, verbatim extracted string that was
# quarantined as `unknown` (no_confident_signal) against the live
# federal_pbs_programs_all facts, found while auditing the current
# quarantine set for genuine precision defects (as opposed to the large,
# correctly-rejected malformed_concatenated_row/table_header buckets).


def test_standalone_gfs_revenue_and_asset_terms_classify_as_financial_statement_line():
    """"Taxes"/"Fees"/"Fines"/"Loans"/"Leases"/"Land" are standard GFS/AASB
    revenue and PP&E sub-category rows, confirmed recurring across Home
    Affairs, Industry, PM&C, Infrastructure, Education and Health Section 3
    tables - never a program name. Previously fell through to `unknown`
    because they weren't in the curated vocabulary; "land, buildings and
    infrastructure" already was, so a standalone "Land" sub-line is the
    same established concept, not new territory."""
    for label in ("Taxes", "Fees", "Fines", "Loans", "Leases", "Land"):
        r = classify_label(label)
        assert r.classification == "financial_statement_line", label
        assert not r.publishable


def test_two_value_tokens_with_accounting_heading_is_malformed():
    """A real program/component title never itself contains both a dollar
    figure and a bare section-heading word - two embedded values plus a
    heading keyword together is decisive even though two values alone is
    not (a real title can legitimately carry one or two numbers, e.g. a
    footnoted citation year)."""
    label = "17,419 17,481 LIABILITIES Payables Suppliers"
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "two_embedded_value_tokens_with_heading"
    assert not r.publishable


def test_two_value_tokens_alone_is_not_automatically_malformed():
    """Guard against the precision fix above becoming a false-positive
    generator: two values with no heading keyword must not be rejected on
    value-count alone."""
    r = classify_label("Program 1.1: Something 2024 2025")
    assert r.classification != "malformed_concatenated_row"


def test_bare_dash_run_glued_to_heading_is_malformed():
    """PBS tables use a lone "-" for a $0 year column; a run of three or
    more is the same flattened-row signal as a bare numeric run, just for
    all-zero columns."""
    label = "- expense adjustment (e) - - - - - Special appropriations"
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "embedded_bare_dash_run"
    assert not r.publishable


def test_bare_dash_run_with_soft_hyphen_glyph_is_malformed():
    label = "\xad appropriation - - - - - - expense adjustment (e) 531 - - - - Special appropriations"
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "embedded_bare_dash_run"


def test_single_leading_dash_bullet_is_not_a_dash_run():
    """A single stray PDF bullet glyph must not trip the new dash-run rule
    - only a genuine run of three or more zero-column placeholders should."""
    r = classify_label("- Special Accounts")
    assert r.rejection_reason != "embedded_bare_dash_run"


# --- Federal deep-data mission: federal_pbs_programs_s6_bridge repair -----
# Every label below is a real, verbatim node name found still published (not
# quarantined) in data/facts.db for federal_pbs_programs_s6_bridge during
# the mission's Phase 1 bridge audit - a second dataset the Task 5 classifier
# already covers via cleanup_pbs_s6_bridge_labels.py, but two precision gaps
# let real defects through uncaught until this pass.


def test_bare_dash_run_recognizes_en_dash_glyph_not_just_ascii_hyphen():
    """BARE_DASH_RUN's character class only covered ASCII "-" and the U+00AD
    soft hyphen; a federal_pbs_programs_s6_bridge row from a PDF generation
    using EN DASH (U+2013) placeholders for $0 columns slipped through as a
    "valid program name" - three financial-statement line items
    (Interest/Dividends/Taxes) concatenated by en-dash placeholders,
    confirmed live in data/facts.db under 'Public order and safety /
    Other public order and safety / ...'."""
    label = "Interest – – – – – Dividends – – – – – Taxes"
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "embedded_bare_dash_run"
    assert not r.publishable


def test_surplus_deficit_operating_statement_line_rejected():
    """"Surplus/(deficit) ..." is a standard AAS/GFS operating-statement
    line with several real qualifier variants across PBS generations - all
    confirmed live in federal_pbs_programs_s6_bridge, previously accepted
    as a bare well-shaped "program" title."""
    for label in (
        "Surplus/(deficit) after income tax",
        "Surplus/(deficit) before income tax",
        "Surplus/(deficit) attributable to the Australian Government",
    ):
        r = classify_label(label)
        assert r.classification == "financial_statement_line", label
        assert r.rejection_reason == "surplus_deficit_line", label
        assert not r.publishable


def test_surplus_deficit_regex_matches_with_no_trailing_word():
    """Regression guard: an earlier version of this pattern ended in a `\\b`
    word boundary immediately after the closing paren, which never matches
    when followed by a space (no boundary between two non-word characters),
    so the rule silently never fired at all."""
    r = classify_label("Surplus/(deficit)")
    assert r.rejection_reason == "surplus_deficit_line"


def test_additional_balance_sheet_and_income_terms_rejected():
    """More AAS/GFS vocabulary confirmed live in federal_pbs_programs_s6_bridge
    across multiple unrelated portfolios with byte-identical labels (a real
    program name would not repeat verbatim across Other economic affairs,
    Public order and safety, and Transport and communication alike)."""
    for label in (
        "Retained surplus (accumulated deficit)",
        "Retained surplus",
        "Rental income",
        "Other income",
        "Other Unearned Income",
        "Asset revaluation reserve",
        "Sublease income",
        "Sublease interest income",
        "Rehabilitation provision",
        "Provision for Impairment",
    ):
        r = classify_label(label)
        assert r.classification == "financial_statement_line", label
        assert not r.publishable, label


def test_add_narrative_lead_rejected_without_matching_additional_words():
    """"Add Provision for Impairment" is a narrative continuation ("Add:" /
    "Add" prefixing a financial-statement adjustment line), the same shape
    as the existing "plus"/"less" leads - but "add" as a narrative-lead
    token must not false-positive on a real word starting with "add", e.g.
    "Additional Support Payments"."""
    r = classify_label("Add Provision for Impairment")
    assert r.classification == "narrative_fragment"
    assert r.rejection_reason == "narrative_continuation_lead"
    assert not r.publishable

    r2 = classify_label("Additional Support Payments")
    assert r2.rejection_reason != "narrative_continuation_lead"
    assert r2.classification == "program"
    assert r2.publishable


def test_cash_flow_and_funding_source_lines_rejected():
    """"Cash used X"/"Funded by/internally X"/"Payments to corporate
    entities X" are Statement of Cash Flows / appropriation-funding-source
    rows, confirmed recurring across many federal_pbs_programs_s6_bridge
    portfolios - an entity or category name appended after the prefix
    (e.g. "Payments to corporate entities(b) Australian Sports
    Commission") does not make it a program, it is still that entity's own
    separate funding-source line, not a program of the reporting agency."""
    for label in (
        "Cash used Employees",
        "Cash used Grant",
        "Cash used Suppliers",
        "Cash to Official Public Account for: - Transfers to other entities (Finance - whole of government)",
        "Funded by capital appropriation – DCB (b)",
        "Funded internally from departmental resources",
        "Payments to corporate entities(b) Australian Sports Commission",
    ):
        r = classify_label(label)
        assert r.classification == "financial_statement_line", label
        assert r.rejection_reason == "cash_flow_or_funding_source_line", label
        assert not r.publishable, label


def test_value_token_with_short_dash_pair_rejected():
    """A run of only 2 dash-placeholder tokens (as opposed to the 3+ that
    BARE_DASH_RUN alone requires) is not decisive by itself, but combined
    with an embedded VALUE_TOKEN it is the same flattened-multi-column-row
    signal - confirmed against a real federal_pbs_programs_s6_bridge row
    where a Table 2.1 label got glued to the following row's leading $0
    placeholder columns."""
    label = "First Nations Languages in Schools 2,540 9,833 150 - - Grants and Awards"
    r = classify_label(label)
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "value_token_with_placeholder_run"
    assert not r.publishable


def test_embedded_nfp_run_rejected_standalone():
    """"nfp" (not for publication) is a standard Commonwealth budget-paper
    placeholder for a suppressed figure - a run of 2+ is the same
    flattened-row-of-placeholder-columns signal as a bare dash run, and
    (unlike the dash-pair case above) is decisive on its own since "nfp"
    repeated is never legitimate title text."""
    r = classify_label(
        "Cellular Broadcast Technologies(b) nfp nfp nfp - - Community Broadcasting Program"
    )
    assert r.classification == "malformed_concatenated_row"
    assert r.rejection_reason == "embedded_nfp_run"
    assert not r.publishable


def test_financial_statement_vocabulary_matches_with_trailing_footnote_marker():
    """A trailing "(a)"/"(b)" PBS footnote marker must not defeat the
    curated-vocabulary lookup - "Depreciation and amortisation (a)" is the
    same real accounting line as the unfootnoted form, confirmed live in
    federal_pbs_programs_s6_bridge with and without the marker attached
    (with a space, and glued directly with none)."""
    for label in (
        "Depreciation and amortisation (a)",
        "Depreciation and amortisation(a)",
        "Fair Value Losses (a)",
    ):
        r = classify_label(label)
        assert r.classification == "financial_statement_line", label
        assert r.rejection_reason == "known_line_item_vocabulary", label
        assert not r.publishable, label


def test_other_provisions_rejected():
    """"Other provisions" (as opposed to "Provisions Other provisions",
    already covered) is its own standalone balance-sheet line, confirmed
    live in federal_pbs_programs_s6_bridge."""
    r = classify_label("Other provisions")
    assert r.classification == "financial_statement_line"
    assert not r.publishable


def test_bare_operating_and_operations_rejected_without_key_cost_category_prefix():
    """Task 2's database-hygiene milestone found every real fact under the
    bare words "Operating"/"Operations"/"Workforce" came from an unrelated
    table (a workforce headcount table, a facilities/property table, a
    Statement of Cash Flows, a Program 1.1 resourcing table) when prefixed
    with "Key cost category /" - the same is true with no prefix at all,
    confirmed against real federal_pbs_programs_s6_bridge rows."""
    for label in ("Operating", "OPERATING", "Operations", "Workforce"):
        r = classify_label(label)
        assert r.classification == "narrative_fragment", label
        assert r.rejection_reason == "bare_generic_term_no_supporting_context", label
        assert not r.publishable, label

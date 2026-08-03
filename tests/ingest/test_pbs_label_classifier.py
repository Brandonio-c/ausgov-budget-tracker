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
    assert classify_label("Key cost category / Operations").classification == "program"


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

"""Tests for scripts/ingest/reload_pbs_programs_all.py's label-quality gate
(Task 8 of the semantic-defect milestone).

Verifies the composition rule: the generic ingest gates (schema/types/
period/node/measure/citation, scripts/ingest/validate.py) run unchanged,
and the Task 5 classifier can only additionally quarantine a row the
generic gates already accepted - it never resurrects a row the generic
gates already rejected, and never weakens Gate 6's citation requirement.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ingest"))

from reload_pbs_programs_all import _apply_label_quality_gate  # noqa: E402
from validate import RowDecision  # noqa: E402


def _decision(node_name: str, publishable: bool = True, quarantine_reason: str | None = None) -> RowDecision:
    return RowDecision(
        row={"node_name": node_name},
        publishable=publishable,
        quarantine_reason=quarantine_reason,
        gate_failures=[],
    )


def test_real_program_label_stays_publishable():
    decisions = [_decision("Health Disability and Ageing / Program 1.1: Aged Care Quality and Safety")]
    result, counts = _apply_label_quality_gate(decisions)
    assert result[0].publishable is True
    assert counts.get("program") == 1


def test_malformed_label_is_downgraded_to_quarantined():
    decisions = [
        _decision("Education / 2027\xad28 2028\xad29 2029\xad30 EXPENSES Suppliers")
    ]
    result, counts = _apply_label_quality_gate(decisions)
    assert result[0].publishable is False
    assert "Label quality" in result[0].quarantine_reason
    assert "malformed_concatenated_row" in result[0].quarantine_reason
    assert counts.get("malformed_concatenated_row") == 1


def test_already_gate_1_6_quarantined_row_is_left_alone():
    """A row the generic gates already rejected (e.g. missing citation)
    must not be reclassified or have its original reason overwritten -
    the label-quality gate only ever adds MORE quarantining, never less,
    and never touches an already-quarantined decision."""
    original_reason = "Gate 6 attribution: incomplete citation: ['locator']"
    decisions = [
        _decision(
            "Health Disability and Ageing / Program 1.1: Aged Care Quality and Safety",
            publishable=False,
            quarantine_reason=original_reason,
        )
    ]
    result, counts = _apply_label_quality_gate(decisions)
    assert result[0].publishable is False
    assert result[0].quarantine_reason == original_reason
    # Already-quarantined rows are not run through the classifier at all.
    assert counts == {}


def test_table_header_label_is_downgraded():
    decisions = [_decision("Defence / EXPENSES")]
    result, counts = _apply_label_quality_gate(decisions)
    assert result[0].publishable is False
    assert "table_header" in result[0].quarantine_reason


def test_mixed_batch_only_downgrades_the_bad_rows():
    decisions = [
        _decision("Defence / Program 1.1: Air Combat Capability"),
        _decision("Defence / Total expenses"),
        _decision("Defence / Program 2.1: Naval Capability"),
    ]
    result, counts = _apply_label_quality_gate(decisions)
    publishable_flags = [d.publishable for d in result]
    assert publishable_flags == [True, False, True]

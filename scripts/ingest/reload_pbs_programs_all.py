#!/usr/bin/env python3
"""Reload federal_pbs_programs_all facts using the Task 5 label-quality
classifier as an additional, PBS-specific gate on top of the generic
ingest validation gates (scripts/ingest/validate.py Gates 1-6).

Deliberately does NOT modify validate.py: label-quality classification is
PBS-specific business logic (this corpus's own extraction artifacts), not
a general ingest concern shared by every other mapping in this system.
Instead this wraps the same extract -> validate -> load flow scripts/
ingest/run.py uses, and downgrades any row the classifier does not
positively classify as program/outcome/component to non-publishable
(quarantined), regardless of what the generic gates decided - the generic
gates (schema/types/period/node/measure/citation) still run first and are
unchanged; this can only make an already-publishable row non-publishable,
never the reverse, so Gate 6's citation requirement is never weakened.

Uses the mapping's own `replace_on_reload: true` (config/mappings/
federal_pbs_programs_all.yaml) via the existing load_decisions() - a full,
idempotent wholesale replace of this one source_document's facts, and
must never alter any other source_document's facts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from duckdb_etl import extract_rows, load_mapping  # noqa: E402
from load_facts import load_decisions  # noqa: E402
from pbs_label_classifier import classify_label  # noqa: E402
from schema_migrate import migrate  # noqa: E402
from validate import RowDecision, validate_batch  # noqa: E402

DEFAULT_DB = REPO_ROOT / "data" / "facts.db"
MAPPING_PATH = REPO_ROOT / "config" / "mappings" / "federal_pbs_programs_all.yaml"


def _label_for_classification(node_name: str) -> str:
    """The final path segment - what display_name() in
    src/backend/breakdown_graph.py actually shows a user, via the same
    rsplit-on-last-" / " rule - not just the portfolio-stripped remainder.
    A node_name can carry more than one " / " (e.g. "Defence / Key cost
    category / workforce", or "Portfolio / Retained surplus / (accumulated
    deficit)"); classifying the first-split remainder ("Key cost category /
    workforce", "Retained surplus / (accumulated deficit)") let both of
    those slip through this gate as `program` via the default clean-shape
    rule, while what a user actually sees drilled down to a bare, lowercase
    "workfoce" or a dangling "(accumulated deficit)" - both correctly
    rejected once classified on the same final segment that gets
    displayed and, for the "workforce"/"operating" case, attached directly
    to a live PBS -> Statement 6 crosswalk edge (found via the Task 9 SQL
    integrity check for exactly this)."""
    if " / " in node_name:
        return node_name.rsplit(" / ", 1)[-1]
    return node_name


def _apply_label_quality_gate(
    decisions: list[RowDecision],
) -> tuple[list[RowDecision], dict[str, int]]:
    """Downgrade any gate-1-6-publishable row whose label is not positively
    classified as program/outcome/component. Rows already quarantined by
    the generic gates are left as-is (already non-publishable)."""
    out: list[RowDecision] = []
    label_quality_counts: dict[str, int] = {}
    for decision in decisions:
        if not decision.publishable:
            out.append(decision)
            continue
        node_name = decision.row.get("node_name") or decision.row.get("category") or ""
        label = _label_for_classification(str(node_name))
        result = classify_label(label)
        label_quality_counts[result.classification] = (
            label_quality_counts.get(result.classification, 0) + 1
        )
        if result.publishable:
            out.append(decision)
            continue
        out.append(
            RowDecision(
                row=decision.row,
                publishable=False,
                quarantine_reason=(
                    f"Label quality: classified as '{result.classification}' "
                    f"({result.rejection_reason}) - not a program/outcome/component"
                ),
                gate_failures=decision.gate_failures,
            )
        )
    return out, label_quality_counts


def reload_pbs_programs_all(db_path: Path = DEFAULT_DB) -> dict:
    migrate(db_path)
    mapping = load_mapping(MAPPING_PATH)
    rows = extract_rows(mapping, REPO_ROOT)
    gate_decisions = validate_batch(mapping, rows)
    gate6_quarantined = sum(
        1
        for d in gate_decisions
        if not d.publishable and d.quarantine_reason and "Gate" in d.quarantine_reason
    )
    final_decisions, label_quality_counts = _apply_label_quality_gate(gate_decisions)
    label_quality_quarantined = sum(
        1
        for d in final_decisions
        if not d.publishable and d.quarantine_reason and d.quarantine_reason.startswith("Label quality")
    )
    stats = load_decisions(mapping, final_decisions, db_path)
    return {
        "source_id": mapping["source_id"],
        "input_rows": len(rows),
        "gate_1_6_quarantined": gate6_quarantined,
        "label_quality_quarantined": label_quality_quarantined,
        "label_quality_class_counts": label_quality_counts,
        **stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    summary = reload_pbs_programs_all(args.db)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

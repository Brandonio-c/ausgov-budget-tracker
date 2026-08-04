# Task 2 — Defence "100.52% of parent" investigation

## Verdict: not source rounding — a genuine extraction/categorisation defect, now fixed

The prior milestone characterized fact_id 337001 ("Defence / Key cost
category / OPERATING", 100.52% of parent) as "verified as a
source-document rounding characteristic." This milestone's own required
verification checklist ("confirm... rather than... a parsing defect")
found that characterization was wrong. It has been corrected here rather
than formalized as-is.

## Evidence

`fact_id 337001` and its 3 same_group siblings under the "Defence / Key
cost category" folder (node 236727) for FY2029-30 sum to exactly the
"parent" total the audit compared against:

| node | fact_id | amount (2029-30) | raw source (`program:` locator, pre-cleaning) |
|---|---:|---:|---|
| Key cost category / OPERATING | 337001 | 48,814,512,000 | page 118, Table 46 (Statement of Cash Flows) "OPERATING ACTIVITIES Cash received Appropriations" |
| Key cost category / Operating | 336897 | -272,153,000 | page 29, "18 -59,327 Expenditure (Operating and Capital) -76,682" |
| Key cost category / Workforce | 336901 | 17,416,000 | page 37, "(Workforce Requirement) ADF Permanent Force [c] 16,193 Navy" |
| Key cost category / Operations | 337004 | 0 | page 159, "Facilities to Support LAND 3025 Phase 2 ... Holsworthy Barracks" |

All 26 facts ever loaded under these 4 labels (5 Workforce + 7 Operations
+ 7 OPERATING + 7 Operating, across multiple PBS editions and years) were
individually checked: **every single one traces back to a different,
unrelated table** (a workforce headcount table, a facilities/property
table, a Statement of Cash Flows, a Program 1.1 resourcing table) —
never the genuine Key Cost Category table (the one that legitimately
produces "Capability Acquisition Program" / "Capability Sustainment
Program", both confirmed clean: short, numbered, single-page, single-table
rows). Independent corroborating evidence: the "OPERATING" series itself
jumps from ~$2.0B (2028-29) to ~$48.8B (2029-30) — a ~24x year-over-year
jump no real cost category exhibits; this is the signature of a completely
different table's row being swept in, not rounding noise.

## Root cause

`scripts/ingest/extractors/pbs_programs_all.py`'s
`_clean_defence_program_label()` applied a bare, case-insensitive
substring match for `Workforce|Operations|Capability Acquisition
Program|Capability Sustainment Program|Operating` against **every row
extracted anywhere in the ~180-page Defence PBS document**, re-labelling
any match to `"Key cost category / <matched word>"` with `prefer=True`
(boosting it in the extractor's own de-duplication). The two multi-word
category names are specific enough to be safe; the three generic single
words are not — they match incidental phrasing in completely unrelated
tables throughout the document.

## Fix (root cause, not a database patch)

1. `scripts/ingest/extractors/pbs_programs_all.py`: `_clean_defence_program_label()`
   now only matches the two verified-safe, multi-word category names.
   New regression test `test_defence_key_cost_category_rejects_generic_single_word_matches`
   (`tests/ingest/test_federal_actuals_depth.py`).
2. `scripts/ingest/pbs_label_classifier.py`: `KEY_COST_CATEGORY` tightened
   to an exact whitelist match (was a bare `^Key cost category\s*/`
   prefix), plus an explicit rejection (`key_cost_category_not_in_verified_whitelist`)
   for anything else with that prefix, so it can never fall through to the
   generic default-accept rule. New tests in `tests/ingest/test_pbs_label_classifier.py`.
3. `scripts/ingest/reload_pbs_programs_all.py`: `_label_for_classification()`
   now keeps "Key cost category / X" together (the last TWO segments) when
   classifying, instead of just the bare final segment "X" - otherwise the
   tightened classifier never even sees the "Key cost category" context to
   reject. New/updated tests in `tests/ingest/test_reload_pbs_programs_all.py`.
4. Re-ran the reload -> cleanup -> crosswalk-regen sequence against
   data/facts.db: the 4 bad "Key cost category" node names (26 facts total)
   were quarantined and their nodes/edges removed (idempotent - a second
   pass found 0 new orphans). See `ops/reports/database-hygiene-and-ci-hardening-final-*.md`
   for the exact before/after counts.
5. Live dashboard audit result after the fix: **0 hard failures, 0
   accepted_source_rounding_warnings** - the additive_reconciliation
   failure disappeared entirely because the defect was removed, not
   because it was accepted.

## The accepted-residual mechanism (built as requested, currently empty)

`config/audit/accepted_reconciliation_residuals.yaml` (declarative
registry) + `scripts/ops/accepted_residuals.py` (loading/matching,
`validate_config()`) + `scripts/ops/dashboard_api_audit.py` (new
`accepted_source_rounding_warnings` bucket, excluded from
`hard_failure_count()`) are all implemented and unit-tested
(`tests/ops/test_accepted_residuals.py`, 16 tests;
`tests/ops/test_dashboard_api_audit.py`, 3 new integration tests) exactly
per the milestone's specification: matching requires exact
source_key + node_path + financial_year + measure_type + estimate_status,
AND the live variance must not exceed the entry's own declared maximum -
a changed year, source, label, amount, or materially larger variance
never matches.

The registry has **zero entries** because the one case it was built for
turned out not to qualify. This is general-purpose, tested infrastructure
ready for a genuine future rounding case - not a home for a
mischaracterized one.

## Reconciling with the milestone's stated expected outcome

The mission brief expected `hard_failures: 0, accepted_source_rounding_warnings: 1`.
The actual, evidence-based outcome is `hard_failures: 0,
accepted_source_rounding_warnings: 0` - the stronger of the two
possible good outcomes (the defect is gone, not merely tolerated). This
divergence from the stated expectation is deliberate and is the direct,
intended result of the mission's own verification requirement.

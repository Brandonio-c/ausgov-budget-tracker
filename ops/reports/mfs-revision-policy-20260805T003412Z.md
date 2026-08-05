# MFS revision and duplicate policy (Task 6)

Generated: 2026-08-05T00:34:12Z.

## What the real corpus actually shows

`federal_mfs_aggregates` has exactly **one** acquired snapshot (Task 2's
inventory: `data/raw/federal/federal_mfs_aggregates/snapshots/20260724T190604Z/`)
- there is no second, time-separated acquisition of this workbook to
compare for genuine revision behaviour. The only overlapping file found
anywhere in the corpus is the legacy, pre-split
`federal_monthly_financial_statements` bulk acquisition's own copy of
`6.-aggregates.xlsx` (Task 4), which is **byte-identical** (confirmed via
SHA-256) to the canonical copy - a confirmed identical republish, not a
competing edition. There is nothing in the real data to classify as a
"corrected revision," "cumulative snapshot," or "different accounting
basis/source series" overlap.

## Policy decision

Given the above, the applicable policy is: **retain the current
snapshot; refuse and quarantine (never silently overwrite) any future
re-acquisition that reports a different amount for an already-loaded
fact_key.** This is the mission's first listed option ("retain only the
latest revision when sources clearly supersede earlier publications"),
adapted to be conservative in the direction of safety: rather than
*automatically* accepting a new number as "the latest, correct" value (a
"processing order decides" outcome the mission explicitly forbids), a
genuine future conflict is quarantined for **explicit human review**,
not auto-resolved either way. `scripts/ingest/load_mfs_aggregates.py`
already implements exactly this (Task 5):

- Compute the fact's stable `fact_key` (source_family, financial_year,
  reporting_month, measure_type, accounting_basis, estimate_status,
  jurisdiction).
- If no fact with that key exists: insert.
- If one exists with the same amount (within 1 cent): skip - an
  idempotent no-op, this is the expected outcome of reloading the same
  source data.
- If one exists with a **different** amount: quarantine
  (`reason=amount_conflict_with_existing_fact`, recording both the
  existing and the new amount) and **do not touch the existing fact**.

No vintage/supersedes tracking columns were added to the schema, because
there is no real multi-vintage data to expose yet - adding unused
columns now would be speculative. If a genuine revision conflict is ever
found (via the quarantine file), the fix is a deliberate, reviewed config
decision (a `config/audit`-style registry, matching this repo's existing
`accepted_reconciliation_residuals.yaml`/`reviewed_duplicate_facts.yaml`
pattern from the prior milestone) - not a code change that silently
picks a winner.

## Synthetic-fixture tests (the real corpus has no case to test against)

`tests/ingest/test_mfs_revision_policy.py`, three tests, all passing:

1. **`test_reload_of_identical_data_is_idempotent`** - loading the same
   workbook twice produces exactly one fact both times; the second run
   reports `facts_to_insert: 0`, `facts_already_present_idempotent_skip: 1`.
2. **`test_reload_with_changed_amount_is_quarantined_not_silently_overwritten`** -
   a "revised edition" reporting a different Revenue figure for the
   identical (financial_year, reporting_month, measure_type) identity is
   quarantined (`revision_conflicts_quarantined: 1`), the original fact's
   `amount_aud` is confirmed unchanged in the database afterward, and the
   quarantine file records both the existing and rejected new amount.
3. **`test_reload_with_new_additional_month_inserts_only_the_new_fact`** -
   confirms the loader correctly distinguishes "a genuinely new reporting
   month" (inserted cleanly) from "a conflicting value for an existing
   one" (quarantined) - the two must not be conflated.

## Fixed a real test-isolation bug found while writing these tests

`load_mfs_aggregates.run()` originally wrote its quarantine JSONL to a
hardcoded repo path
(`data/staging/quarantine/mfs_load_quarantine.jsonl`) unconditionally -
running the revision-conflict test would have silently overwritten that
real (eventually production-meaningful, post-Task-7) file. Added a
`quarantine_path` parameter (default unchanged, for real CLI usage) so
tests can isolate their output to `tmp_path`; verified by re-running the
tests and confirming the real path is untouched.

## Next

Task 7: back up `data/facts.db` again immediately before running
`--apply` for real, run the load once, record before/after counts, run
the complete load again and confirm zero new duplicates/nodes/edges/
semantic changes, then run `task9_sql_integrity_checks.py`.

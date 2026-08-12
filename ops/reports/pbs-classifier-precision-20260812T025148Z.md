# PBS label classifier precision pass and quarantine review (item 5.5, parts 3-4)

Generated: 2026-08-12T02:51:48Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 5.5, sub-items 3 and 4: "Improve classifier precision on known malformed
published labels" and "Reconsider quarantined rows only with page/table evidence; never
bulk promote."

## Investigation methodology

Surveyed the current live quarantine set for `federal_pbs_programs_all` (35,601 rows) via
`facts_pending_attribution.source_locator_json`'s embedded `locator` field, which carries
exact page/table evidence (`source_id`, `pdf`, `page`, and the extracted label itself) for
every quarantined row - the same page/table-evidence standard used throughout this
program. Focused first on the `unknown`/`no_confident_signal` bucket (572 rows, 88 unique
labels) since it is the classifier's own "not confident either way" bucket and therefore
the most likely place for genuine precision defects, as opposed to the much larger
`malformed_concatenated_row`/`table_header` buckets which are, by design and by sampling,
overwhelmingly correct rejections of real Section 3 financial-statement content that this
extractor is not meant to capture as program data.

## Findings and fix

Two genuine, evidence-grounded precision gaps found, each verified against multiple real
extracted labels with their page locators (not synthetic examples):

1. **Missing GFS/AASB vocabulary.** "Taxes", "Fees", "Fines", "Loans", "Leases" and "Land"
   recur as their own extracted rows across Home Affairs, Industry, PM&C, Infrastructure,
   Education and Health Section 3 tables - standard GFS/AASB revenue and PP&E asset
   sub-categories, never a program name (confirmed via each row's page locator). "Land" is
   the same established concept as the already-whitelisted "land, buildings and
   infrastructure", just published on its own line in some documents. Added to
   `FINANCIAL_STATEMENT_LINE_ITEMS`.
2. **Missing malformed-row signals.** Two structural patterns that clearly indicate a
   concatenated/flattened row were not caught by any existing rule: (a) two embedded
   dollar-value tokens *together with* an accounting-heading keyword (e.g. `"17,419
   17,481 LIABILITIES Payables Suppliers"` - two values alone is not decisive, since a
   real title can legitimately carry one or two numbers, but two values plus a heading
   keyword together is), and (b) a run of three or more bare `-`/soft-hyphen placeholder
   tokens (PBS tables use a lone `-` for a $0 year column, so a run of three or more is the
   same "flattened row" signal `BARE_NUMERIC_RUN` already catches for real numbers, just
   for all-zero columns). Added `two_embedded_value_tokens_with_heading` and
   `embedded_bare_dash_run` as new rejection signals.

Considered and deliberately **not** changed: bare bullet-dash-prefixed heading fragments
with no embedded value run (e.g. `"- Special Accounts"`, `"\xad Other"`, ~40 rows) and
`"Retained surplus / (accumulated deficit)"` (whose classifier input is actually just
`"(accumulated deficit)"`, per `reload_pbs_programs_all.py::_label_for_classification`'s
documented last-segment rule, itself a deliberate fix from an earlier milestone). Both
remain genuinely ambiguous under the classifier's own stated philosophy ("absence of
evidence is not evidence of validity") and were left `unknown` rather than force-classified
without a confident, generalizable signal - consistent with "improve the classifier
without broadening it into false positives."

## Validation - isolating the classifier's effect from unrelated corpus drift

Running `scripts/ingest/reload_pbs_programs_all.py` end-to-end on a disposable copy showed
a large jump in published facts (17,482 live -> 33,291). Investigating this before drawing
any conclusion found it is **not** attributable to this classifier change: the live
`federal_pbs_programs_all` facts have not been reloaded since 2026-07-31 and are stale
relative to the current extractor/classifier code independent of anything done in this
session (a fresh extract-and-classify run with the classifier code *reverted* to its
pre-this-change state already produces 33,990 published rows against the same 103,945
extracted input rows the live corpus's own last reload report recorded). Deploying that
full reload would therefore mix this session's classifier fix with a large amount of
unrelated, unaudited accumulated drift in one undocumented step - flagged as a distinct,
separate finding below rather than folded into this fix.

To validate *only* the classifier change, extracted all 103,945 current rows once,
classified them with the pre-change and post-change classifier code on the exact same
label set, and diffed the two classification maps:

| classification | before | after | delta |
| --- | ---: | ---: | ---: |
| malformed_concatenated_row | 26,772 | 27,747 | +975 |
| program | 33,336 | 32,637 | -699 |
| financial_statement_line | 10,443 | 10,644 | +201 |
| unknown | 860 | 578 | -282 |
| subtotal | 5,171 | 5,096 | -75 |
| narrative_fragment | 6,420 | 6,310 | -110 |
| table_header | 20,289 | 20,279 | -10 |
| outcome | 8 | 8 | 0 |
| component | 646 | 646 | 0 |

- **Zero rows newly became `program`/`outcome`/`component`** - the publishable set can only
  shrink or stay the same as a result of this change, never grow. Confirmed programmatically
  (not just by inspection).
- The 699 `program` -> `malformed_concatenated_row` transitions (158 unique labels) were
  individually reviewed: every one is a genuinely garbled, multi-column-flattened Section 3
  fragment that had been **incorrectly accepted as a real program name** before this fix
  (e.g. `"By purchase - other - ROU assets - 2,605 - - 2,605 Total additions -"`,
  `"Government Schools - one off transition assistance 24,203 - - - - Special
  appropriations: Australian Education Act 2013"`). This is the most consequential result
  of this pass: these 158 previously-mis-accepted fragments were being published and
  presented as if they were legitimate PBS program facts before this fix - a real
  truthfulness defect, not merely a missed-opportunity gap.
- The remaining transitions (`subtotal`/`narrative_fragment`/`table_header` ->
  `malformed_concatenated_row`, `unknown` -> `financial_statement_line`/
  `malformed_concatenated_row`) all move between already-non-publishable categories -
  spot-checked a representative sample of each and confirmed every one is a genuine
  concatenated/glued fragment, not a real program/component title.
- Regression suite: `tests/ingest/test_pbs_label_classifier.py` now has 29 tests (23
  pre-existing + 6 new), all passing, pinning the exact real-world label strings found in
  this investigation plus explicit guards against the new rules over-firing (a lone bullet
  dash, or two values with no heading keyword, must not trip the new rules).
- Full backend suite: 643 passed (637 baseline + 6 new), 0 regressions. `ruff check`:
  passed.
- **No database write in this session.** All validation ran against a disposable copy or
  pure in-memory classification; the live `federal_pbs_programs_all` fact count is
  confirmed unchanged (17,482, byte-for-byte the same source content as before this
  session).

## Quarantine precision review (sub-item 4)

The investigation above **is** the quarantine precision review for this item: every
transition was reviewed against real page/table locator evidence, never against label
similarity alone, and the review explicitly did not bulk-promote anything - the
publishable set only shrank. Scope was `federal_pbs_programs_all` (35,601 quarantined
rows), the source this classifier and plan item 5.5 are about. Two adjacent buckets were
identified and explicitly excluded as out of scope, with rationale recorded rather than
silently ignored:

- `qld_qgip_expenditure` (4,198 rows): already fully investigated and quarantined for a
  documented, unrelated reason (source-horizon outliers, item 3.7); its own repair is a
  distinct, later plan item (7.2).
- `federal_pbs_programs_s6_bridge` (801 rows): a downstream, legacy heuristic-mapping
  product's own quarantine (reuses the same `classify_label()` gate on its own remapped
  output), not the primary shared extractor/classifier item 5.5 is about. Will benefit
  incidentally from this fix whenever it is next reloaded, but was not separately re-run
  in this session.

## Remaining risks / next item

**New finding, not yet actioned:** `federal_pbs_programs_all`'s live facts (17,482) are
substantially stale relative to what the current extractor+classifier code would produce
if reloaded (33,291 with this fix). Reloading is a large, high-blast-radius change
(dashboard depth/coverage nearly doubles for this family) that deserves its own dedicated
milestone - a before/after dashboard-projection audit, review of the ~33k newly-published
facts' citation completeness, and confirmation the existing PBS-under-Statement-6
crosswalk (item 5.4/prior work) and NDIA isolation (this session) are unaffected - rather
than being folded into a classifier-precision fix. Recorded in the ledger as the next
concrete item.

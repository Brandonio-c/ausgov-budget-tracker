# State borrowing (item 7.3) - status correction and scoping

Generated: 2026-08-14T14:00:19Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 7.3: "Repair or add adapters for acquired missing/broken sources using a
common borrowing adapter contract." The current progress ledger and the atlas/backlog
reports describe this as "seven loaded, six adapter-missing, three adapter-broken."
Investigated before writing any adapter code, per this program's standing discipline -
found the "three broken" characterization is stale and would have led to a wrong action
if acted on directly.

## Finding 1: the "three broken" sources are not broken - they are already-resolved, intentionally retired duplicates

`nsw_tcorp_weekly_bonds`, `qld_qtc_benchmark_bonds`, and
`qld_qtc_weekly_outstandings_2026_07_17` each have a `source_documents` row with zero
live facts, which the atlas/backlog reports characterize as "broken/zero-fact" needing
repair. Re-running each through the current pipeline confirms they extract and load
cleanly with zero errors (14/36/19 facts respectively, tested against a disposable copy,
not live) - so nothing is actually broken in the code today.

However, `ops/reports/orphan-node-investigation-20260804T180700Z.md` (2026-08-04, predating
this session) already investigated and resolved this exact question: these three
`source_id`s are **fully-retired legacy identifiers**, superseded by
`nsw_tcorp_bonds_on_issue` and `qld_qtc_aud_bond_outstandings` respectively, no longer
referenced anywhere in `m_borrowing_authorities.py`'s `SOURCE_PARSERS` dict, and their
orphaned nodes were already deliberately cleaned up as a one-time pass. Their
`source_documents` rows were **left in place on purpose** (informational-only per
`task9_sql_integrity_checks.py`'s `dangling_source_documents` classification, not a hard
failure) as a record of retirement, not a to-do item.

**Reloading these three would be actively wrong**: `nsw_tcorp_weekly_bonds` and
`nsw_tcorp_bonds_on_issue` cover the same NSW TCorp bond population from two different
report cadences (weekly vs on-issue); loading both under the same `gfs_liability`
compatibility group would double-count NSW debt. Same for the two QTC sources against
`qld_qtc_aud_bond_outstandings`. The atlas report's "three broken" framing is stale and
should not be read as a to-do list.

## Finding 2: the state-borrowing "missing" family is broader and messier than a clean "six"

Beyond the 7 loaded + 3 retired-legacy sources tracked in
`config/lineage/canonical_datasets.yaml`'s `state_borrowing_authorities` entry,
`config/procurement_sources.yaml` has 8 further acquired-but-unadapted state-authority
sources, each with real raw files already on disk:

| source_id | authority | file format |
| --- | --- | --- |
| `nt_nttc_annual_report_2024_25` | NT NTTC | PDF (annual report) |
| `sa_safa_funding_program_2026_27` | SA SAFA | PDF |
| `tas_tascorp_bond_programme` | TAS TASCORP | PDF |
| `tas_tascorp_financial_markets` | TAS TASCORP | PDF |
| `vic_tcv_data_feeds` | VIC TCV | XLSX |
| `vic_tcv_benchmark_bond_outstandings` | VIC TCV | CSV |
| `wa_watc_annual_report_2025` | WA WATC | PDF |
| `wa_watc_investor_term_sheets` | WA WATC | (format not yet checked) |

Separately, the most recent ingestion-coverage audit
(`ops/reports/ingestion-coverage-20260808T161257Z.md`) shows a materially larger,
**federal** debt-instrument family (AOFM - Australian Office of Financial Management) with
12 `adapter_missing`/`adapter_broken` sources (`aofm_foreign_holdings`,
`aofm_portfolio_aggregate_dealt/settlement`, `aofm_register_government_borrowing`,
`aofm_stock_ags_csv`, `aofm_treasury_bonds_dealt/settlement`,
`aofm_treasury_indexed_bonds_dealt/settlement`, `aofm_treasury_notes_dealt/settlement`) -
outside plan item 7.3's explicit "state borrowing" scope, but worth flagging as a
distinct, larger family the plan does not yet have a numbered item for.

## Finding 3: at least one "missing" candidate substantially overlaps already-loaded data

Direct inspection of `vic_tcv_benchmark_bond_outstandings.csv` before writing any adapter
code: it is a maturity-keyed table with two reporting-date columns (30.06.2025,
30.06.2026). Cross-checking one security (17-Nov-26 maturity) against the already-loaded
`vic_tcv_amount_on_issue` staging data: this file's 30.06.2026 figure ($7,071.344m) matches
the already-loaded "17 Nov 2026 5.5" fixed-rate bond fact ($7,071,340,000) to within normal
independent-rounding tolerance - the same security, the same population, substantially the
same current-date figures already captured by the loaded source. The only genuinely new
information in this file is the 30.06.2025 (prior-year) column - a real, non-duplicative
historical comparison point, but building an adapter that treats the whole file as new
data would risk exactly the double-counting this program's rules forbid. A correct
adapter here would need to either load only the non-overlapping historical column, or tag
the whole file under a measure_type that is explicitly understood as a named
subset/cross-section view rather than an independent additive quantity - not attempted in
this pass, since it requires more careful verification than fits inside this session's
remaining scope for this item.

## Disposition

- **Ledger corrected**: "three broken" is downgraded from "needs repair" to "confirmed
  intentionally retired, no action needed" - a real, load-bearing correction to this
  program's own record, preventing a future agent from wrongly reloading duplicate data.
- **Six-plus missing sources inventoried with real evidence**, not the previous vague
  "six." At least one (`vic_tcv_benchmark_bond_outstandings`) is flagged as needing
  careful non-additive treatment rather than a straightforward new adapter.
- No adapter code written this pass - each of the 4 remaining PDF-format sources
  (`nt_nttc_annual_report_2024_25`, `sa_safa_funding_program_2026_27`,
  `tas_tascorp_bond_programme`, `tas_tascorp_financial_markets`, `wa_watc_annual_report_2025`
  - 5, not 4) carries the same per-document table-shape risk already demonstrated this
  session for the MFS Operating Statement workbook and would need the same
  evidence-first, one-at-a-time treatment before any is safely adapted.

## Recommended next steps for a dedicated future pass

1. Directly inspect each of the 5 PDF sources' actual table structure before writing any
   parser (matching the discipline already applied throughout this session) - do not
   assume they share `adapters/state_debt_instruments.py`'s existing `kind` parsers
   without verifying.
2. For `vic_tcv_benchmark_bond_outstandings` and `vic_tcv_data_feeds`, resolve the
   overlap/subset relationship with the already-loaded `vic_tcv_amount_on_issue` before
   loading anything, following the same evidence-based method used here.
3. Treat the AOFM (federal) debt-instrument family as a separate, larger piece of work,
   not folded into item 7.3's "state borrowing" scope without an explicit plan decision.

## Next item

Given the real per-source investigation each of these requires, redirecting this
session's Wave 5 effort to a more homogeneous, better-scoped item - item 7.5 (QLD
on-time payments, 42 acquired CSVs, likely one consistent format from one publisher) -
while leaving this corrected, evidence-based inventory for item 7.3's next dedicated pass.

## Addendum (2026-08-14T19:30:00Z), after item 7.5 landed: `vic_tcv_data_feeds` checked and found mislabeled

Re-checked `vic_tcv_data_feeds` (the one XLSX-format source in the 8-source inventory
above, hoped to be more tractable than the 5 PDFs) before writing any adapter code: its
one acquired file is `5.4_2022_Financial_Statements.xlsx` with 26 sheets literally named
`Page 2`..`Page 26` - a full annual financial-statements report converted page-by-page to
Excel, not a structured bond-outstandings data feed as the `source_id` name implies. This
carries the same unstructured per-page/per-table inspection risk already flagged for the
5 PDF sources, not a quick win. No adapter code written.

`wa_watc_investor_term_sheets` (`.zip`, contents now checked) unzips to 17 individual PDF
"investor term sheets," one per WA WATC bond issuance (e.g.
`watc-225-23-july-2041-final-investor-termsheet.pdf`). These are a fundamentally
different document type from the rest of this family: a term sheet describes the
**static issuance terms** of one bond (coupon, maturity, ISIN, face value at issue) at a
point in time, not a periodic time series of outstanding balances - the shape the
existing `gfs_liability`/borrowing-outstanding measure contract expects. Modeling these
correctly would need either a distinct non-additive "instrument static terms" measure
type (not summed with outstanding-balance facts) or per-issuance reconciliation against
`wa_watc_annual_report_2025`'s own outstanding figures - a design question, not an
extraction question, and out of scope for a same-pattern adapter reuse.

**Revised conclusion**: all 8 sources in this inventory (5 PDF + `vic_tcv_data_feeds`
mislabeled-XLSX + `vic_tcv_benchmark_bond_outstandings` overlap risk +
`wa_watc_investor_term_sheets` wrong-shape-entirely) genuinely require individual
bespoke design, not a shared adapter reuse pass. None was built this session.

## Addendum (2026-08-15T16:35:00Z): a pre-existing generic borrowing adapter already covers all 7 authorities - the "5 missing PDFs" are supplementary documents, not a complete gap

Before attempting to build any of the 5 PDF sources, `scripts/ingest/adapters/
state_debt_instruments.py` was found and read in full - a **pre-existing, already-wired**
generic adapter (`InstrumentRow` dataclass, proper `face_value`/`fair_value`
`valuation_basis` distinction, `instrument_type_aggregate` vs `individual_security`
`amount_granularity` distinction - exactly the "keep face value/fair value distinctions
explicit" contract this mission's own instructions ask for) with 7 `SOURCE_PARSERS`
entries. Checked directly against live `data/facts.db`: **all 7 are already loaded**:

| source_id | live facts |
| --- | --- |
| `vic_tcv_amount_on_issue` | 32 |
| `nsw_tcorp_bonds_on_issue` | 36 |
| `qld_qtc_aud_bond_outstandings` | 38 |
| `sa_safa_weekly_funding_update` | 18 |
| `wa_watc_funding_sources` | 21 |
| `nt_nttc_borrowing_strategy` | 17 |
| `tas_tascorp_annual_report_2024_25` | 8 |

Every one of the 7 named borrowing authorities already has at least some coverage. The 5
PDF sources this report investigates (`nt_nttc_annual_report_2024_25`,
`sa_safa_funding_program_2026_27`, `tas_tascorp_bond_programme`,
`tas_tascorp_financial_markets`, `wa_watc_annual_report_2025`) are **different
source_ids from, and different documents than**, the ones already adapted (e.g.
`wa_watc_annual_report_2025` is a 118-page annual report; `wa_watc_funding_sources`,
already loaded, is a different, presumably instrument-level CSV/data feed) - they would
be **supplementary** additions for already-partially-covered authorities, not filling a
complete gap, and the value/effort case is accordingly weaker than initially assumed.

Direct inspection of 3 of the 5 (not attempted in the original pass):

- **`sa_safa_funding_program_2026_27`** (5 pages): a narrative "Market Release" bulletin,
  not a tabular bond-outstanding dataset - dominated by multi-year Budget/MYEFO
  **forecast/estimate** tables for FY2026-27..FY2029-30, with exactly one genuine
  actual/current data point (Total debt "Actuals 4 June" = $50.4bn). Loading the
  forecast tables under the same measure as actual outstanding debt would violate this
  program's "never substitute a forecast for an actual" rule; the one real actual figure
  is too thin (a single point-in-time total, not a series) to justify a dedicated build.
- **`tas_tascorp_bond_programme.pdf`** (38 pages): an investor-presentation slide deck
  ("2026-27 Debt Investor Update") - narrative/marketing content (Tasmanian economy,
  sustainability credentials, government structure) dominates the pages checked; likely
  unreliable for structured text extraction even where tables exist (slide-deck tables
  are frequently rendered as images/charts, not extractable text).
- **`wa_watc_annual_report_2025.pdf`** (118 pages): genuinely well-structured financial
  statements (a clean "Statement of Financial Position" note with `Borrowings 49,459.5
  47,857.2` for FY2025/FY2024) - the most tractable of the 5, but only yields 2 years of
  data from this single acquired edition (no historical series without acquiring further
  editions), and its relationship to the already-loaded `wa_watc_funding_sources`
  instrument-level data (does the aggregate reconcile to the sum of individual
  securities?) has not been checked - a genuine cross-check opportunity, not attempted
  this pass given the low data-volume return.

## Disposition (revised)

Given all 7 authorities already have baseline coverage via the existing generic adapter,
and the 5 PDF sources are lower-value supplementary documents (one is forecast-dominated
and not safely loadable at all; one is a narrative slide deck with likely poor
extractability; the most tractable one yields only 2 data points), this item's remaining
work is genuinely lower-priority than initially ranked. Redirecting this session's further
Wave 5 effort to item 7.4 (QLD Consolidated Fund), a completely unstarted area with (on
initial inspection) a larger and more clearly-scoped acquired corpus (46 PDFs).

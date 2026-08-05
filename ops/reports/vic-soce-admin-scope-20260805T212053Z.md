# VIC SOCE/Admin scope (Task 1)

Generated: 2026-08-05T21:20:53Z.

## Ground truth verified before any implementation

- `git status --short`: clean. Branch `main`. `HEAD` and `origin/main`
  both at `4acd4f8` (verified via `git fetch origin` + `git rev-parse`).
- `ops/reports/current-state.md`: general project overview, no
  family-specific detail affecting this selection.
- `config/canonical_datasets.yaml` does not exist at that path - the
  actual file is `config/lineage/canonical_datasets.yaml`, and (as
  found in the prior two milestones) it only tracks already-fully-
  ingested canonical datasets, not this backlog item.
- `config/procurement_sources.yaml`: `vic_budget_portfolio_outcomes_
  2024_25`'s registry entry (already used by the loaded VIC BPO family)
  is the same source for these deferred sheets - no separate
  acquisition needed.
- `grep -rn` across `scripts/ingest/` and `config/measure-semantics/`
  for SOCE/Admin-specific logic: nothing found - only the already-
  committed OS/BS/CFS handling exists.

## Which "SOCE" and "Admin" - disambiguating between two workbooks

Both the already-loaded VIC AFS and VIC BPO workbooks have a sheet
literally or conceptually named "Statement of Changes in Equity" /
"Administered ...". The mission's own wording ("VIC Statement of Changes
in Equity (SOCE)", "VIC Administration sheet(s)") uses the exact sheet
**tab names** that only match the **BPO** workbook (`SOCE`, `Admin`) -
the AFS workbook's equivalent sheets are named differently and there are
more of them (`Statement of Changes in Equity`, `Departmental Outputs
Schedule`, `Annual Appropriations`, `Special Appropriations`,
`Administered Income & Expenses`, `Administered Assets & Liab` - 6
sheets, a substantially larger and more varied deferred set). The
mission's own framing ("the remaining limitation is that VIC SOCE and
Admin sheets were deferred" - stated as a single, bounded pair) also
matches BPO's exactly-2-sheet remainder, not AFS's 6-sheet remainder.

**Selected: the BPO workbook's `SOCE` and `Admin` sheets.** AFS's
remaining 6 deferred sheets are out of scope for this milestone
(unchanged from the prior deferral - a future, separate milestone).

## Source file - already on disk, unchanged

- `data/raw/state/vic_budget_portfolio_outcomes_2024_25/snapshots/20260724T190604Z/files/Budget-portfolio-outcomes-2024-25.xlsx`
- sha256 `a947a1bfe2dc7ec701acd8c03630010d7f55312d214aaf10cf273ca99809547e` -
  verified identical to the hash already recorded when VIC BPO's OS/BS/
  CFS sheets were loaded (same acquisition, same file, no re-download
  needed).
- Format: structured xlsx (not PDF) - both sheets.

## `SOCE` - fully re-inspected

23 rows, 4 columns. Genuinely different shape from OS/BS/CFS: a
**rolling-balance-across-multiple-columns** structure, not a simple
Actual/Budget/Variance comparison table:

- 3 **row-blocks**, each headed by its own label (`2024-25 actuals`,
  `2024-25 original budget`, `Variance`), determining `estimate_status`
  for every row until the next block header.
- 3 **columns** (`Accumulated surplus`, `Contributions by owner`,
  `Total equity`) - a further sub-component breakdown of equity.
- Within each block: `Balance at 1 July 2024` (opening), `Comprehensive
  result`, `Transactions with owners in their capacity as owners`,
  `Balance at 30 June 2025` (closing, with a trailing footnote marker on
  the budget block's row).

Two values are **already captured elsewhere and would duplicate**:
`Balance at 30 June 2025` (Total equity column) = 83/87, identical to
the already-loaded `vic_bpo_net_assets` (BS); `Comprehensive result`
(Total equity column) = 7/0, identical to the already-loaded
`vic_bpo_net_result` (OS). Two values are **genuinely new**: `Balance at
1 July 2024` (opening equity position - FY2024-25's actual/budget both
show 76, never previously captured since OS/BS/CFS only cover the
FY2024-25 closing position) and `Transactions with owners in their
capacity as owners` (capital contributed by/returned to the State as
owner - actual=0, budget=10 - a genuinely new concept, distinct from
operating result).

The `Accumulated surplus`/`Contributions by owner` sub-component columns
are **out of scope this milestone** (deferred, not silently dropped) -
only the `Total equity` aggregate column is extracted, matching the
level of detail already modelled elsewhere in this family.

## `Admin` - fully re-inspected

68 rows, 4 columns. Same column shape as OS/BS/CFS (`Actual | Budget |
Variance`, with the same multi-line header text, inline footnote
markers, and lowercase-letter-parenthetical footnote-block
termination) - but a **materially different concept**: Administered
Items (payments made **on behalf of the State**, not the department's
own controlled operations), at a **completely different scale** (e.g.
`$82 billion` administered income vs `$466 million` controlled
revenue, already documented as the reason for deferring this sheet).

**A real design finding**: `Admin`'s row labels `Net result` and `Net
assets` are **identical text** to `OS`'s `Net result` and `BS`'s `Net
assets`, but mean entirely different things (administered vs controlled
operations). The existing, already-deployed `vic_bpo.py`/`reload_
vic_bpo.py`'s `build_label_index()` builds a single flat
label-to-measure_type dictionary and raises `ValueError` on any
colliding label claimed by two measure types - it has no per-sheet
scoping, because it was never asked to handle two sheets sharing a row
label with different meanings. Extending its `TARGET_SHEETS` to include
`Admin` would hit this collision immediately. **This is not a bug in
the already-shipped OS/BS/CFS loader** - it was correct for its actual
scope - but it means SOCE/Admin need their own, separately-scoped label
index, not a reuse of the existing one. Confirmed also: `Admin`'s own
`Net result` (-16,443/-14,571) and `Comprehensive result`
(-15,657/-13,823) are **not** a duplicate pair here (unlike OS's) -
they genuinely differ by the `$786m/$747m` "other comprehensive income"
adjustment, so both are loaded as distinct measures.

## Decision

Build one new, additional adapter (extractor + loader + semantic model)
for `SOCE` + `Admin` together - a tight cluster from the same workbook,
deferred together, with their own sheet-scoped label index - **without
modifying** the existing, already-deployed `vic_bpo.py`/`reload_vic_bpo.
py`/`vic_bpo.yaml` at all (no bug found in them; the collision is a
consequence of widening scope, not a defect in what's already shipped).

## Cloudflare route dependency

VIC BPO (including this deferred-sheet extension) is exposed via the
existing GFS/jurisdiction explorer (`/explorers/gfs`), reached in
practice via in-app client-side navigation - the same page and the same
reasoning already established and re-confirmed in the prior two
milestones. See Task 2's dedicated triage report for the explicit
scope decision.

## Next

Task 2: Cloudflare scope decision. Task 3: build the SOCE/Admin adapter.

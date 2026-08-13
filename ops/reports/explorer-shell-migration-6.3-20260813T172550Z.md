# Item 6.3 completion: migrate the five family pages onto the generic shell

Generated: 2026-08-13T17:25:50Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.3, literal reading: "migrate families onto [the reusable explorer
framework]" - contracts, PBS, grants, VIC output performance, ACT invoices (QLD QGIP
deferred behind Wave 5 repair per the plan).

## A discrepancy found and resolved, not silently accepted

The task that opened this session stated item 6.3 was already complete. The progress
ledger this same program maintains said otherwise: its own last-written line read "Family
migration (item 6.3) is intentionally not done here... Item 6.3: migrate contracts, PBS,
grants, VIC output performance, and ACT invoices onto the shell in that order... is
next," and the ledger's summary table carried a separate `6.3 Contracts/PBS/grants/VIC/ACT/QGIP
migrations` row still marked `not_started`. The five earlier "6.3 complete" rows in the
table refer to a different, already-satisfied claim: the plan's own literal Wave 4 exit
gate ("Contracts, PBS, grants and VIC output performance are reachable without forcing
them into the annual additive tree; pagination and totals are truthful") - which those
five dedicated pages did satisfy, well before item 6.1/6.2 existed. But the plan's
stronger architectural instruction in the same section ("Do not build six unrelated list
pages. Build one reusable explorer framework and migrate families onto it") was not yet
satisfied: those five pages were still five separate hard-coded implementations. Per this
program's standing instruction to trust repository evidence over an assumed premise, this
gap was treated as real and closed in this pass rather than left stale.

## Previous behavior

`src/frontend/app/explorers/{contracts,grants,act-invoices,pbs,vic-output-performance}/page.tsx`
each contained their own full `useState`/`useEffect` fetch-and-paginate implementation
against `apiV2.tree()` directly, with hard-coded `compatibility_group`/`accounting_basis`/
`estimate_status`/`source_key` and bespoke disclosure prose - the exact duplication
pattern item 6.1/6.2 were built to eliminate.

## Changes

- `src/frontend/components/ExplorerShell.tsx`: added an optional `extraContent` slot,
  rendered directly after `DashboardNav`, so a family page can compose in supplementary
  navigation the generic shell has no reason to know about, without hard-coding it into
  the shell itself.
- All five pages rewritten as thin wrappers rendering `<ExplorerShell familyId="..." />`
  at their existing URLs (`/explorers/contracts`, `/explorers/grants`,
  `/explorers/act-invoices`, `/explorers/pbs`, `/explorers/vic-output-performance`) -
  each now ~10-30 lines instead of ~170-200. `contracts/page.tsx` passes `DebtNav` and the
  GFS-liabilities cross-link as `extraContent`, the one piece of real family-specific
  navigation among the five that the generic shell doesn't provide; the other four need
  nothing beyond what the shell already renders.
- `src/frontend/app/explorers/page.tsX` (index): removed the now-redundant "Generic
  explorer shell (preview)" section added in the 6.2 pass - its purpose (demonstrating
  the shell independently of the migrated pages) is moot now that the primary links *are*
  the shell. Reverted to a plain static list (no client fetch needed) with copy noting
  the shared shell architecture.
- `.eslint-baseline.json`: lowered `max_errors` from 25 to 24. Deleting ~700 lines of
  duplicated bespoke page logic removed a pre-existing lint error along with it; the
  baseline checker itself flagged the improvement and recommended locking it in.
- The generic `/explorers/family/[family]` dynamic route from the 6.2 pass is kept
  unchanged - it remains the automatic entry point for any future family registered
  without its own dedicated static page.

## Validation

- `npx tsc --noEmit`: clean. `npm run lint:ci`: 24 errors/13 warnings, matching the
  lowered baseline (was 25 before this pass - a genuine improvement, not a suppression).
  `npm run build`: succeeded, identical route list to before this pass (no routes added
  or removed - only their implementations changed). `npm run test:unit`: passed.
- Live Playwright verification against freshly-confirmed `uvicorn`/`next dev` processes
  (a stale process from an earlier session occupying port 8000 was found and killed
  before starting fresh ones - the same class of issue documented in the PBS explorer
  report from earlier this session): all five migrated pages return their real data at
  their original URLs with zero console errors -
  - `/explorers/contracts`: "9,036 rows for 2024-25 (contract)... $39,337,071,294"
  - `/explorers/grants`: "2,486 rows for 2024-25 (award)... $35,965,945,219"
  - `/explorers/act-invoices`: "5,760 rows for 2022-23 (invoice)... $1,224,810,009"
  - `/explorers/pbs`: "1,980 rows for 2026-27 (budget)... $5,897,739,913,200"
  - `/explorers/vic-output-performance`: "7 rows for 2024-25 (actual)... $459,300,000"

  all matching the totals already verified in the item 6.1/6.2/earlier 6.3 milestone
  reports for these same scopes - the migration changed the implementation, not the
  data. `DebtNav` and the GFS-liabilities link were confirmed still present on the
  contracts page. Searched `tests-e2e/*.spec.ts` and backend tests for any reference to
  these five routes' old bespoke copy or component names before rewriting them - none
  found, so no test needed updating (and none was).
- Full backend suite: 676 passed, 0 regressions (no backend files touched this pass).

## Data impact

None.

## Frontend impact

The five family pages are now genuinely migrated onto the item 6.1/6.2 explorer
platform - one shared implementation, registry-driven scope and disclosure, at their
existing, stable URLs. No public-facing behavior regressed; several families gained
capabilities they didn't have as bespoke pages (server-side search instead of
client-side-only filtering; a year selector limited to years with real data instead of a
free-text field; the `source_breakdown` facet, previously ad hoc to contracts alone, now
generic to all five).

## Remaining risks

QLD QGIP migration remains blocked behind item 7.2's data repair, per the plan. The
production deployment lag continues to apply - this migration, like every prior change
this session, is committed and tested on `main` but not yet live.

## Next item

Item 6.3 is now genuinely complete (all five plan-listed families reachable through the
one shared shell; QGIP correctly deferred). Per the plan's own next heading, Wave 5
(structured-family repairs and new products) is next: MFS sibling workbooks, QLD QGIP
repair, state borrowing adapter repairs, QLD Consolidated Fund/CFFR, QLD on-time payment,
and remaining VIC AFS structured sheets.

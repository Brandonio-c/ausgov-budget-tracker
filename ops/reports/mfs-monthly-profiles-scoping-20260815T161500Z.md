# MFS Monthly Profiles - scoping investigation

Generated: 2026-08-15T16:15:00Z
Repository: `ausgov-budget-tracker`, branch `main`

## Context

Item 7.1's fifth named workbook, Monthly Profiles (`federal_mfs_monthly_profiles`,
`1.-aggregates-mp.xlsx`, 17 year-sheets 2009-10..2025-26). An earlier scoping pass this
session (based on a 2-year sample) characterized this as "only the first column of each
year is ACTUAL; every later column is a forward-looking forecast profile never replaced
with real actuals." A full 17-sheet header dump before writing any extractor code found
that characterization was incomplete, and surfaced a genuinely harder design problem than
initially scoped.

## Finding 1: the earlier "only first column is ACTUAL" claim is wrong for at least 4 of 17 years

Direct inspection of every sheet's per-column status label (the first line of each
header cell) shows `ACTUAL*` reappearing **after** a run of forecast-basis columns in
several years - not just leading:

- **FY2020-21**: `ACTUAL*, ACTUAL*, Budget, Budget, Budget, MYEFO, MYEFO, MYEFO, MYEFO, MYEFO, Revised` (2 leading actuals, not 1)
- **FY2022-23**: `ACTUAL*, ACTUAL*, ACTUAL*, ACTUAL*, October, October, October, October, October, October, Revised` (4 leading actuals)
- **FY2023-24**: `ACTUAL*, Budget, Budget, Budget, ACTUAL*, ACTUAL*, MYEFO, MYEFO, MYEFO, MYEFO, Revised Budget Profile` (actuals reappear at columns 5-6, after 3 Budget-basis columns)
- **FY2025-26**: `ACTUAL*, Budget, Budget Profile, Budget Profile, Budget Profile, Budget Profile, MYEFO Profile, MYEFO Profile, MYEFO Profile, ACTUAL*, Revised Budget Profile` (an actual reappears at column 10, after 5 forecast-basis columns)

This means the file is republished/updated over time as forecasts convert to real
actuals for months that have since occurred - sensible real-world behavior for a "monthly
profile" tracking tool, but the opposite of what the earlier scoping pass concluded.

## Finding 2: the estimate_status label set is far messier than a simple 2-3 value enum

Every sheet's status labels, verified directly (first line of each column header cell,
not assumed from one era):

| raw label variants seen | apparent meaning |
| --- | --- |
| `ACTUAL*` | actual |
| `Budget`, `Budget Profile`, `BUDGET` | budget-time forecast profile |
| `MYEFO`, `MYEFO Profile` | Mid-Year Economic and Fiscal Outlook forecast profile |
| `Revised`, `Revised Budget`, `REVISED`, `Revised Budget Profile` | a revised/updated forecast profile, itself inconsistently named |
| `October` (FY2022-23 only) | almost certainly the October 2022 Budget (Australia's 2022 federal election delayed that year's usual May Budget to October) - a genuine, real one-off basis, not a data error |

At least 4 distinct real economic bases (actual, budget-time forecast, MYEFO forecast,
revised forecast) are disclosed under at least 10 raw label spellings/casings, with one
further year-specific one-off (`October`) that needs its own confirmed interpretation
before being safely classified. Normalizing this correctly (verifying each variant means
the same thing across every year it appears, not just assuming from textual similarity)
is a genuine design task on the same order of complexity as the Balance Sheet
generation-crosswalk work already done this session - not a small extension of the
existing YTD-flow extractor.

## Finding 3: the file's own unit changes within itself

Confirmed directly (already found in an earlier scoping pass, re-verified here): `$m` for
every year except FY2025-26, which uses `$b` - must be read per-year from the header, never
hardcoded.

## Finding 4: the genuinely new value is concentrated in the forecast columns, which carry all of the above complexity

The `ACTUAL*` columns in this file describe the exact same real-world Revenue/Expenses/
Net operating balance/Net capital investment/Fiscal balance/Underlying cash balance/
Headline cash balance figures already loaded from `federal_mfs_aggregates` under the
`mfs_ytd_*` measures - loading them again from this file would be pure duplication, not
new information (and risks two independently-provenanced series for the same real fact,
the same risk already avoided for Balance Sheet's headline totals). The forecast-basis
columns (`Budget`/`MYEFO`/`Revised`/etc.) are the only genuinely new information this
workbook offers - but extracting them correctly requires solving Finding 2's
classification problem first.

## Disposition

Given the plan lists Monthly Profiles as the last of the 5 named MFS sibling workbooks,
and this investigation confirms it needs a dedicated estimate_status-normalization design
pass (comparable in scope to the Balance Sheet generation-crosswalk work) rather than a
quick extension of the already-proven YTD-flow extraction pattern, no extractor/loader
code was written this pass. Recommended before any future build: confirm the `October`
FY2022-23 label's exact meaning against the real October 2022 Budget publication, and
verify (not assume) that each of `Budget`/`Budget Profile`/`BUDGET` genuinely represents
the same underlying forecast basis across every year it appears, the same way this
session verified label-identity claims for every other MFS sibling before combining
labels into one measure.

## Next item

Item 7.1's other 4 named workbooks are now resolved (Note 3 loaded, Operating Statement
deferred with evidence, Balance Sheet loaded, Tax Notes 1-2 loaded); Monthly Profiles is
the 5th, now also deferred with evidence rather than force-built. Redirecting this
session's effort to item 7.2 (QLD QGIP dedicated explorer, following the already-completed
data-contract repair) per the mission's explicit ordering.

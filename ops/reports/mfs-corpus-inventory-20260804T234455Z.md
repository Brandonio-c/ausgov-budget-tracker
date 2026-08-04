# MFS corpus inventory (Task 2)

Generated: 2026-08-04T23:44:55Z. Read-only inspection of every acquired
Federal Monthly Financial Statements workbook under `data/raw/federal/`.
Full per-sheet detail: `ops/reports/mfs-corpus-inventory-20260804T234455Z.csv`
(produced by `scripts/ops/mfs_corpus_inventory.py`). No writes to
`data/facts.db`.

## Seven distinct acquired source_ids, mapping onto the mission's required shapes

| source_id | shape | file | sheets (years) | extractor support |
|---|---|---|---:|---|
| `federal_mfs_aggregates` | Aggregates | `6.-aggregates.xlsx` | 26 (2000-01..2025-26) | **Supported** - `scripts/ingest/extractors/mfs_aggregates.py` - this milestone's load target |
| `federal_mfs_operating_statement` | Operating Statement | `1.-operating-statement.xlsx` | 21 (2005-06..2025-26) | Not supported - no extractor; out of scope this milestone |
| `federal_mfs_balance_sheet` | Balance Sheet | `2.-balance-sheet.xlsx` | 21 (2005-06..2025-26) | Not supported - out of scope |
| `federal_mfs_note3_function` | Notes/supplementary (Expense by Function) | `5.-note-3-function-statement.xlsx` | 21 | Not supported - out of scope |
| `federal_mfs_tax_notes_1_2` | Notes/supplementary (Income Tax detail) | `4.-note-1-and-2.xlsx` | 21 | Not supported - out of scope |
| `federal_mfs_monthly_profiles` | Monthly Profiles | `1.-aggregates-mp.xlsx` | 17 | Not supported - out of scope |
| `federal_monthly_financial_statements` | legacy bulk (pre-split), incl. `3.-cashflow-statement.xlsx` | 10 assets across 8 old snapshots | Superseded by the sources above (cash flow statement has no dedicated source_id yet); the 288-fact stray preload from this source was removed in Task 1 |

No dedicated `federal_mfs_cashflow_statement` source_id exists yet - the
Cash Flow Statement shape is only present inside the legacy, superseded
`federal_monthly_financial_statements` bulk acquisition
(`3.-cashflow-statement.xlsx`). This milestone does not re-acquire or load
it (only `federal_mfs_aggregates` has a tested extractor and is this
milestone's load target); documented here as a known gap for a future
milestone, not silently ignored.

"Fiscal Balance / Cash Balance tables" (the mission's required distinct
category) are not a separate file at all - they are rows *within* the
Aggregates workbook itself (`Fiscal balance`, `Underlying cash balance`,
`Headline cash balance` - see below).

## The Aggregates workbook's real row structure, verified across all 26 sheets

One sheet per financial year, sheet name = short FY (`2000-01` .. `2025-26`).
Row 0 = title. Row 1 = column headers (one per reporting month, `June`
never present - see below). Row 2+ = one row per named aggregate. Final
row = footnote-text paragraph (starts with `(a)`, not a data row).

**Every single row label across all 26 years, unedited:**

| FY | row labels (source order, as published) |
|---|---|
| 2000-01 | Revenue(a), Expenses(a), Operating Result, Assets, Liabilities, Net Assets(a), Fiscal Balance, Underlying Cash Balance, Headline Cash Balance |
| 2001-02..2004-05 | Underlying Cash Balance, Fiscal Balance, Headline Cash Balance, Revenue(a), Expenses(a), Operating Result, Assets, Liabilities, Net Assets(a) |
| 2005-06 | Underlying Cash Balance, Fiscal Balance, Headline Cash Balance, **Income**, Expenses, Operating Result, Assets, Liabilities *(no Net Assets row this year at all - genuine gap, not zero)* |
| 2006-07 | Underlying Cash Balance (b), Fiscal Balance (b)(c), Headline Cash Balance (b), Income (a), Expenses (a), Operating Result (a)(c), Assets, Liabilities, Net Assets (a) |
| 2007-08..2009-10 | Revenue, Expenses, **Net operating balance**, **Net capital investment** *(new)*, Fiscal balance, Underlying cash balance, Headline cash balance, **Total assets**, **Total liabilities**, **Net worth** |
| 2010-11..2012-13 | Revenue, Expenses, Net operating balance, Net capital investment, Fiscal balance, [Underlying Cash Receipts/Payments in 2011-12/12-13 only], Underlying cash balance(x), Headline cash balance, Total assets, Total liabilities, Net worth(x), **Net debt(x)** *(new from 2010-11)* |
| 2013-14 | ..., Receipts(a), Payments(b), Net Future Fund earnings, Underlying cash balance(c), ... |
| 2014-15..2019-20 | ..., Receipts(x), **less Payments(x)**, **less Net Future Fund earnings**, Underlying cash balance(x), ... |
| 2020-21..2025-26 | ..., Receipts(x), Payments(x) *("less" dropped again)*, Underlying cash balance, Headline cash balance, ... *(Net Future Fund earnings line **gone entirely** from 2020-21 onward)* |

`(x)` = a footnote letter that **changes almost every year** (renumbered
based on how many footnotes exist that year) - it carries no independent
meaning and must be stripped before label matching, exactly as
`mfs_aggregates.py`'s existing `TRAILING_FOOTNOTE_MARK` regex already
does. Row **order** also changes (2021-22 onward puts the cash-balance
block before Revenue/Expenses) - matching must be by stripped label, never
by row position.

**Confirmed genuine synonym pairs (same concept, different wording, not silent
normalization - each documented individually in Task 3's semantic YAML):**

| pre-2007 wording | 2007-08+ wording |
|---|---|
| Revenue(a) / Income | Revenue |
| Expenses(a) | Expenses |
| Operating Result | Net operating balance |
| Assets | Total assets |
| Liabilities | Total liabilities |
| Net Assets(a) | Net worth |
| Underlying Cash Receipts (2011-12/12-13 only) | Receipts |
| Underlying Cash Payments (2011-12/12-13 only) | Payments |
| less Payments (2014-15..2019-20) | Payments (2013-14, 2020-21+) |
| less Net Future Fund earnings (2014-15..2019-20) | Net Future Fund earnings (2013-14) |

**Rows that do not exist for every year (absent ≠ zero):**

- `Net capital investment`, `Total assets/liabilities/Net worth` renamed
  vocabulary: introduced 2007-08.
- `Net debt`: **absent for every year before 2010-11** (the concept was
  not published in this table until then).
- `Net Future Fund earnings` / `less Net Future Fund earnings`: only
  disclosed 2013-14 through 2019-20; absent before and after.
- `Receipts`/`Payments` breakdown of the cash balance: absent before
  2011-12 (only the net `Underlying Cash Balance` bottom-line was shown).
- `Net Assets`: missing for FY2005-06 specifically (one-year gap, not a
  naming change - the surrounding years both have it).

## Units: a real millions→billions transition, mid-corpus

Column-header unit token confirmed by direct inspection:

| FY range | unit |
|---|---|
| 2000-01 .. 2023-24 | `$m` (millions) |
| **2024-25, 2025-26** | **`$b` (billions)** |

`mfs_aggregates.py`'s existing `UNIT_SCALE = {"$m": 1_000_000, "$b":
1_000_000_000, "$": 1}` already handles both correctly, applied
per-column (not per-file) - verified this is necessary, since the
transition happens mid-corpus, not at a file boundary.

## Structural fact: no sheet ever reaches a full 12-month year

Every single sheet (all 26 years, old and new) has exactly **11** monthly
columns: July through May. **June/EOY is never present in the Aggregates
workbook** - the full financial year's actual result is published
separately (Final Budget Outcome / annual GFS), not as part of the
Monthly Financial Statements series. This means an MFS Aggregates YTD
fact can **never** legitimately be treated as "the full year" even at its
maximum extent (YTD May = 11/12 of the year) - a structural, permanent
reason (not just a labelling one) reinforcing the mission's constraint
against comparing YTD to annual figures.

## Bare-month ambiguity, confirmed real (not hypothetical)

Column header wording for July itself is **inconsistent across years**:

- 2000-01: bare `July` (no `YTD` prefix - and July has no prior month to
  accumulate, so YTD July == July, unambiguous in this specific case).
- 2001-02 onward: explicitly `YTD July`.

`mfs_aggregates.py`'s existing heuristic (`is_ytd = bool(m.group("ytd"))
or m.group("month") == "July"`) already treats bare `July` as YTD by
construction, which is safe for *this specific* column (July always
equals its own YTD by definition). This does not generalize to other
bare months - none were found for August-May in any sheet inspected.

## `federal_mfs_monthly_profiles`: mixed actual/forecast columns in one sheet

Distinct from Aggregates despite the similar filename
(`1.-aggregates-mp.xlsx`). Sample (FY2009-10): columns for July/August/
September are headed `ACTUAL*`, but October onward are headed `MYEFO
Profile` (a **Budget-estimate profile from the Mid-Year Economic and
Fiscal Outlook**, not an actual). A single sheet mixes `estimate_status`
values by column. Out of scope for this milestone's load (no extractor),
but flagged so a future extension does not assume uniform estimate_status
per sheet.

## Balance Sheet: explicit "as at" stock semantics (out of scope for this load)

`federal_mfs_balance_sheet`'s column headers read `ACTUAL\nas at\n31 July
2015\n$m` - **"as at \<date\>"**, not "YTD \<month\>" - a clean,
source-native signal distinguishing point-in-time stocks from
cumulative-period flows. The Aggregates workbook's own `Total
assets`/`Total liabilities`/`Net worth`/`Net debt` rows do **not** carry
this "as at" wording in their shared column headers (same `YTD <month>`
header as the flow rows) - for those rows, "as at" must be inferred from
the row label itself (a known stock concept), with the reporting month's
final calendar day as the effective balance date. This distinction is
carried into Task 3's semantic model explicitly per measure type
(`flow_or_stock`), not inferred from column headers alone.

## Extractor scope confirmed

Only `federal_mfs_aggregates` has a tested extractor
(`scripts/ingest/extractors/mfs_aggregates.py`) and is this milestone's
load target, matching the mission's own framing ("Federal Monthly
Financial Statements **Aggregates**", "a tested extractor already
exists"). The other five acquired shapes (Operating Statement, Balance
Sheet, the two Notes workbooks, Monthly Profiles) are inventoried above
for completeness and to confirm no missing/undiscovered file shape, but
building extractors for them is new ingestion work beyond this milestone's
bounded scope (loading the Aggregates data). Documented here, not
silently dropped.

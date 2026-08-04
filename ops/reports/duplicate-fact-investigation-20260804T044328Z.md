# Duplicate-fact investigation (Task 3)

Full per-fact evidence: `ops/reports/duplicate-fact-investigation-20260804T044328Z.csv`.
Every group was checked against its raw source file directly (not assumed
from the database alone) - the CSV/XLSX rows the pipeline actually read.

**Headline finding: only 1 of the 5 flagged groups is a true duplicate.**
The other 4 are query false positives - genuinely different real-world
records that a shared, under-specified node and/or a wrong-column amount
extraction made *look* identical to the SQL group-by check. Two distinct,
more significant upstream defects were found in the course of this
investigation (missing per-entity node granularity; a column-order-
dependent amount-column selection bug) - both are documented below and
in the final report as out-of-scope discoveries, since fully fixing them
would mean redesigning two extractors' column semantics and node-identity
schemes, well beyond "resolve 5 duplicate facts."

## Group 1 — VIC local government (`vic_local_govt_financial`)

**facts 3030, 3070** - node 1044 "Total expenses / Employee benefits",
FY2016-17, $84,180,000 both.

- fact 3030: `sheet:Financial Data | cell:E6588`
- fact 3070: `sheet:Financial Data | cell:E6938`

Two **different cells in the same spreadsheet** - i.e. two different
Victorian councils' own "Employee benefits" expense rows. Node 1044 has
**425 facts attached to it in total** (one per council per year) with
**zero per-council dimension at all** - the extractor's `category` column
never included the council name, so every council's figure for a given
line item shares one node. These two happen to report the identical
dollar figure for FY2016-17 (plausible for councils of similar size, nfp
otherwise unrelated). Deleting either would discard one council's real,
distinct, correctly-cited expense record.

**Classification: query false positive.**
**Decision: retain both. No deletion.**
**Separate defect found (out of scope for this milestone): missing
per-council node dimension across the entire `vic_local_govt_financial`
dataset (425 facts sharing 1 node just for this one line item) - would
require re-extracting from the raw XLSX with council name preserved, a
substantially larger undertaking than this milestone's bounded scope.**

## Group 2 — QLD QGIP, Goondiwindi Regional Council "Black Spot" (`qld_qgip_expenditure`)

**facts 81987, 217525** - node "GOONDIWINDI REGIONAL COUNCIL / Black Spot"
(with/without trailing space - two distinct nodes), FY2024-25 (mislabeled,
see below), $42,750 both.

- fact 81987: `18-19-expenditure-data-consolidated.csv`, row 24023
- fact 217525: `consolidated-expenditure-data-17-18.csv`, row 33737

Both raw rows checked directly: **identical ABN (79969846487), identical
legal entity, identical funding agency (DTMR), identical program ("Black
Spot" / "Black Spot "), identical purpose, identical "Total funding under
this agreement to date" ($42,750) and identical "Financial year
expenditure" ($42,750)**. This is the same real government funding
record, re-published in two overlapping "consolidated" yearly export
files (QLD's exports are cumulative, not incremental), differing only by
a trailing space on "Program title" in one file.

**Classification: true duplicate.**
**Decision: delete one, retain the other** (Task 4's cleanup script; see
that section for the precedence applied).
**Root cause: no whitespace normalization on `category`/`agency` before
building `node_name`/`fact_key` in `scripts/ingest/m7_qld_procurement.py`'s
`export_qgip()` - fixed at the root in Task 4.**

## Group 3 — QLD QGIP, "various individuals / nan" (`qld_qgip_expenditure`)

**facts 108117, 108168** - node "various individuals / nan" (with/without
leading space), FY2012-13, $0 both.

- fact 108117: `2012-13-consolidated-qgip-expenditure.csv`, row 1284 -
  **"Grant Program - RentConnect Tenancy Assistance"**, funding source
  Commonwealth, real relevant figure ("Previous financial year" column)
  **$108,476**.
- fact 108168: same file, row 1393 - **"Lending product - Bond Loans"**,
  funding source State, real relevant figure **$23,018,000**.

These are **two completely different, unrelated funding programs**
("Program title" is blank/NaN for both, which is why they collapsed to
the same generic node text). Both also show **$0** in the database
because the amount-column auto-selection picked "Total funding under this
agreement" (genuinely 0 for both, an unrelated field) instead of the real
relevant "Previous financial year" figures ($108,476 and $23,018,000
respectively) - a column-selection defect, not a duplicate-creation one.

**Classification: query false positive (two different real programs;
also exposes a separate amount-column-selection defect).**
**Decision: retain both. No deletion under any circumstance** - deleting
either would permanently discard a distinct, real, unrelated funding
program's only record.

## Group 4 — QLD QGIP, "QLD Murray Darling Committee Inc" (`qld_qgip_expenditure`)

**facts 132896, 132897** - node "... Investment Progam" (with/without
trailing space), FY2014-15, $2,350,000 both.

- fact 132896: `2014-15-consolidated-qgip-expenditure.csv`, row 20336 -
  real "Financial year expenditure" **$426,667**.
- fact 132897: same file, row 20344 - real "Financial year expenditure"
  **$355,333**.

Same funding agreement (same ABN, same funding title, same agreement
dates), but **two genuinely different rows with different real annual
expenditure figures** for what appears to be different years within a
multi-year grant. Both show **$2,350,000** in the database because this
file's column order put "Total funding under this agreement" (a static,
repeated, whole-of-agreement total) ahead of "Financial year expenditure"
in the auto-detection search - the same column-selection defect as Group
3, manifesting differently (a nonzero but wrong, agreement-level total
instead of $0).

**Classification: query false positive (different real annual
expenditures; the amount-column-selection defect, not a duplicate).**
**Decision: retain both. No deletion** - deleting either would discard a
distinct, real annual expenditure figure for this multi-year grant.

## Group 5 — QLD QGIP, "Palm Island Aboriginal Shire Council" (`qld_qgip_expenditure`)

**facts 236933, 237159** - node "... Behaviour Change Study Program"
(with/without trailing space), FY2024-25, $42,764 both.

- fact 236933: `21-22-expenditure-data-consolidated.csv`, row 9722 -
  sub-program "Vandalism-proof metal litter bins", "Total funding under
  this agreement to date" $117,764.
- fact 237159: same file, row 10197 - sub-program "Palm Island vandalism
  proof bins", "Total funding under this agreement to date" $129,540.

This file's column order puts "Financial year expenditure" ahead of
"Total funding..." (the correct column is picked here), and both rows
genuinely show $42,764 in that column. However, the two rows have
**different sub-program titles, different purposes, and different
whole-of-agreement totals** - the extractor's `category` only uses
"Program title" (identical for both, modulo whitespace), silently
dropping "Sub-program title", so two distinct sub-activities collapse to
one node. Whether this is the same disbursement double-counted under two
sub-program labels by the QLD government's own reporting, or two
genuinely separate activities that coincidentally share a rounded
expenditure figure, cannot be determined from the data alone.

**Classification: query false positive (missing sub-program dimension;
insufficient evidence to prove true duplication).**
**Decision: retain both. No deletion** - the ambiguity itself is a reason
not to delete (per "do not delete a fact merely because the current
duplicate query groups it with another fact").

## Summary

| group | classification | decision | fact(s) removed |
|---|---|---|---:|
| VIC Employee benefits | query false positive | retain both | 0 |
| QLD Goondiwindi Black Spot | **true duplicate** | delete one | 1 |
| QLD various individuals | query false positive | retain both | 0 |
| QLD Murray Darling | query false positive | retain both | 0 |
| QLD Palm Island | query false positive | retain both | 0 |

**Only 1 fact is deleted across all 5 groups.** See Task 4 for the
precedence-based choice of which of the Goondiwindi pair is retained, the
extractor fix, and the idempotent cleanup script.

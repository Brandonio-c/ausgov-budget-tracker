# MFS duplicate-fact investigation (Task 7)

Generated: 2026-08-05T00:38:18Z. Found by
`scripts/ops/task9_sql_integrity_checks.py` immediately after the first
real MFS load pass.

## Two candidate groups, both under `mfs_ytd_net_capital_investment`

`duplicate_facts()` groups by `(node_id, financial_year, measure_type,
estimate_status, amount_aud)` - it does not include `reporting_month` in
its grouping key. Every MFS fact for one measure_type shares a single
node (Task 5's "one node per measure_type, many time-series facts"
design), so two **genuinely different months** that happen to report the
identical cumulative YTD figure are indistinguishable from a true
duplicate to this general-purpose check - the same class of query false
positive the prior milestone found for `vic_local_govt_financial` (Task
3), here for a structural reason specific to this node design rather
than a missing dimension.

### Group 1: FY2013-14, $1,315,000,000

Fact IDs 354260 (February) and 354261 (March). Verified directly against
the raw workbook (`6.-aggregates.xlsx`, sheet `2013-14`, row `Net capital
investment`): column YTD February = `1315`, column YTD March = `1315` -
**identical in the source itself**. The full row's YTD sequence (`-160,
-397, -86, 150, 619, 839, 1090, 1315, 1315, 2061, 2673`) shows no net
capital-investment activity between the two months (the cumulative total
simply did not move) - an entirely ordinary outcome for a lumpy,
infrequent flow like capital investment, not a parsing or duplication
defect.

### Group 2: FY2022-23, $4,400,000,000

Fact IDs 355665 (February) and 355667 (April). Verified directly against
the raw workbook, sheet `2022-23`: YTD February = `4.4`, YTD March =
`4.2` (a genuine **decrease** that month), YTD April = `4.4` (a genuine
increase back to the same cumulative total). The two months in the
candidate group (February and April) are separated by a real change in
between (March) that happens to net out to zero across the two-month
span - confirmed by inspecting every month in the row, not just the two
flagged ones.

## Classification: query false positive, both groups

Both are genuine, distinct, correctly-cited facts (different
`fact_key`, different `period_end`, different source cell locator) that
coincidentally report the same cumulative YTD amount. Deleting either
fact in either group would discard a real, distinct, correctly-cited
monthly data point. Recorded in
`config/audit/reviewed_duplicate_facts.yaml` (matching the established
pattern from the prior milestone) so they are reported as informational
`reviewed_duplicate_facts`, not hard failures, while any genuinely new or
unreviewed MFS duplicate-look-alike group still is.

## Result after registering both

`task9_sql_integrity_checks.py`: `hard_failures: 0` (was 2).
`reviewed_duplicate_config.entry_count`: 6 (was 4).

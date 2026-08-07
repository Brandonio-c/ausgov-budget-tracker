# Queensland MYFER semantic decision

Generated: 2026-08-07T16:50:25Z

## Decision

Publish only five General Government Sector measures from the six-edition
compact-table cluster: revenue, expenses, net operating balance, purchases of
non-financial assets, and fiscal balance. The selected value is the
current-edition MYFER/revised-estimate column, represented as
`estimate_status=revised_estimate` with `source_budget_year` equal to the
publication's financial-year vintage.

Revenue, expenses, and purchases of non-financial assets are financial-year
flows. Net operating balance and fiscal balance are non-additive
financial-year balances. Native `$ million` values are multiplied by exactly
1,000,000 and stored as AUD. Parentheses mean negative; no sign is inferred
from prose.

## Compatibility

MYFER remains separate from RSF. MYFER is an in-year revised forecast, while
the loaded RSF series contains estimated-actual and audited actual values from
final reports. Each `qld_myfer_*` measure therefore has its own compatibility
group. Side-by-side display is acceptable only with visible period, vintage,
and estimate-status disclosure; additive merging is forbidden.

## Revision and quarantine policy

Semantic identity includes source, publication vintage, target financial year,
measure, basis, estimate status, and jurisdiction. Equal reloads are no-ops.
A different amount for an existing identity is quarantined as a revision
conflict, never selected by processing order.

Malformed six-column rows, missing expected rows, ambiguous sector/period
attribution, missing PDF locators, and revision conflicts are quarantine-only.
Borrowing, Net debt, NFPS, lease, and securities rows are explicit scope
exclusions because their concepts or availability drift across the cluster;
they are not silently published under a common label.

Older detailed UPF editions and the OCR-dependent 2002-03 edition remain
deferred. Cloudflare is unrelated and remains external.

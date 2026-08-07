# QLD on-time payment inventory and disposition (20260807T175100Z)

## Selection and inventory

This is canonical queue position 6, following the deferred Consolidated Fund
cash-report family. The acquisition manifest for
`qld_on_time_payment_reports` contains **42 CSV assets with 42 distinct
SHA-256 hashes**, covering agency reports from 2020-21 through 2025-26.

The files represent 42 agency/report snapshots, including DPC, Agriculture,
Education, Health, Police, Corrective Services, Fire, Transport, Resources,
Housing/Public Works, regional-development, training/employment, justice, and
successive machinery-of-government departments. The exact resource URL and
cached file path for every asset remain in `latest.json`.

All 42 files were header-inspected. The dominant shape has eight or nine
columns:

1. quarter;
2. eligible penalty-interest claims;
3. penalty interest paid;
4. eligible and undisputed invoice count;
5. late eligible/undisputed invoice count;
6. value of those late invoices;
7. mean days paid late;
8. late-payment percentage for small business; and
9. late-payment percentage for others.

There is bounded but real drift: UTF-8 BOMs, whitespace/capitalisation
variants, `invs` versus `invoices`, a file omitting the total-invoice column,
and at least one multi-line quoted header. The registry correctly describes
the family as quarterly agency-level aggregate compliance reporting, not
contract- or invoice-line data.

## Semantic assessment

The safe semantic types would be counts, percentages, mean days, penalty
interest paid, and value of late invoices. These are procurement/payment-policy
performance indicators. They are not government expenditure, fiscal
aggregates, appropriations, or a breakdown of an authoritative total. They
would require a new contextual compliance view and machinery-of-government
agency identity policy; publishing them into the existing fiscal graph would
be semantically false.

## Disposition

**Deferred to a contextual procurement/compliance milestone.** This is the
same explicit scope conclusion reached by the focused QLD/TAS ranking and the
consolidated backlog report. The CSVs are acquired and structurally tractable;
the blocker is product/semantic fit, not access or parser feasibility.

No extractor, semantic YAML, database, source document, node, edge, API, or UI
was changed. No database write means backup/load/idempotency steps are not
applicable. Counts remain 289,315 facts, 133 source documents, 222,575 nodes,
and 0 edges. Task 9 and dashboard results remain the clean
`20260807T174624Z` no-data-change baseline; frontend and production checks are
not applicable.

This queue item is explicitly addressed and deferred, not marked ingested.

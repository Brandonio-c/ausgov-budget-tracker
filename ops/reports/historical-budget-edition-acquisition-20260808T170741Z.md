# Historical Statement 6/PBS edition acquisition

Generated: 2026-08-08T17:07:41Z
Plan item: 5.1

## Outcome

The repository now has distinct registered and acquired source identities for the March 2022-23, October 2022-23 and 2023-24 Budget editions. Each edition has one official Budget Paper No. 1 source containing Statement 6 and one directly archived Treasury Portfolio Budget Statement representative. March and October 2022-23 remain separate publication vintages even though their financial-year labels overlap.

The six downloads completed through `scripts/procure_sources.py` with status `downloaded`. Their `latest.json` acquisition manifests retain requested/final URLs, retrieval time, detected type, byte count and SHA-256 checksum.

## Acquired edition manifest

| Source identity | Edition / vintage | Official original resource URL | Bytes | Pages | SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| `federal_budget_statement_6_2022_23_march` | 2022-23 March Budget / `2022-03` | `https://archive.budget.gov.au/2022-23/bp1/download/bp1_2022-23.pdf` | 6,275,025 | 365 | `057ac399236ae5e90d0c955534b679fb41fa99ee20a5f3f718dd9267872f20c1` |
| `federal_budget_statement_6_2022_23_october` | 2022-23 October Budget / `2022-10` | `https://archive.budget.gov.au/2022-23-october/bp1/download/bp1_2022-23.pdf` | 7,201,525 | 400 | `0df9a3630447181b263936ff5732c564564ccc76377a98208dbe8d04d96c779d` |
| `federal_budget_statement_6_2023_24` | 2023-24 Budget / `2023-05` | `https://archive.budget.gov.au/2023-24/bp1/download/bp1_2023-24.pdf` | 8,098,996 | 438 | `4c78c15cf174d82236cd3295d7555f6aa31f42f2a96a43dcd8984bed57379cdc` |
| `federal_pbs_2022_23_march_treasury` | 2022-23 March Budget / `2022-03` | `https://treasury.gov.au/sites/default/files/2022-03/tsy_pbs_2022-23.pdf` | 6,615,878 | 375 | `f5504b3c9759b0cead128090b37ff4a4a40a86ef6d8d5bfbf67b294c6359fdaf` |
| `federal_pbs_2022_23_october_treasury` | 2022-23 October Budget / `2022-10` | `https://treasury.gov.au/sites/default/files/2022-10/tsy_pbs_october-2022-23.pdf` | 6,570,396 | 410 | `d9f464a670f6fbb0f40c3eb4e7d962acdf3de8eff1e76ad270c293dcb63a07ed` |
| `federal_pbs_2023_24_treasury` | 2023-24 Budget / `2023-05` | `https://treasury.gov.au/sites/default/files/2023-07/tsy_pbs_2023-24_230727.pdf` | 6,659,953 | 421 | `1dacad4cf55379533c096b4d821c219ded5fb659f3e3bf2f146083bb1764831d` |

All six checksum values are distinct. `pdfinfo` recognized all six files as PDFs and returned the page counts above.

## FBO coverage

No duplicate FBO acquisition was created. The corresponding audited Final Budget Outcome editions are already represented by `federal_budget_archive_function_series`, whose 2022-23 and 2023-24 PDFs have exact-edition retrieval identities and were deployed in plan item 4.2. An October 2022-23 Budget is a Budget publication vintage, not a separate Final Budget Outcome vintage.

## Scope boundary and exclusions

The official archive landing pages provide a stable direct Treasury PBS PDF for each target edition. They list the other portfolios by name and state that those documents were held on agency websites at release, but do not supply durable direct URLs for the broader set. This milestone therefore acquires a bounded Treasury representative for each vintage. It does **not** claim complete all-portfolio PBS coverage. Additional portfolio documents require official URL resolution and must be added under their own edition-bearing source identities.

These sources are acquired but not yet ingested. Edition-specific Statement 6 layout fixtures/adapters are plan item 5.2; historical PBS fixtures/adapters are item 5.3. No facts, graph edges, dashboard totals or API responses changed in this acquisition milestone.

## Validation

- Procurement registry schema/load: passed with 373 unique sources.
- Acquisition run `20260808T170741Z`: 6 downloaded, 0 failed.
- Manifest completeness: all six assets have original requested URLs, stored paths, byte counts and SHA-256 checksums.
- PDF validation: six readable PDFs, 2,409 pages total.
- Edition registry regressions: March/October source identity, publication edition/vintage and original URL are executable invariants.

## Next item

Plan item 5.2: build bounded Statement 6 adapters for these three layouts, starting with table/page discovery and edition fixtures before extracting function, subfunction and published component rows.

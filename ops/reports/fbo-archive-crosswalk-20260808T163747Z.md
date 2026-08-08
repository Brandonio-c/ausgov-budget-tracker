# Historical FBO archive crosswalk preflight

Generated: `2026-08-08T16:38:21+00:00`

This is a no-write audit of the already-published 2019-20 through 2023-24 Final Budget Outcome Appendix A facts. Cross-source differences are evidence only: FBO budget functions and ABS GFS COFOG-A purposes are not additively interchangeable.

## Result

- Facts audited: **415** across **5** exact fact years.
- Semantic failures: **0**; every fact is `actual_accrual_expense / accrual / audited_actual`.
- Crosswalk comparisons with evidence on both sides: **50**; missing evidence: **0**.
- Source classification label additions/removals after 2019-20: **12**.
- Facts with all six exact-year citation signals: **0 / 415**.

## Source-native inventory

| year | facts | function parents | subfunction facts | total facts | semantic failures | label changes |
|---|---:|---:|---:|---:|---:|---:|
| 2019-20 | 83 | 11 | 71 | 12 | 0 | 0 |
| 2020-21 | 83 | 11 | 71 | 12 | 0 | 6 |
| 2021-22 | 83 | 11 | 71 | 12 | 0 | 4 |
| 2022-23 | 83 | 11 | 71 | 12 | 0 | 0 |
| 2023-24 | 83 | 11 | 71 | 12 | 0 | 2 |

The eleven function-parent labels are stable across all five editions. Three subfunction labels vary only by dash, apostrophe, or capitalization; those exact source-label changes are listed below.

### 2019-20 functions

`Agriculture, forestry and fishing`, `Education`, `General public services`, `Health`, `Housing and community amenities`, `Other economic affairs`, `Other purposes`, `Public order and safety`, `Recreation and culture`, `Social security and welfare`, `Transport and communication`

### 2020-21 functions

`Agriculture, forestry and fishing`, `Education`, `General public services`, `Health`, `Housing and community amenities`, `Other economic affairs`, `Other purposes`, `Public order and safety`, `Recreation and culture`, `Social security and welfare`, `Transport and communication`

### 2021-22 functions

`Agriculture, forestry and fishing`, `Education`, `General public services`, `Health`, `Housing and community amenities`, `Other economic affairs`, `Other purposes`, `Public order and safety`, `Recreation and culture`, `Social security and welfare`, `Transport and communication`

### 2022-23 functions

`Agriculture, forestry and fishing`, `Education`, `General public services`, `Health`, `Housing and community amenities`, `Other economic affairs`, `Other purposes`, `Public order and safety`, `Recreation and culture`, `Social security and welfare`, `Transport and communication`

### 2023-24 functions

`Agriculture, forestry and fishing`, `Education`, `General public services`, `Health`, `Housing and community amenities`, `Other economic affairs`, `Other purposes`, `Public order and safety`, `Recreation and culture`, `Social security and welfare`, `Transport and communication`

## COFOG crosswalk evidence

The repository's existing `cofog_to_budget_function` mapping is reversed here only to locate comparable labels. Approximate mappings and classification aggregation remain explicit.

| year | FBO budget function | FBO | ABS mapped purpose(s) | ABS | FBO − ABS | quality |
|---|---|---:|---|---:|---:|---|
| 2019-20 | Defence | $33.187b | Defence | $39.442b | $-6.255b | exact |
| 2019-20 | Education | $39.885b | Education | $43.948b | $-4.063b | exact |
| 2019-20 | General public services | $29.472b | General public services | $104.704b | $-75.232b | exact |
| 2019-20 | Health | $87.023b | Health | $90.216b | $-3.193b | exact |
| 2019-20 | Housing and community amenities | $10.664b | Housing and community amenities; Environmental protection | $9.051b | $1.613b | approx; exact |
| 2019-20 | Other economic affairs | $65.494b | Economic affairs | $71.493b | $-5.999b | approx |
| 2019-20 | Public order and safety | $6.388b | Public order and safety | $6.741b | $-0.353b | exact |
| 2019-20 | Recreation and culture | $3.971b | Recreation, culture and religion | $3.752b | $0.219b | approx |
| 2019-20 | Social security and welfare | $196.119b | Social protection | $199.969b | $-3.850b | approx |
| 2019-20 | Transport and communication | $7.321b | Transport | $7.522b | $-0.201b | approx |
| 2020-21 | Defence | $34.007b | Defence | $40.659b | $-6.652b | exact |
| 2020-21 | Education | $42.331b | Education | $47.877b | $-5.546b | exact |
| 2020-21 | General public services | $31.942b | General public services | $115.740b | $-83.798b | exact |
| 2020-21 | Health | $92.740b | Health | $97.075b | $-4.335b | exact |
| 2020-21 | Housing and community amenities | $12.582b | Housing and community amenities; Environmental protection | $9.924b | $2.658b | approx; exact |
| 2020-21 | Other economic affairs | $82.067b | Economic affairs | $100.279b | $-18.212b | approx |
| 2020-21 | Public order and safety | $6.655b | Public order and safety | $6.894b | $-0.239b | exact |
| 2020-21 | Recreation and culture | $4.096b | Recreation, culture and religion | $4.056b | $0.040b | approx |
| 2020-21 | Social security and welfare | $220.360b | Social protection | $226.126b | $-5.766b | approx |
| 2020-21 | Transport and communication | $12.804b | Transport | $12.070b | $0.734b | approx |
| 2021-22 | Defence | $38.246b | Defence | $44.447b | $-6.201b | exact |
| 2021-22 | Education | $43.225b | Education | $50.285b | $-7.060b | exact |
| 2021-22 | General public services | $31.273b | General public services | $123.119b | $-91.846b | exact |
| 2021-22 | Health | $106.185b | Health | $109.818b | $-3.633b | exact |
| 2021-22 | Housing and community amenities | $14.066b | Housing and community amenities; Environmental protection | $10.240b | $3.826b | approx; exact |
| 2021-22 | Other economic affairs | $21.781b | Economic affairs | $31.567b | $-9.786b | approx |
| 2021-22 | Public order and safety | $6.658b | Public order and safety | $7.186b | $-0.528b | exact |
| 2021-22 | Recreation and culture | $4.270b | Recreation, culture and religion | $4.033b | $0.237b | approx |
| 2021-22 | Social security and welfare | $221.427b | Social protection | $231.621b | $-10.194b | approx |
| 2021-22 | Transport and communication | $11.503b | Transport | $11.140b | $0.363b | approx |
| 2022-23 | Defence | $41.436b | Defence | $45.356b | $-3.920b | exact |
| 2022-23 | Education | $44.932b | Education | $51.510b | $-6.578b | exact |
| 2022-23 | General public services | $30.111b | General public services | $141.572b | $-111.461b | exact |
| 2022-23 | Health | $102.680b | Health | $106.898b | $-4.218b | exact |
| 2022-23 | Housing and community amenities | $16.704b | Housing and community amenities; Environmental protection | $11.647b | $5.057b | approx; exact |
| 2022-23 | Other economic affairs | $14.399b | Economic affairs | $26.463b | $-12.064b | approx |
| 2022-23 | Public order and safety | $7.513b | Public order and safety | $7.889b | $-0.376b | exact |
| 2022-23 | Recreation and culture | $4.641b | Recreation, culture and religion | $4.369b | $0.272b | approx |
| 2022-23 | Social security and welfare | $222.911b | Social protection | $231.968b | $-9.057b | approx |
| 2022-23 | Transport and communication | $12.166b | Transport | $12.031b | $0.135b | approx |
| 2023-24 | Defence | $45.103b | Defence | $48.398b | $-3.295b | exact |
| 2023-24 | Education | $48.011b | Education | $53.362b | $-5.351b | exact |
| 2023-24 | General public services | $31.563b | General public services | $149.946b | $-118.383b | exact |
| 2023-24 | Health | $106.589b | Health | $108.856b | $-2.267b | exact |
| 2023-24 | Housing and community amenities | $13.965b | Housing and community amenities; Environmental protection | $11.173b | $2.792b | approx; exact |
| 2023-24 | Other economic affairs | $13.490b | Economic affairs | $30.469b | $-16.979b | approx |
| 2023-24 | Public order and safety | $7.739b | Public order and safety | $8.018b | $-0.279b | exact |
| 2023-24 | Recreation and culture | $5.088b | Recreation, culture and religion | $4.585b | $0.503b | approx |
| 2023-24 | Social security and welfare | $253.184b | Social protection | $259.127b | $-5.943b | approx |
| 2023-24 | Transport and communication | $14.041b | Transport | $13.343b | $0.698b | approx |

### Unmapped and excluded classifications

The existing crosswalk does not independently map the FBO classifications `Agriculture, forestry and fishing`, `labour and employment affairs`, or `Other purposes`. They must remain explicit exceptions in the graph pack; silently folding them into `Economic affairs` or another ABS purpose would introduce an unreviewed classification rule. `Total expenses` is an aggregate and is excluded from function mapping.

## Citation and exact-year audit

| year | locator | landing URL | resource URL | locator cached path | retrieval URL | retrieval local path | all six |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2019-20 | 83 | 83 | 83 | 0 | 83 | 0 | 0 |
| 2020-21 | 83 | 83 | 83 | 0 | 0 | 0 | 0 |
| 2021-22 | 83 | 83 | 83 | 0 | 0 | 0 | 0 |
| 2022-23 | 83 | 83 | 83 | 0 | 0 | 0 | 0 |
| 2023-24 | 83 | 83 | 83 | 83 | 0 | 83 | 0 |

All 415 fact locators, landing URLs, and original official resource URLs identify the correct fact year. The ingestion provenance is nevertheless not exact-year safe: all facts share one retrieval row whose resolved URL is 2019-20 and whose local path is the 2023-24 PDF; the locator JSON cached path also points to the 2023-24 PDF for every year. Therefore item 4.2 must repair per-edition retrieval/cached-copy attribution before deploying graph edges.

## Classification changes

- `2020-21`: added ["Education / School education - specific funding", "Health / Assistance to the states for public hospitals", "Other purposes / Government's behalf"]; removed ["Education / School education — specific funding", "Health / Assistance to the States for public hospitals", "Other purposes / Government’s behalf"].
- `2021-22`: added ["Education / School education – specific funding", "Other purposes / Government’s behalf"]; removed ["Education / School education - specific funding", "Other purposes / Government's behalf"].
- `2023-24`: added ["Other purposes / Government's behalf"]; removed ["Other purposes / Government’s behalf"].

These are typographic/capitalization changes, not substantive classification additions or removals. Exact-label graph construction must still avoid treating them as new semantic categories.

## Preflight disposition

**Conditional pass.** Measures, basis, status, year labels, source-native classification, official locator URLs, and crosswalk coverage are sufficient to design an exact-only augmenting pack. Deployment is blocked until the shared retrieval/cached-copy provenance is repaired and re-audited. Cross-source amount differences must remain related evidence and must never reconcile into ABS totals.

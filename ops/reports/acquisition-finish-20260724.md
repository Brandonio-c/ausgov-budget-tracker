# Acquisition finish — 2026-07-24

## Verdict

Manual **need** queue is empty. Almost all P0/P1 automated downloads that can be fetched from official public sources are on disk. Remaining open items are either confirmed **no public bulk**, or P2 `related_view` / GrantConnect-style adapters still running or flaky.

## Final queue snapshot

Regenerate with:

```bash
python scripts/procure_acquisition_queue.py --all-sources --json \
  --write data/.procurement/reports/remaining-full-queue.json
```

Final regen: **`done=347`**, **`no_bulk=9`**, **`need/flaky/candidate=0`**, **`automated=9`** (all P2 related-view / GrantConnect adapters; primary packs largely already held under other IDs). Related-view batch stalled after DSS income-support + jobseeker and was stopped.

## Closed this session (highlights)

### Prior “need” leftovers
- `nt_local_grants_commission_reports` — Infrastructure FAG NT 2025–26 PDF
- `sa_lggc_publications_database_reports` — 2023–24 Database Reports PDF
- `cofog_a_classification` — ABS HTML classification page
- `commonwealth_balance_sheet_user_guide` — Finance HTML guide
- `abn_bulk_extract_resource_index` — data.gov.au CKAN `package_show` JSON (5 resources)
- `federal_pbs_2025_26_industry_science_and_resources` — industry.gov.au Budget 2025–26 PBS PDF
- PBO 2024–25 and 2025–26 PBS (pbo.gov.au; 2026–27 already had)

### Automated / blocked_auth recoveries
- Full ABS GFS 2024–25 workbook set (state + local + aggregates)
- ACT 2026–27 statements A–H + summary + budget tables (XLSX via browser)
- NSW / QLD / TAS / WA / SA / NT 2026–27 budget papers (NT BP2 + TAFR via browser)
- Federal MFS profiles + aggregates / balance sheet / operating / tax notes
- VIC 2026–27 Service Delivery, Statement of Finances, Department Performance Statement (S3 `+` URLs via browser)
- VIC local ABS2–3 balance finance XLSX
- CFS 2024–25 notes filled from the published full CFS PDF (notes are not a separate file)
- Alias imports: social-services / health / NDIA / DVA 2026–27 PBS duplicate IDs; SA FBO CFR; SA/NT grants alternate IDs

## Explicit no-bulk (registry)

Added to `NO_BULK` in `scripts/procure_acquisition_queue.py`:

| source_id | reason |
|---|---|
| `federal_transparency_pbs_set_16` | No TP bulk PBS zip; individual PBS already acquired |
| `qld_sds_machine_readable_2025_26` | No published machine-readable SDS pack for 2025–26 |
| `vic_local_govt_financial` | VAGO portal / no single bulk export |

Plus prior: Austender weekly, WA/SA tenders portals, MyCouncil, SA Councils in Focus, NT LGC return.

## Still open / lower priority

- P2 `*_related_view` adapters (DSS, AusTender OCDS, GrantConnect, NDIS, Services Australia) — discovery/fetch in progress; primary datasets often already held under non-`related_view` IDs
- `grantconnect_awards_by_agency` — same class

## Reports

- `data/.procurement/reports/20260724T190530Z.json` — ABS GFS / ACT / MFS batch
- `data/.procurement/reports/20260724T190604Z.json` — large P1 automated batch (65 downloaded)
- `data/.procurement/reports/remaining-full-queue.json` — live queue

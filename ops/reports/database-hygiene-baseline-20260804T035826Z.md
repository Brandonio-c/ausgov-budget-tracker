# Database hygiene milestone — baseline

Generated: 2026-08-04T03:58:26Z. git HEAD: `76af563` (clean working tree,
matches `origin/main`). Backup: `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260804T035734Z.db`
(SHA-256 recorded in the accompanying `.backup-report.json`).

## Baseline counts

| metric | count |
|---|---:|
| facts | 285,574 |
| nodes | 222,798 |
| fact_nodes | 285,574 |
| node_edges | 0 |
| breakdown_edges | 14,183 |
| source_documents | 127 |
| facts_pending_attribution | 36,391 |

## `task9_sql_integrity_checks.py` output

`hard_failures: 283` (exit code 1). Matches the prior milestone's known
carry-over exactly:

| check | count |
|---|---:|
| duplicate_facts | 5 |
| duplicate_breakdown_edges | 0 |
| orphan_facts | 0 |
| orphan_nodes | 278 |
| orphan_edges | 0 |
| dangling_source_documents | 0 |
| cross_government_additive_edges | 0 |
| cross_jurisdiction_additive_edges | 0 |
| pbs_crosswalk_children_with_rejected_labels | 0 |
| pbs_children_missing_source_year | 0 |

## Duplicate-fact groups (5)

| node_id | financial_year | measure_type | estimate_status | amount_aud | fact_ids |
|---|---|---|---|---:|---|
| 1044 | 2016-17 | actual_accrual_expense | audited_actual | 84,180,000 | 3030, 3070 |
| 67316 | 2024-25 | actual_accrual_expense | actual | 42,750 | 81987, 217525 |
| 93316 | 2012-13 | actual_accrual_expense | actual | 0 | 108117, 108168 |
| 116100 | 2014-15 | actual_accrual_expense | actual | 2,350,000 | 132896, 132897 |
| 196635 | 2024-25 | actual_accrual_expense | actual | 42,764 | 236933, 237159 |

Full investigation with source_key/provenance/citation detail per fact is
Task 3's deliverable (`ops/reports/duplicate-fact-investigation-*.csv/.md`).

## Orphan nodes by source_key (278 total)

| source_key | count |
|---|---:|
| nsw_tcorp_bonds_on_issue | 64 |
| qld_qtc_aud_bond_outstandings | 47 |
| nsw_tcorp_weekly_bonds | 36 |
| vic_tcv_amount_on_issue | 32 |
| wa_watc_funding_sources | 23 |
| qld_qtc_weekly_outstandings_2026_07_17 | 19 |
| sa_safa_weekly_funding_update | 18 |
| nt_nttc_borrowing_strategy | 17 |
| qld_qtc_benchmark_bonds | 14 |
| tas_tascorp_annual_report_2024_25 | 8 |

All 10 source_keys are state/territory central-borrowing-authority debt
datasets (NSW TCorp, QLD QTC, VIC TCV, WA WATC, SA SAFA, NT NTTC, TAS
TASCORP) — none are PBS-related. Full inventory with node type/creation
pattern/name-pattern classification is Task 5's deliverable.

## This report is read-only evidence

No writes were made to `data/facts.db` in the course of producing this
baseline. All fixes in this milestone will be measured against these
exact numbers.

# M12 — Autonomous cutover

## DoD

- Script checks: top-10 published; Gate 6 100% on exposed facts; M3 reconciliations balanced or explained; regression green
- Switch default route to new store; keep `/legacy`
- Checklist with measured values

## Criteria script

`scripts/ingest/cutover_criteria.py` → **pass=True**

### Measured values

| Metric | Value |
|---|---|
| Exposed facts | 257,706 |
| Incomplete exposed citations | 0 |
| Pending attribution (quarantine) | 15 |
| Reconciliations | {'balanced': 30} |
| Top-10 all published | True |

Top-10 counts:

```json
{
  "federal_expense_by_function": 381,
  "sa_gfs_by_function": 1893,
  "vic_local_govt_financial": 1700,
  "abs_gfs_commonwealth_130": 230,
  "act_notifiable_invoices": 46714,
  "nt_awarded_government_contracts": 1494,
  "nsw_local_olg_time_series": 2794,
  "tas_local_cdc": 2600,
  "federal_monthly_financial_statements": 288,
  "nsw_procurement_ocds_registry": 7853
}
```

## Cutover actions

1. Default route `app/page.tsx` now reads **facts.db via API v2** (`data-default-store="facts"`).
2. Phase 1 pie/drill-down preserved at **`/legacy`**.
3. Explorers remain at `/explorers/contracts` and `/explorers/gfs`.
4. Regression updated and green (`default_view_regression_ok`).

## Notes

Live `spending.db` was never written during M0–M11; it remains available for `/legacy` and Phase 1 rebuilds via the unified registry.

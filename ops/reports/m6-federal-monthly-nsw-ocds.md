# M6 — Federal monthly + NSW OCDS

## DoD

- `monthly_actuals` measure; OCDS flatten to `contract_value` + supplier/contract nodes
- Spot-check 3–5 NSW contracts vs public eTendering

## Verification

| Source | Published | Quarantined | Notes |
|---|---:|---:|---|
| federal_monthly_financial_statements | 288 | 14 | July expense lines across FYs; measure=`monthly_actuals` |
| nsw_procurement_ocds_registry | 7,853 | 0 | 2024 jsonl.gz awards with value |

Spot-check targets: `ops/reports/m6-nsw-ocds-spotchecks.json` (eTendering CN search URLs for 5 awards).

## Artefacts

- `scripts/ingest/m6_monthly_ocds.py`
- `data/staging/m6/`

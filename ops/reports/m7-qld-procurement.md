# M7 — QLD QGIP + Contract Disclosure

## DoD

- Sample ≥15 disclosure CSVs; auto decision ≥90% identical schema → one mapping; else exceptions doc
- Agency renames via `entities.valid_from/valid_to`

## Verification

| Check | Result |
|---|---|
| Schema sample | 20 CSVs, 18 unique schemas |
| Dominant share | 0.15 |
| Decision | **split_mappings** (below 90% threshold) |
| Exceptions doc | `ops/reports/m7-schema-exceptions.md` |
| qld_qgip_expenditure | 386,836 published |
| qld_contract_disclosure (40 files) | 13,024 published |
| entities seeded | 86,472 agency rows with valid_from |

## Artefacts

- `scripts/ingest/m7_qld_procurement.py`

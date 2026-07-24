# M4 — ABS GFS + ACT + NT

## DoD

- DuckDB-inspect ABS files; shared template or documented variants
- First `territory` facts; attribution completeness reported

## Verification

| Source family | Published | Quarantine |
|---|---:|---:|
| ABS GFS Table_4 (16 workbooks; shared template) | 1,760 (110×16) | 0 |
| act_notifiable_invoices | 124,173 | 0 |
| nt_awarded_government_contracts | 1,993 | 0 |
| Territory-level facts | 48,768 | — |
| Attribution on published | 100% | — |

Note: Plan cited “×13”; on-disk family has **16** jurisdiction workbooks (commonwealth + 8 state/territory + 7 local), all sharing Contents+Table_1..4. Shared melt in `adapters/abs_gfs.py` + `config/mappings/templates/abs_gfs_table4.yaml`.

## Artefacts

- `scripts/ingest/adapters/abs_gfs.py`
- `scripts/ingest/m4_gfs_act_nt.py`
- mappings under `config/mappings/abs_gfs_*.yaml`, `act_notifiable_invoices.yaml`, `nt_awarded_government_contracts.yaml`

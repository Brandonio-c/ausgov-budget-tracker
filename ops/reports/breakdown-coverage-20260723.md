# Breakdown coverage matrix

Generated `20260723` from `data/facts.db`.

Federal packs: `abs_gfs_table4` → `bp1_s6_a61` → `bp1_s6_components` → `pbs_programs_dss`.
Related edges never roll into parent GFS pie totals.

| ABS purpose | Budget function | Quality | A.6.1 subs | Components | PBS | Related | Deepest |
|---|---|---|---:|---:|---:|---:|---|
| General public services | General public services | exact | 0 | 0 | 0 | 0 | abs_only |
| Defence | Defence | exact | 0 | 0 | 0 | 1 | related_total |
| Public order and safety | Public order and safety | exact | 2 | 0 | 0 | 2 | s6_subfunction |
| Education | Education | exact | 8 | 8 | 0 | 0 | s6_component |
| Health | Health | exact | 7 | 18 | 0 | 0 | s6_component |
| Social protection | Social security and welfare | approx | 8 | 23 | 17 | 8 | pbs_program |
| Housing and community amenities | Housing and community amenities | exact | 3 | 0 | 0 | 3 | s6_subfunction |
| Recreation, culture and religion | Recreation and culture | approx | 4 | 0 | 0 | 4 | s6_subfunction |
| Economic affairs | Other economic affairs | approx | 6 | 0 | 0 | 6 | s6_subfunction |
| Environmental protection | Housing and community amenities | approx | 3 | 0 | 0 | 3 | s6_subfunction |
| Transport | Transport and communication | approx | 6 | 0 | 0 | 6 | s6_subfunction |

## State / territory analogues

- ABS GFS state and territory Table_4 workbooks remain the Actuals same_group source.
- Commonwealth Budget Statement 6 and DSS PBS packs are federal-only.
- Future state analogues: state budget paper function tables + agency PBS equivalents,
  registered as separate packs with their own `compatibility_group` and crosswalks.

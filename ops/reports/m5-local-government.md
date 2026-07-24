# M5 — Local NSW / TAS / VIC

## DoD

- ZIP unpack for TAS CDC; inspect year layout before mapping
- VIC 2014–19 still present vs M3 baseline

## Verification

| Source | Published | Notes |
|---|---:|---|
| nsw_local_olg_time_series | 2,794 | 2024-25 Your Council expense columns |
| tas_local_cdc | 2,600 | Unpacked 2015-2025 zip; FY 2015-16…2024-25 |
| vic_local_vgc_abs_returns | 889 | VGC1 Total Exp 2024-25 |
| VIC M3 baseline 2014-19 | 1,700 before = 1,700 after | preserved |

## Artefacts

- `scripts/ingest/m5_local_government.py`
- `data/staging/m5/` (+ `tas_unpacked/`)

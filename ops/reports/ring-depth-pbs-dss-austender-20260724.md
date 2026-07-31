# Ring depth expand — PBS cascade + DSS demos + AusTender (2026-07-24)

## Goal

Unlock more Federal Actuals drill-down rings using data already on disk:

1. Cleaner / broader PBS → Statement 6 cascade  
2. DSS recipient demographics under Social protection PBS  
3. AusTender contract aggregates under Defence / Health / Transport  

Grant $ / recipient counts / contract values remain **navigational** (do not inflate the GFS $745B pie).

## What shipped

| Pack | Files |
| --- | --- |
| Expanded PBS s6 bridge | `scripts/ingest/extractors/pbs_programs_s6_bridge.py` |
| DSS demographics | `scripts/ingest/extractors/dss_payment_demographics.py`, `config/breakdowns/dss_payment_demographics.yaml` |
| AusTender top-N | `scripts/ingest/extractors/austender_contracts.py`, `config/breakdowns/austender_contracts.yaml` |
| Shared linker | `link_path_children_under_cascade` in `scripts/ingest/breakdown_pack.py` |

### Run

```bash
# stop API container first if facts.db is locked
docker compose -f docker-compose.vibefactory.yml stop

python scripts/ingest/breakdown_pack.py --pack pbs_programs_s6_bridge
python scripts/ingest/breakdown_pack.py --pack dss_payment_demographics
python scripts/ingest/breakdown_pack.py --pack austender_contracts

docker compose -f docker-compose.vibefactory.yml up -d
```

## Results

| Source | Facts | Cascade edges |
| --- | ---: | ---: |
| `federal_pbs_programs_s6_bridge` | 1,273 | ~1,193 new `pbs_dss_bridge` links |
| `federal_dss_payment_demographics` | 52 | 15 `dss_demo_under_pbs` |
| `federal_austender_contracts` | 147 | 3 function-level `austender_under_s6` (+ path kids) |

### Live tree checks (Federal Actuals FY 2024–25)

- **Job Seeker Income Support → Recipients by state / by age → NSW, Victoria, …**  
- **Support for Seniors / Carers / Disability → Recipients by state**  
- **Defence → Contracts (AusTender 2019–20) → UNSPSC → supplier**  

## Caveats

- PBS bridge filters aggressively (program-like labels, FY 2023–26, ≥$100k) — Health/SSW still thin vs curated DSS/Health packs.  
- AusTender dump is **2019–20** (nearest-FY banner under Actuals 2024–25). Refresh when current CN/OCDS is acquired.  
- Recipient counts use `measure_type=recipient_count` (not AUD expense).  
- Stop the vibefactory backend before large pack runs — SQLite lock contention otherwise.

## Next

1. Acquire current AusTender / OCDS for FY 2024–25.  
2. Loosen Health PBS remapper with Table 2.1-only extract.  
3. Optional grants explorer + contracts explorer pages.

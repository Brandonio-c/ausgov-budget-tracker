# GrantConnect under PBS — ring depth MVP (2026-07-24)

## Goal

Add true rings past PBS program (ring 5–6+) for Federal Actuals FY **2024–25** without mixing grant dollars into the ABS GFS Commonwealth pie (**$745B**).

## What shipped

| Piece | Path |
| --- | --- |
| Extractor | `scripts/ingest/extractors/grantconnect_awards.py` |
| Mapping | `config/mappings/federal_grantconnect_awards.yaml` |
| Pack | `config/breakdowns/grantconnect_awards.yaml` |
| Linker | `link_grants_under_pbs` in `scripts/ingest/breakdown_pack.py` |
| Cascade depth | `build_same_group_subtree` / `build_related_subtree` `max_depth` **6 → 8** |

### Matching strategy

1. **Seeded** high-confidence DSS/component parents (Child Care, Aged Care, NDIS, …)
2. **Exact leaf** match against DSS / Health PBS + Statement 6 components
3. **Agency → A.6.1** fallback (Health, Education, Defence, DEWR, DISR, DFAT, …)
4. Aggregate to **Grant Program**; top **10 recipients** (+ Other) when program ≥ $1M

### Run (local)

```bash
python scripts/ingest/breakdown_pack.py --pack grantconnect_awards
# or include in: python scripts/ingest/breakdown_pack.py --all
```

## Results (facts.db after pack)

| Metric | Value |
| --- | ---: |
| Staging / published facts | **2,486** |
| Grant programs matched | **468** |
| `grantconnect_under_pbs` edges | **865** |
| Matched award $ (FY quarters) | **~$18.0B** |
| Unmatched award $ | **~$0.13B** |

### Depth (Federal Actuals FY 2024–25)

| Measure | Before | After |
| --- | ---: | ---: |
| Raw API tree depth under Commonwealth | ~5 | **7** |
| Additive ring Depth (sunburst) | ~4 | **6** |

Example path now reachable:

`Health → Medical services and benefits → Medical benefits → Medical Benefits → Visiting Optometrists Scheme - VOS → <recipient>`

Social protection also reaches grant programs under Aged Care Services (CHSP, Domestic Assistance, …).

## Non-goals / caveats

- Grant $ are **commitment/award**, not GFS Actuals — hung as `same_group` under PBS/S6 with `preserve_amount` on the cascade (parent GFS/S6 amounts stay authoritative; sunburst `scaleToSum` keeps arcs aligned).
- Agency→A.6.1 fallback is coarse (e.g. DEWR → Education function); refine with portfolio crosswalk later.
- Remaining unmatched (~$132M): PMC, DoT, AFP, ATO, ASIC, etc. — add agency maps as needed.
- AusTender / OCDS **not** wired (no stable PBS program key).

## Next steps

1. Tighten DEWR / DISR / DFAT parents to Statement 6 **sub-functions** where published.
2. Optional: grants explorer page (facts already `measure_type=grant_award`).
3. Optional: AusTender under procurement-heavy wedges (agency/UNSPSC join).
4. Redeploy vibefactory backend after `facts.db` update (compose mount); frontend Depth logic already prefers Statement 6 cascades.

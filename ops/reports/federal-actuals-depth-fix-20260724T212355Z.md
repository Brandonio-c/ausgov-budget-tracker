# Federal Actuals depth fix — 2026-07-24

## Scope

Deepen Federal Actuals sunburst rings for FY **2024–25** without mixing Statement 6 / FBO / PBS amounts into the ABS GFS Commonwealth pie (**$745.03B**).

## Before → after (max related depth by purpose)

| Purpose | Before (approx.) | After depth | Navigable related |
| --- | ---: | ---: | --- |
| Social protection | deep (S6 → components → DSS PBS) | 3 | leaf S6 replace + FBO folder |
| Defence | 0–1 (ABS lump) | **3** | S6 `Defence` → components → PBS programs; FBO folder |
| Health | ABS kids + $0 S6 folder | **4** | ABS kids + Statement 6 folder @ **$118.16B** + FBO |
| Education | ABS kids + $0 S6 folder | **4** | ABS kids + Statement 6 folder @ **$55.73B** + FBO |
| Economic affairs | ABS lump | **2** | S6 subfunctions (leaf replace) + FBO; PBS under `Other economic affairs nec` |
| Transport | ABS lump | **2** | S6 subfunctions + FBO; PBS under Road/Air/… |
| Public order and safety | ABS kids | **2** | S6 / FBO; PBS under `Other public order and safety` |

Commonwealth total unchanged: **$745.03B**.

## What changed

1. **Defence PBS extract** — start on Budget Expenses / Cost Summary markers; keep Cost Summary tables; join label + numeric-only lines; prefer program totals.
2. **`pbs_programs_s6_bridge` pack** — remaps Defence / Education / Infrastructure / Home Affairs / Industry onto Statement 6 function paths; cascade via `link_pbs_to_components`.
3. **`link_a61_to_components`** — also links exact-name component lumps (e.g. `Defence`) so PBS under components is reachable from A.6.1 related children.
4. **FBO Appendix A** — function headers no longer nest under the previous function; stale `General public services / Defence` FBO node removed; related pack + dual folders.
5. **Ring UX** — Statement 6 / FBO folders use parent purpose amount + `preserve_amount`; folders excluded from GFS additive rollup (purpose nodes with `related_breakdown` still count).

## Smoke

In-process `TestClient` `/v2/dashboard/tree?mode=actuals&level=federal&year=2024-25`:

- Commonwealth **$745.03B**
- Defence program-like PBS rows present under related cascade
- Health / Education Statement 6 folder values equal parent GFS amounts

## Tests

- `tests/ingest/test_federal_actuals_depth.py` — Defence heuristics + FBO nesting
- `tests/api/test_breakdown_related.py` — thin-purpose depth, S6/FBO folder amounts, rollup exclusion

## Non-goals (unchanged)

- Mass OCR cleanup of noisy PBS narrative rows
- Replacing GFS as Actuals basis
- Summing S6 / FBO / PBS into the $745B pie

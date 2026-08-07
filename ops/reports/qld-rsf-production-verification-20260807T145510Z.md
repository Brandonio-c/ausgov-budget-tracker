# Production verification (Task 10)

Generated: 2026-08-07T14:55:10Z.

## 1. Backend rebuilt and restarted

`docker compose -f docker-compose.vibefactory.yml up --build -d` -
required since this milestone changed backend code (new router
`src/backend/routers/v2/qld_rsf.py`, registered in `__init__.py`);
`data/facts.db`/`config/` are bind-mounted read-only and were already
live without a rebuild.

Healthy: `GET /api/health` -> `200 {"status":"ok"}`. `GET /v2/qld-rsf/
measures` -> `200`, 8 measures. `GET /v2/tas-ggs/measures` -> `200`,
10 measures - unaffected, confirming the existing router was never
touched.

## 2. Frontend deployed

`npm run deploy:vibefactory` - includes the new "QLD RSF" toggle
(Task 7). Deploy succeeded; 48 files uploaded. Confirmed the new code
is genuinely in the deployed bundle: fetched the exact chunk
(`0wzd1o_inieg4.js`) from the live URL (`cf-cache-status: MISS`, a
fresh fetch not a stale cache hit) and diffed it byte-for-byte against
the local build output - **identical**, and the local file itself
contains the `"qld-rsf"` string.

## 3. Public API - fully verified

| check | result |
|---|---|
| `https://ausgov-budget-api.vibefactory.app/v2/qld-rsf/measures` | 200, 8 measures |
| `.../v2/qld-rsf/series?measure_type=qld_rsf_fiscal_balance` | 200, 2018-19 actual = -2,191,000,000 AUD, correct citation (`file:2018-19-Report-on-State-Finances.pdf \| page:10 \| table:Key UPF Financial Aggregates \| row:Fiscal balance`) |
| `.../v2/dashboard/tree?mode=actuals&level=federal&year=2024-25` | 745,030,000,000 - unchanged |
| `.../v2/dashboard/tree?mode=actuals&level=state&year=2024-25` | 553,464,488,764.25 - unchanged |
| `.../v2/vic-afs/measures` | 200, 11 measures - unaffected |
| `.../v2/vic-bpo/measures` | 200, 11 measures - unaffected |
| `.../v2/vic-bpo-soce-admin/measures` | 200, 9 measures - unaffected |
| `.../v2/mfs/measures` | 200, 15 measures - unaffected |
| `.../v2/tas-ggs/measures` | 200, 10 measures - unaffected |

## 4. Production semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against the container's own port:
**`total_hard_failures: 0`, `total_accepted_source_rounding_warnings:
0`** across all 6 required paths and 7 PBS crosswalk cases.

## 5. UI verification method and the Cloudflare finding

A fresh real-browser (Playwright) check directly against the live
production site (`page.goto("https://vibefactory.app/ausgov-budget-
tracker/explorers/gfs/?view=qld_rsf")`) returned a 404 page. This is
**not a regression from this milestone** - re-confirmed by testing the
exact same hard-navigation request against the GFS explorer's own root
path (`/explorers/gfs/`, unrelated to this milestone's changes): plain
`fetch`-style request returns 200, but a `Sec-Fetch-Mode: navigate`
request returns 404 - identical to the pre-existing, already-
documented Cloudflare issue from the two prior milestones. `page.goto()`
always triggers a hard navigation, so this affects any direct
production Playwright check regardless of which page is targeted.

Per Task 2's decision, this remains out of scope for repo changes this
milestone. The actual feature UI was instead verified through:

- Direct verification of the live public API (section 3 above) -
  proves the real, deployed backend serves correct data for the new
  family, including full citations.
- Byte-for-byte confirmation that the exact compiled UI code is
  present in the deployed frontend bundle (section 2 above).
- The already-completed Task 7 real-browser Playwright check (a real
  `next build` static export + a real backend + the real, now-loaded
  `data/facts.db` - byte-for-byte the same code now deployed) which
  fully exercised the QLD RSF toggle, measure selection, both vintages
  rendering, and citation display end-to-end and passed.

## 6. Existing dashboard paths confirmed unchanged

Federal actuals FY2024-25, state actuals FY2024-25, and every sibling
family's measure count all confirmed unchanged against both the
container directly and the public API.

## Conclusion

Backend and frontend deployed successfully; the new QLD Report on
State Finances family is fully verified working end-to-end in
production via its dedicated API and via the already-completed local
real-browser check against byte-identical code. Existing dashboard
behavior is unchanged across every family. The Cloudflare nested-route
issue remains open, external, and unchanged since the prior
milestones' findings - confirmed not specific to this milestone's new
route.

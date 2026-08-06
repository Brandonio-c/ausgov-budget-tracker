# Production verification (Task 10)

Generated: 2026-08-06T17:41:53Z.

## 1. Backend rebuilt and restarted

`docker compose -f docker-compose.vibefactory.yml up --build -d` -
required since this milestone changed backend code (new router
`src/backend/routers/v2/tas_ggs.py`, registered in `__init__.py`);
`data/facts.db`/`config/` are bind-mounted read-only and were already
live without a rebuild.

Healthy: `GET /api/health` -> `200 {"status":"ok"}`. `GET /v2/tas-ggs/
measures` -> `200`, 10 measures. `GET /v2/vic-bpo/measures` -> `200`,
11 measures - unaffected, confirming the existing router was never
touched.

## 2. Frontend deployed

`npm run deploy:vibefactory` - includes the "TAS GGS" toggle (Task 7).
Deploy succeeded; 48 files uploaded. Confirmed the new code is
genuinely in the deployed bundle: `_next/static/chunks/06ejt2c5xypvo.js`
matches the local build byte-for-byte on the `"tas-ggs"` string search
(1 match in both).

## 3. Public API - fully verified

| check | result |
|---|---|
| `https://ausgov-budget-api.vibefactory.app/v2/tas-ggs/measures` | 200, 10 measures |
| `.../v2/tas-ggs/series?measure_type=tas_ggs_net_debt` | 200, 2016-17 actual = -791,000,000 AUD, correct citation (`cell:H7`, `column:Net Debt at 30 June`) |
| `.../v2/dashboard/tree?mode=actuals&level=federal&year=2024-25` | 745,030,000,000 - unchanged |
| `.../v2/dashboard/tree?mode=actuals&level=state&year=2024-25` | 553,464,488,764.25 - unchanged |
| `.../v2/vic-afs/measures` | 200, 11 measures - unaffected |
| `.../v2/vic-bpo/measures` | 200, 11 measures - unaffected |
| `.../v2/vic-bpo-soce-admin/measures` | 200, 9 measures - unaffected |
| `.../v2/mfs/measures` | 200, 15 measures - unaffected |

## 4. Production semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against the container's own port
immediately after rebuild: **`total_hard_failures: 0`,
`total_accepted_source_rounding_warnings: 0`** across all 6 required
paths and 7 PBS crosswalk cases.

## 5. Existing dashboard paths confirmed unchanged

Federal actuals FY2024-25 (745,030,000,000), VIC state actuals
FY2024-25 (553,464,488,764.25), VIC AFS (11 measures), VIC BPO (11
measures), VIC BPO SOCE/Admin (9 measures), and MFS (15 measures) all
confirmed unchanged against both the container directly and the public
API.

## 6. Cloudflare route issue: unchanged, still out of scope per Task 2's decision

Task 2 explicitly decided this pre-existing, unrelated issue is out of
scope for this milestone (the selected family is exposed via the
already-working GFS explorer, reached via in-app client-side
navigation - no new route). No repo-side changes were made to it.

For the record only (not a re-investigation - Task 2's decision
stands): re-checked the same finding from the prior VIC SOCE/Admin
milestone (root path 404s under hard navigation with `Sec-Fetch-Mode:
navigate`, 200 under a plain fetch-style request) - **unchanged**
since that report, consistent with it being a stable (if unfortunate)
state of the same external Cloudflare-side issue rather than something
actively worsening further. Remains tracked as the same open external
infrastructure follow-up; no further investigation was performed here.

## Conclusion

Backend and frontend deployed successfully; the new TAS GGS family is
fully verified working end-to-end in production via its dedicated API
and via the GFS explorer's in-app navigation (verified locally in Task
7's real-browser check against byte-identical code). Existing dashboard
behavior is unchanged across every family. The Cloudflare nested-route
issue remains open, correctly deferred per Task 2's explicit decision
rather than re-investigated, and its status is unchanged since the
prior milestone's finding.

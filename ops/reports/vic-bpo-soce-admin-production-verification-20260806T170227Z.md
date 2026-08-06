# Production verification (Task 8)

Generated: 2026-08-06T17:02:27Z.

## 1. Backend rebuilt and restarted

`docker compose -f docker-compose.vibefactory.yml up --build -d` -
required since this milestone changed backend code (new router
`src/backend/routers/v2/vic_bpo_soce_admin.py`, registered in
`__init__.py`); `data/facts.db`/`config/` are bind-mounted read-only and
were already live without a rebuild.

Healthy: `GET /api/health` -> `200 {"status":"ok"}`. `GET /v2/vic-bpo-
soce-admin/measures` -> `200`, 9 measures. `GET /v2/vic-bpo/measures`
-> `200`, 11 measures - unaffected, confirming the existing router was
never modified.

## 2. Frontend deployed

`npm run deploy:vibefactory` - includes the merged VIC BPO dropdown
(Task 5). Deploy succeeded; 48 files uploaded. Confirmed the new
router's URL string is genuinely present in the deployed JS bundle
(`grep` found `"vic-bpo-soce-admin"` compiled into
`_next/static/chunks/1ymanc33uhk4s.js`).

## 3. Public API - fully verified

| check | result |
|---|---|
| `https://ausgov-budget-api.vibefactory.app/v2/vic-bpo-soce-admin/measures` | 200, 9 measures |
| `.../v2/vic-bpo-soce-admin/series?measure_type=vic_bpo_admin_income` | 200, correct amounts (82,428,000,000 actual), correct citation (`sheet:Admin`) |
| `.../v2/dashboard/tree?mode=actuals&level=federal&year=2024-25` | 745,030,000,000 - unchanged |
| `.../v2/dashboard/tree?mode=actuals&level=state&year=2024-25` | 553,464,488,764.25 - unchanged |
| `.../v2/vic-afs/measures` | 200, 11 measures - unaffected |

## 4. Production semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against the container's own port
immediately after rebuild: **`total_hard_failures: 0`,
`total_accepted_source_rounding_warnings: 0`** across all 6 required
paths and 7 PBS crosswalk cases.

## 5. UI verification method and the Cloudflare finding

A fresh real-browser (Playwright) check against the live production
site was attempted (`page.goto("https://vibefactory.app/ausgov-budget-
tracker/")` then in-app navigation to the GFS explorer). It failed -
**the root path itself now also returns 404 under hard navigation**
(`Sec-Fetch-Mode: navigate`), re-confirmed stable after a 15s wait
(not a transient post-deploy cache state). This is a **worsening** of
the pre-existing, already-triaged Cloudflare issue: prior milestones'
reports explicitly found the root path unaffected and only nested
routes affected (with the nested-route symptom itself having already
shifted once before, from homepage-fallback to 404-fallback). Plain
`fetch`-style requests (no `Sec-Fetch-Mode: navigate` header) to the
same root path still return 200 - the symptom's trigger condition is
unchanged, only its blast radius has grown to include the entry point.

Per Task 2's decision, this remains out of scope for repo changes this
milestone (no code in this repository controls Cloudflare's edge
routing behavior; two repo-side mitigations are already deployed and
exhausted). However, since a fresh production Playwright check could
not complete for this reason (not because of anything this milestone
changed), the actual feature UI was instead verified through:

- Direct verification of the live public API (section 3 above) -
  proves the real, deployed backend serves correct data for the new
  family.
- Confirmation that the exact compiled UI code is present in the
  deployed frontend bundle.
- The already-completed Task 7 real-browser Playwright check (a real
  `next build` static export + a real backend + the real, now-loaded
  `data/facts.db` - byte-for-byte the same code that is now deployed)
  which fully exercised the merged dropdown, series rendering, and
  citation display end-to-end and passed.

**Recommendation for the user**: given the root path is now affected
(not just nested routes), this infrastructure issue likely warrants
priority attention outside this repo (Cloudflare dashboard-level
investigation - Page Rules/Cache Rules/Bot settings keyed on
`Sec-Fetch-Mode: navigate`, or a support ticket) sooner than "deferred,
low urgency" - it may now affect every fresh visit to the site, not
only deep links.

## 6. Existing dashboard paths confirmed unchanged

Federal actuals FY2024-25 (745,030,000,000), VIC state actuals
FY2024-25 (553,464,488,764.25), and the VIC AFS API (11 measures,
unaffected) all confirmed against both the container directly and the
public API.

## Conclusion

Backend and frontend deployed successfully; the new VIC SOCE/Admin
family is fully verified working end-to-end in production via its
dedicated API and via the already-completed local real-browser check
against byte-identical code. Existing dashboard behavior is unchanged.
The Cloudflare nested-route issue remains open and out of scope per
Task 2's decision, but a new finding (root-path impact) is recorded
here for the record and flagged as likely warranting more urgent
attention than previously assessed.

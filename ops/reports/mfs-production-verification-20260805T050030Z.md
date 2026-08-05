# Production verification (Task 12)

Generated: 2026-08-05T05:00:30Z.

## 1. Backend rebuilt and restarted

`docker compose -f docker-compose.vibefactory.yml up --build -d`
(`data/facts.db` and `config/` are bind-mounted read-only, but the
Python application code - including the new `mfs.py` router - is baked
into the image at build time, so a rebuild was required for the MFS API
to become live).

**The first rebuild attempt surfaced a real, production-only bug**:
`GET /v2/mfs/measures` returned `500 Internal Server Error`. Container
logs: `FileNotFoundError: /config/measure-semantics/mfs.yaml` (missing
`/app` prefix entirely). Root cause: `mfs.py` computed
`REPO_ROOT = Path(__file__).resolve().parents[4]`, correct for the repo
checkout (`.../ausgov-budget-tracker/src/backend/routers/v2/mfs.py`) but
wrong for the container, where the Dockerfile's `COPY . /app/backend`
(build context `./src/backend`) makes the same file's on-disk depth
**one level shallower** (`/app/backend/routers/v2/mfs.py`) - a single
fixed `parents[N]` cannot resolve correctly in both places. This exact
problem was already solved once in this codebase
(`compatibility.py`'s `_default_view_families_path()`, a multi-candidate
resolver trying a hardcoded `/app/config/...` path plus the correct
local-checkout depth) - `mfs.py` just hadn't followed that pattern yet.
Fixed identically: `_default_semantics_path()`, verified by direct
empirical check of `.parents[N]` for both the real local path and a
simulated container path (not assumed), then two new regression tests
(`tests/api/test_mfs_api.py::test_semantics_path_resolves_in_repo_checkout`,
`test_semantics_path_candidates_cover_both_layouts` - the second
literally recreates the container's directory depth in a `tmp_path` and
asserts the same candidate resolves it).

Rebuilt again with the fix: container healthy
(`GET /api/health` → `200 {"status":"ok"}`), `GET /v2/mfs/measures` →
`200`, 15 measures.

## 2. Frontend deployed

`npm run deploy:vibefactory` (`next build` with
`NEXT_PUBLIC_API_BASE=https://ausgov-budget-api.vibefactory.app`, then
`wrangler deploy --config wrangler.vibefactory.toml`). Succeeded:
`explorers/mfs/index.html` and its supporting chunks uploaded; Cloudflare
reports the deploy live at `vibefactory.app/ausgov-budget-tracker`.

## 3. Public MFS API - fully verified

Against `https://ausgov-budget-api.vibefactory.app`:

| check | result |
|---|---|
| `/v2/mfs/measures` | 15 measures, correct labels |
| `/v2/mfs/series?measure_type=mfs_ytd_revenue&financial_year=2024-25` | 11 facts |
| `/v2/mfs/compare?measure_types=mfs_stock_net_debt,mfs_ytd_revenue` | `422`, correct stock/flow rejection message |
| `/v2/mfs/years?measure_type=mfs_stock_net_debt` | `2007-08 .. 2025-26` |

## 4. Public MFS UI - API-backed content confirmed; a pre-existing, unrelated routing issue found

The static asset itself is confirmed correct - it is the identical build
that passed 20/20 local Playwright tests (served via a plain static
server, no Cloudflare layer in between) immediately before this deploy.

However, verifying the **live public URL** with a real browser
(Playwright against `https://vibefactory.app/ausgov-budget-tracker/explorers/mfs/`)
found it renders the **site homepage's** content (H1 "AusGov Budget
Tracker", no MFS badges/charts) instead of the MFS explorer page.
Investigated before concluding anything:

- Ruled out CDN cache staleness: retried with a cache-busting query
  string and after a further wait - identical result, and
  `cf-cache-status` behavior was consistent with the origin being asked
  each time, not a stale edge hit clearing on its own.
- **Confirmed this is pre-existing and NOT caused by this milestone**:
  `https://vibefactory.app/ausgov-budget-tracker/explorers/gfs/` and
  `.../timeline/` - both shipped in earlier milestones, both already
  live in production before today - show the **identical** symptom
  (homepage content, not their own). The root page itself
  (`.../ausgov-budget-tracker/`) renders correctly.
- This points to `wrangler.vibefactory.toml`'s
  `not_found_handling = "single-page-application"` - a setting whose
  premise (a true client-side-only SPA with one shell page) does not
  match this app's actual shape (a Next.js static export with multiple
  separately pre-rendered pages, each with its own real `index.html`
  physically present in the upload) - but confirming the exact
  Cloudflare-side mechanism and fixing it is a distinct, pre-existing,
  site-wide deployment-configuration question, not part of this
  milestone's scope. **Not changed** - flagged here for a deliberate,
  separate decision instead of an unreviewed change to shared production
  deployment configuration.

## 5. Production semantic dashboard audit

`scripts/ops/dashboard_api_audit.py --base-url http://127.0.0.1:8010`
(the container's own port, immediately after the rebuild):
**`total_hard_failures: 0`, `total_accepted_source_rounding_warnings: 0`**
across all 6 required paths and 7 PBS crosswalk cases - identical to
every prior clean run this milestone.

## 6. Existing views confirmed unchanged (public API)

| view | value | matches pre-deploy? |
|---|---:|---|
| federal actuals FY2024-25 | 745,030,000,000 | yes |
| state actuals FY2024-25 | 553,464,488,764.25 | yes |
| local actuals | 8,753 rows at `local` level | yes |
| debt | mixed-valuation warning, root total suppressed (unchanged) | yes |
| GDP/ratios | unchanged | yes |
| PBS crosswalk (Defence, `same_group`) | unchanged | yes |

## Conclusion

Backend: fully deployed and verified, including a real bug found and
fixed along the way (container path resolution). Frontend: deployed
successfully; the new page's content is confirmed correct at the asset
level, but a **pre-existing** (not introduced here) Cloudflare routing
issue currently prevents any nested static route - old or new - from
rendering correctly for a real browser hitting the public domain
directly. This is a genuine, separate finding to raise, not a defect in
this milestone's work.

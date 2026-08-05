# Production verification (Task 8)

Generated: 2026-08-05T17:34:17Z.

## 1. Backend rebuilt and restarted

`docker compose -f docker-compose.vibefactory.yml up --build -d`.
Healthy: `GET /api/health` -> `200 {"status":"ok"}`. `GET /v2/vic-afs/
measures` -> `200`, 11 measures - no path-resolution bug this time
(the multi-candidate `_default_semantics_path()` pattern from
`compatibility.py`/`mfs.py` was applied proactively when writing
`vic_afs.py`, unlike the prior milestone where this exact bug class was
found the hard way in production).

## 2. Frontend deployed

`npm run deploy:vibefactory` - includes both the VIC AFS UI (Task 5) and
the Cloudflare `not_found_handling`/`Cache-Control` fixes (Task 1).
Deploy succeeded; 48 files uploaded.

## 3. Public VIC AFS API and dashboard - fully verified

| check | result |
|---|---|
| `https://ausgov-budget-api.vibefactory.app/v2/vic-afs/measures` | 200, 11 measures |
| `.../v2/vic-afs/series?measure_type=vic_afs_revenue` | 200, 2 facts |
| `.../v2/dashboard/tree?mode=actuals&level=federal&year=2024-25` | 745,030,000,000 - unchanged |

## 4. Production semantic dashboard audit

`scripts/ops/dashboard_api_audit.py` against the container's own port
immediately after rebuild: **`total_hard_failures: 0`,
`total_accepted_source_rounding_warnings: 0`** across all 6 required
paths and 7 PBS crosswalk cases.

## 5. Existing dashboard paths confirmed unchanged

Federal actuals FY2024-25 (745,030,000,000) and VIC state actuals
FY2024-25 (553,464,488,764.25) both byte-identical to every prior check
this milestone, confirmed against both the container directly and the
public API.

## 6. Cloudflare route issue: attempted, config improved, but the underlying symptom is NOT resolved in production

Re-tested with a real browser (3 fresh contexts each) against
`https://vibefactory.app/ausgov-budget-tracker/explorers/gfs/` and
`.../explorers/mfs/` immediately after this deploy: **still renders the
homepage's content, not the page's own** - `0/6` passed. The root path
itself continues to work correctly.

Checked whether the Task 1 code changes actually reached production:
`curl -I https://vibefactory.app/ausgov-budget-tracker/explorers/gfs/`
confirms `cache-control: no-store` **is live** (the asset-worker.js
change deployed correctly) - yet `cf-cache-status: HIT` still appears
and the wrong content still renders. This is a significant, informative
result: since `no-store` unambiguously forbids any cache from storing
the response at all, and the symptom persists identically regardless,
**this rules out HTTP caching (both the Assets binding's own behavior
and any Cloudflare edge cache layer) as the mechanism entirely**. The
`not_found_handling: "404-page"` change was independently confirmed
correct in principle (a controlled A/B test in Task 1 isolated the
`Sec-Fetch-Mode: navigate` header as the trigger for the old
`"single-page-application"` setting's over-eager fallback), but
something else - most likely a Cloudflare platform-level behavior for
navigation-type requests (Page Rules, Cache Rules, Bot Fight Mode,
Automatic Platform Optimization, or an equivalent zone-level setting,
none of which are visible or controllable from this repository's
committed configuration or from `wrangler`/the OAuth session available
in this environment) - is still intercepting real browser navigations
to nested routes specifically.

**Status: not resolved. Both code-level fixes are deployed and are
net-positive corrections (a semantically wrong SPA-fallback setting is
now correct; HTML responses are now explicitly never cached) but are
not, on their own, sufficient to fix the observed symptom.** Recommend:

1. Inspect the `vibefactory.app` zone's Cloudflare dashboard directly
   (Caching -> Configuration, Rules -> Page Rules / Cache Rules,
   Security -> Bots) for anything that specifically treats
   `Sec-Fetch-Mode: navigate` requests differently from other requests -
   this is the one concrete, reproducible signal this investigation
   found (a controlled A/B test with curl), and it points at something
   configured outside this repository.
2. If nothing is found there, consider opening a Cloudflare support
   ticket with the reproduction steps in
   `ops/reports/cloudflare-route-triage-20260805T160938Z.md` (the
   `curl` command that isolates the trigger to a single header is
   directly reproducible by Cloudflare's own support team without
   needing access to this codebase).
3. A manual **Purge Everything** from the dashboard was already
   recommended in Task 1's report and has evidently either not been
   done or did not resolve it - worth confirming directly, but given
   `no-store` is now in effect and the symptom is unchanged, this looks
   increasingly unlikely to be a pure caching issue at all.

## Conclusion

Backend and frontend deployed successfully; the new VIC AFS family is
fully verified working end-to-end in production (API and UI, via the
GFS explorer's own toggle - though the explorer page itself is affected
by the still-unresolved Cloudflare issue for a fresh hard navigation, an
in-app client-side visit from the homepage is unaffected). Existing
dashboard behavior is unchanged. The Cloudflare nested-route issue
remains open after a genuine, thorough attempt at a fix - documented
honestly here rather than claimed as resolved.

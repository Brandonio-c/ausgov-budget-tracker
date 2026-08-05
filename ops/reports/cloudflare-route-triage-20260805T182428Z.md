# Cloudflare nested-route issue - scope check for VIC BPO (Task 2)

Generated: 2026-08-05T18:24:28Z.

## Symptom (recap, unchanged since the prior milestone)

Hard navigation (a fresh page load, bookmark, shared link, or new tab)
to any nested static route under `vibefactory.app/ausgov-budget-tracker/*`
renders the homepage's content instead of the intended page. The root
path itself is unaffected, and in-app client-side `<Link>` navigation
starting from an already-loaded page is unaffected (Next.js's client
router handles that without a server round-trip). Full investigation,
root-cause isolation (a controlled A/B test pinpointed the
`Sec-Fetch-Mode: navigate` header as the trigger), and two rounds of
repo-side fixes are documented in
`ops/reports/cloudflare-route-triage-20260805T160938Z.md` and
`ops/reports/adapter-repair-followup-production-verification-20260805T173417Z.md`.
Both fixes (`not_found_handling: "404-page"`, an explicit
`Cache-Control: no-store` for HTML) remain deployed and are confirmed
live in production (`curl -I` shows the header), but the symptom itself
was confirmed to persist in production afterward - ruling out HTTP
caching as the mechanism entirely and pointing at a Cloudflare
platform-level behavior (Page Rules, Cache Rules, Bot settings, or
similar) outside this repository's committed configuration or the
`wrangler` OAuth session available in this environment.

## Affected route(s) for this milestone

`vic_budget_portfolio_outcomes_2024_25` will be exposed as a fourth
toggle option on the **existing** `/explorers/gfs` page (Task 5) -
the same nested route the already-shipped VIC AFS family already uses
successfully. No new route is being introduced.

## Does this block the selected family?

**No.** Reasoning:

1. The symptom only affects **hard navigation** to the page (a fresh
   load/bookmark/shared link). Every real user path this milestone
   actually needs - an in-app visitor clicking through from the
   homepage's `Combined`/`Timeline`/`Corpus`/explorer nav links, or the
   `/explorers` index page's own `<Link>` to `/explorers/gfs` - is
   client-side navigation, which is unaffected.
2. VIC AFS already ships on this exact page today and has been verified
   working end-to-end via in-app navigation (Task 5/8 of the prior
   milestone). Adding a fourth toggle option to an already-integrated
   page does not introduce any new dependency on the broken hard-
   navigation behavior - it inherits the page's existing state exactly
   as AFS already does.
3. The prior milestone already exhausted the fixes available from
   inside this repository (two rounds, both confirmed deployed and
   live) and confirmed the residual cause is outside repo control.
   Re-attempting the same investigation here would not produce a
   different result and would not serve this milestone's actual goal
   (shipping the VIC BPO family).

## Decision

**Defer / external ticket - not a blocker for this milestone.** No
repo-side code changes for the Cloudflare issue are made in this
milestone. It remains tracked as an infrastructure follow-up requiring
Cloudflare dashboard-level investigation (see the prior report's
recommended actions: inspect Page Rules/Cache Rules/Bot settings for
anything keyed on `Sec-Fetch-Mode: navigate`, or open a support ticket
with the reproducible `curl` A/B test as evidence).

## Next

Task 3: build the VIC BPO adapter and expose it via the existing GFS
explorer page, same as VIC AFS.

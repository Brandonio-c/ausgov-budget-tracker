# Cloudflare nested-route issue - scope check for VIC SOCE/Admin (Task 2)

Generated: 2026-08-05T21:22:14Z.

## Symptom (recap, unchanged since the prior two milestones)

Hard navigation (a fresh page load, bookmark, shared link, or new tab)
to any nested static route under `vibefactory.app/ausgov-budget-tracker/*`
can render the wrong content instead of the intended page - the exact
symptom has shifted over time (homepage content, then a 404 page - see
`ops/reports/cloudflare-route-triage-20260805T160938Z.md` and
`ops/reports/vic-bpo-production-verification-20260805T193545Z.md`). The
root path itself is unaffected, and in-app client-side `<Link>`
navigation starting from an already-loaded page is unaffected. Two
rounds of repo-side fixes remain deployed
(`not_found_handling: "404-page"`, an explicit `Cache-Control: no-store`
for HTML) but did not fully resolve the underlying, evidently
Cloudflare-platform-level cause.

## Affected route(s) for this milestone

The deferred VIC SOCE/Admin measures will be exposed as additional
measure options within the **existing** `vic_bpo` toggle on the
`/explorers/gfs` page - the exact same nested route the already-shipped
VIC AFS and VIC BPO families already use successfully. No new route is
being introduced.

## Does this block the selected work?

**No.** Same reasoning as the prior VIC BPO milestone's own Task 2
triage, re-confirmed rather than assumed:

1. The symptom only affects **hard navigation** to the page. Every real
   user path this milestone needs - clicking through from the homepage,
   the `/explorers` index page, or already being on `/explorers/gfs` and
   switching the existing measure dropdown to a new SOCE/Admin option -
   is client-side navigation or a same-page state change, neither of
   which touches the affected code path at all.
2. VIC BPO's existing OS/BS/CFS measures already ship on this exact page
   today and have been verified working end-to-end via in-app
   navigation twice now (Tasks 5/8 of the prior milestone). Adding more
   measure options to an already-integrated dropdown introduces no new
   dependency on the broken hard-navigation behaviour.
3. Two repo-side fixes have already been attempted and exhausted; the
   residual cause is external to this repository (see the linked prior
   reports for the full investigation). Re-investigating it again here
   would not advance this milestone's actual goal (loading the deferred
   SOCE/Admin measures) and would not change the external conclusion.

## Decision

**Out of scope - external follow-up, unchanged.** No repo-side code
changes for the Cloudflare issue are made in this milestone. It remains
tracked as an infrastructure follow-up requiring Cloudflare dashboard-
level investigation (Page Rules/Cache Rules/Bot settings keyed on
`Sec-Fetch-Mode: navigate`, or a support ticket, per the original
triage report's recommended action).

## Next

Task 3: build the VIC SOCE/Admin adapter.

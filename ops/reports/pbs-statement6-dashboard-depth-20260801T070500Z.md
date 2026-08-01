# PBS -> Statement 6 dashboard depth — before/after (Task 7)

## Before

- `federal_pbs_programs_all` facts (53,083, all 63 portfolio documents)
  existed in `facts.db` but were not linked into the Federal dashboard's
  Statement 6 hierarchy at all - `breakdown_edges` had zero rows with
  `crosswalk_id = 'pbs_programs_all_under_s6'` (it didn't exist).
- Drilling into any Statement 6 function/subfunction in the dashboard
  (Budget or Actuals mode) showed only Statement 6's own structure; no path
  reached PBS program-level detail.
- Root total (Budget mode, federal, FY2026-27): **$24,679,913,611,800**.
  Every top-level sibling (Health $208,732,000,000; Social security and
  welfare $335,186,058,000; Defence $72,300,480,400; Education
  $91,756,000,000; etc.) recorded before any edge changes.

## After

- 16,365 `related_breakdown` edges added (`crosswalk_id =
  'pbs_programs_all_under_s6'`), connecting 33 distinct Statement 6
  function/subfunction/component nodes (across all editions:
  `federal_budget_statement_6_2026_27`, `_a61`, `_components`) to 7,746
  distinct PBS program nodes (42,489 of the 53,083 PBS facts, spanning
  every financial year/estimate status those programs carry).
- 9,791 `same_group` edges added under `federal_pbs_programs_all` itself
  (portfolio-folder internal nesting - e.g. "Health Disability and
  Ageing" as a browsable parent of its own ~800 programs), unrelated to
  the Statement 6 boundary crossing but useful PBS-internal navigation.
- **Root total after**: **$24,679,913,611,800** - byte-identical. Every
  top-level sibling value also byte-identical (compared programmatically,
  not just spot-checked) - confirmed via
  `ops/reports/dashboard-api-audit-20260801T070234Z.json` and the direct
  before/after tree comparison recorded during this milestone.
- **7/7 required representative cases verified reachable** through the
  real backend + real static-export frontend (not just direct SQL):
  Social Services, Health, NDIA, Defence, Education, DVA (health-labelled
  programs), DVA (welfare-labelled programs). For each: the related PBS
  node appears, is explicitly labelled non-additive ("Related breakdown
  from a different measure family ... must not be summed into the parent
  pie slice"), the parent Statement 6 node's own amount is preserved
  (not re-summed from the PBS children), and at least one PBS child has a
  complete citation (`has_source_file` or `locator` present).
- Playwright: 7 new browser-driven tests
  (`src/frontend/tests-e2e/pbs-s6-crosswalk.spec.ts`), all passing,
  confirming the SAME reachability through the real browser's own
  CORS-enabled fetch calls (not just a server-side check).

## A real bug found and fixed during this verification

The first implementation attached related_breakdown edges to a shared
"portfolio folder" node per portfolio (to avoid thousands of direct
children under one Statement 6 parent). Verifying against the *real* API
found this was completely invisible: the backend's `fact_for_node_year()`
requires the related_breakdown **child** to carry a fact directly, and a
portfolio-folder node (pure aggregation, no fact of its own) fails that
check silently. Fixed by attaching directly to each individual PBS program
node instead - matching the existing precedent (`pbs_dss_bridge`,
`grantconnect_under_pbs`), which already does this for the same reason.
A second, smaller finding: `/item/{fact_id}/children` treats `same_group`
and `related_breakdown` as mutually exclusive (`same_group` always wins
when present) - since most Statement 6 function/subfunction nodes already
have real internal `same_group` structure, this would have made this
crosswalk's edges permanently unreachable at every non-leaf Statement 6
node. Fixed with a minimal, additive change to
`dashboard_item_children()`: when both exist, the same_group children are
returned as before, with an extra "Related PBS program detail" folder
appended (clearly labelled non-additive, preserving the parent's own
amount) rather than dropping the related content. Both fixes are covered
by new regression tests (`tests/ingest/test_pbs_s6_crosswalk.py`) and the
Playwright/API verification above.

## Known, documented limitation

One Statement 6 leaf, "Social security and welfare / Assistance to people
with disabilities / National Disability Insurance Scheme" under the
`federal_budget_statement_6_components` edition specifically, already has
a pre-existing `same_group` edge (from the older `pbs_under_component`
cascade) pointing at a *different* dataset's node
(`federal_dss_pbs_programs`) that happens to share the exact same name.
This crosswalk's own related_breakdown edge at that specific node is
therefore shadowed by the pre-existing same_group edge in the same way
described above - an artifact of that older cascade, not of this
crosswalk - and does not affect the other 32 attach points (confirmed via
direct query: only this one of 33 distinct target nodes has this
particular same-name collision with a non-Statement-6 dataset). NDIA
content remains fully reachable via the deeper leaf tested above (a
different, real leaf under the same subfunction) and via the Health/Social
Services portfolio-level routes.

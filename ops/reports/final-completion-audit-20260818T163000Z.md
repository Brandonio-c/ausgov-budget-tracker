# Final completion audit - ops/data_remediation_plan.md

Generated: 2026-08-18T163000Z
Repository: `ausgov-budget-tracker`, branch `main`
Authoritative execution ledger: `ops/reports/data-remediation-progress.md`

## Purpose

This report re-reads the plan from start to finish and assigns every plan item one of:
**COMPLETE**, **ALREADY SATISFIED**, **DEFERRED BY EXPLICIT PLAN DECISION**, or
**BLOCKED EXTERNAL**. It is a snapshot audit, not a replacement for the execution ledger
(`data-remediation-progress.md`), which remains the authoritative, evidence-linked record
of exactly what changed and why.

## Disposition by plan section

| Plan section | Disposition | Evidence |
| --- | --- | --- |
| 1.1 Explicit tree projection semantics | COMPLETE | `de70595` |
| 1.2 Declarative edge-set policy | COMPLETE | `be1f25b` |
| 1.3 Annual tree as projection, not hierarchy | COMPLETE | `de70595` |
| 2.1 Golden projection fixtures | COMPLETE | `b6f5c1e` |
| 2.2 Depth/visibility audit contract | COMPLETE | `b6f5c1e` |
| 2.3 Graph integrity checks | COMPLETE | `be1f25b` |
| 3.1 Ring-value truthfulness | COMPLETE | `e106772` |
| 3.2 Federal year availability | COMPLETE | `34a36bc` |
| 3.3 Edge-cascade merge safety | COMPLETE | `be1f25b` |
| 3.4 Flat tree pagination/totals | COMPLETE | `dde1c08` |
| 3.5 Edge uniqueness/idempotency | COMPLETE | `754c669` |
| 3.6 Lineage/registry consistency | COMPLETE | `af0294b` |
| 3.7 Source-aware fiscal-year validation | COMPLETE | `9dd056f` |
| 4.1 Historical FBO preflight (2019-20..2023-24) | COMPLETE | `ed3567f` |
| 4.2 Historical FBO graph pack | COMPLETE | `3d48680` |
| 4.3 Historical federal traversal tests | COMPLETE | `468eed2` |
| 4.4 Ring-depth/branch UX | COMPLETE | `d3446b3` |
| 5.1 Historical edition acquisition | COMPLETE | `3ec6d55` |
| 5.2 Statement 6 adapters | COMPLETE | `4adcbcc` |
| 5.3 Historical PBS adapter family | COMPLETE | `2553851` |
| 5.4 Crosswalk and graph | COMPLETE | `474cdd7` |
| 5.5 Repair current PBS gaps | COMPLETE | `a7aad12`, `1ec8b68` |
| 6.1 Backend explorer API | COMPLETE | `d7717fb`, `26dd135`, `14eede9`, `42a05c9` |
| 6.2 Frontend explorer shell | COMPLETE | `4f76350` |
| 6.3 Family migrations (contracts/PBS/grants/VIC/ACT + QGIP) | COMPLETE | `c115219`, `87ee556` |
| 7.1 MFS sibling workbooks | COMPLETE (3/5 loaded live, 2/5 explicitly deferred with evidence) | `31c8b4d`, `c61b3db`, `7c72ab8`, `ea9c64d` |
| 7.2 QLD QGIP (repair + explorer) | COMPLETE | `26522e2`, `87ee556` |
| 7.3 State borrowing | ALREADY SATISFIED, with one correction | `ecb6546`, `c21288e` - see note below |
| 7.4 QLD Consolidated Fund | COMPLETE (first slice: 17-year annual series, 9 measures) - DEFERRED BY EXPLICIT PLAN DECISION for the remainder (quarterly editions, Operating/Investment split, 3 ambiguous receipt lines, Note 1/2 detail) | `2afbaf6` |
| 7.5 QLD on-time payment | COMPLETE (data + dedicated explorer) | `209d65f`, `e4012fc` |
| 7.6 VIC AFS and non-dollar output KPIs | DEFERRED BY EXPLICIT PLAN DECISION | `de67438` - see note below |
| 8.1 Pre-2019 FBO generation parsers | DEFERRED BY EXPLICIT PLAN DECISION (properly scoped, not yet built) | `cf7ce1e` - see note below |
| 8.2 1985-86 and 1986-87 | BLOCKED EXTERNAL | `e6fa161` - see note below |

## Notes on non-trivial dispositions

**7.3 State borrowing** - "ALREADY SATISFIED" reflects a real finding, not inaction: all 7
named borrowing authorities (VIC, NSW, QLD, SA, WA, NT, TAS) already have live baseline
coverage via a pre-existing, well-designed generic adapter
(`scripts/ingest/adapters/state_debt_instruments.py`) found during this pass. The plan's
"missing/broken sources" framing was stale - 3 previously-flagged "broken" sources are
confirmed intentionally retired duplicates (reloading them would double-count debt), and
the remaining 8 "unadapted" sources are lower-value supplementary documents for
already-covered authorities (one is a forecast-only bulletin unsafe to load as actuals,
one is a mislabeled document, one is a fundamentally different document shape). See
`ops/reports/state-borrowing-scoping-20260814T140019Z.md`.

**7.6 VIC non-dollar output KPIs** - confirmed with direct evidence (not just re-citing an
earlier assessment) that the ~70 KPI rows are each a unique, largely one-off
performance-measure label with a single year of data and no time-series value - a
genuinely poor effort-to-value case, not an access or acquisition problem. See
`data-remediation-progress.md`'s 7.6 row.

**8.1 Pre-2019 FBO parsers** - the existing broad parser is confirmed unsafe (contaminates
the function hierarchy with unrelated tables). A later re-scoping of the "internally
consistent" cluster the original 2026-08-07 triage recommended starting with found it is
not actually internally consistent - at least 4 distinct sub-generations exist within it.
FY2010-11..FY2013-14 (4 years) has a confirmed-stable page anchor and is the genuinely
tractable next slice for a dedicated future pass; the rest need their own investigation.
See `ops/reports/fbo-appendix-a-page-anchor-scoping-20260818T160000Z.md`.

**8.2 1985-86/1986-87** - independently re-verified as genuinely blocked-external using
live web search/fetch tooling a prior session did not have, reaching the same conclusion:
no machine-accessible primary source exists for the function-outlay series in either
year. A modern republished alternative was checked and ruled out (aggregates only, no
function breakdown). See the addendum in
`ops/reports/fbo-historical-archive-triage-20260807T175900Z.md`.

## Definition-of-done checklist (plan section 14)

| Criterion | Status |
| --- | --- |
| Annual dashboard nodes explicitly additive/related/navigation | Met |
| Displayed amounts/units match their facts | Met |
| Every availability entry queryable and basis-labeled | Met |
| No edge set can silently drop path data | Met |
| Historical FBO available for every supported same-year federal actual tree | Met (2019-20..2023-24 population; pre-2019 is item 8.1, tracked separately per the plan's own Wave 5/6 split) |
| 2022-23/2023-24 have a fully verified Statement 6/PBS program route | Met |
| Contracts, PBS, grants, VIC output, ACT invoices, repaired QGIP have specialist surfaces | Met |
| MFS siblings and selected missing borrowing sources have explicit adapters/products | Met (3/5 MFS loaded + 2/5 deferred with evidence; all 7 borrowing authorities already covered) |
| QLD cash/compliance families have independent semantic models | Met (CFFR cash-basis semantics live; on-time-payments compliance semantics live with dedicated explorer) |
| Pre-2019 FBO adapters generation-bounded and contamination-tested | **Not yet met** - properly scoped, not built (item 8.1) |
| Coverage/depth/source-year/quarantine/citation metrics generated in CI | Met (`tests/ops`, `tests/ingest` wired into `.github/workflows/ci.yml`; full-corpus checks excluded from CI via a `full_data` marker for practical runtime, but the tools' own correctness is tested) |
| Deliberate limitations remain visible, not presented as missing implementation | Met - every deferred/blocked item has a dedicated evidence report and an honest ledger row, never silently dropped |

## Overall assessment

Of 12 definition-of-done criteria, 11 are met. The one unmet criterion (pre-2019 FBO
generation-bounded parsers) is properly scoped with a confirmed-tractable first slice
identified, not attempted or fabricated. Every plan item from section 1 through section
8.2 has an evidence-linked disposition; no item is silently unaddressed.

## Recommended next session's starting point

1. Build the FY2010-11..FY2013-14 pre-2019 FBO slice (item 8.1's confirmed-tractable
   4-year cluster).
2. Continue item 7.4 (QLD Consolidated Fund) toward its deferred scope (quarterly
   editions, the 3 ambiguous receipt sub-line-items, Note 1/2 department-level detail).
3. Investigate item 8.1's remaining 3+ sub-generations one at a time.

# Item 6.2 completion: generic frontend explorer shell

Generated: 2026-08-13T16:33:57Z
Repository: `ausgov-budget-tracker`, branch `main`

## Item

Plan section 6.2: "Add a generic explorer page/component" consuming item 6.1's
registry-backed explorer API, with breadcrumbs, a facet panel, search and pagination, a
source/semantic banner, a citation panel, and explicit unit/period labels.

## Gap analysis (before this pass)

- `src/backend/routers/v2/explorers.py` (item 6.1): complete and verified - registry,
  `list`, `availability`, `tree` (cursor pagination, search, honest `path` rejection),
  `facets`, `item`. No changes needed; re-verified by curling a freshly-confirmed
  `uvicorn` process before touching the frontend (see Validation below).
- `src/frontend/components/ExplorerShell.tsx`, `src/frontend/lib/explorerApi.ts`,
  `src/frontend/app/explorers/[family]/page.tsx` (the plan's suggested 6.2 files):
  **none existed** - confirmed via `find` before writing anything.
- The five family pages built earlier this session (`contracts`, `grants`,
  `vic-output-performance`, `act-invoices`, `pbs`) each still hard-code their own
  `compatibility_group`/`accounting_basis`/`estimate_status`/`source_key` and duplicate
  citation/pagination/search UI logic per file - exactly the "six unrelated list pages"
  pattern the plan's 6.1/6.2 preamble warns against. Per this task's explicit boundary
  ("later family migration work can proceed cleanly" after 6.2, "do not jump ahead"),
  these five pages were **not migrated or touched** in this pass - only verified
  unaffected (see Validation).

## Changes

- `src/frontend/lib/explorerApi.ts`: new typed client for every item-6.1 endpoint
  (`list`, `availability`, `facets`, `tree`, `item`). Every type mirrors a backend
  response field-for-field - nothing reconstructed or inferred client-side.
- `src/frontend/components/ExplorerShell.tsx`: the generic shell. Registry-driven
  end to end -
  - bootstraps from `availability` (family label/estimate_statuses/`additive_note`,
    plus which financial_year x estimate_status combinations have real data) and
    `facets` (family-wide source/measure breakdown);
  - year selector is a `<select>` populated only with years that actually have data for
    the chosen status (with counts shown), not a free-text field;
  - estimate-status selector renders only when a family has more than one registered
    status (contracts/grants/act_invoices have one; PBS has four; VIC output performance
    has two) - no fake choice offered where there is none;
  - the `additive_note` from the registry is rendered as the source/semantic banner,
    replacing bespoke per-page disclosure prose with one registry-driven mechanism;
  - `source_breakdown` from the tree response is always shown (even single-entry, for
    consistency), generalizing what was built ad hoc for the contracts page;
  - search is server-side (`q` on `/v2/explorers/{family}/tree`), debounced 300ms client-side;
  - breadcrumb is honestly limited to "Explorers > {family label}" - no deeper
    drill-in/tree UI is rendered, because (re-verified, see below) no registered family
    has real `node_edges` hierarchy; a fabricated tree from label structure would violate
    the standing rule against inferring hierarchy from label similarity;
  - citation panel reuses the existing generic `CitationPanel` component unchanged;
  - explicit error/empty states: unknown family (backend's own detail text shown
    verbatim), a requested year with zero rows (shown honestly, never silently swapped
    for a different year), zero search matches, and fetch/network errors.
- `src/frontend/app/explorers/family/[family]/page.tsx`: the dynamic route. Placed at
  `/explorers/family/{id}` rather than the plan's literal suggested `/explorers/[family]`
  - the five existing pages already occupy those exact static slugs, and Next.js always
    prefers a static route over a same-path dynamic one, so a `[family]` route directly
    under `/explorers` would be permanently unreachable for every currently registered
    family until item 6.3 removes those pages. This path makes the shell fully
    exercisable against every real family today without touching them.
  - This site builds as a static export (`output: "export"`), which requires
    `generateStaticParams()` for any dynamic route. Rather than hard-coding a parallel
    family-id list (the exact anti-pattern item 6.2 exists to avoid), it reads
    `config/explorers/families.yaml` directly (the same file the backend registry loads)
    and regex-extracts each `id:` - one file, so the two cannot drift. No YAML-parsing
    dependency was added; the file's `- id: <value>` shape is simple, stable, and fully
    authored within this repo.
- `src/frontend/app/explorers/page.tsx`: converted to a client component that fetches
  `/v2/explorers` and renders a new "Generic explorer shell (item 6.2, preview)" section
  linking to `/explorers/family/{id}` for every registered family, with no hard-coded
  family list for that section. The original hard-coded links to the five dedicated pages
  were left untouched, with copy explaining they remain the primary, exit-gate-verified
  entry points until item 6.3 migrates them onto this shell.

## A defaulting bug found and fixed during live verification

The first working version picked each family's default year as the *most recent* year
with any data. Live-testing surfaced this as a real UX defect, not merely a style
preference: contracts defaulted to 2026-27 with 21 rows (vs. 9,036 for 2024-25), and PBS
defaulted to 2029-30 with 603 rows and $2.6T (vs. 1,980 rows / $5.9T for 2026-27) - both
technically correct and fully disclosed (visible in the selector, nothing hidden), but
misleadingly sparse-looking as a first view of a substantively deep family. Investigating
PBS's year list also surfaced genuine pre-existing data-quality artifacts already present
in the source data - malformed `financial_year` values `"2025-20"`, `"2025-28"`,
`"2026-29"`, `"2027-30"` (the same class of defect as the `"2022-20"` value already
flagged for contracts in the item 6.1 completion report) - not introduced by this change
and out of scope for 6.2, but now doubly evidenced. Fixed `pickDefaultYear()` to select
the *most-populated* year for the family's default status instead of the most recent one.
This changes nothing about what data is reachable - every year with `count > 0`,
malformed or not, still appears in the selector - it only changes which single year loads
first.

## Validation

- `npx tsc --noEmit`: clean (this also empirically confirmed the dynamic route's
  `params: Promise<{ family: string }>` convention is correct for this Next.js version,
  which the repo's own `AGENTS.md` warns may differ from training-data assumptions -
  verified by letting the build's own generated route types accept or reject the shape,
  not by guessing).
- `npm run lint:ci`: back to the committed baseline (25 errors/13 warnings) after fixing
  two `react-hooks/set-state-in-effect` violations (synchronous `setState` calls at the
  top of an effect body, before the async call) by moving all state updates into the
  `.then()`/`.catch()` callbacks, matching the pattern already established for the
  contracts/grants pages earlier this session.
- `npm run build`: succeeded once `generateStaticParams()` was added (a required fix -
  the first build attempt failed with "missing generateStaticParams() ... output: export"
  for the new dynamic route). Confirmed via the build's route listing that exactly the
  five real registered families (`contracts`, `grants`, `vic_output_performance`,
  `act_invoices`, `pbs`) were statically generated - proving the YAML-derived
  `generateStaticParams()` genuinely tracks the registry file, not a hardcoded guess.
- `npm run test:unit`: passed.
- Live browser verification via Playwright against freshly-confirmed `uvicorn` (new PID
  checked) and `next dev` processes:
  - All five families render correctly through the one shell implementation with their
    real, registry-derived labels, estimate-status options, and now-substantive default
    years; zero console errors on any of them.
  - PBS server-side search ("health") correctly narrowed 1,980 -> 131 rows with a
    populated citation panel on row click.
  - Unknown family (`does-not-exist`) showed the backend's own honest 404 detail text.
  - A deep link to a year with zero data (`?year=1899-00&status=budget`) showed
    "No data for 1899-00" rather than silently substituting a different year.
  - Contracts rendered its full four-jurisdiction `source_breakdown` and its
    `additive_note` banner with zero bespoke code - both now come from the shared shell.
  - The explorers index page's new registry-driven section listed exactly the five real
    families with their real labels.
  - The two already-verified dedicated pages (`/explorers/pbs`, `/explorers/contracts`)
    were re-checked and are byte-for-byte unaffected (same summary text, zero console
    errors) - confirming this pass did not regress item 6.1/prior Wave 4 work, and no
    backend files were touched in this pass (`git status` confirms frontend-only diff).

## Data impact

None. No backend or database change in this pass.

## Frontend impact

A new, generic, registry-driven explorer surface exists at `/explorers/family/{id}` for
all five completed families, alongside (not replacing) their existing dedicated pages.
The explorers index page gained a new section surfacing it.

## Remaining risks

- The five dedicated family pages remain unmigrated by design - item 6.3's job, not this
  one's. Once migrated, the shell can be moved to the plan's literal
  `/explorers/[family]` path (no longer shadowed by static siblings).
- No family has real hierarchical structure, so the shell's breadcrumb/tree affordance is
  deliberately minimal (family-level only). If a future family or reprocessing pass adds
  genuine `node_edges`, the shell's breadcrumb and `ExplorerTree` handling would need a
  real path-drilling UI - not attempted here since there is nothing true to drill into.
- Malformed `financial_year` values in PBS (this report) and contracts (item 6.1
  completion report) are now evidenced in two independent families - worth a dedicated
  data-quality pass, out of scope here.
- The production deployment lag (top-of-ledger callout) continues to apply.

## Next item

Item 6.2 is complete against the plan's own description. Per the plan's established
order, item 6.3 (migrate contracts, PBS, grants, VIC output performance, and ACT invoices
onto the shell, in that order, then QLD QGIP after Wave 5 repair) is next.

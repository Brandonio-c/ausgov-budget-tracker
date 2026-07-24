# Research-agent handoff: expand ring drill-down (have vs need)

**Date:** 2026-07-24  
**Repo:** `ausgov-budget-tracker`  
**Audience:** research agent (find **direct download URLs**, hierarchy notes, FY coverage — not code changes)  
**Related prior handoff:** [`ops/research-agent-handoff-ring-depth-gdp-20260724.md`](research-agent-handoff-ring-depth-gdp-20260724.md) (still valid for GDP/tax; this doc updates **spending/debt depth** after Federal Actuals cascade work)

---

## 0. Product question you are answering

> For Combined / Federal / State rings (Actuals, Budget, Debt), how deep *can* we go with data we already hold, and what **additional published datasets** unlock rings 5–8+ under major wedges?

Return evidence as tables of sources with **stable direct file URLs**, not landing-page essays.

---

## 1. How rings work today (constraints the research must respect)

| Rule | Implication for research |
|------|--------------------------|
| Preferred **Actuals** pie = ABS GFS expenses (Commonwealth ~**$745B** FY 2024–25) | Do **not** propose replacing GFS with PBS totals |
| Statement 6 / FBO / PBS hang as **`related_breakdown`** (navigation; non-additive) | Still valuable for drill-down — label FY + estimate vs audited |
| Sunburst **Depth −/+** uses **additive nestable** children only | Statement 6 / FBO *folders* are excluded from additive depth so parent $ is not doubled |
| Measured Federal Actuals FY 2024–25 | Additive nestable depth ≈ **4**; raw API tree (incl. folders) ≈ **5** |
| Typical published hierarchy | Jurisdiction → purpose → sub-purpose → (budget function) → component → **program**. Almost nothing public goes cleanly past program without grants/contracts |

**User expectation:** “waaaaay further than 4 rings.” Research must separate:

1. **Unused data we already have** (ingest/link gaps)  
2. **New sources** that add true hierarchy levels (grants, instruments, agency program trees)

---

## 2. Current depth snapshot (post 2026-07-24 Actuals work)

### 2.1 Federal Actuals FY 2024–25 (live `facts.db`)

| Purpose (approx $bn) | Raw subtree depth | Additive nestable depth | What fills outer rings |
|----------------------|------------------:|------------------------:|------------------------|
| Health (~118) | 4 | 2–3 | ABS kids + Statement 6 / FBO folders + Health PBS where linked |
| Education (~56) | 4 | 2–3 | Same pattern |
| Social protection (~287) | 3 | ~4 | Statement 6 → components → DSS PBS (best cascade) |
| Defence (~50) | 3 | ~4 | S6 lump → components → **bridged Defence PBS** (new) |
| Transport / Economic affairs / Public order | 2–3 | 2–3 | S6/FBO + noisy PBS bridge under some subs |
| GPS / Housing / Environment / Recreation | ~2 | 1–2 | Mostly GFS only |

### 2.2 Other modes (approximate ceilings)

| Mode | Typical max depth | Blocker |
|------|------------------:|---------|
| Federal **Budget** | ~4 | Same S6 → components → PBS shape; many noisy PBS leaves |
| **Combined** Actuals | 2–4 | States/local = GFS purpose/sub-purpose; federal related packs do not invent state programs |
| **Debt** | **2** | ABS Table_3 = six liability classes; no instrument ring under Debt securities |

### 2.3 Inventory already in `facts.db` / staging (do not re-download blindly)

| Source key / asset | Facts / rows (approx) | Hierarchy it *can* provide | Gap for rings |
|--------------------|----------------------:|----------------------------|---------------|
| `abs_gfs_*` (49 jurisdiction sources) | GFS expense + liability | Juris → purpose → limited sub-purpose | Stops early on many wedges |
| `federal_fbo_2024_25_function_subfunction` | ~85 | Function → sub-function (audited) | No program level |
| `federal_budget_statement_6_a61` | ~432 | Budget function / sub-function (estimates) | FY often budget/forward vs Actuals year |
| `federal_budget_statement_6_components` | ~225 | Component under S6 | Thin coverage outside DSS/Health-style tables |
| `federal_dss_pbs_programs` | ~60 | Program under SSW | Small set |
| `federal_health_pbs_programs` | ~15 | Program under Health | Small set |
| `federal_pbs_programs_s6_bridge` | ~10k facts | Remapped portfolio PBS → S6 paths | Noisy OCR; 2–3 path levels only |
| `federal_pbs_programs_all` | ~56k facts / ~124k staging rows | Portfolio → program-ish labels | **Not fully cascaded** into Actuals rings; quality uneven |
| Raw PBS-ish PDFs on disk | ~76 | Outcome / Table 2.1 / Cost Summary | Many pages still narrative; extract heuristics incomplete |
| `gfs_liability` | ~1.3k | Juris → 6 liability classes | No Bonds/TIBs/Notes |
| `borrowing_authority_debt_outstanding` / net & face debt | partial | Time series / authority stocks | Not sunburst rings under ABS classes |

**PBS portfolios with large staging volume (already held):** Infrastructure…, Health, Treasury, Attorney-General’s, PMC, Climate…, Agriculture, Finance, Industry, Employment, Social Services, Home Affairs, DFAT, Education, Veterans’, Defence (now extracting program totals).

---

## 3. Research mission A — Spending Actuals / Budget: “have vs need”

### 3.1 Questions to answer

1. For each major **Commonwealth purpose** (Defence, Health, Education, Social protection, Economic affairs, Transport, GPS, Public order, Housing, Environment, Recreation), list:
   - deepest hierarchy **already on disk** in this repo (`data/raw`, staging CSVs, `facts.db` source keys)
   - deepest hierarchy **published but not acquired**
   - deepest hierarchy **not published as open tables** (needs FOI / paid / scrape-only — flag clearly)
2. What is the **next real level after PBS program** that governments publish? (GrantConnect? administered item tables? PAES? annual reports?)
3. Which sources are **machine-readable** (CSV/XLSX/JSON) vs PDF-only?

### 3.2 Already on disk — research agent should *verify and document*, not re-fetch unless URL missing

| Asset | Where to look in repo | Research output needed |
|-------|----------------------|------------------------|
| Transparency Portal / budget.gov.au PBS PDFs | `data/raw/federal/**` + `latest.json` | Canonical **direct PDF URLs** per portfolio × FY (2024–25 FBO-aligned, 2025–26, 2026–27) |
| Statement 6 BP1 | `federal_budget_statement_6*` snapshots | Direct URL for each FY PDF; note which tables are A.6.1 vs components |
| FBO Appendix A | `federal_fbo_2024_25_*` | Confirm companion Excel/CSV if any; else PDF-only |
| ABS GFS annual XLSX | `abs_gfs_*` | List **all sheets** deeper than Table_4 (purpose detail we are not melting) |
| State budget / SDS / QAO packs already acquired | `data/raw` state trees; prior ops reports | Per jurisdiction: agency → service → program tables with URLs |

### 3.3 Need research agent to find (Priority order)

#### P0 — Commonwealth program depth that is still missing or FY-misaligned

| Target | Why | Hubs to search | Desired artefact |
|--------|-----|----------------|------------------|
| Full PBS suite **all portfolios**, FYs matching Actuals 2024–25 **and** Budget 2025–26 / 2026–27 | Bridge pack is incomplete/noisy; many portfolios not in Actuals cascade | https://budget.gov.au/content/pbs/index.htm ; https://archive.budget.gov.au/ ; https://www.transparency.gov.au/publications | Per file: direct URL, portfolio, FY, format |
| Inside each PBS: **named expense tables** usable for rings | We need Outcome → Program → $ columns, not narrative | Same PDFs | Table captions + page hints (“Table 2.1 Program expenses…”, “Cost Summary for Program…”) |
| Statement 6 **estimated actual / FBO-year** twins | Related packs skew to budget/forward FYs | BP1 Statement 6 + FBO site | Direct URLs + which column is Outcome vs Estimate |
| Machine-readable Statement 6 / function expenses | PDF extract is fragile | budget.gov.au downloads; data.gov.au | XLSX/CSV if exists |

#### P1 — True ring 5–6 under programs (this is what “waaaaay further” requires)

| Target | Why | Hubs | Desired artefact |
|--------|-----|------|------------------|
| GrantConnect / grants.gov.au awards linked to PBS program or outcome IDs | Program → grant lines | https://www.grants.gov.au ; data.gov.au GrantConnect | Bulk CSV/API + join keys to PBS |
| Administered program / special account tables beyond PBS Table 2.1 | Extra leaf detail | PBS Section 3; Finance CBMS publications if public | Direct URLs + schema |
| AusTender contract notices by portfolio/category (optional, noisy) | Contract-level under procurement-heavy wedges | https://www.tenders.gov.au ; OCDS dumps we may already hold | Confirm whether OCDS can hang under GFS purpose without double-count |

#### P2 — State / territory / local depth beyond GFS

| Target | Why | Where |
|--------|-----|-------|
| State budget papers — expenses by agency / outcome / COFOG / program | Combined rings stall at GFS purpose | Each Treasury “Budget papers” / open data portals |
| State annual reports / Outcome statements with program tables | Same | State legislatures / Treasuries |
| Local government finance more detailed than ABS Table_4 | Local depth sparse | ABS local GFS tables; state LG grants commissions |

For **each jurisdiction**, return whether depth stops at: purpose / agency / program / line item.

### 3.4 Acceptance criteria (spending research)

Deliver a markdown or CSV table with columns:

```text
scope (federal|state|local)
jurisdiction
purpose_or_portfolio
layer (gfs_purpose|gfs_sub|budget_function|component|program|grant|contract|other)
source_name
landing_url
direct_file_url
format (xlsx|csv|json|pdf|html|api)
fy_coverage
already_in_repo (yes|no|unknown)
path_or_source_key_if_yes
hierarchy_levels_provided (integer or list)
notes (estimate vs audited; join keys; caveats)
```

Plus a short **“depth unlock matrix”**:

| Desired ring depth | Possible with current repo? | Blocked on |
|--------------------|-----------------------------|------------|
| 4 | Mostly yes (federal some purposes) | Linking / clean extract |
| 5 | Rarely | Grants / administered detail |
| 6+ | No for most wedges | New sources |

---

## 4. Research mission B — Debt rings 3+

### 4.1 Have

- ABS GFS liabilities → **6 flat classes** (Debt securities is ~60% Commonwealth — leaf today)
- Partial net debt / face-value / borrowing-authority series (timeline, not pie children)

### 4.2 Need (fill ring 3–4 under Debt securities)

| Target | Hub | Desired files |
|--------|-----|---------------|
| AOFM monthly positions — Bonds / TIBs / Notes aggregates | https://www.aofm.gov.au/data-hub ; data.gov.au AOFM monthly positions | Direct XLSX URLs; field list; update frequency |
| Optional: security-level / maturity / ownership | Same | Confirm public vs chart-pack-only |
| State financing authorities (TCorp, TCV, QTC, …) | Per-state | Outstanding by instrument type |
| Statement 11 Tables 11.4 / 11.5 | budget.gov.au | Confirm latest direct PDF URL (we have snapshots) |

**Acceptance:** under Commonwealth **Debt securities**, research shows a published split that can sum ≈ ABS Debt securities (same FY / as-at date notes).

---

## 5. Research mission C — GDP + tax (third view) — pointer only

Full brief remains in [`ops/research-agent-handoff-ring-depth-gdp-20260724.md`](research-agent-handoff-ring-depth-gdp-20260724.md) §4.

Quick reminder:

- ABS GFS **Table_1 Taxation revenue** is on disk in jurisdiction XLSX but not fully productised as a revenue explorer.
- Need ABS national accounts GVA-by-industry + Taxation Revenue, Australia key tables with **direct URLs**.

Do **not** mix GDP into the GFS expense pie.

---

## 6. Explicit non-goals for the research agent

- Writing ingest code or changing the sunburst UI  
- Proposing to **sum** PBS/Statement 6 into the GFS $745B Actuals pie  
- Mass OCR of every PBS narrative page without first listing **structured table** targets  
- Scraping behind login / CAPTCHA without noting the blocker

---

## 7. Suggested research order (time-box)

1. **Inventory pass (1 pass):** map repo `data/raw` + staging + source keys → depth-unlock matrix (have).  
2. **URL pass:** fill missing `direct_file_url` for PBS / Statement 6 / FBO / AOFM / state budget packs (need).  
3. **Ring 5+ pass:** GrantConnect (or equivalent) joinability to PBS program IDs.  
4. **Debt pass:** AOFM instrument files that can nest under ABS Debt securities.  
5. **GDP/tax pass:** only after spending/debt URL tables are delivered (or in parallel if staffed).

---

## 8. Handoff checklist for research output

- [ ] Depth-unlock matrix (rings 3 / 4 / 5 / 6+) for Federal Actuals, Federal Budget, Combined, Debt  
- [ ] Master source table (schema in §3.4)  
- [ ] Per-purpose “best next source” recommendation (one primary URL each)  
- [ ] List of **already-on-disk** files that unlock depth if ingest/link only (no new download)  
- [ ] Clear FY / estimate_status caveats for anything hanging under Actuals  

**Engineering will use your URL table to decide the next ingest sprint** (clean PBS vs GrantConnect vs AOFM), not to re-litigate whether rings *should* go deeper — product wants deeper drill-down wherever published data allows.

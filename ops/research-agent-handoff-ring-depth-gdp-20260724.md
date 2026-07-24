# Research-agent handoff: ring-depth gaps + GDP/revenue third view

**Date:** 2026-07-24  
**Repo:** `ausgov-budget-tracker`  
**Live charts analysed:** Combined rings — Actuals FY 2024-25 (~$1.21T displayed) and Debt FY 2024-25 (~$2.27T displayed)  
**Goal for research agent:** Return **direct download URLs** (CSV/XLSX/JSON preferred; PDF only when unavoidable) plus parse notes so we can deepen Actuals rings 4+, Debt rings 2+, and add a GDP + tax-revenue explorer.

---

## 0. How to read the charts (important)

| Chart | Ring 1 (inner) | Ring 2 | Ring 3+ |
|-------|----------------|--------|---------|
| Combined Actuals | Government level / jurisdiction | COFOG / GFS purpose | Sub-function → Statement 6 / PBS programs (where linked) |
| Combined Debt | Jurisdiction | ABS GFS liability class (6 lines) | **Empty today** — no instrument / maturity hierarchy ingested |

Combined totals **must not** be read as one national sum (UI banner). Depth gaps below are about **missing hierarchy under wedges**, not about the integrity banner.

---

## 1. What we already have (facts.db + raw)

### 1.1 Spending Actuals — present

| Layer | Source key(s) | On disk? | In facts.db? | Typical ring depth |
|-------|---------------|----------|--------------|--------------------|
| ABS GFS expenses by purpose (Table_4) | `abs_gfs_*` (16 jurisdictions) | Yes | Yes (`gfs_expense`) | Juris → purpose → limited sub-purpose |
| Federal FBO function/sub-function | `federal_fbo_2024_25_function_subfunction` | Yes (PDF) | Yes | Function → sub-function |
| Budget Paper 1 Statement 6 | `federal_budget_statement_6_*` | Yes (`bp1_bs-6.pdf`) | Partial (~687 facts, mostly **estimates** not audited actuals) | Adds related packs under Health / Social protection |
| PBS program tables | `federal_dss_pbs_programs`, `federal_health_pbs_programs` | Many PDFs | **Thin** (75 program facts; DSS+Health only) | Programs under a few portfolios |
| Transparency Portal PBS PDFs | `federal_transparency_portal` | **16 PBS PDFs** | **Not program-ingested** | — |

**Measured API depth (FY 2024-25):**

- Federal Commonwealth: max path depth **6**, but **39 leaves stop at depth 3** (purpose/sub-purpose only).
- State/territory: max depth 6, but pattern shows **6 leaf purposes at depth 2** with no children — matches empty outer rings on large wedges.
- Local: max depth 5; denser mid-rings from GFS purpose hierarchy only.

**Federal purpose subtree depths (Actuals, preferred GFS basis):**

| Purpose | ~$bn | Subtree depth under purpose |
|---------|------|-----------------------------|
| Social protection | 287 | 3 (best — Statement 6 / DSS related) |
| Health | 118 | 4 |
| General public services | 159 | 2 |
| Education | 56 | 2 |
| Defence | 50 | **1** (stops early — empty outer rings) |
| Economic affairs | 33 | **1** |
| Transport | 16 | **1** |
| Public order, Environment, Housing, Recreation | 5–9 each | **1** |

**Chart diagnosis (Image 1):** Outer “barcode” rings are mostly **Statement 6 related_breakdown** children (budget estimates / PBS program lines) hanging under a few purposes. Large wedges (esp. Defence / Economic affairs / many state GFS purposes) have **no program children** → rings 4+ look empty or splintered.

### 1.2 Debt — present

| Layer | Source | On disk? | In facts.db? | Ring depth |
|-------|--------|----------|--------------|------------|
| ABS GFS Table_3 liabilities | `abs_gfs_*_liabilities` | Yes (same XLSX as expenses) | Yes (`gfs_liability`, 1,120 facts) | Juris → **6 flat categories only** |
| Statement 11 historical (net debt, face value CGS, net worth) | `federal_budget_statement_11_historical` PDF | Yes | **Almost unused** (wrong/minimal expense extract only) | Would be **time series**, not instrument pie |
| Consolidated Financial Statements | `federal_cfs_2024_25` | Yes (large PDF) | Not as liability instruments | Notes / aggregates |
| AOFM CGS instrument portfolio | — | **No** | **No** | Needed for Debt securities → Bonds / TIBs / Notes |

**Liability categories we have (leaves at ring 2):**

1. Currency and deposits  
2. Advances  
3. Other loans and placements  
4. Debt securities *(~60% of Commonwealth — needs AOFM breakdown)*  
5. Provisions for defined benefit superannuation  
6. Other liabilities  

**Chart diagnosis (Image 2):** Max tree depth is **2 by construction**. Rings 3–4 cannot fill until we ingest instrument / maturity / holder hierarchies under those six lines (especially **Debt securities**).

### 1.3 GDP / tax revenue — present

| Need | Status |
|------|--------|
| GDP / GVA by industry | **Missing** from registry + facts.db |
| Tax revenue by type / jurisdiction | **Missing** as published measure; ABS GFS **Table_1 Taxation revenue** exists **on disk** in every jurisdiction XLSX but is **not melted/ingested** |
| Budget Paper Statement 5 revenue | Not ingested (Statement 6 expenses only) |
| Statement 11 Tables 11.1 / 11.3 / 11.8 taxation receipts | In Statement 11 PDF on disk; not extracted |

---

## 2. Gap A — Spending Actuals rings 4+

### 2.1 What is missing (product requirement)

Fill outer rings with **audited/actual** (or clearly labelled estimate) program / component lines under every major purpose, for:

1. **Commonwealth** — all portfolios, not only DSS + Health snippets  
2. **States / territories** — agency or COFOG sub-function → program where published  
3. Prefer **same FY as dashboard Actuals** (2024-25 FBO/GFS), and separately keep Budget estimate packs labelled

### 2.2 Already on disk but not fully used (ingest first)

| Asset | Path / key | Action for research agent |
|-------|------------|---------------------------|
| Transparency Portal PBS set (16 PDFs, 2025-26) | `data/raw/federal/federal_transparency_portal/.../*-PBS.pdf` | Confirm canonical **direct file URLs** + 2024-25 / 2026-27 equivalents; list table names for Outcome / Program expenses |
| DSS / Health / DVA / NDIA PBS | Manual inbox + raw snapshots | Confirm stable download URLs for latest + prior FY |
| Statement 6 PDF | `.../federal_budget_statement_6_2026_27/.../bp1_bs-6.pdf` | Confirm URL for **2024-25 FBO / Budget** Statement 6 twin if different |
| FBO Appendix A | `.../federal_fbo_2024_25_function_subfunction/.../05_appendix_a.pdf` | Confirm landing + any machine-readable companion |

### 2.3 Need research agent to find (download links)

**Priority 1 — Commonwealth program depth (rings 4–6)**

| Target | Why | Where to look | Desired artefact |
|--------|-----|---------------|------------------|
| Full PBS suite for **all portfolios** for FY aligning to Actuals (2024-25 FBO and/or 2025-26 PBS) | Only DSS+Health programs ingested; Defence etc. stop at ring 2 | https://budget.gov.au/content/pbs/index.htm ; https://archive.budget.gov.au/ ; https://www.transparency.gov.au/publications | Per-portfolio PDF **or** HTML tables; Excel if any portfolio publishes it |
| Program expense tables inside each PBS | Outcome → Program → expenses | Same | Direct URLs + table captions (“Table 2.1 Program expenses…” etc.) |
| GrantConnect / administered program dumps linked to PBS program IDs | Optional ring 5–6 | https://www.grants.gov.au / data.gov.au GrantConnect | CSV/API |

**Priority 2 — Align Actuals year with deep packs**

| Target | Why | Where to look |
|--------|-----|---------------|
| Statement 6 **estimated actual / FBO-aligned** tables for 2024-25 | Current Statement 6 facts skew to budget/forward years → related packs can mismatch Actuals FY | Budget Paper No.1 Statement 6 for 2024-25 and 2025-26; FBO expenses by function |
| Machine-readable Statement 6 | PDF extract is fragile | budget.gov.au downloads; data.gov.au |

**Priority 3 — State / local depth beyond GFS Table_4**

| Target | Why | Where to look |
|--------|-----|---------------|
| State budget papers — expenses by agency / service / COFOG | State wedges stop at GFS purpose | Each state Treasury “Budget papers” / open data |
| State annual GFS or Outcome statements with program tables | Same | ABS GFS annual “Download all” + state Treasuries |
| Local government finance by purpose (more detail than Table_4) | Local max depth 5 but sparse | ABS GFS local tables; state LG grants commissions |

**Known ABS hub (already used for Table_4):**  
https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/latest-release  
Research agent should list **every Key Table / jurisdiction XLSX** URL and note which sheets add **deeper expense purpose** than our current Table_4 melt.

### 2.4 Acceptance criteria (Actuals)

- Combined Actuals rings at depth ≥4 show **labelled** children for Defence, Education, Economic affairs (not only Health/Social).  
- Related packs tagged with FY + estimate_status so UI can warn on estimate-vs-actual.  
- Research output: spreadsheet or markdown table of `{source_id, landing_url, direct_file_url, format, sheet_or_table, fy_coverage, hierarchy_levels_provided}`.

---

## 3. Gap B — Debt rings 2+

### 3.1 What is missing

| Desired ring | Content | Status |
|--------------|---------|--------|
| 2 | Liability class (current) | Done (ABS Table_3) |
| 3 | Under **Debt securities**: Treasury Bonds / Indexed Bonds / Treasury Notes / other | **Missing** — need AOFM |
| 3 | Under **Other loans**: by lender / maturity bucket if published | Missing |
| 3 | Under **Super provisions**: scheme / actuarial split if published | Optional (CFS / Finance) |
| 4 | Per-line security / maturity date outstanding | AOFM security-level files |
| Separate series | Commonwealth **net debt**, **gross debt (face value)** | Statement 11 Tables 11.4 & 11.5 **on disk**, not ingested |
| State debt | TCorp / QTC / TCV etc. outstanding by instrument | Not acquired |

### 3.2 On disk / quick wins (may not need new download)

| Asset | Action |
|-------|--------|
| Statement 11 PDF Tables 11.4 (net debt), 11.5 (face value of CGS), 11.7 (net worth) | Extract + ingest as stock time series (`net_debt`, `gross_debt_face_value`) — still won’t fill pie rings 3+, but feeds Timeline |
| ABS Table_3 (already) | Keep as ring 1–2 |

### 3.3 Need research agent to find

**Priority 1 — Commonwealth instrument breakdown (fills Debt securities ring 3–4)**

| Target | Landing / known hubs | Desired files |
|--------|----------------------|---------------|
| AOFM Data Hub monthly positions | https://www.aofm.gov.au/data-hub | `portfolio aggregate - dealt.xlsx`, Treasury Bonds / TIBs / Notes dealt & settlement workbooks |
| Same on data.gov.au | https://data.gov.au/data/dataset/australian-office-of-financial-management-monthly-positions | Stable resource URLs for each XLSX |
| AOFM ownership / non-resident holdings (optional ring) | AOFM Data Hub “ownership” datasets | XLSX/CSV |
| Investor chart pack (context only) | https://www.aofm.gov.au/publications/investor-chart-pack | PDF — not primary ingest |

**Priority 2 — Official net debt / gross debt definitions**

| Target | Notes |
|--------|-------|
| Budget Paper 1 Statement 11 (latest + historical) | Confirm current FY direct PDF URL (we have one snapshot: `bp1_bs-11.pdf`) |
| Monthly Financial Statements — gross/net debt lines | Already have some monthly source; find tables with debt stocks |

**Priority 3 — State / territory / local debt instruments**

| Jurisdiction | Likely publishers | What to return |
|--------------|-------------------|----------------|
| NSW | TCorp | Bonds outstanding by series |
| VIC | TCV | Same |
| QLD | QTC | Same |
| SA / WA / TAS / ACT / NT | Respective financing authorities | Same |
| Local | ABS GFS local balance sheet only (already) unless states publish LG debt registers | URLs if any |

Research agent: for each, return `{authority, landing_url, direct_file_url, update_frequency, fields_available}`.

### 3.4 Acceptance criteria (Debt)

- Combined Debt rings: under Commonwealth **Debt securities**, ring 3 shows Bonds / TIBs / Notes (or equivalent) summing to ~ABS Debt securities.  
- Optional ring 4: maturity buckets or top ISINs.  
- Timeline mode can plot net debt % GDP if GDP series also acquired.

---

## 4. Gap C — Third view: GDP + tax revenue

### 4.1 Product sketch (for research scoping)

Suggested hierarchy (mirrors spending UX):

1. **GDP / production** — Australia total → industry GVA (ANZSIC divisions) → optional state GSP  
2. **Tax revenue** — All governments → Commonwealth / State / Local → tax type (PIT, CIT, GST, excise, …)  
3. Cross-link: tax / GDP ratios (ABS already publishes tax as % GDP)

Do **not** mix GDP (economy) and government expense in one additive pie without a clear mode switch.

### 4.2 Already on disk (ingest without new fetch)

From each `55120DO*.xlsx` **Table_1 Operating Statement**:

- Taxation revenue  
- Sales of goods and services  
- Interest / Dividend / Royalty / Other revenue  
- Total GFS revenue  

→ Enough for a first **GFS revenue** pie by jurisdiction (parallel to liabilities ingest). Research agent should still confirm ABS “Download all” bundle URL and list Table_1 presence for every jurisdiction file.

### 4.3 Need research agent to find

**GDP / national accounts**

| Target | Hub | Desired download |
|--------|-----|------------------|
| Australian National Accounts: National Income, Expenditure and Product | https://www.abs.gov.au/statistics/economy/national-accounts/australian-national-accounts-national-income-expenditure-and-product/latest-release | Tables with **GDP**, **GVA by industry** (chain volume + current prices); CSV/XLSX |
| Annual national accounts / industry detail | ABS 5204.0 family (confirm current title) | Industry GVA annual |
| State accounts / GSP by industry | ABS State Accounts latest release | State × industry if available |

**Tax revenue (full typology)**

| Target | Hub | Desired download |
|--------|-----|------------------|
| Taxation Revenue, Australia | https://www.abs.gov.au/statistics/economy/government/taxation-revenue-australia/latest-release | “Table 1-10” XLSX + Key Tables — by level of government, jurisdiction, tax type |
| Budget Paper 1 **Statement 5: Revenue** | budget.gov.au / archive.budget.gov.au | PDF + any Excel chart data; tables for individuals, companies, super, GST, excise |
| Statement 11 Tables 11.3 / 11.8 taxation receipts (historical) | Same Statement 11 PDF we hold | Confirm latest URL; extract plan |

**Optional enrichment**

| Target | Hub |
|--------|-----|
| Tax Expenditures and Insights Statement (revenue forgone — not cash) | https://treasury.gov.au/publication/p2025-607085 |
| Monthly Financial Statements — tax receipts | Already partially in raw tree — confirm tax receipt tables |

### 4.4 Acceptance criteria (GDP / tax view)

- Research returns direct URLs for: (a) GDP + industry GVA, (b) tax by type × jurisdiction, (c) optional Statement 5.  
- Formats prefer XLSX/CSV.  
- Note units ($m vs $b), chain-volume vs current price, and FY vs calendar year.

---

## 5. Priority order for the research agent

1. **AOFM monthly portfolio XLSX URLs** (unblocks Debt rings 3–4 under Debt securities).  
2. **ABS Taxation Revenue Australia XLSX URLs** + confirm GFS Table_1 already covers coarse revenue.  
3. **ABS National Accounts GDP / GVA-by-industry download URLs**.  
4. **Complete PBS direct URLs** for all portfolios (2024-25 and/or 2025-26) + which tables hold program expenses.  
5. **State financing authority debt outstanding** datasets.  
6. **Statement 5 Revenue** + latest **Statement 11** direct PDF URLs (historical stocks / tax receipts).

---

## 6. Output format expected back from research agent

For each candidate source, return:

```yaml
- proposed_source_id: aofm_cgs_portfolio_dealt
  title: ...
  publisher: Australian Office of Financial Management
  landing_url: https://...
  direct_file_urls:
    - https://...xlsx
  format: xlsx
  update_cadence: monthly
  fills_gap: debt_ring_3_debt_securities
  hierarchy:
    - Debt securities
    - Treasury Bonds | Treasury Indexed Bonds | Treasury Notes
    - (optional) maturity / ISIN
  fy_or_period_coverage: "2003-06 onward (EOM)"
  licence: CC BY 4.0 (confirm)
  parse_notes: "Sheet names, $m vs face value vs market value"
  already_on_disk: false
```

Also flag: **duplicate of something already under `data/raw/`** so we don’t re-download.

---

## 7. Explicit non-goals / pitfalls

- Do **not** treat “Public debt transactions” (GFS **expense** / interest) as debt stock.  
- Do **not** sum Combined rings across federal+state+local into “Australia debt”.  
- Statement 6 / PBS **budget estimates** must stay labelled if attached under Actuals.  
- Tax expenditures ≠ tax revenue collected.  
- GDP industry shares are **not** government spending shares.

---

## 8. Quick reference — hubs to start from

| Hub | URL |
|-----|-----|
| ABS GFS Annual | https://www.abs.gov.au/statistics/economy/government/government-finance-statistics-annual/latest-release |
| ABS Taxation Revenue | https://www.abs.gov.au/statistics/economy/government/taxation-revenue-australia/latest-release |
| ABS National Accounts (5206 family) | https://www.abs.gov.au/statistics/economy/national-accounts/australian-national-accounts-national-income-expenditure-and-product/latest-release |
| AOFM Data Hub | https://www.aofm.gov.au/data-hub |
| AOFM on data.gov.au | https://data.gov.au/data/dataset/australian-office-of-financial-management-monthly-positions |
| Budget PBS index | https://budget.gov.au/content/pbs/index.htm |
| Budget archive | https://archive.budget.gov.au/ |
| Transparency Portal publications | https://www.transparency.gov.au/publications |

---

## 9. Internal audit snapshot (2026-07-24)

```
Actuals FY2024-25 tree max depths: federal 6, state 6, territory 6, local 5
Debt FY2024-25 tree max depths: all levels 2 (6 liability leaves per jurisdiction)
gfs_liability facts: 1120
PBS program facts ingested: 75 (2 portfolios)
Transparency PBS PDFs on disk: 16 (not program-parsed)
ABS GFS Table_1 revenue: on disk, not ingested
AOFM / GDP / Taxation Revenue Australia: not in procurement registry as first-class sources
```

*End of handoff.*

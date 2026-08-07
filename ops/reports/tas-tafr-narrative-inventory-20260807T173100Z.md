# TAS TAFR narrative-era inventory and selection

Generated: 2026-08-07T17:31:00Z.

All seven editions from 2003-04 through 2009-10 are born-digital and yield
substantial usable text; none requires OCR. They are not one stable layout.

## Selection

Select the 2007-08 through 2009-10 transition cluster. These three editions
contain labelled General Government Sector tables with explicit original
budget and final actual columns. Five measures are common and unambiguous:
revenue, expenses, net operating balance, fiscal balance, and net debt. This
produces 30 facts (five measures x two statuses x three years).

The table layouts drift, but the semantic shape is stable and bounded by an
edition manifest: exact PDF page, exact row label, and explicit budget/actual
column indices. Total State columns and intermediate 2009-10 revision/outcome
columns are excluded.

## Deferred editions

The 2003-04 through 2006-07 Executive Summaries place values in prose and
chart-adjacent lists. More importantly, the 2007-08 report states that its
Fiscal Balance and Net Operating Balance time series was recast for AASB 1049.
Publishing the earlier printed values directly into the existing
`tas_ggs_*` compatibility groups would therefore assert comparability that the
source does not establish. These four editions are explicitly deferred rather
than parsed from prose or silently treated as the recast series.

## Semantic boundary

The selected facts extend the existing TAS GGS family backward without
overlapping the already-loaded 2010-11 onward years. Flows cover the financial
year; Net Operating Balance and Fiscal Balance are non-additive annual
balances; Net Debt is a stock at 30 June. Native AUD millions are multiplied by
1,000,000. Original budget and audited actual remain distinct vintages.

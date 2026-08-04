# Orphan-node investigation (Task 5)

All 278 orphan nodes found by `scripts/ops/task9_sql_integrity_checks.py`
(zero `fact_nodes`, zero `breakdown_edges` as parent or child, zero
`node_edges` as parent or child) belong to the state/territory
borrowing-authority debt-instrument sources, spread across 10 distinct
`source_key` values:

| source_key | orphan count |
|---|---:|
| nsw_tcorp_bonds_on_issue | 64 |
| qld_qtc_aud_bond_outstandings | 47 |
| nsw_tcorp_weekly_bonds | 36 |
| vic_tcv_amount_on_issue | 32 |
| wa_watc_funding_sources | 23 |
| qld_qtc_weekly_outstandings_2026_07_17 | 19 |
| sa_safa_weekly_funding_update | 18 |
| nt_nttc_borrowing_strategy | 17 |
| qld_qtc_benchmark_bonds | 14 |
| tas_tascorp_annual_report_2024_25 | 8 |
| **total** | **278** |

## Two distinct causes, both traced to raw code and data, not assumed

### Cause 1 - naming-scheme drift on 7 currently-active sources (226 nodes)

`nsw_tcorp_bonds_on_issue`, `qld_qtc_aud_bond_outstandings`,
`vic_tcv_amount_on_issue`, `wa_watc_funding_sources`,
`sa_safa_weekly_funding_update`, `nt_nttc_borrowing_strategy`, and
`tas_tascorp_annual_report_2024_25` are all still ingested today via
`scripts/ingest/m_borrowing_authorities.py` (their `source_id` keys are
in that script's live `SOURCE_PARSERS` dict).

Directly comparing a live node against its orphaned counterpart for the
same real-world bond makes the mechanism visible (VIC example):

| | live node (current) | orphan node |
|---|---|---|
| name | `Debt securities / TCV / Fixed-rate bonds / 17 Nov 2026 5.5` | `Debt securities / Fixed-rate bonds / 17 Nov 2026 5.5` |
| same bond? | same maturity (17 Nov 2026), same coupon (5.5) | same maturity, same coupon |

And an NSW example, showing a second, independent naming change
(instrument reclassification) stacked on top of the first:

| | live node (current) | orphan node |
|---|---|---|
| name | `Debt securities / TCorp / Fixed-rate bonds / 20 May 2027 3.00%` | `Debt securities / Other funding instruments / 20 May 2027 3.00%` |

Root cause, read directly from the code:

- `scripts/ingest/load_facts.py`'s `ensure_node()` gives every node a
  `canonical_key` of `f"{source_id}|node|{name}"` where `name` is the
  *entire* category string (`Debt securities / <authority> /
  <instrument_type> / <security>` for a leaf, or the same without the
  last segment for the instrument-type roll-up total) - there is no
  decomposition into a parent/child node hierarchy, and this whole
  source family never creates a `breakdown_edges` or `node_edges` row.
  Every node is a flat, independent leaf keyed by its full display text.
- `scripts/ingest/m_borrowing_authorities.py` (lines 57-74, before this
  milestone's fix) deletes every `fact` and `fact_nodes` row for a
  source's `source_document_id` on every reload ("so path/valuation
  upgrades do not double-count"), then re-derives fresh facts/nodes from
  the newly parsed instrument list - but never touched the `nodes` table
  itself.
- `scripts/ingest/adapters/state_debt_instruments.py`'s
  `InstrumentRow.category()` (the text that becomes `node_name`) has
  changed at least twice in this repo's history: it now always includes
  the authority name (`Debt securities / {authority} / ...`), and a
  classification fix (`parse_source()`, lines 682-683: `if
  r.instrument_type == INSTRUMENT_OTHER and authority in {"QTC", "WATC",
  "NTTC"}: r.instrument_type = INSTRUMENT_FIXED`) reclassifies some
  bonds that used to fall into a generic "Other funding instruments"
  bucket into the correct "Fixed-rate bonds" bucket.

Every time either change shipped, the *next* reload created brand-new
nodes under the new text (different `canonical_key` -> `ensure_node()`
inserts rather than reuses) while the old-text nodes, now with zero
facts attached and never linked by any edge in the first place, were
silently abandoned. This is exactly the mission's listed candidate cause
"replace-on-reload deleting facts but not unused nodes" combined with
"changing node keys between runs."

**Verification that this is safe to delete:** every one of these 226
orphans was individually re-confirmed (not assumed from the SQL count
alone) to have zero `fact_nodes`, zero `breakdown_edges`, and zero
`node_edges` rows - i.e. exactly the same "genuinely unreachable"
definition `task9_sql_integrity_checks.py`'s `orphan_nodes()` uses, and
distinct from a legitimate fact-less folder node (which always has at
least one `breakdown_edges`/`node_edges` row to a child - none of the
7 live sources' current, non-orphaned nodes for these same authorities
have any either, confirming this whole source family simply never uses
folder/child edges at all, live or orphaned).

### Cause 2 - fully-retired legacy source_ids (52 nodes)

`nsw_tcorp_weekly_bonds`, `qld_qtc_benchmark_bonds`, and
`qld_qtc_weekly_outstandings_2026_07_17` are **not** present in
`m_borrowing_authorities.py`'s current `SOURCE_PARSERS` dict at all -
they are earlier, one-off `source_id`s from before the pipeline was
consolidated onto today's 7-authority canonical set (superseded by
`nsw_tcorp_bonds_on_issue` and `qld_qtc_aud_bond_outstandings`
respectively). Direct query confirms all three now have **zero facts of
any kind** still attached to their `source_document_id` - they are fully
dead, not merely stale:

| source_key | source_document still exists | live facts remaining |
|---|---|---:|
| nsw_tcorp_weekly_bonds | yes (doc_id 85) | 0 |
| qld_qtc_weekly_outstandings_2026_07_17 | yes (doc_id 87) | 0 |
| qld_qtc_benchmark_bonds | yes (doc_id 88) | 0 |

These will never be re-ingested (no code path references these
`source_id`s any more), so their 52 nodes are permanently orphaned
one-off historical debris, not an ongoing upstream defect to fix in
code - a one-time cleanup pass is the correct and complete resolution.
Their (now fact-less and node-less, after cleanup) `source_documents`
rows are left in place: `task9_sql_integrity_checks.py`'s
`dangling_source_documents()` check already classifies a source
document with no remaining facts or nodes as **informational only, not
a hard failure** (per this milestone's Task 6 spec), and the mission
did not ask for source_document cleanup - only orphan nodes.

## Fix applied

1. **Upstream (Cause 1):** `scripts/ingest/m_borrowing_authorities.py`
   now calls `scripts/ops/cleanup_orphan_nodes.py`'s
   `orphan_node_ids_for_source_document()` /
   `delete_orphan_nodes()` immediately after dropping a source's prior
   facts/fact_nodes on every reload, scoped to that source's own
   `source_document_id` - so any node that just lost its last fact is
   deleted in the same transaction as the reload, before new nodes are
   created. This makes a future naming/classification change
   self-cleaning instead of leaking. Regression tests
   (`tests/ingest/test_m_borrowing_authorities.py`) drive `main()`
   end-to-end against a synthetic fixture database and a monkeypatched
   single-source `SOURCE_PARSERS` entry (no real raw-data corpus
   needed), proving a reload deletes its own now-orphaned node and that
   two consecutive reloads are idempotent (zero orphans, stable fact
   count).
2. **One-time cleanup (both causes):** `scripts/ops/cleanup_orphan_nodes.py`
   - a generic, transaction-safe, `--dry-run`-by-default /
   `--apply` / `--report` / `--source`-filterable utility using the
   exact same orphan definition as `task9_sql_integrity_checks.py` -
   applied once against the real database to remove all 278 existing
   orphans. Fixture-backed tests
   (`tests/ops/test_cleanup_orphan_nodes.py`) prove it finds only
   genuine orphans, never a legitimate fact-less folder node (one with a
   `breakdown_edges` row to a child), source-filters correctly, deletes
   correctly, and is idempotent across repeated `--apply` runs.

See `ops/reports/orphan-node-cleanup-apply-*.json`/`.md` for the applied
run's per-node detail and the dry-run/second-run reports proving the
before/after counts and idempotency.

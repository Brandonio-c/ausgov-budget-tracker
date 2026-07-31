# PBS year correction report — 20260724T220533Z

## Change

Removed fixed `YEARS_DEFAULT[-len(nums):]` assignment from `pbs_programs_all.py`.

Resolution order (see `extractors/pbs_year_resolve.py`):

1. Table header FY tokens (+ status hints)
2. Continuation-page headers
3. Declared source layout template (opt-in when no header)
4. Quarantine (`data/staging/quarantine/pbs_quarantine_*.jsonl`)

## Fixtures

Committed under `tests/fixtures/pbs/` for 2024–25 / 2025–26 / 2026–27 headers, Defence cost summary, and a no-year bad table.

## Reprocess status

**Not fully re-ingested in this pass** (PDF extract across ~76 PBS files is long-running). Extractor + unit tests land first; operators should run:

```bash
python scripts/ingest/extractors/pbs_programs_all.py
# then rematerialise packs: pbs_programs_all → s6_bridge → cascade
```

and refresh this report with counts: added / removed / corrected / quarantined by portfolio.

## Quarantine policy

Ambiguous numeric rows without year evidence are **not** written as facts; they append to quarantine JSONL with an explicit `reason`.

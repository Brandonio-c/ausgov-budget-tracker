# Ingest maximise handoff

- Generated: `20260724T200621Z`
- Facts: **279,543** (baseline ~270,937)
- Source documents: **123**

## Highlights

- `pbs_programs_all`: 14,631
- `borrowing_authority`: 170
- `superannuation_liability`: 3
- `gsp_current`: 8
- `gdp_chain_volume`: 10
- `with_observation_date`: 387
- `with_valuation_basis`: 387

## Remaining gaps

- NSW grants commission ZIP contains PDFs only (`pdf_only_no_structured_xlsx`); OLG time-series remains canonical.

- Defence PBS PDFs still yield 0 program rows (layout/OCR).
- Most QLD SDS PDFs marked extraction_unreliable pending stable table patterns.
- QAO local PDFs: no_useful_fiscal_data — use structured VLGGC/OLG/CDC returns.
- Do not commit facts.db or raw downloads.

See also `visualization-depth-*.md`, `debt-reconciliation-*.md`, `ingestion-coverage-*.md`, `qld-sds-extraction-*.md`, `local-qao-limits-*.md`.

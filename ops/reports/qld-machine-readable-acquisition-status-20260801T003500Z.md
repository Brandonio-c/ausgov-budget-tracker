# QLD machine-readable packs — acquisition status (Task 7)

Covers the three sources named in the directive: `qld_sds_machine_readable_2025_26`,
`qld_budget_bp2_machine_readable_2025_26`, `qld_budget_measures_bp4_machine_readable_2025_26`.

## Registry status

All three are registered in `config/procurement_sources.yaml` (validated against
`config/procurement_sources.schema.json`), `enabled: true`, `access_method:
landing_page_discovery`. `qld_budget_bp2_machine_readable_2025_26` and
`qld_budget_measures_bp4_machine_readable_2025_26` were already registered with
verified resource manifests as of 2026-07-31 (M11); this session added the same
treatment to `qld_sds_machine_readable_2025_26`, which previously lacked one.

## Resource manifests (verified via CKAN metadata API, not file download)

Queried each dataset's public `package_show` CKAN API endpoint
(`https://www.data.qld.gov.au/api/3/action/package_show?id=<dataset>`) - a
lightweight, unauthenticated JSON metadata read, not a file download, and
confirmed it is **not** WAF-gated (plain HTTP 200). Used it only to enumerate
real resource URLs; no data was downloaded through it.

- `qld_sds_machine_readable_2025_26` (dataset `6132a498-6195-4b1d-b18e-997fd25c5140`):
  4 resources - balance sheets, income statements, cash flow statements, and a
  data dictionary, all CSV. Manifest:
  `ops/manifests/qld_sds_machine_readable_2025_26.json`.
- `qld_budget_bp2_machine_readable_2025_26` (dataset
  `e680b776-6468-46ae-8216-5186325879c1`): 9 resources, Budget Paper 2 tables
  8.1-8.9 (GGS/PNFC/NFPS operating statement, balance sheet, cash flow
  statement). Manifest: `ops/manifests/qld_budget_bp2_machine_readable_2025_26.json`.
- `qld_budget_measures_bp4_machine_readable_2025_26` (dataset
  `30cce1c9-e032-4788-b795-e5173ebd9def`): 3 resources - the budget measures
  table itself, a data dictionary, and explanatory notes. Manifest:
  `ops/manifests/qld_budget_measures_bp4_machine_readable_2025_26.json`.

## Acquisition blocker (re-confirmed, not assumed)

Made exactly one direct HTTP GET per dataset family (not a retry storm) against
a real resource URL to confirm the blocker still applies:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}, size=%{size_download}\n" \
  "https://www.data.qld.gov.au/dataset/6132a498-.../resource/ce6a5a90-.../download/sds-balance-sheets-service-delivery-statements-2025-26.csv"
HTTP 202, size=0
```

Same AWS WAF empty-challenge signature (HTTP 202, empty body) already
documented for the BP2/BP4 datasets. This confirms the blocker is real and
current, not stale from July - and that it is a challenge-response issue, not
an absent bulk export (the files are real and enumerable via the API).

**Per the operating rules for this directive, no further attempt was made.**
This environment has no display and no Xvfb (`$DISPLAY` is empty, `Xvfb`/
`xvfb-run` are not installed) and no interactive human session available to
clear a browser challenge, so the headed-browser path
(`scripts/procure_browser_session.py`) cannot be run from here. This matches
the same blocker already found earlier in this engagement (no display / no
root) - re-verified rather than assumed carried over.

## Exact commands for a human with a real display session

Run from the repo root, in the `ausgov-budget-tracker` conda environment, on a
machine with an actual display (or via a remote desktop / VNC session) and a
human available to clear the Cloudflare/AWS WAF challenge in the opened
browser window:

```bash
conda run -n ausgov-budget-tracker python scripts/procure_browser_session.py \
  --source-id qld_sds_machine_readable_2025_26 \
  --urls-file ops/manifests/qld_sds_machine_readable_2025_26.json

conda run -n ausgov-budget-tracker python scripts/procure_browser_session.py \
  --source-id qld_budget_bp2_machine_readable_2025_26 \
  --urls-file ops/manifests/qld_budget_bp2_machine_readable_2025_26.json

conda run -n ausgov-budget-tracker python scripts/procure_browser_session.py \
  --source-id qld_budget_measures_bp4_machine_readable_2025_26 \
  --urls-file ops/manifests/qld_budget_measures_bp4_machine_readable_2025_26.json
```

Each opens a real (non-headless) Chromium window against the resource URLs in
the manifest; a human clears the WAF challenge once per domain/session, after
which the script downloads the files and (unless `--no-import` is passed) runs
`procure_manual_import` to register them under `data/raw/state/<source_id>/`.

## Expected CSV schema: deliberately not guessed

Searched `data/raw/state/` for any existing QLD file that could legitimately
serve as a schema template for these three datasets. Found only contract-
disclosure and on-time-payment CSVs (`qld_contract_disclosure_agency_datasets`,
`qld_on_time_payment_reports`) - a completely different data domain (individual
contract/payment records, not budget financial-statement tables) with no
genuine column overlap. No prior-year machine-readable SDS/BP2/BP4 pack is on
disk either. Per the directive's explicit instruction not to invent columns
from filenames, **no expected schema is documented here** - the real column
structure will only be known once a file is actually opened after acquisition.
Adapter interface design is deferred to that point rather than guessed now.

## Status

**Externally blocked** on all three sources. Not blocking the rest of the
directive - proceeding to Task 8. Exact retained commands above; do not repeat
headless attempts against this same confirmed challenge result.

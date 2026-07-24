# M8 — API v2 + compatibility guard

## DoD

- Routes require one `(compatibility_group, accounting_basis, estimate_status)` triple
- Illegal cross-group → 400; reconciliation view allowed; all responses citation-bearing
- Tests: `test_compatibility_guard.py`, `test_citation_completeness.py`

## Verification

| Test | Result |
|---|---|
| missing triple → 400 | pass |
| partial triple → 400 | pass |
| valid triple → 200 + citations | pass |
| view=reconciliation without triple | pass |
| citation completeness on /v2/facts and /v2/tree | pass |
| Suite | 6 passed |

## Artefacts

- `src/backend/routers/v2/query.py`
- `tests/api/test_compatibility_guard.py`
- `tests/api/test_citation_completeness.py`

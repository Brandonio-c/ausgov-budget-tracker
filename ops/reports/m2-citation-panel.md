# M2 — Citation API + CitationPanel

## DoD

- `GET /v2/facts/{id}/citation` matching Citation contract
- CitationPanel tests: complete citation renders 3 links; quarantined facts never reachable via UI/API

## Verification

| Check | Result |
|---|---|
| `tests/api/test_citation.py` | 3 passed |
| `tests/frontend/test_citation_panel.mjs` | ok (3 link roles present) |
| Quarantined pending id without facts row | 404 |
| Touched `spending.db` / default route | **no** |

## Artefacts

- `src/backend/facts_db.py`
- `src/backend/routers/v2/{__init__,citation,facts}.py`
- `src/frontend/components/CitationPanel/`

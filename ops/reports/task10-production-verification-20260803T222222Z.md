# Task 10 — production deployment and verification

## Deployment

- Backend origin (`ausgov-budget-tracker-backend-1`, Docker container behind
  the vibefactory Cloudflare Tunnel at `ausgov-budget-origin.vibefactory.app`,
  reverse-proxied by the `ausgov-budget-api.vibefactory.app` Worker):
  rebuilt and restarted via `docker compose -f docker-compose.vibefactory.yml
  up --build -d`. `data/facts.db` is bind-mounted read-only directly from
  this checkout, so the Task 8 PBS rebuild was already the live file the
  container reads from before restart; the rebuild picks up all Python code
  changes (Tasks 3, 4, 7).
- Frontend (`ausgov-budget-tracker-frontend-vibefactory`, Cloudflare Worker
  serving the static `next build` export at `vibefactory.app/ausgov-budget-tracker`):
  deployed via `npm run deploy:vibefactory` in `src/frontend`.
- Both confirmed live: `https://ausgov-budget-api.vibefactory.app/api/health`
  → 200; `https://vibefactory.app/ausgov-budget-tracker/` → 200.

## Production audit

`scripts/ops/dashboard_api_audit.py --base-url https://ausgov-budget-api.vibefactory.app`
(`ops/reports/dashboard-api-audit-20260803T222222Z.{json,md}`):

| path | visited_nodes | hard failures |
|---|---:|---:|
| federal_actuals_2024_25 | 298 | 0 |
| federal_budget_latest | 1,643 | 1 (additive_reconciliation, same 0.52%-over Defence "Key cost category / OPERATING" rounding case documented in Task 9) |
| qld_state_actuals_2024_25 | 223 | 0 |
| local_government_actuals_2024_25 | 1,624 | 0 |
| federal_debt_latest | 49 | 0 |
| federal_gdp_ratios_latest | 3 | 0 |

**Total: 1 hard failure**, identical in kind and magnitude to the local
audit's residual - production and local match exactly.

PBS → Statement 6 crosswalk (7/7): social_services, health, ndia, defence,
education, dva_health, dva_welfare - all `reachable`, `citation_ok=True`,
`parent_amount_preserved=True`.

## Manual verification of named production views

Queried directly against `https://ausgov-budget-api.vibefactory.app`:

| view | result |
|---|---|
| Federal Actuals 2024-25 | `federal — 2024-25`, $745.03B |
| Federal Budget | years available through 2029-30 |
| QLD state actuals | `QLD`, $91.22B |
| Local-government actuals | 7 top-level (state) branches |
| Federal debt | $971.44B (2025-26) |
| GDP/ratios | `Australia` node present |
| Social Services / Health / NDIA / Defence / Education / DVA health / DVA welfare PBS detail | all 7 confirmed reachable, non-additive, cited, and amount-preserving via the crosswalk verification above |

Production and local are consistent in every respect checked.

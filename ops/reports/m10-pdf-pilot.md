# M10 — PDF Tier A pilot

## DoD

- Hand CSV for BP1 Statement 6 + one state headline table; page/table locators satisfy Gate 6
- Reconcile vs GFS Table 130; go/no-go recommendation recorded; proceed either way

## Verification

| Source | Published | Locators |
|---|---:|---|
| federal_budget_statement_6_2026_27 (Table 6.3) | 30 | page 225 / Table 6.3 |
| sa_budget_headline_expenses (Total Expenses) | 2 | Budget Statement p.141 |

Gate 6 quarantine: federal=0 SA=0

## Reconcile vs ABS GFS commonwealth_130

{
  "gfs_health_2023_24": [
    [
      "2023-24",
      "Community health services",
      37922000000
    ],
    [
      "2023-24",
      "Public health services",
      7634000000
    ],
    [
      "2023-24",
      "Other health",
      12582000000
    ],
    [
      "2023-24",
      "Total health",
      108856000000
    ]
  ],
  "budget_health_2025_26": 127015000000,
  "gfs_total_recent": [
    [
      "2024-25",
      159277000000
    ],
    [
      "2024-25",
      118155000000
    ],
    [
      "2024-25",
      55729000000
    ],
    [
      "2024-25",
      745029000000
    ],
    [
      "2023-24",
      149946000000
    ]
  ],
  "reconcile_note": "Budget Table 6.3 (estimates, budget_expense) is not additive with ABS GFS Table 4 actuals (actual_expense/gfs). Differences are expected; treat as explained_difference, not error."
}

## Recommendation

**GO for Tier A hand-CSV with page/table locators; NO-GO for unsupervised PDF numeric expansion (Tier B) until a layout-aware extractor + measure-aware reconcile harness exists.**

Proceeding to M11 with Tier A accepted; Tier B not expanded.

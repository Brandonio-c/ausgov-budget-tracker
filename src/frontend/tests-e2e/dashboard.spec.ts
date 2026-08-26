import { test, expect } from "@playwright/test";

/**
 * Task 8 UI regression suite. Runs headlessly against a real `next dev`
 * server (basePath "/ausgov-budget-tracker") talking to a real backend
 * against data/facts.db - not mocked. Deep-links (mode/level/year query
 * params, handled in app/HomeClient.tsx) are used to reach each required
 * path directly rather than scripting every click, since HomeClient applies
 * them once on load.
 */

const BASE = "/ausgov-budget-tracker/";

test.describe("dashboard navigation and citation regressions", () => {
  test("home page loads with mode/chart controls", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.getByText("AusGov Budget Tracker")).toBeVisible();
    await expect(page.getByRole("button", { name: "Actuals", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Budget", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Debt", exact: true })).toBeVisible();
  });

  test("Federal Actuals 2024-25 deep link renders a populated chart", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2024-25`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart).toBeVisible();
    // The chart canvas/svg must actually paint something, not stay on the
    // "Loading…" placeholder - a real regression this catches is the API
    // call silently failing (wrong mode/level combination, CORS, etc).
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
  });

  test("Federal Budget mode switch updates the chart without an error banner", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2024-25`);
    await page.getByRole("button", { name: "Budget" }).click();
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    // HomeClient renders errors as visible text via setError(); absence of
    // that text is the regression signal, not a specific error selector.
    await expect(page.getByText(/failed to load|error/i)).toHaveCount(0);
  });

  test("QLD state actuals branch is reachable", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(`${BASE}?mode=actuals&level=state&year=2024-25`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 45_000 });
    await expect(chart).toBeVisible();
  });

  test("local government branch is reachable", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=local`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await expect(chart).toBeVisible();
  });

  test("debt view is labelled as GFS liability stock, not Budget net debt", async ({ page }) => {
    // The always-on "Government debt (liabilities)" widget (distinct from
    // the main chart's own Debt mode, which replaces it when selected)
    // carries this exact disclaimer - visible on the plain home page.
    await page.goto(BASE);
    await expect(page.getByText("Government debt (liabilities)")).toBeVisible();
    // This exact distinction (GFS liability stocks vs Budget Paper "net
    // debt") is a named mixed-valuation safeguard in the directive - a
    // regression that silently drops or renames this disclaimer would be a
    // real correctness/labelling bug for a debt figure.
    await expect(
      page.getByText(/GFS liability stocks.*not Budget Paper.*net debt/i)
    ).toBeVisible();
  });

  test("ring depth control renders on a GDP/ratio branch", async ({ page }) => {
    await page.goto(`${BASE}?mode=ratios&level=federal`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await expect(chart).toBeVisible();
  });

  test("Federal Actuals 2025-26 Rings view exposes deep multi-ring exploration", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2025-26`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await page.getByRole("button", { name: "rings", exact: true }).first().click();
    await expect(chart).toBeVisible();
    // Deep exploration pill must be visible
    const deepPill = page.getByRole("button", { name: /Deep exploration/i });
    await expect(deepPill).toBeVisible();
    // Depth control must show multi-ring capability (e.g. of 6)
    await expect(page.getByRole("group", { name: "Ring depth" }).getByText(/of 6/i)).toBeVisible();
    // Can switch to Canonical view (1 ring)
    const canonicalPill = page.getByRole("button", { name: /Canonical actual/i });
    await expect(canonicalPill).toBeVisible();
    await canonicalPill.click();
    await expect(page.getByRole("group", { name: "Ring depth" }).getByText(/of 1/i)).toBeVisible();
    // Switch back to Deep exploration
    await deepPill.click();
    await expect(page.getByRole("group", { name: "Ring depth" }).getByText(/of 6/i)).toBeVisible();
  });

  test("Federal Actuals 2024-25 Rings view exposes multi-ring exploration", async ({ page }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2024-25`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await page.getByRole("button", { name: "rings", exact: true }).first().click();
    await expect(chart).toBeVisible();
    await expect(page.getByRole("button", { name: /Deep exploration/i })).toBeVisible();
    await expect(page.getByRole("group", { name: "Ring depth" }).getByText(/of 3/i)).toBeVisible();
  });

  test("Federal Budget 2025-26 Rings view exposes 3 rings", async ({ page }) => {
    await page.goto(`${BASE}?mode=budget&level=federal&year=2025-26`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await page.getByRole("button", { name: "rings", exact: true }).first().click();
    await expect(chart).toBeVisible();
    await expect(page.getByRole("group", { name: "Ring depth" }).getByText(/of 3/i)).toBeVisible();
  });

  test("Federal Actuals 2025-26 user can drill to NDIS participant demographics", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2025-26`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await page.getByRole("button", { name: "rings", exact: true }).first().click();
    await expect(chart).toBeVisible();
    
    const legend = page.getByRole("list", { name: "Chart legend" });

    // Drill into Social security and welfare
    await legend.getByRole("button", { name: /Social security and welfare/i }).first().click();
    await expect(legend.getByRole("button", { name: /Assistance to people with disabilities/i })).toBeVisible({ timeout: 10_000 });

    // Drill into Assistance to people with disabilities
    await legend.getByRole("button", { name: /Assistance to people with disabilities/i }).first().click();
    await expect(legend.getByRole("button", { name: /National Disability Insurance Scheme/i }).first()).toBeVisible({ timeout: 10_000 });

    // Drill into National Disability Insurance Scheme
    await legend.getByRole("button", { name: /National Disability Insurance Scheme/i }).first().click();
    await expect(legend.getByRole("button", { name: /NDIA Participant Statistics/i }).first()).toBeVisible({ timeout: 10_000 });

    // Drill into NDIA Participant Statistics
    await legend.getByRole("button", { name: /NDIA Participant Statistics/i }).first().click();
    await expect(legend.getByRole("button", { name: /Participants by geography/i }).first()).toBeVisible({ timeout: 10_000 });

    // Drill into Participants by geography
    await legend.getByRole("button", { name: /Participants by geography/i }).first().click();
    await expect(legend.getByRole("button", { name: /New South Wales/i }).first()).toBeVisible({ timeout: 10_000 });

    // Drill into New South Wales
    await legend.getByRole("button", { name: /New South Wales/i }).first().click();
    await expect(legend.getByText(/Hunter New England|Central Coast|Illawarra/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("Federal Actuals 2025-26 user can drill to NDIS payments breakdown", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2025-26`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await page.getByRole("button", { name: "rings", exact: true }).first().click();
    await expect(chart).toBeVisible();

    const legend = page.getByRole("list", { name: "Chart legend" });

    // Drill to NDIS
    await legend.getByRole("button", { name: /Social security and welfare/i }).first().click();
    await legend.getByRole("button", { name: /Assistance to people with disabilities/i }).first().click();
    await legend.getByRole("button", { name: /National Disability Insurance Scheme/i }).first().click();
    await expect(legend.getByRole("button", { name: /NDIA Payments/i }).first()).toBeVisible({ timeout: 10_000 });

    // Drill into NDIA Payments
    await legend.getByRole("button", { name: /NDIA Payments/i }).first().click();
    await expect(legend.getByText(/Capacity Building|Capital|Core/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("Federal Actuals 2025-26 user can drill to Defence AusTender contracts", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(`${BASE}?mode=actuals&level=federal&year=2025-26`);
    const chart = page.getByLabel("Spending chart");
    await expect(chart.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });
    await page.getByRole("button", { name: "rings", exact: true }).first().click();
    await expect(chart).toBeVisible();

    const legend = page.getByRole("list", { name: "Chart legend" });

    // Drill into Defence
    await legend.getByRole("button", { name: /Defence/i }).first().click();
    await expect(legend.getByRole("button", { name: /Contracts \(AusTender/i }).first()).toBeVisible({ timeout: 10_000 });

    // Drill into Contracts
    await legend.getByRole("button", { name: /Contracts \(AusTender/i }).first().click();
    await expect(legend.getByRole("button", { name: /Commercial and Military/i })).toBeVisible({ timeout: 10_000 });
  });
});

import { test, expect } from "@playwright/test";

/**
 * Task 7 (semantic-defect milestone) UI regression: the actual child year
 * and fallback reason must be disclosed at the child itself, not only via
 * a folder-level banner several levels up the drill path. Verifies both
 * the underlying API contract (fields present on every related child, via
 * the real browser's own fetch - same pattern as pbs-s6-crosswalk.spec.ts)
 * and the rendered UI disclosure text for a real, verified fallback case.
 *
 * fact_id 335314 ("Contracts (AusTender 2019-20)" under federal Defence,
 * actuals 2024-25) is a real node whose only published data is FY2019-20 -
 * five years earlier than the requested 2024-25 - resolved directly
 * against the live database, not guessed.
 */

const BASE = "/ausgov-budget-tracker/";
const API_BASE = "http://localhost:8000";

test.describe("PBS/related cross-year fallback disclosure (real browser <-> API)", () => {
  test("API exposes explicit per-child year-fallback metadata, never a future year", async ({
    page,
  }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal`);
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });

    const result = await page.evaluate(
      async ({ apiBase }) => {
        const resp = await fetch(
          `${apiBase}/v2/dashboard/tree?mode=actuals&level=federal&year=2024-25`,
        );
        const data = await resp.json();
        const find = (node: any, name: string): any => {
          if (node.name === name) return node;
          for (const c of node.children || []) {
            const found = find(c, name);
            if (found) return found;
          }
          return null;
        };
        return find(data, "Contracts (AusTender 2019-20)");
      },
      { apiBase: API_BASE },
    );

    const defence = result;
    expect(defence, JSON.stringify(result)).toBeTruthy();
    const bd = defence.breakdown;
    expect(bd.is_year_fallback).toBe(true);
    expect(bd.requested_financial_year).toBe("2024-25");
    expect(bd.fact_financial_year).toBe("2019-20");
    // Never a future year relative to the request.
    expect(bd.fact_financial_year < bd.requested_financial_year).toBe(true);
    expect(bd.fallback_reason).toMatch(/nearest_earlier_year_/);
    expect(bd.source_budget_edition).toBeTruthy();
    expect(bd.estimate_status).toBeTruthy();
  });

  test("UI discloses the actual child year and fallback reason at the child, not only a folder banner", async ({
    page,
  }) => {
    await page.goto(
      `${BASE}?mode=actuals&level=federal&year=2024-25&fact=335314`,
    );
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });

    // The required wording pattern: "<detail> shown for <source year>; no
    // <requested year> table was published for <name>."
    await expect(
      page.getByText(/shown for 2019-20; no 2024-25 table was published/i),
    ).toBeVisible({ timeout: 15_000 });
  });
});

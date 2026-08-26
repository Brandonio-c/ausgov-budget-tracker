import { test, expect } from "@playwright/test";

/**
 * Task 7 (semantic-defect milestone) UI regression: the actual child year
 * and fallback reason must be disclosed at the child itself, not only via
 * a folder-level banner several levels up the drill path. Verifies both
 * the underlying API contract (fields present on every related child, via
 * the real browser's own fetch - same pattern as pbs-s6-crosswalk.spec.ts)
 * and the rendered UI disclosure text for a real, verified fallback case.
 *
 * fact_id 597724 ("Support for Industry Service Organisations program"
 * under federal Economic affairs, actuals 2024-25) is a real node whose
 * only published data is FY2023-24 - one year earlier than the requested
 * 2024-25 - resolved directly against the live database, not guessed.
 *
 * This replaced an earlier example under Defence/AusTender contracts
 * (fact_id 335314, FY2019-20 data) after the Federal deep-data mission's
 * Defence loop refreshed AusTender contracts from that stale 2019-20
 * sample to a current (2025-26+) one - since year-fallback only ever
 * looks EARLIER, never later, and actuals mode's own year range tops out
 * at 2025-26, no request in that range can fall back into the refreshed
 * data anymore (a deliberate, correct consequence of using current data,
 * not a defect). The underlying fallback-disclosure mechanism this test
 * verifies is unrelated to which specific source demonstrates it.
 */

import type { BreakdownMeta } from "../lib/types";

interface FallbackNode {
  name: string;
  breakdown: BreakdownMeta;
  children?: FallbackNode[] | null;
}

const BASE = "/ausgov-budget-tracker/";
const API_BASE = "http://localhost:8000";

test.describe("PBS/related cross-year fallback disclosure (real browser <-> API)", () => {
  test("API exposes explicit per-child year-fallback metadata, never a future year", async ({
    page,
  }) => {
    await page.goto(`${BASE}?mode=actuals&level=federal`);
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });

    const result = await page.evaluate(
      async ({ apiBase }): Promise<FallbackNode | null> => {
        const resp = await fetch(
          `${apiBase}/v2/dashboard/tree?mode=actuals&level=federal&year=2024-25`,
        );
        const data = await resp.json();
        type TreeLike = {
          name: string;
          breakdown?: BreakdownMeta;
          children?: TreeLike[] | null;
        };
        const find = (node: TreeLike, name: string): FallbackNode | null => {
          if (node.name === name && node.breakdown) {
            return { name: node.name, breakdown: node.breakdown };
          }
          for (const c of node.children || []) {
            const found = find(c, name);
            if (found) return found;
          }
          return null;
        };
        return find(data, "Support for Industry Service Organisations program");
      },
      { apiBase: API_BASE },
    );

    const node = result;
    expect(node, JSON.stringify(result)).toBeTruthy();
    expect(node).not.toBeNull();
    if (!node) return;
    const bd = node.breakdown;
    expect(bd.is_year_fallback).toBe(true);
    expect(bd.requested_financial_year).toBe("2024-25");
    expect(bd.fact_financial_year).toBe("2023-24");
    // Never a future year relative to the request.
    expect(
      (bd.fact_financial_year ?? "") < (bd.requested_financial_year ?? ""),
    ).toBe(true);
    expect(bd.fallback_reason).toMatch(/nearest_earlier_year_/);
    expect(bd.source_budget_edition).toBeTruthy();
    expect(bd.estimate_status).toBeTruthy();
  });

  test("UI discloses the actual child year and fallback reason at the child, not only a folder banner", async ({
    page,
  }) => {
    await page.goto(
      `${BASE}?mode=actuals&level=federal&year=2024-25&fact=597724`,
    );
    await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });

    // The required wording pattern (banner field, rendered verbatim):
    // "Selected year <requested>; showing <source year>."
    await expect(
      page.getByText(/Selected year 2024-25; showing 2023-24/i),
    ).toBeVisible({ timeout: 15_000 });
  });
});

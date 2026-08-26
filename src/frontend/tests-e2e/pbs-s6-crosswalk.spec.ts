import { test, expect } from "@playwright/test";

/**
 * Task 7 (PBS -> Statement 6 crosswalk milestone) UI regression suite.
 * Verifies the new related_breakdown navigation is actually reachable
 * through the real browser <-> API path (not just a direct server-side
 * check), for the milestone's named representative portfolios plus the
 * DVA health/welfare split. Runs against a real `next build` static
 * export with a real backend against data/facts.db (see
 * playwright.config.ts for why `next dev` cannot be used here).
 *
 * fact_id/year pairs below were resolved directly against the live
 * database (scripts/ops/dashboard_api_audit.py's verify_pbs_s6_crosswalk),
 * not guessed - each is a real Statement 6 node this crosswalk attached a
 * related_breakdown edge to. They are stable as long as the load stays
 * idempotent (verified separately).
 */

const BASE = "/ausgov-budget-tracker/";
const API_BASE = "http://localhost:8000";

const CASES: { label: string; factId: number; year: string }[] = [
  { label: "Social Services", factId: 257892, year: "2029-30" },
  { label: "Health", factId: 257838, year: "2029-30" },
  { label: "NDIA", factId: 602804, year: "2029-30" },
  { label: "Defence", factId: 257718, year: "2029-30" },
  { label: "Education", factId: 257790, year: "2029-30" },
  { label: "DVA health", factId: 602764, year: "2029-30" },
  { label: "DVA welfare", factId: 257850, year: "2029-30" },
];

test.describe("PBS -> Statement 6 crosswalk reachability (real browser <-> API)", () => {
  for (const { label, factId, year } of CASES) {
    test(`${label}: related PBS detail is reachable, non-additive, and cited`, async ({
      page,
    }) => {
      await page.goto(`${BASE}?mode=budget&level=federal`);
      await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 15_000 });

      // Drive /item/{id}/children through the browser's own CORS-enabled
      // fetch, exactly as the frontend does - not a server-side curl.
      const result = await page.evaluate(
        async ({ apiBase, factId, year }) => {
          const resp = await fetch(
            `${apiBase}/v2/dashboard/item/${factId}/children?year=${encodeURIComponent(year)}`,
          );
          const data = await resp.json();
          let relatedBlock: any = null;
          if (data.kind === "related_breakdown") {
            relatedBlock = data;
          } else {
            relatedBlock = (data.children || []).find(
              (c: any) =>
                (c.breakdown && c.breakdown.kind === "related_breakdown") ||
                (c.name || "").includes("Related PBS"),
            );
          }
          if (!relatedBlock) {
            return { ok: false, reason: `no_related_block, kind=${data.kind}` };
          }
          const breakdown = relatedBlock.breakdown || {};
          const children = relatedBlock.children || [];
          const sampleChild = children[0];
          let citationOk = false;
          if (sampleChild && sampleChild.id) {
            const ev = await (
              await fetch(`${apiBase}/v2/dashboard/item/${sampleChild.id}/evidence`)
            ).json();
            citationOk = Boolean(ev.has_source_file || ev.locator);
          }
          return {
            ok: true,
            banner: breakdown.banner || "",
            childCount: children.length,
            citationOk,
          };
        },
        { apiBase: API_BASE, factId, year },
      );

      expect(result.ok, JSON.stringify(result)).toBe(true);
      expect(result.banner).toContain("must not be summed");
      expect(result.childCount).toBeGreaterThan(0);
      expect(result.citationOk).toBe(true);
    });
  }
});

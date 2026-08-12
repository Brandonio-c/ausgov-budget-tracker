"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiV2, Citation } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";
import { appHref } from "@/lib/searchDisplay";

const PAGE_SIZE = 200;

// This scope (compatibility_group=commitment / accounting_basis=commitment /
// estimate_status=contract) is genuinely shared by federal AusTender and
// three state contract-disclosure sources - they are safely additive (same
// compatibility group), but a page titled plainly "Contracts explorer" would
// mislead a reader into assuming this is federal AusTender data specifically
// (as every sibling family page - PBS, grants, VIC, ACT - is single-source
// or explicitly source-key-scoped). The breakdown below discloses the real
// jurisdiction mix instead of hiding it.
const SOURCE_LABELS: Record<string, string> = {
  federal_austender_contracts: "Federal (AusTender)",
  nsw_procurement_ocds_registry: "NSW (Procurement OCDS)",
  nt_awarded_government_contracts: "NT (Awarded government contracts)",
  qld_contract_disclosure_agency_datasets: "QLD (Contract disclosure)",
};

function ContractsExplorerInner() {
  const searchParams = useSearchParams();
  const [year, setYear] = useState(searchParams.get("year") || "2024-25");
  const [filter, setFilter] = useState(searchParams.get("q") || "");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<
    Array<{ name: string; value: number; id: number; citation: Citation }>
  >([]);
  const [selected, setSelected] = useState<Citation | null>(null);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [totalValue, setTotalValue] = useState<number | null>(null);
  const [sourceBreakdown, setSourceBreakdown] = useState<
    Array<{ source_key: string; count: number; value: number }>
  >([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    const y = searchParams.get("year");
    const q = searchParams.get("q");
    if (y) setYear(y);
    if (q) setFilter(q);
  }, [searchParams]);

  // Fetch the first page whenever the requested year changes. The list is
  // server-truncated per page but the *scope* (year) totals below always
  // reflect every contract for that year, not just what has been loaded
  // into the browser so far - never present a partial-page sum as the
  // family total. State updates happen only inside the fetch callback
  // (not synchronously in the effect body) so a year switch replaces the
  // previous year's rows/totals/cursor together, atomically, once the new
  // data arrives.
  useEffect(() => {
    apiV2
      .tree({
        compatibility_group: "commitment",
        accounting_basis: "commitment",
        estimate_status: "contract",
        financial_year: year,
        limit: PAGE_SIZE,
      })
      .then((tree) => {
        const kids = tree.children || [];
        setRows(kids);
        setTotalCount(tree.total_count);
        setTotalValue(tree.total_value);
        setSourceBreakdown(tree.source_breakdown || []);
        setNextCursor(tree.next_cursor);
        const fact = searchParams.get("fact");
        const match = fact ? kids.find((r) => String(r.id) === fact) : kids[0];
        setSelected(match?.citation ?? kids[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year]);

  const loadMore = () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    apiV2
      .tree({
        compatibility_group: "commitment",
        accounting_basis: "commitment",
        estimate_status: "contract",
        financial_year: year,
        limit: PAGE_SIZE,
        cursor: nextCursor,
      })
      .then((tree) => {
        setRows((prev) => [...prev, ...(tree.children || [])]);
        setNextCursor(tree.next_cursor);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingMore(false));
  };

  // The search filter only matches contracts already loaded into the
  // browser - it is not a server-side search over the full scope. "Load
  // all" (below) fetches every remaining page so the filter can cover the
  // complete year's contracts when needed.
  const visible = filter
    ? rows.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : rows;
  const allLoaded = nextCursor === null && totalCount !== null;

  return (
    <main className="mx-auto max-w-5xl p-6" data-explorer="contracts">
      <h1 className="text-2xl font-semibold">Contracts explorer</h1>
      <p className="mt-2 text-sm opacity-80">
        Compatibility group <code>commitment</code> / contract values (API v2).
        This combines federal AusTender contract notices with state contract
        disclosure registers (NSW, NT, QLD) that publish on the same
        compatible basis - it is <strong>not</strong> federal-only. See the
        per-jurisdiction split below before treating a total as one
        government&apos;s contracting activity. For GFS liability stocks use{" "}
        <a className="underline" href={appHref("/explorers/gfs?view=liabilities")}>
          GFS explorer → Liabilities
        </a>{" "}
        or the Debt mode on Breakdown / Combined / Timeline.
      </p>
      <DashboardNav />
      <DebtNav />
      <div className="mt-4 flex flex-wrap gap-3">
        <label className="block text-sm">
          Financial year{" "}
          <input
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Filter{" "}
          <input
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search contracts…"
          />
        </label>
      </div>
      {error ? <p className="mt-4 text-red-600">{error}</p> : null}
      {totalCount !== null ? (
        <p className="mt-4 text-sm opacity-80">
          {totalCount.toLocaleString("en-AU")} contracts for {year}, total value{" "}
          {totalValue?.toLocaleString("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 })}
          {" — "}
          {rows.length.toLocaleString("en-AU")} loaded
          {filter ? ` (${visible.length.toLocaleString("en-AU")} match the filter)` : ""}.
        </p>
      ) : null}
      {sourceBreakdown.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs opacity-70">
          {sourceBreakdown.map((b) => (
            <li key={b.source_key}>
              {SOURCE_LABELS[b.source_key] || b.source_key}:{" "}
              {b.count.toLocaleString("en-AU")} (
              {b.value.toLocaleString("en-AU", {
                style: "currency",
                currency: "AUD",
                maximumFractionDigits: 0,
              })}
              )
            </li>
          ))}
        </ul>
      ) : null}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div className="max-h-[70vh] overflow-auto">
          <ul className="space-y-2">
            {visible.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className="text-left underline"
                  onClick={() => setSelected(r.citation)}
                >
                  {r.name.slice(0, 120)} — {r.value?.toLocaleString("en-AU")}
                </button>
              </li>
            ))}
          </ul>
          {nextCursor ? (
            <button
              type="button"
              className="mt-4 border px-3 py-1 text-sm dark:border-white/20"
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading…" : `Load next ${PAGE_SIZE}`}
            </button>
          ) : allLoaded ? (
            <p className="mt-4 text-xs opacity-60">All {totalCount?.toLocaleString("en-AU")} contracts loaded.</p>
          ) : null}
        </div>
        <CitationPanel citation={selected} />
      </div>
    </main>
  );
}

export default function ContractsExplorerPage() {
  return (
    <Suspense fallback={<main className="p-6 text-sm text-zinc-500">Loading…</main>}>
      <ContractsExplorerInner />
    </Suspense>
  );
}

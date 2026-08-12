"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiV2, Citation } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";

const PAGE_SIZE = 200;

function ActInvoicesExplorerInner() {
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
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  // year/filter are seeded from the URL once at mount (useState initializer
  // above); this page does not additionally re-sync from later searchParams
  // changes, to avoid a setState-in-effect call.

  // Fetch the first page whenever the requested year changes. The list is
  // server-truncated per page but the *scope* (year) totals below always
  // reflect every notifiable invoice for that year, not just what has been
  // loaded into the browser so far - never present a partial-page sum as
  // the family total. State updates happen only inside the fetch callback
  // so a year switch replaces the previous year's rows/totals/cursor
  // together, atomically.
  useEffect(() => {
    apiV2
      .tree({
        compatibility_group: "cash_outflow",
        accounting_basis: "cash",
        estimate_status: "invoice",
        financial_year: year,
        limit: PAGE_SIZE,
      })
      .then((tree) => {
        const kids = tree.children || [];
        setRows(kids);
        setTotalCount(tree.total_count);
        setTotalValue(tree.total_value);
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
        compatibility_group: "cash_outflow",
        accounting_basis: "cash",
        estimate_status: "invoice",
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

  // The search filter only matches invoices already loaded into the
  // browser - it is not a server-side search over the full scope.
  const visible = filter
    ? rows.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : rows;
  const allLoaded = nextCursor === null && totalCount !== null;

  return (
    <main className="mx-auto max-w-5xl p-6" data-explorer="act-invoices">
      <h1 className="text-2xl font-semibold">ACT notifiable invoices</h1>
      <p className="mt-2 text-sm opacity-80">
        ACT Government notifiable invoices register (API v2, compatibility group{" "}
        <code>cash_outflow</code>, estimate status <code>invoice</code>). Each row is a
        cash-outflow payment on an accounting-cash basis - a distinct measure from accrual
        expense, and never additive to the ACT&apos;s accrual expenditure in the annual
        tree. The label is agency / supplier-or-description as published.
      </p>
      <DashboardNav />
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
            placeholder="Search invoices…"
          />
        </label>
      </div>
      {error ? <p className="mt-4 text-red-600">{error}</p> : null}
      {totalCount !== null ? (
        <p className="mt-4 text-sm opacity-80">
          {totalCount.toLocaleString("en-AU")} invoices for {year}, total value{" "}
          {totalValue?.toLocaleString("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 })}
          {" — "}
          {rows.length.toLocaleString("en-AU")} loaded
          {filter ? ` (${visible.length.toLocaleString("en-AU")} match the filter)` : ""}.
        </p>
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
            <p className="mt-4 text-xs opacity-60">All {totalCount?.toLocaleString("en-AU")} invoices loaded.</p>
          ) : null}
        </div>
        <CitationPanel citation={selected} />
      </div>
    </main>
  );
}

export default function ActInvoicesExplorerPage() {
  return (
    <Suspense fallback={<main className="p-6 text-sm text-zinc-500">Loading…</main>}>
      <ActInvoicesExplorerInner />
    </Suspense>
  );
}

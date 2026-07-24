"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiV2, Citation } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";

type GfsView = "expenses" | "liabilities";

function GfsExplorerInner() {
  const searchParams = useSearchParams();
  const [view, setView] = useState<GfsView>(
    searchParams.get("view") === "liabilities" ? "liabilities" : "expenses",
  );
  const [year, setYear] = useState("2023-24");
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<
    Array<{ name: string; value: number; id: number; citation: Citation }>
  >([]);
  const [selected, setSelected] = useState<Citation | null>(null);

  useEffect(() => {
    const v = searchParams.get("view");
    if (v === "liabilities" || v === "expenses") setView(v);
  }, [searchParams]);

  useEffect(() => {
    const query =
      view === "liabilities"
        ? {
            compatibility_group: "gfs_liability",
            accounting_basis: "gfs",
            estimate_status: "actual",
            financial_year: year,
            limit: 200,
          }
        : {
            compatibility_group: "actual_expense",
            accounting_basis: "gfs",
            estimate_status: "actual",
            financial_year: year,
            limit: 200,
          };
    apiV2
      .tree(query)
      .then((tree) => {
        setRows(tree.children || []);
        setSelected(tree.children?.[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [year, view]);

  const visible = filter
    ? rows.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : rows;

  return (
    <main className="mx-auto max-w-5xl p-6" data-explorer="gfs">
      <h1 className="text-2xl font-semibold">GFS / jurisdiction explorer</h1>
      <p className="mt-2 text-sm opacity-80">
        {view === "liabilities" ? (
          <>
            Compatibility group <code>gfs_liability</code> (ABS Table_3 balance-sheet stocks).
          </>
        ) : (
          <>
            Compatibility group <code>actual_expense</code> on GFS basis (API v2).
          </>
        )}
      </p>
      <DashboardNav />
      {view === "liabilities" ? <DebtNav /> : null}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <div className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
          {(
            [
              ["expenses", "Expenses"],
              ["liabilities", "Liabilities"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setView(id)}
              className={`px-3 py-1.5 text-sm font-medium ${
                view === id
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "bg-white text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
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
            placeholder="Filter rows…"
          />
        </label>
      </div>
      {error ? <p className="mt-4 text-red-600">{error}</p> : null}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <ul className="max-h-[70vh] space-y-2 overflow-auto">
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
        <CitationPanel citation={selected} />
      </div>
    </main>
  );
}

export default function GfsExplorerPage() {
  return (
    <Suspense fallback={<main className="p-6 text-sm opacity-70">Loading…</main>}>
      <GfsExplorerInner />
    </Suspense>
  );
}

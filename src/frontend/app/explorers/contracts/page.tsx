"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiV2, Citation } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";
import { appHref } from "@/lib/searchDisplay";

function ContractsExplorerInner() {
  const searchParams = useSearchParams();
  const [year, setYear] = useState(searchParams.get("year") || "2024-25");
  const [filter, setFilter] = useState(searchParams.get("q") || "");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<
    Array<{ name: string; value: number; id: number; citation: Citation }>
  >([]);
  const [selected, setSelected] = useState<Citation | null>(null);

  useEffect(() => {
    const y = searchParams.get("year");
    const q = searchParams.get("q");
    if (y) setYear(y);
    if (q) setFilter(q);
  }, [searchParams]);

  useEffect(() => {
    apiV2
      .tree({
        compatibility_group: "commitment",
        accounting_basis: "commitment",
        estimate_status: "contract",
        financial_year: year,
        limit: 200,
      })
      .then((tree) => {
        const kids = tree.children || [];
        setRows(kids);
        const fact = searchParams.get("fact");
        const match = fact
          ? kids.find((r) => String(r.id) === fact)
          : filter
            ? kids.find((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
            : kids[0];
        setSelected(match?.citation ?? kids[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [year, filter, searchParams]);

  const visible = filter
    ? rows.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()))
    : rows;

  return (
    <main className="mx-auto max-w-5xl p-6" data-explorer="contracts">
      <h1 className="text-2xl font-semibold">Contracts explorer</h1>
      <p className="mt-2 text-sm opacity-80">
        Compatibility group <code>commitment</code> / contract values (API v2).
        For GFS liability stocks use{" "}
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

export default function ContractsExplorerPage() {
  return (
    <Suspense fallback={<main className="p-6 text-sm text-zinc-500">Loading…</main>}>
      <ContractsExplorerInner />
    </Suspense>
  );
}

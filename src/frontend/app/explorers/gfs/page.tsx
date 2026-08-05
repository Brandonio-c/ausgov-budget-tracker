"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiV2, apiVicAfs, Citation, VicAfsCitation, VicAfsMeasureInfo } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";

type GfsView = "expenses" | "liabilities" | "vic_afs";

function VicAfsCitationBox({ citation }: { citation: VicAfsCitation | null }) {
  if (!citation) {
    return (
      <aside className="rounded-md border border-black/10 p-4 text-sm text-zinc-500 dark:border-white/10 dark:text-zinc-400">
        No citation
      </aside>
    );
  }
  return (
    <aside className="rounded-md border border-black/10 p-4 dark:border-white/10">
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Source citation</h3>
      <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-300">
        Locator: <code className="break-all">{citation.locator}</code>
      </p>
      {citation.cached_copy_path ? (
        <p className="mt-1 break-all text-xs text-zinc-500 dark:text-zinc-400">{citation.cached_copy_path}</p>
      ) : null}
    </aside>
  );
}

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

  const [vicAfsMeasures, setVicAfsMeasures] = useState<VicAfsMeasureInfo[]>([]);
  const [vicAfsMeasureType, setVicAfsMeasureType] = useState("vic_afs_revenue");
  const [vicAfsRows, setVicAfsRows] = useState<
    Array<{ name: string; value: number; id: string; citation: VicAfsCitation; financial_year: string; period_end: string }>
  >([]);
  const [vicAfsSelected, setVicAfsSelected] = useState<VicAfsCitation | null>(null);

  useEffect(() => {
    const v = searchParams.get("view");
    if (v === "liabilities" || v === "expenses" || v === "vic_afs") setView(v);
  }, [searchParams]);

  useEffect(() => {
    apiVicAfs.measures().then(setVicAfsMeasures).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (view !== "vic_afs") return;
    apiVicAfs
      .series(vicAfsMeasureType)
      .then((resp) => {
        const mapped = resp.facts.map((f) => ({
          name: `${f.financial_year} — ${f.label}`,
          value: f.amount_aud,
          id: `${f.measure_type}|${f.financial_year}`,
          financial_year: f.financial_year,
          period_end: f.period_end,
          citation: f.citation,
        }));
        setVicAfsRows(mapped);
        setVicAfsSelected(mapped[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [view, vicAfsMeasureType]);

  useEffect(() => {
    if (view === "vic_afs") return;
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
        ) : view === "vic_afs" ? (
          <>
            Victorian Department of Treasury and Finance&apos;s own departmental annual financial
            statements (2024-25) - department-level detail, not whole-of-Victorian-government. Each
            measure has its own dedicated compatibility group; never summed into any additive tree.
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
              ["vic_afs", "VIC AFS"],
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
        {view === "vic_afs" ? (
          <label className="block text-sm">
            Measure{" "}
            <select
              className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
              value={vicAfsMeasureType}
              onChange={(e) => setVicAfsMeasureType(e.target.value)}
            >
              {vicAfsMeasures.map((m) => (
                <option key={m.measure_type} value={m.measure_type}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <>
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
          </>
        )}
      </div>
      {view === "vic_afs" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {(() => {
            const info = vicAfsMeasures.find((m) => m.measure_type === vicAfsMeasureType);
            if (!info) return null;
            const isStock = info.flow_or_stock === "stock" || info.flow_or_stock === "stock_balance";
            return (
              <>
                <span
                  className={`rounded-full px-2 py-0.5 font-medium ${
                    isStock
                      ? "bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-100"
                      : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                  }`}
                >
                  {isStock ? "Stock (point-in-time)" : "Flow (financial year)"}
                </span>
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
                  Source vintage: current (single acquired 2024-25 edition)
                </span>
              </>
            );
          })()}
        </div>
      ) : null}
      {error ? <p className="mt-4 text-red-600">{error}</p> : null}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {view === "vic_afs" ? (
          <>
            <ul className="max-h-[70vh] space-y-2 overflow-auto">
              {vicAfsRows.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="text-left underline"
                    onClick={() => setVicAfsSelected(r.citation)}
                  >
                    {r.name} (as at {r.period_end}) — {r.value.toLocaleString("en-AU")}
                  </button>
                </li>
              ))}
            </ul>
            <VicAfsCitationBox citation={vicAfsSelected} />
          </>
        ) : (
          <>
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
          </>
        )}
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

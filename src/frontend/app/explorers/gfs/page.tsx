"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  apiQldMyfer,
  apiQldRsf,
  apiTasGgs,
  apiV2,
  apiVicAfs,
  apiVicBpo,
  apiVicBpoSoceAdmin,
  Citation,
  QldMyferCitation,
  QldMyferMeasureInfo,
  QldRsfCitation,
  QldRsfMeasureInfo,
  TasGgsCitation,
  TasGgsMeasureInfo,
  VicAfsCitation,
  VicAfsMeasureInfo,
  VicBpoCitation,
  VicBpoMeasureInfo,
} from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";
import { formatApiAvailability } from "@/lib/availability";

type GfsView = "expenses" | "liabilities" | "vic_afs" | "vic_bpo" | "tas_ggs" | "qld_rsf" | "qld_myfer";

function SimpleCitationBox({
  citation,
}: {
  citation: VicAfsCitation | VicBpoCitation | TasGgsCitation | QldRsfCitation | QldMyferCitation | null;
}) {
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
    Array<{ name: string; value: number; id: string; citation: VicAfsCitation; financial_year: string; estimate_status: string; period_end: string }>
  >([]);
  const [vicAfsSelected, setVicAfsSelected] = useState<VicAfsCitation | null>(null);

  const [vicBpoMeasures, setVicBpoMeasures] = useState<VicBpoMeasureInfo[]>([]);
  const [vicBpoMeasureType, setVicBpoMeasureType] = useState("vic_bpo_revenue");
  const [vicBpoRows, setVicBpoRows] = useState<
    Array<{ name: string; value: number; id: string; citation: VicBpoCitation; financial_year: string; estimate_status: string; period_end: string }>
  >([]);
  const [vicBpoSelected, setVicBpoSelected] = useState<VicBpoCitation | null>(null);
  // SOCE/Admin measure_types served by the separate vic-bpo-soce-admin
  // endpoint (see api.ts) - tracked so the shared vic_bpo dropdown/series
  // effect below can route each selected measure to the right API.
  const [vicBpoSoceAdminTypes, setVicBpoSoceAdminTypes] = useState<Set<string>>(new Set());

  const [tasGgsMeasures, setTasGgsMeasures] = useState<TasGgsMeasureInfo[]>([]);
  const [tasGgsMeasureType, setTasGgsMeasureType] = useState("tas_ggs_revenue");
  const [tasGgsRows, setTasGgsRows] = useState<
    Array<{ name: string; value: number; id: string; citation: TasGgsCitation; financial_year: string; estimate_status: string; period_end: string }>
  >([]);
  const [tasGgsSelected, setTasGgsSelected] = useState<TasGgsCitation | null>(null);

  const [qldRsfMeasures, setQldRsfMeasures] = useState<QldRsfMeasureInfo[]>([]);
  const [qldRsfMeasureType, setQldRsfMeasureType] = useState("qld_rsf_revenue");
  const [qldRsfRows, setQldRsfRows] = useState<
    Array<{ name: string; value: number; id: string; citation: QldRsfCitation; financial_year: string; estimate_status: string; period_end: string }>
  >([]);
  const [qldRsfSelected, setQldRsfSelected] = useState<QldRsfCitation | null>(null);

  const [qldMyferMeasures, setQldMyferMeasures] = useState<QldMyferMeasureInfo[]>([]);
  const [qldMyferMeasureType, setQldMyferMeasureType] = useState("qld_myfer_revenue");
  const [qldMyferRows, setQldMyferRows] = useState<
    Array<{ name: string; value: number; id: string; citation: QldMyferCitation; financial_year: string; estimate_status: string; source_budget_year: string; period_end: string }>
  >([]);
  const [qldMyferSelected, setQldMyferSelected] = useState<QldMyferCitation | null>(null);

  useEffect(() => {
    const v = searchParams.get("view");
    if (
      v === "liabilities" ||
      v === "expenses" ||
      v === "vic_afs" ||
      v === "vic_bpo" ||
      v === "tas_ggs" ||
      v === "qld_rsf" ||
      v === "qld_myfer"
    )
      setView(v);
  }, [searchParams]);

  useEffect(() => {
    apiVicAfs.measures().then(setVicAfsMeasures).catch((e: Error) => setError(e.message));
    Promise.all([apiVicBpo.measures(), apiVicBpoSoceAdmin.measures()])
      .then(([bpo, soceAdmin]) => {
        setVicBpoMeasures([...bpo, ...soceAdmin]);
        setVicBpoSoceAdminTypes(new Set(soceAdmin.map((m) => m.measure_type)));
      })
      .catch((e: Error) => setError(e.message));
    apiTasGgs.measures().then(setTasGgsMeasures).catch((e: Error) => setError(e.message));
    apiQldRsf.measures().then(setQldRsfMeasures).catch((e: Error) => setError(e.message));
    apiQldMyfer.measures().then(setQldMyferMeasures).catch((e: Error) => setError(e.message));
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
          estimate_status: f.estimate_status,
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
    if (view !== "vic_bpo") return;
    const client = vicBpoSoceAdminTypes.has(vicBpoMeasureType) ? apiVicBpoSoceAdmin : apiVicBpo;
    client
      .series(vicBpoMeasureType)
      .then((resp) => {
        const mapped = resp.facts.map((f) => ({
          name: `${f.estimate_status === "actual" ? "Actual" : "Budget"} — ${f.label}`,
          value: f.amount_aud,
          id: `${f.measure_type}|${f.estimate_status}`,
          financial_year: f.financial_year,
          estimate_status: f.estimate_status,
          period_end: f.period_end,
          citation: f.citation,
        }));
        setVicBpoRows(mapped);
        setVicBpoSelected(mapped[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [view, vicBpoMeasureType, vicBpoSoceAdminTypes]);

  useEffect(() => {
    if (view !== "tas_ggs") return;
    apiTasGgs
      .series(tasGgsMeasureType)
      .then((resp) => {
        const mapped = resp.facts.map((f) => ({
          name: `${f.financial_year} (${f.estimate_status.replace("_", " ")}) — ${f.label}`,
          value: f.amount_aud,
          id: `${f.measure_type}|${f.financial_year}`,
          financial_year: f.financial_year,
          estimate_status: f.estimate_status,
          period_end: f.period_end,
          citation: f.citation,
        }));
        setTasGgsRows(mapped);
        setTasGgsSelected(mapped[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [view, tasGgsMeasureType]);

  useEffect(() => {
    if (view !== "qld_rsf") return;
    apiQldRsf
      .series(qldRsfMeasureType)
      .then((resp) => {
        const mapped = resp.facts.map((f) => ({
          name: `${f.financial_year} (${f.estimate_status.replace("_", " ")}) — ${f.label}`,
          value: f.amount_aud,
          id: `${f.measure_type}|${f.financial_year}|${f.estimate_status}`,
          financial_year: f.financial_year,
          estimate_status: f.estimate_status,
          period_end: f.period_end,
          citation: f.citation,
        }));
        setQldRsfRows(mapped);
        setQldRsfSelected(mapped[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [view, qldRsfMeasureType]);

  useEffect(() => {
    if (view !== "qld_myfer") return;
    apiQldMyfer
      .series(qldMyferMeasureType)
      .then((resp) => {
        const mapped = resp.facts.map((f) => ({
          name: `${f.financial_year} MYFER (${f.estimate_status.replace("_", " ")}) — ${f.label}`,
          value: f.amount_aud,
          id: `${f.measure_type}|${f.source_budget_year}|${f.financial_year}`,
          financial_year: f.financial_year,
          estimate_status: f.estimate_status,
          source_budget_year: f.source_budget_year,
          period_end: f.period_end,
          citation: f.citation,
        }));
        setQldMyferRows(mapped);
        setQldMyferSelected(mapped[0]?.citation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [view, qldMyferMeasureType]);

  useEffect(() => {
    if (view === "vic_afs" || view === "vic_bpo" || view === "tas_ggs" || view === "qld_rsf" || view === "qld_myfer") return;
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
            statements - department-level detail, not whole-of-Victorian-government. Each
            measure has its own dedicated compatibility group; never summed into any additive tree.
          </>
        ) : view === "vic_bpo" ? (
          <>
            Victorian Department of Treasury and Finance&apos;s own Budget Portfolio Outcomes
            - an actual-vs-budget variance comparison, not an assumed multi-year
            series. Includes the department&apos;s own controlled-operations measures (Operating
            Statement / Balance Sheet / Cash Flow Statement) plus administered items and equity
            movements (Admin / Statement of Changes in Equity) - each on its own dedicated
            compatibility group; never conflated with each other, with VIC AFS above, or with any
            whole-of-government total.
          </>
        ) : view === "tas_ggs" ? (
          <>
            Tasmanian Department of Treasury and Finance&apos;s own General Government Sector Key
            Fiscal Measures Time Series - a genuine multi-year series whose API reports each
            year carrying one vintage (actual, revised estimate, or forward estimate). Never
            conflated with the ABS&apos;s own independently-compiled GFS series for Tasmania - a
            different publisher and methodology, despite similar-sounding measure names.
          </>
        ) : view === "qld_rsf" ? (
          <>
            Queensland Treasury&apos;s own Report on State Finances - &quot;Key UPF Financial
            Aggregates&quot; table, General Government Sector only. Each API-reported year can carry
            two vintages: <code>estimated actual</code> (the outcome as projected in
            a later budget-cycle document) and <code>actual</code> (the audited outcome) - a
            different vintage concept from TAS&apos;s budget/actual pair. Never conflated with the
            ABS&apos;s own independently-compiled GFS series for Queensland.
          </>
        ) : view === "qld_myfer" ? (
          <>
            Queensland Treasury&apos;s Mid-Year Fiscal and Economic Review, General Government
            Sector key fiscal aggregates. These are current-year <code>revised estimates</code>,
            not audited RSF actuals. The publication vintage, financial-year period, flow/balance
            status, and citation remain visible; MYFER is never merged into annual additive trees.
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
              ["vic_bpo", "VIC BPO"],
              ["tas_ggs", "TAS GGS"],
              ["qld_rsf", "QLD RSF"],
              ["qld_myfer", "QLD MYFER"],
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
        ) : view === "vic_bpo" ? (
          <label className="block text-sm">
            Measure{" "}
            <select
              className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
              value={vicBpoMeasureType}
              onChange={(e) => setVicBpoMeasureType(e.target.value)}
            >
              {vicBpoMeasures.map((m) => (
                <option key={m.measure_type} value={m.measure_type}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        ) : view === "tas_ggs" ? (
          <label className="block text-sm">
            Measure{" "}
            <select
              className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
              value={tasGgsMeasureType}
              onChange={(e) => setTasGgsMeasureType(e.target.value)}
            >
              {tasGgsMeasures.map((m) => (
                <option key={m.measure_type} value={m.measure_type}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        ) : view === "qld_rsf" ? (
          <label className="block text-sm">
            Measure{" "}
            <select
              className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
              value={qldRsfMeasureType}
              onChange={(e) => setQldRsfMeasureType(e.target.value)}
            >
              {qldRsfMeasures.map((m) => (
                <option key={m.measure_type} value={m.measure_type}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        ) : view === "qld_myfer" ? (
          <label className="block text-sm">
            Measure{" "}
            <select
              className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
              value={qldMyferMeasureType}
              onChange={(e) => setQldMyferMeasureType(e.target.value)}
            >
              {qldMyferMeasures.map((m) => (
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
                  {formatApiAvailability(vicAfsRows)}
                </span>
              </>
            );
          })()}
        </div>
      ) : view === "vic_bpo" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {(() => {
            const info = vicBpoMeasures.find((m) => m.measure_type === vicBpoMeasureType);
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
                  {formatApiAvailability(vicBpoRows)}
                </span>
              </>
            );
          })()}
        </div>
      ) : view === "tas_ggs" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {(() => {
            const info = tasGgsMeasures.find((m) => m.measure_type === tasGgsMeasureType);
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
                  {formatApiAvailability(tasGgsRows)}
                </span>
              </>
            );
          })()}
        </div>
      ) : view === "qld_rsf" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {(() => {
            const info = qldRsfMeasures.find((m) => m.measure_type === qldRsfMeasureType);
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
                  {formatApiAvailability(qldRsfRows)}
                </span>
              </>
            );
          })()}
        </div>
      ) : view === "qld_myfer" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          {(() => {
            const info = qldMyferMeasures.find((m) => m.measure_type === qldMyferMeasureType);
            if (!info) return null;
            return (
              <>
                <span className="rounded-full bg-blue-100 px-2 py-0.5 font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                  {info.flow_or_stock === "flow" ? "Flow (financial year)" : "Balance (financial year)"}
                </span>
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
                  {formatApiAvailability(qldMyferRows)}
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
            <SimpleCitationBox citation={vicAfsSelected} />
          </>
        ) : view === "vic_bpo" ? (
          <>
            <ul className="max-h-[70vh] space-y-2 overflow-auto">
              {vicBpoRows.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="text-left underline"
                    onClick={() => setVicBpoSelected(r.citation)}
                  >
                    {r.name} (as at {r.period_end}) — {r.value.toLocaleString("en-AU")}
                  </button>
                </li>
              ))}
            </ul>
            <SimpleCitationBox citation={vicBpoSelected} />
          </>
        ) : view === "tas_ggs" ? (
          <>
            <ul className="max-h-[70vh] space-y-2 overflow-auto">
              {tasGgsRows.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="text-left underline"
                    onClick={() => setTasGgsSelected(r.citation)}
                  >
                    {r.name} (as at {r.period_end}) — {r.value.toLocaleString("en-AU")}
                  </button>
                </li>
              ))}
            </ul>
            <SimpleCitationBox citation={tasGgsSelected} />
          </>
        ) : view === "qld_rsf" ? (
          <>
            <ul className="max-h-[70vh] space-y-2 overflow-auto">
              {qldRsfRows.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="text-left underline"
                    onClick={() => setQldRsfSelected(r.citation)}
                  >
                    {r.name} (as at {r.period_end}) — {r.value.toLocaleString("en-AU")}
                  </button>
                </li>
              ))}
            </ul>
            <SimpleCitationBox citation={qldRsfSelected} />
          </>
        ) : view === "qld_myfer" ? (
          <>
            <ul className="max-h-[70vh] space-y-2 overflow-auto">
              {qldMyferRows.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="text-left underline"
                    onClick={() => setQldMyferSelected(r.citation)}
                  >
                    {r.name} (period ending {r.period_end}; vintage {r.source_budget_year}) —{" "}
                    {r.value.toLocaleString("en-AU")}
                  </button>
                </li>
              ))}
            </ul>
            <SimpleCitationBox citation={qldMyferSelected} />
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

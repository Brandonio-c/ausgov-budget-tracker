"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { apiMfs, MfsCitation, MfsFact, MfsMeasureInfo } from "@/lib/api";
import { formatAudFull } from "@/lib/colors";
import { useDarkMode } from "@/lib/useDarkMode";
import DashboardNav from "@/components/DashboardNav";
import MfsLineChart, { MfsChartSeries } from "@/components/MfsLineChart";

const MONTH_ORDER = [
  "July", "August", "September", "October", "November", "December",
  "January", "February", "March", "April", "May",
];

function periodDisclosure(fact: MfsFact | undefined): string {
  if (!fact) return "";
  if (fact.flow_or_stock === "stock" || fact.flow_or_stock === "stock_balance") {
    return `Point-in-time stock at ${fact.period_end}`;
  }
  return `Year-to-date flow through ${fact.reporting_month} ${fact.financial_year} (month ${fact.elapsed_months} of 12 - this series never reaches a 12th/June column, so it is never a full-year annual actual)`;
}

function seriesToChart(facts: MfsFact[], name: string): MfsChartSeries {
  const byMonth = new Map(facts.map((f) => [f.reporting_month, f]));
  return {
    name,
    points: MONTH_ORDER.filter((m) => byMonth.has(m)).map((m) => {
      const f = byMonth.get(m)!;
      return { x: m, y: f.amount_aud, factId: `${f.financial_year}|${f.reporting_month}|${f.measure_type}` };
    }),
  };
}

function CitationBox({ citation }: { citation: MfsCitation | null }) {
  if (!citation) {
    return <p className="text-sm opacity-60">Click a data point to see its source citation.</p>;
  }
  return (
    <div className="rounded-md border border-black/10 p-3 text-sm dark:border-white/10">
      <div className="font-medium">Source citation</div>
      <div className="mt-1 break-words opacity-80">{citation.locator}</div>
      {citation.cached_copy_path ? (
        <div className="mt-1 break-words text-xs opacity-60">{citation.cached_copy_path}</div>
      ) : null}
    </div>
  );
}

function MfsExplorerInner() {
  const dark = useDarkMode();
  const [measures, setMeasures] = useState<MfsMeasureInfo[]>([]);
  const [measureType, setMeasureType] = useState("mfs_ytd_revenue");
  const [years, setYears] = useState<string[]>([]);
  const [year, setYear] = useState("");
  const [priorYear, setPriorYear] = useState("");
  const [reportingMonth, setReportingMonth] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const [primaryFacts, setPrimaryFacts] = useState<MfsFact[]>([]);
  const [revExpChart, setRevExpChart] = useState<MfsChartSeries[]>([]);
  const [balanceChart, setBalanceChart] = useState<MfsChartSeries[]>([]);
  const [stockChart, setStockChart] = useState<MfsChartSeries[]>([]);
  const [yoyChart, setYoyChart] = useState<MfsChartSeries[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<MfsCitation | null>(null);

  useEffect(() => {
    apiMfs.measures().then(setMeasures).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    apiMfs
      .years(measureType)
      .then((ys) => {
        setYears(ys);
        if (ys.length) {
          setYear(ys[ys.length - 1]);
          setPriorYear(ys.length > 1 ? ys[ys.length - 2] : ys[ys.length - 1]);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [measureType]);

  useEffect(() => {
    if (!year) return;
    apiMfs
      .series(measureType, year)
      .then((resp) => {
        setPrimaryFacts(resp.facts);
        if (!reportingMonth && resp.facts.length) {
          setReportingMonth(resp.facts[resp.facts.length - 1].reporting_month);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [measureType, year]); // eslint-disable-line react-hooks/exhaustive-deps

  // 1. YTD revenue vs YTD expenses by reporting month.
  useEffect(() => {
    if (!year) return;
    apiMfs
      .compare(["mfs_ytd_revenue", "mfs_ytd_expense"], year)
      .then((resp) =>
        setRevExpChart(resp.series.map((s) => seriesToChart(s.facts, s.facts[0]?.label ?? s.measure_type))),
      )
      .catch((e: Error) => setError(e.message));
  }, [year]);

  // 2. Fiscal balance and underlying cash balance as separate lines.
  useEffect(() => {
    if (!year) return;
    apiMfs
      .compare(["mfs_ytd_fiscal_balance", "mfs_ytd_underlying_cash_balance"], year)
      .then((resp) =>
        setBalanceChart(resp.series.map((s) => seriesToChart(s.facts, s.facts[0]?.label ?? s.measure_type))),
      )
      .catch((e: Error) => setError(e.message));
  }, [year]);

  // 3. Net debt, net worth, assets, liabilities as point-in-time stock series.
  useEffect(() => {
    if (!year) return;
    apiMfs
      .compare(
        ["mfs_stock_total_assets", "mfs_stock_total_liabilities", "mfs_stock_net_worth", "mfs_stock_net_debt"],
        year,
      )
      .then((resp) =>
        setStockChart(resp.series.map((s) => seriesToChart(s.facts, s.facts[0]?.label ?? s.measure_type))),
      )
      .catch((e: Error) => setError(e.message));
  }, [year]);

  // 4. Latest report vs prior-year same-month comparison, for the selected measure.
  useEffect(() => {
    if (!year || !priorYear) return;
    Promise.all([apiMfs.series(measureType, year), apiMfs.series(measureType, priorYear)])
      .then(([latest, prior]) => {
        const latestLabel = latest.facts[0]?.label ?? measureType;
        setYoyChart([
          seriesToChart(latest.facts, `${latestLabel} (${year})`),
          seriesToChart(prior.facts, `${latestLabel} (${priorYear})`),
        ]);
      })
      .catch((e: Error) => setError(e.message));
  }, [measureType, year, priorYear]);

  const currentFact = useMemo(
    () => primaryFacts.find((f) => f.reporting_month === reportingMonth),
    [primaryFacts, reportingMonth],
  );
  const selectedMeasureInfo = measures.find((m) => m.measure_type === measureType);

  function handlePointClick(facts: MfsFact[], seriesName: string, pointIndex: number) {
    const monthsPresent = MONTH_ORDER.filter((m) => facts.some((f) => f.reporting_month === m));
    const month = monthsPresent[pointIndex];
    const fact = facts.find((f) => f.reporting_month === month);
    if (fact) setSelectedCitation(fact.citation);
  }

  return (
    <main className="mx-auto max-w-6xl p-6" data-explorer="mfs">
      <h1 className="text-2xl font-semibold">Monthly Financial Statements (MFS) explorer</h1>
      <p className="mt-2 max-w-3xl text-sm opacity-80">
        Federal Government Monthly Financial Statements &quot;Aggregates&quot; workbook - year-to-date
        (YTD) flows and point-in-time balance-sheet stocks, month by month. This data is{" "}
        <strong>never</strong> inserted into the annual expenditure/revenue pie or any other existing
        dashboard total - it is exposed only here, through its own dedicated API
        (<code>/v2/mfs/*</code>), because a partial-year YTD figure is not comparable to a full-year
        annual actual.
      </p>
      <DashboardNav />

      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        <label>
          Measure{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={measureType}
            onChange={(e) => {
              setMeasureType(e.target.value);
              setReportingMonth("");
            }}
          >
            {measures.map((m) => (
              <option key={m.measure_type} value={m.measure_type}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Financial year{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reporting month{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={reportingMonth}
            onChange={(e) => setReportingMonth(e.target.value)}
          >
            {primaryFacts.map((f) => (
              <option key={f.reporting_month} value={f.reporting_month}>
                {f.reporting_month}
              </option>
            ))}
          </select>
        </label>
        <label>
          Compare against prior year{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={priorYear}
            onChange={(e) => setPriorYear(e.target.value)}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <p className="mt-4 text-red-600">{error}</p> : null}

      {selectedMeasureInfo ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span
            className={`rounded-full px-2 py-0.5 font-medium ${
              selectedMeasureInfo.flow_or_stock === "stock" || selectedMeasureInfo.flow_or_stock === "stock_balance"
                ? "bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-100"
                : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
            }`}
          >
            {selectedMeasureInfo.flow_or_stock === "stock" || selectedMeasureInfo.flow_or_stock === "stock_balance"
              ? "Stock (point-in-time)"
              : "Flow (year-to-date)"}
          </span>
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
            Source vintage: current (single acquired edition - see ops/reports/mfs-revision-policy-*.md)
          </span>
          {currentFact ? (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 font-medium dark:bg-zinc-800">
              {periodDisclosure(currentFact)}
            </span>
          ) : null}
        </div>
      ) : null}

      {currentFact ? (
        <div className="mt-3 text-2xl font-semibold">{formatAudFull(currentFact.amount_aud)}</div>
      ) : null}

      <section className="mt-8">
        <h2 className="text-lg font-medium">YTD revenue vs YTD expenses, by reporting month ({year})</h2>
        <p className="text-xs opacity-70">
          Two distinct series - never summed into one combined total.
        </p>
        <MfsLineChart series={revExpChart} dark={dark} />
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-medium">Fiscal balance vs underlying cash balance ({year})</h2>
        <p className="text-xs opacity-70">
          Both are already-derived balances - shown as separate lines, never summed with revenue/expense
          or with each other.
        </p>
        <MfsLineChart series={balanceChart} dark={dark} />
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-medium">
          Balance-sheet stocks: assets, liabilities, net worth, net debt ({year})
        </h2>
        <p className="text-xs opacity-70">
          Point-in-time figures as at the end of each reporting month - not a year-to-date accumulation.
        </p>
        <MfsLineChart series={stockChart} dark={dark} />
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-medium">
          {selectedMeasureInfo?.label ?? measureType}: {year} vs {priorYear} (same reporting month)
        </h2>
        <p className="text-xs opacity-70">
          Compares the same elapsed fiscal period across two years - never a partial year compared
          against a full year.
        </p>
        <MfsLineChart
          series={yoyChart}
          dark={dark}
          onPointClick={(_name, idx) => handlePointClick(primaryFacts, _name, idx)}
        />
      </section>

      <section className="mt-8 max-w-xl">
        <CitationBox citation={selectedCitation ?? currentFact?.citation ?? null} />
      </section>
    </main>
  );
}

export default function MfsExplorerPage() {
  return (
    <Suspense fallback={<main className="p-6 text-sm opacity-70">Loading…</main>}>
      <MfsExplorerInner />
    </Suspense>
  );
}

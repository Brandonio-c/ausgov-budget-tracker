"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import {
  apiQldOtp,
  QldOtpAgencyValue,
  QldOtpAvailability,
  QldOtpCitation,
  QldOtpMeasureInfo,
} from "@/lib/api";
import { formatMeasureValue } from "@/lib/colors";
import DashboardNav from "@/components/DashboardNav";

function CitationBox({ citation }: { citation: QldOtpCitation | null }) {
  if (!citation) {
    return <p className="text-sm opacity-60">Click an agency row to see its source citation.</p>;
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

function QldOtpExplorerInner() {
  const [measures, setMeasures] = useState<QldOtpMeasureInfo[]>([]);
  const [measureType, setMeasureType] = useState("qld_otp_eligible_claims");
  const [availability, setAvailability] = useState<QldOtpAvailability[]>([]);
  const [financialYear, setFinancialYear] = useState("");
  const [quarter, setQuarter] = useState<number>(1);
  const [agencies, setAgencies] = useState<QldOtpAgencyValue[]>([]);
  const [totalValue, setTotalValue] = useState<number | null | undefined>(undefined);
  const [totalValueNote, setTotalValueNote] = useState<string | null | undefined>(undefined);
  const [selectedCitation, setSelectedCitation] = useState<QldOtpCitation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiQldOtp.measures().then(setMeasures).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    apiQldOtp
      .years(measureType)
      .then((avail) => {
        setAvailability(avail);
        if (avail.length) {
          const latest = avail[avail.length - 1];
          setFinancialYear(latest.financial_year);
          setQuarter(latest.quarter);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [measureType]);

  useEffect(() => {
    if (!financialYear || !quarter) return;
    setSelectedCitation(null);
    apiQldOtp
      .breakdown(measureType, financialYear, quarter)
      .then((resp) => {
        setAgencies(resp.agencies);
        setTotalValue(resp.total_value);
        setTotalValueNote(resp.total_value_note);
      })
      .catch((e: Error) => setError(e.message));
  }, [measureType, financialYear, quarter]);

  const selectedMeasureInfo = measures.find((m) => m.measure_type === measureType);
  const years = useMemo(() => [...new Set(availability.map((a) => a.financial_year))], [availability]);
  const quartersForYear = useMemo(
    () => availability.filter((a) => a.financial_year === financialYear).map((a) => a.quarter),
    [availability, financialYear],
  );

  return (
    <main className="mx-auto max-w-6xl p-6" data-explorer="qld-otp">
      <h1 className="text-2xl font-semibold">QLD on-time payments (small business) explorer</h1>
      <p className="mt-2 max-w-3xl text-sm opacity-80">
        Queensland Government On-Time Payment compliance reports, by agency, by quarter. Counts,
        percentages, days and payment values are <strong>typed and kept separate</strong> - never
        merged into any expenditure/procurement total, and a per-agency percentage or day-average is{" "}
        <strong>never summed</strong> across agencies (a mean-of-means or an averaged percentage is
        not a meaningful whole-of-government figure).
      </p>
      <DashboardNav />

      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        <label>
          Measure{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={measureType}
            onChange={(e) => setMeasureType(e.target.value)}
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
            value={financialYear}
            onChange={(e) => setFinancialYear(e.target.value)}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label>
          Quarter{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={quarter}
            onChange={(e) => setQuarter(Number(e.target.value))}
          >
            {quartersForYear.map((q) => (
              <option key={q} value={q}>
                Q{q}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <p className="mt-4 text-red-600">{error}</p> : null}

      {selectedMeasureInfo ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
            Unit: {selectedMeasureInfo.unit}
          </span>
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
            Accounting basis: {selectedMeasureInfo.accounting_basis}
          </span>
        </div>
      ) : null}

      <p className="mt-3 text-sm">
        {agencies.length} agencies reported for {financialYear} Q{quarter}
        {totalValue !== null && totalValue !== undefined ? (
          <>
            {" "}
            &mdash; total {formatMeasureValue(totalValue, selectedMeasureInfo?.unit)}
          </>
        ) : null}
      </p>
      {totalValueNote ? <p className="mt-1 text-xs opacity-70">{totalValueNote}</p> : null}

      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-3">
        <section className="md:col-span-2">
          <ul className="divide-y divide-black/10 dark:divide-white/10">
            {agencies.map((a) => (
              <li key={a.agency_code}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between py-2 text-left text-sm hover:underline"
                  onClick={() => setSelectedCitation(a.citation)}
                >
                  <span>{a.agency_code}</span>
                  <span className="font-medium">{formatMeasureValue(a.value, selectedMeasureInfo?.unit)}</span>
                </button>
              </li>
            ))}
          </ul>
          {agencies.length === 0 ? (
            <p className="text-sm opacity-60">No agencies reported for this measure/quarter.</p>
          ) : null}
        </section>
        <section>
          <CitationBox citation={selectedCitation} />
        </section>
      </div>
    </main>
  );
}

export default function QldOtpExplorerPage() {
  return (
    <Suspense fallback={<main className="p-6 text-sm opacity-70">Loading…</main>}>
      <QldOtpExplorerInner />
    </Suspense>
  );
}

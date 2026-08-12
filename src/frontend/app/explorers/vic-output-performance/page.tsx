"use client";

import { useEffect, useState } from "react";
import { apiV2, Citation } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";

const FINANCIAL_YEAR = "2024-25";

type OutputRow = {
  name: string;
  actual: number | null;
  actualCitation: Citation | null;
  budget: number | null;
  budgetCitation: Citation | null;
};

function formatAud(value: number | null): string {
  if (value == null) return "—";
  return value.toLocaleString("en-AU", {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 0,
  });
}

export default function VicOutputPerformancePage() {
  const [rows, setRows] = useState<OutputRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Citation | null>(null);

  useEffect(() => {
    Promise.all([
      apiV2.tree({
        compatibility_group: "vic_output_total_cost",
        accounting_basis: "accrual",
        estimate_status: "actual",
        financial_year: FINANCIAL_YEAR,
        limit: 100,
      }),
      apiV2.tree({
        compatibility_group: "vic_output_total_cost",
        accounting_basis: "accrual",
        estimate_status: "budget",
        financial_year: FINANCIAL_YEAR,
        limit: 100,
      }),
    ])
      .then(([actualTree, budgetTree]) => {
        const byName = new Map<string, OutputRow>();
        for (const child of actualTree.children || []) {
          byName.set(child.name, {
            name: child.name,
            actual: child.value,
            actualCitation: child.citation,
            budget: null,
            budgetCitation: null,
          });
        }
        for (const child of budgetTree.children || []) {
          const existing = byName.get(child.name);
          if (existing) {
            existing.budget = child.value;
            existing.budgetCitation = child.citation;
          } else {
            byName.set(child.name, {
              name: child.name,
              actual: null,
              actualCitation: null,
              budget: child.value,
              budgetCitation: child.citation,
            });
          }
        }
        const merged = Array.from(byName.values()).sort((a, b) =>
          a.name.localeCompare(b.name),
        );
        setRows(merged);
        setSelected(merged[0]?.actualCitation ?? merged[0]?.budgetCitation ?? null);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="mx-auto max-w-5xl p-6" data-explorer="vic-output-performance">
      <h1 className="text-2xl font-semibold">Victoria — Output Performance</h1>
      <p className="mt-2 text-sm opacity-80">
        Total output cost per departmental output, Victorian Department of Treasury and
        Finance Output Performance Measures, {FINANCIAL_YEAR} actual vs. target. This is a
        specialist performance-measurement product, not an additive expenditure figure -
        it is not part of, and must never be summed into, the whole-of-government annual
        tree. Only the seven dollar-denominated &quot;Total output cost&quot; rows are
        shown here; count/date/percentage/ratio KPI rows from the same workbook are
        deliberately not coerced into a dollar figure and remain unpublished.
      </p>
      <DashboardNav />
      {error ? <p className="mt-4 text-red-600">{error}</p> : null}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left dark:border-white/20">
              <th className="py-2 pr-4">Output</th>
              <th className="py-2 pr-4 text-right">Actual</th>
              <th className="py-2 pr-4 text-right">Target</th>
              <th className="py-2 text-right">Variance</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.name}
                className="cursor-pointer border-b hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/5"
                onClick={() => setSelected(r.actualCitation ?? r.budgetCitation)}
              >
                <td className="py-2 pr-4">{r.name}</td>
                <td className="py-2 pr-4 text-right">{formatAud(r.actual)}</td>
                <td className="py-2 pr-4 text-right">{formatAud(r.budget)}</td>
                <td className="py-2 text-right">
                  {r.actual != null && r.budget != null
                    ? formatAud(r.actual - r.budget)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <CitationPanel citation={selected} />
      </div>
    </main>
  );
}

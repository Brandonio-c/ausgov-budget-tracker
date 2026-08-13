"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  explorerApi,
  ExplorerAvailability,
  ExplorerFacets,
  ExplorerTree,
} from "@/lib/explorerApi";
import type { Citation } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import DashboardNav from "@/components/DashboardNav";

const PAGE_SIZE = 200;
const SEARCH_DEBOUNCE_MS = 300;

function pickDefaultYear(availability: ExplorerAvailability, status: string): string {
  // Most-populated year for this status, not most-recent: some families'
  // corpora include sparse trailing/leading years (a just-opened forward
  // year, or a malformed financial_year artifact from source extraction -
  // e.g. PBS's real "2025-20"/"2026-29" data-quality defects, tracked in
  // ops/reports/explorer-shell-6.2-20260813*.md) that would otherwise
  // become the default view and make a substantively deep family look
  // empty. This never hides those years - every one with count > 0 still
  // appears in the year selector - it only changes which one loads first.
  const rows = availability.years.filter((y) => y.estimate_status === status && y.count > 0);
  if (rows.length === 0) return "";
  return rows.reduce((best, r) => (r.count > best.count ? r : best)).financial_year;
}

type Props = { familyId: string };

function ExplorerShellInner({ familyId }: Props) {
  const searchParams = useSearchParams();

  const [availability, setAvailability] = useState<ExplorerAvailability | null>(null);
  const [facets, setFacets] = useState<ExplorerFacets | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [booted, setBooted] = useState(false);

  const [status, setStatus] = useState("");
  const [year, setYear] = useState("");
  const [filterInput, setFilterInput] = useState(searchParams.get("q") || "");
  const [filter, setFilter] = useState(searchParams.get("q") || "");

  const [rows, setRows] = useState<ExplorerTree["children"]>([]);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [totalValue, setTotalValue] = useState<number | null>(null);
  const [sourceBreakdown, setSourceBreakdown] = useState<ExplorerTree["source_breakdown"]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selected, setSelected] = useState<Citation | null>(null);
  const [treeError, setTreeError] = useState<string | null>(null);

  // Bootstrap once per family: availability gives the family's registered
  // metadata (label, additive_note, registered estimate_statuses) plus
  // which financial_year x estimate_status combinations actually have
  // live, publishable data - not a guess, not derived from label text.
  // A deep-linked ?year=/?status= is honored as-is; only when neither is
  // present do we pick a default (the most recent year with real data for
  // the family's registered default_estimate_status). Never silently swap
  // an explicitly-requested year for a different one.
  useEffect(() => {
    let cancelled = false;
    Promise.all([explorerApi.availability(familyId), explorerApi.facets(familyId)])
      .then(([avail, fac]) => {
        if (cancelled) return;
        const initialStatus = searchParams.get("status") || avail.family.default_estimate_status;
        const initialYear = searchParams.get("year") || pickDefaultYear(avail, initialStatus);
        setAvailability(avail);
        setFacets(fac);
        setStatus(initialStatus);
        setYear(initialYear);
        setBootError(null);
        setBooted(true);
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setBootError(e.message);
        setBooted(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyId]);

  // Debounce free-text search before it becomes a real server request -
  // this hits /v2/explorers/{family}/tree?q= server-side (item 6.1's
  // search capability), not a client-side filter over an already-loaded
  // page, so it must not fire on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setFilter(filterInput), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [filterInput]);

  // Fetch the first page whenever family/year/status/search changes, once
  // booted. Totals below always describe the full searched scope, never a
  // partial-page sum - state updates happen only inside the fetch
  // callback so a switch replaces the previous scope's rows/totals/cursor
  // together, atomically.
  useEffect(() => {
    if (!booted || !year || !status) return;
    explorerApi
      .tree(familyId, { financial_year: year, estimate_status: status, q: filter, limit: PAGE_SIZE })
      .then((tree) => {
        setRows(tree.children);
        setTotalCount(tree.total_count);
        setTotalValue(tree.total_value);
        setSourceBreakdown(tree.source_breakdown);
        setNextCursor(tree.next_cursor);
        const factParam = searchParams.get("fact");
        const match = factParam ? tree.children.find((r) => String(r.id) === factParam) : tree.children[0];
        setSelected(match?.citation ?? tree.children[0]?.citation ?? null);
        setTreeError(null);
      })
      .catch((e: Error) => {
        setTreeError(e.message);
        setRows([]);
        setTotalCount(null);
        setTotalValue(null);
        setSourceBreakdown([]);
        setNextCursor(null);
        setSelected(null);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyId, year, status, filter, booted]);

  const loadMore = () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    explorerApi
      .tree(familyId, {
        financial_year: year,
        estimate_status: status,
        q: filter,
        limit: PAGE_SIZE,
        cursor: nextCursor,
      })
      .then((tree) => {
        setRows((prev) => [...prev, ...tree.children]);
        setNextCursor(tree.next_cursor);
      })
      .catch((e: Error) => setTreeError(e.message))
      .finally(() => setLoadingMore(false));
  };

  if (!booted) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <p className="text-sm text-zinc-500">Loading explorer…</p>
      </main>
    );
  }

  if (bootError || !availability) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="text-2xl font-semibold">Explorer</h1>
        {/* The backend's own detail text is already the honest error
            (e.g. "Unknown explorer family: does-not-exist") - shown
            verbatim rather than paraphrased. */}
        <p className="mt-4 text-red-600">{bootError || "Failed to load this explorer."}</p>
        <p className="mt-2 text-sm">
          <Link className="underline" href="/explorers">
            Back to explorers index
          </Link>
        </p>
      </main>
    );
  }

  const { family } = availability;
  const yearsForStatus = availability.years
    .filter((y) => y.estimate_status === status)
    .sort((a, b) => a.financial_year.localeCompare(b.financial_year));
  const allLoaded = nextCursor === null && totalCount !== null;
  const hasRequestedYearWithNoData = year && !yearsForStatus.some((y) => y.financial_year === year);

  return (
    <main className="mx-auto max-w-5xl p-6" data-explorer={familyId}>
      {/* Honest breadcrumb - "Explorers > {family}" only. None of the
          registered families have source-native hierarchy beneath their
          flat fact list (verified directly against node_edges when
          item 6.1's tree endpoint was built), so this shell does not
          render a deeper drill-in breadcrumb or tree-navigation affordance
          - fabricating one from label structure is exactly what the
          program's rules forbid. */}
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        <Link className="underline" href="/explorers">
          Explorers
        </Link>{" "}
        / {family.label}
      </p>
      <h1 className="mt-1 text-2xl font-semibold">{family.label}</h1>

      {/* Source/semantic banner - drawn directly from the registry, not
          bespoke per-page prose, so every family gets a real disclosure. */}
      {family.additive_note ? (
        <p className="mt-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
          {family.additive_note}
        </p>
      ) : null}

      <DashboardNav />

      <div className="mt-4 flex flex-wrap gap-3">
        <label className="block text-sm">
          Financial year{" "}
          <select
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          >
            {year && !yearsForStatus.some((y) => y.financial_year === year) ? (
              <option value={year}>{year} (no data)</option>
            ) : null}
            {yearsForStatus.map((y) => (
              <option key={y.financial_year} value={y.financial_year}>
                {y.financial_year} ({y.count.toLocaleString("en-AU")})
              </option>
            ))}
          </select>
        </label>

        {family.estimate_statuses.length > 1 ? (
          <label className="block text-sm">
            Estimate status{" "}
            <select
              className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {family.estimate_statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="self-end text-sm opacity-70">
            Estimate status: <code>{family.estimate_statuses[0]}</code>
          </p>
        )}

        <label className="block text-sm">
          Search{" "}
          <input
            className="ml-2 border px-2 py-1 dark:border-white/20 dark:bg-zinc-900"
            value={filterInput}
            onChange={(e) => setFilterInput(e.target.value)}
            placeholder={`Search ${family.label.toLowerCase()}…`}
          />
        </label>
      </div>

      {facets ? (
        <p className="mt-3 text-xs opacity-60">
          {facets.sources.length > 1
            ? `${facets.sources.length} sources across this family: `
            : "Source: "}
          {facets.sources.map((s) => s.source_key).join(", ")}
          {facets.measures.length ? ` — measure: ${facets.measures.map((m) => m.measure_type).join(", ")}` : ""}
        </p>
      ) : null}

      {treeError ? <p className="mt-4 text-red-600">{treeError}</p> : null}

      {hasRequestedYearWithNoData ? (
        <p className="mt-4 text-sm text-amber-700 dark:text-amber-400">
          No data for {year} ({status}). Choose a different year above - years with real
          data are listed in the selector.
        </p>
      ) : totalCount !== null ? (
        <p className="mt-4 text-sm opacity-80">
          {totalCount.toLocaleString("en-AU")} rows for {year} ({status}), total value{" "}
          {totalValue?.toLocaleString("en-AU", {
            style: "currency",
            currency: "AUD",
            maximumFractionDigits: 0,
          })}
          {" — "}
          {rows.length.toLocaleString("en-AU")} loaded
          {filter ? ` (server-side search: "${filter}")` : ""}.
        </p>
      ) : null}

      {sourceBreakdown.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs opacity-70">
          {sourceBreakdown.map((b) => (
            <li key={b.source_key}>
              {b.source_key}: {b.count.toLocaleString("en-AU")} (
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
            {rows.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className="text-left underline"
                  onClick={() => setSelected(r.citation)}
                >
                  {r.name.slice(0, 140)} — {r.value?.toLocaleString("en-AU")}
                </button>
              </li>
            ))}
          </ul>
          {rows.length === 0 && !hasRequestedYearWithNoData && totalCount === 0 ? (
            <p className="mt-4 text-xs opacity-60">
              No rows match {filter ? `the search "${filter}"` : "this scope"}.
            </p>
          ) : null}
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
            <p className="mt-4 text-xs opacity-60">
              All {totalCount?.toLocaleString("en-AU")} rows loaded.
            </p>
          ) : null}
        </div>
        <CitationPanel citation={selected} />
      </div>
    </main>
  );
}

export function ExplorerShell({ familyId }: Props) {
  return (
    <Suspense fallback={<main className="p-6 text-sm text-zinc-500">Loading…</main>}>
      <ExplorerShellInner familyId={familyId} />
    </Suspense>
  );
}

export default ExplorerShell;

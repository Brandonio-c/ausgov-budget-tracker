"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiDashboard, DashboardMode, DashboardSeries } from "@/lib/api";
import { LevelSummary, TreeNode } from "@/lib/types";
import {
  INTEGRITY_BANNER,
  LEVEL_LABELS,
  commonCategoryNames,
} from "@/lib/combineTrees";
import { DASHBOARD_MODES, isDashboardMode, modeLabel } from "@/lib/dashboardMode";
import { useDarkMode } from "@/lib/useDarkMode";
import TimelineChart, { TimelinePointClick } from "@/components/TimelineChart";
import FactCitationViewer from "@/components/FactCitationViewer";
import ResizableSplitPane from "@/components/ResizableSplitPane";
import DashboardNav from "@/components/DashboardNav";
import { formatAudFull } from "@/lib/colors";

function TimelinePageInner() {
  const dark = useDarkMode();
  const searchParams = useSearchParams();

  const [mode, setMode] = useState<DashboardMode>(() => {
    const m = searchParams.get("mode");
    return isDashboardMode(m) ? m : "actuals";
  });
  const [availableLevels, setAvailableLevels] = useState<LevelSummary[]>([]);
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState<string>(searchParams.get("category") || "");
  const [series, setSeries] = useState<DashboardSeries | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(
    searchParams.get("fact") && Number.isFinite(Number(searchParams.get("fact")))
      ? Number(searchParams.get("fact"))
      : null,
  );
  const [pointNote, setPointNote] = useState(
    "Click a point to preview a sample citation for that level and year",
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const m = searchParams.get("mode");
    if (isDashboardMode(m)) setMode(m);
    const cat = searchParams.get("category");
    if (cat) setCategory(cat);
    const fact = searchParams.get("fact");
    if (fact && Number.isFinite(Number(fact))) {
      setSelectedItemId(Number(fact));
      setPointNote("Opened from search — citation for the matched item.");
    }
    const lvl = searchParams.get("level");
    if (lvl) setSelectedLevels([lvl]);
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    setSeries(null);
    setCategories([]);
    setSelectedItemId((id) => (searchParams.get("fact") ? id : null));
    if (!searchParams.get("category")) setCategory("");
    apiDashboard
      .levels(mode)
      .then((data) => {
        if (cancelled) return;
        setAvailableLevels(data);
        const linked = searchParams.get("level");
        setSelectedLevels(
          linked && data.some((l) => l.level === linked)
            ? [linked]
            : data.map((l) => l.level),
        );
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Load category options from latest year trees (intersection of semantic names).
  useEffect(() => {
    if (selectedLevels.length === 0) {
      setCategories([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const yearLists = await Promise.all(
          selectedLevels.map((level) => apiDashboard.years(mode, level)),
        );
        const entries: Array<{ level: string; tree: TreeNode }> = [];
        await Promise.all(
          selectedLevels.map(async (level, i) => {
            const years = yearLists[i];
            const latest = years[years.length - 1];
            if (!latest) return;
            try {
              const tree = await apiDashboard.tree(mode, level, latest);
              entries.push({ level, tree });
            } catch {
              /* level may lack that year */
            }
          }),
        );
        if (cancelled) return;
        const common = commonCategoryNames(entries);
        setCategories(common);
        setCategory((prev) => (prev && common.includes(prev) ? prev : ""));
      } catch (err) {
        if (!cancelled) setError(String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mode, selectedLevels.join(",")]);

  useEffect(() => {
    if (selectedLevels.length === 0) {
      setSeries(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    apiDashboard
      .series(mode, selectedLevels, category || null)
      .then((data) => {
        if (cancelled) return;
        setSeries(data);
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, selectedLevels.join(","), category]);

  const subtitle = useMemo(() => {
    const kind = mode === "debt" ? "liability stocks" : "spending";
    if (category) return `Category: ${category} (${kind})`;
    return `Per-level ${kind} totals over time`;
  }, [category, mode]);

  function toggleLevel(level: string) {
    setSelectedItemId(null);
    setPointNote("Click a point to preview a sample citation for that level and year");
    setSelectedLevels((prev) => {
      if (prev.includes(level)) {
        if (prev.length === 1) return prev;
        return prev.filter((l) => l !== level);
      }
      return [...prev, level].sort(
        (a, b) =>
          availableLevels.findIndex((x) => x.level === a) -
          availableLevels.findIndex((x) => x.level === b),
      );
    });
  }

  function handlePointClick(point: TimelinePointClick) {
    const label = LEVEL_LABELS[point.level] ?? point.level;
    if (point.fact_id != null) {
      setSelectedItemId(point.fact_id);
      setPointNote(
        `${label} · FY ${point.financial_year} · ${formatAudFull(point.total_aud)}`,
      );
    } else {
      setSelectedItemId(null);
      setPointNote(
        `${label} · FY ${point.financial_year} · ${formatAudFull(point.total_aud)} — no sample fact id for citation`,
      );
    }
  }

  return (
    <div className="min-h-screen w-full px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Timeline
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Temporal comparison by government level. Actuals, Budget, and Debt
          stay separate; levels are never summed into one national total.
        </p>
        <DashboardNav />
      </header>

      {error && (
        <p className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div
        className="mb-4 rounded-md border border-amber-300/80 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100"
        role="status"
      >
        {INTEGRITY_BANNER}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
          {DASHBOARD_MODES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-4 py-2 text-sm font-medium ${
                mode === m
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "bg-white text-zinc-600 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
              }`}
            >
              {modeLabel(m)}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {availableLevels.map((l) => {
            const on = selectedLevels.includes(l.level);
            return (
              <button
                key={l.level}
                type="button"
                onClick={() => toggleLevel(l.level)}
                aria-pressed={on}
                className={`rounded-md border px-3 py-2 text-sm font-medium ${
                  on
                    ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-50 dark:bg-zinc-50 dark:text-zinc-900"
                    : "border-black/10 bg-white text-zinc-600 hover:bg-zinc-100 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                }`}
              >
                {LEVEL_LABELS[l.level] ?? l.level}
              </button>
            );
          })}
        </div>

        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setSelectedItemId(null);
            setPointNote("Click a point to preview a sample citation for that level and year");
          }}
          className="rounded-md border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-50"
        >
          <option value="">All / total for level</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <p className="mb-3 text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>

      {series?.warning ? (
        <p className="mb-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {series.warning}
        </p>
      ) : null}

      <ResizableSplitPane
        left={
          <section
            className="min-w-0 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900"
            aria-label="Timeline chart"
          >
            {series && !loading ? (
              <TimelineChart data={series} dark={dark} onPointClick={handlePointClick} />
            ) : (
              <p className="py-20 text-center text-sm text-zinc-500">
                {loading ? "Loading…" : "Select at least one level"}
              </p>
            )}
          </section>
        }
        right={
          <aside
            className="min-w-0 rounded-lg border border-black/10 bg-white dark:border-white/10 dark:bg-zinc-900"
            aria-label="Source citation"
          >
            <FactCitationViewer
              key={selectedItemId ?? "empty"}
              factId={selectedItemId}
              emptyMessage={pointNote}
            />
          </aside>
        }
      />
    </div>
  );
}

export default function TimelinePage() {
  return (
    <Suspense fallback={<div className="min-h-screen px-4 py-8 text-sm text-zinc-500">Loading…</div>}>
      <TimelinePageInner />
    </Suspense>
  );
}

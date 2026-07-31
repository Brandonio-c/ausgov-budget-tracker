"use client";

import { useEffect, useMemo, useState } from "react";
import { apiDashboard, DashboardMode } from "@/lib/api";
import { LevelSummary, TreeNode } from "@/lib/types";
import { foldToTopN } from "@/lib/colors";
import { LEVEL_LABELS } from "@/lib/combineTrees";
import { useDarkMode } from "@/lib/useDarkMode";
import SpendingChart, { ChartType } from "@/components/SpendingChart";
import FactCitationViewer from "@/components/FactCitationViewer";
import ResizableSplitPane from "@/components/ResizableSplitPane";
import RingDepthControl from "@/components/RingDepthControl";
import DebtNav from "@/components/DebtNav";
import { maxAdditiveDepth, additiveChildren } from "@/lib/sunburstTree";

const DEBT_MODE: DashboardMode = "debt";

/**
 * Liability stock explorer (ABS GFS Table_3) — same chart/citation UX as spending.
 */
export default function DebtViewer() {
  const dark = useDarkMode();

  const [levels, setLevels] = useState<LevelSummary[]>([]);
  const [level, setLevel] = useState<string>("");
  const [years, setYears] = useState<string[]>([]);
  const [year, setYear] = useState<string>("");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [chartType, setChartType] = useState<ChartType>("pie");
  const [ringDepth, setRingDepth] = useState(2);
  const [drillPath, setDrillPath] = useState<TreeNode[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [sourcePrompt, setSourcePrompt] = useState(
    "Hover a liability line to preview its source citation",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTree(null);
    setYears([]);
    setLevel("");
    setYear("");
    setDrillPath([]);
    apiDashboard
      .levels(DEBT_MODE)
      .then((data) => {
        if (cancelled) return;
        setLevels(data);
        const preferred = data[0]?.level ?? "";
        if (preferred) setLevel(preferred);
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!level) return;
    let cancelled = false;
    apiDashboard
      .years(DEBT_MODE, level)
      .then(async (data) => {
        if (cancelled) return;
        setYears(data);
        const preferred = data[data.length - 1] ?? "";
        setYear(preferred);
        if (preferred) setTree(await apiDashboard.tree(DEBT_MODE, level, preferred));
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
  }, [level]);

  useEffect(() => {
    if (!level || !year || !years.includes(year)) return;
    apiDashboard
      .tree(DEBT_MODE, level, year)
      .then((data) => {
        setTree(data);
        setError(null);
      })
      .catch((err) => setError(String(err)));
  }, [year, level, years]);

  const rootNode =
    level === "federal" && tree?.children?.length === 1 ? tree.children[0] : tree;
  const currentNode = drillPath.length > 0 ? drillPath[drillPath.length - 1] : rootNode;
  const rawChildren = currentNode?.children ?? null;
  const displayedChildren = useMemo(
    () => (rawChildren?.length ? foldToTopN(additiveChildren(rawChildren)) : []),
    [rawChildren],
  );
  const chartNodes = chartType === "rings" ? rawChildren ?? [] : displayedChildren;
  const maxRingDepth = useMemo(
    () => Math.max(1, maxAdditiveDepth(rawChildren)),
    [rawChildren],
  );
  const centerLabel =
    chartType === "rings"
      ? drillPath.length > 0
        ? drillPath[drillPath.length - 1].name
        : `${LEVEL_LABELS[level] ?? level}`
      : null;

  useEffect(() => {
    if (ringDepth > maxRingDepth) setRingDepth(maxRingDepth);
  }, [maxRingDepth, ringDepth]);

  const atLeaf =
    !!currentNode &&
    (!currentNode.children || currentNode.children.length === 0) &&
    drillPath.length > 0;

  function handleNodeClick(node: TreeNode) {
    if (node.children && node.children.length > 0) {
      setSelectedItemId(node.id);
      setSourcePrompt(
        node.id != null
          ? "Hover a deeper leaf for its citation, or keep this parent selected"
          : "Hover a liability line to preview its source citation",
      );
      setDrillPath((path) => [...path, node]);
    } else if (node.id !== null) {
      setSelectedItemId(node.id);
      setSourcePrompt(
        "No deeper published liability breakdown — citation for this line.",
      );
    }
  }

  function handleNodeHover(node: TreeNode) {
    if (node.id !== null) {
      setSelectedItemId(node.id);
      return;
    }
    setSelectedItemId(null);
    setSourcePrompt(
      node.name.startsWith("Other (")
        ? `Drill into ${node.name} to see citations for each included category`
        : "Drill into this segment to reach its source citation",
    );
  }

  function handleLevelChange(nextLevel: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setSourcePrompt("Hover a liability line to preview its source citation");
    setLevel(nextLevel);
  }

  function handleYearChange(nextYear: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setSourcePrompt("Hover a liability line to preview its source citation");
    setYear(nextYear);
  }

  return (
    <section className="mt-14 border-t border-black/10 pt-10 dark:border-white/10" aria-label="Government debt">
      <header className="mb-6">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          Government debt (liabilities)
        </h2>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          End-of-year GFS liability stocks from ABS balance sheets — not Budget Paper
          “net debt”. Pie slices are liability categories (debt securities, loans,
          superannuation provisions, etc.). Same drill-down and citation behaviour as
          spending above.
        </p>
        <DebtNav />
      </header>

      {tree?.warning ? (
        <p className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {tree.warning}
          {tree.observation_dates?.length
            ? ` Dates: ${tree.observation_dates.join(", ")}.`
            : null}
        </p>
      ) : null}

      {error && (
        <p className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
          {levels.map((l) => (
            <button
              key={l.level}
              type="button"
              onClick={() => handleLevelChange(l.level)}
              className={`px-4 py-2 text-sm font-medium ${
                level === l.level
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "bg-white text-zinc-600 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
              }`}
            >
              {LEVEL_LABELS[l.level] ?? l.level}
            </button>
          ))}
        </div>

        <select
          value={year}
          onChange={(e) => handleYearChange(e.target.value)}
          className="rounded-md border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-50"
        >
          {years.map((y) => (
            <option key={y} value={y}>
              FY {y}
            </option>
          ))}
        </select>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
            {(["pie", "rings", "bar"] as ChartType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setChartType(t)}
                className={`px-4 py-2 text-sm font-medium capitalize ${
                  chartType === t
                    ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                    : "bg-white text-zinc-600 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          {chartType === "rings" && (
            <RingDepthControl
              depth={ringDepth}
              maxDepth={maxRingDepth}
              onChange={setRingDepth}
            />
          )}
        </div>
      </div>

      {chartType === "rings" && (
        <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
          Outer rings nest under the matching inner wedge. Click a segment to expand it;
          use Back or the breadcrumb to zoom out.
        </p>
      )}

      <nav className="mb-4 flex flex-wrap items-center gap-1 text-sm text-zinc-500 dark:text-zinc-400">
        <button type="button" className="hover:underline" onClick={() => setDrillPath([])}>
          {LEVEL_LABELS[level] ?? level} — Liabilities — FY {year}
        </button>
        {drillPath.map((node, i) => (
          <span key={i} className="flex items-center gap-1">
            <span>/</span>
            <button
              type="button"
              className="hover:underline"
              onClick={() => setDrillPath((path) => path.slice(0, i + 1))}
            >
              {node.name}
            </button>
          </span>
        ))}
      </nav>

      {atLeaf && (
        <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
          No deeper published liability breakdown for this line.
        </p>
      )}

      {(currentNode?.is_aggregate || currentNode?.valuation_basis === "fair_value") && (
        <p className="mb-3 inline-flex items-center rounded border border-sky-300 bg-sky-50 px-2 py-1 text-xs text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200">
          {currentNode?.valuation_basis === "fair_value"
            ? "Fair-value aggregate (e.g. TASCORP instrument-type totals) — not individual securities."
            : "Aggregate stock — not an individual security leaf."}
          {currentNode?.amount_granularity
            ? ` Granularity: ${currentNode.amount_granularity}.`
            : null}
        </p>
      )}

      <ResizableSplitPane
        left={
          <section
            className="relative min-w-0 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900"
            aria-label="Debt chart"
          >
            {tree ? (
              <SpendingChart
                nodes={chartNodes}
                chartType={chartType}
                dark={dark}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                ringDepth={ringDepth}
                centerLabel={centerLabel}
              />
            ) : (
              <p className="py-20 text-center text-sm text-zinc-500">Loading…</p>
            )}
            <button
              type="button"
              onClick={() => setDrillPath((path) => path.slice(0, -1))}
              disabled={drillPath.length === 0}
              className="absolute bottom-3 left-3 z-10 rounded-md border border-black/10 bg-white/95 px-3 py-1.5 text-sm font-medium text-zinc-700 shadow-sm backdrop-blur hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:bg-zinc-900/95 dark:text-zinc-200 dark:hover:bg-zinc-800"
              aria-label="Go back one drill-down level"
            >
              ← Back
            </button>
          </section>
        }
        right={
          <aside
            className="min-w-0 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900"
            aria-label="Debt source citation"
          >
            <FactCitationViewer factId={selectedItemId} emptyMessage={sourcePrompt} />
          </aside>
        }
      />
    </section>
  );
}

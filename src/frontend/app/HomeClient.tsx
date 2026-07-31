"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiDashboard, DashboardMode } from "@/lib/api";
import { LevelSummary, TreeNode } from "@/lib/types";
import { foldToTopN } from "@/lib/colors";
import { LEVEL_LABELS } from "@/lib/combineTrees";
import { DASHBOARD_MODES, isDashboardMode, modeLabel } from "@/lib/dashboardMode";
import { useDarkMode } from "@/lib/useDarkMode";
import { findDrillPath } from "@/lib/findDrillPath";
import SpendingChart, { ChartType } from "@/components/SpendingChart";
import FactCitationViewer from "@/components/FactCitationViewer";
import ResizableSplitPane from "@/components/ResizableSplitPane";
import DashboardNav from "@/components/DashboardNav";
import RingDepthControl from "@/components/RingDepthControl";
import DebtViewer from "@/components/DebtViewer";
import { maxAdditiveDepth, additiveChildren } from "@/lib/sunburstTree";

export default function HomeClient() {
  const dark = useDarkMode();
  const searchParams = useSearchParams();
  const appliedDeepLink = useRef<string>("");

  const [mode, setMode] = useState<DashboardMode>("actuals");
  const [levels, setLevels] = useState<LevelSummary[]>([]);
  const [level, setLevel] = useState<string>("");
  const [years, setYears] = useState<string[]>([]);
  const [year, setYear] = useState<string>("");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [chartType, setChartType] = useState<ChartType>("pie");
  const [ringDepth, setRingDepth] = useState(2);
  const [drillPath, setDrillPath] = useState<TreeNode[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [highlightName, setHighlightName] = useState<string | null>(null);
  const [sourcePrompt, setSourcePrompt] = useState(
    "Hover a leaf item to preview its source citation",
  );
  const [error, setError] = useState<string | null>(null);

  // Apply deep-link query params once (from global search).
  useEffect(() => {
    const key = searchParams.toString();
    if (!key || appliedDeepLink.current === key) return;
    appliedDeepLink.current = key;

    const m = searchParams.get("mode");
    if (isDashboardMode(m)) setMode(m);
    const lvl = searchParams.get("level");
    if (lvl) setLevel(lvl);
    const yr = searchParams.get("year");
    if (yr) setYear(yr);
    const fact = searchParams.get("fact");
    if (fact && Number.isFinite(Number(fact))) setSelectedItemId(Number(fact));
    const hl = searchParams.get("highlight");
    if (hl) setHighlightName(hl);
  }, [searchParams]);

  // Levels for selected measure mode.
  useEffect(() => {
    let cancelled = false;
    setTree(null);
    setYears([]);
    // Keep deep-linked level/year if present; otherwise reset.
    const linkedLevel = searchParams.get("level");
    const linkedYear = searchParams.get("year");
    if (!linkedLevel) setLevel("");
    if (!linkedYear) setYear("");
    setDrillPath([]);
    apiDashboard
      .levels(mode)
      .then((data) => {
        if (cancelled) return;
        setLevels(data);
        const preferred = linkedLevel && data.some((l) => l.level === linkedLevel)
          ? linkedLevel
          : data[0]?.level ?? "";
        if (preferred) setLevel(preferred);
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Years + default tree for level.
  useEffect(() => {
    if (!level) return;
    let cancelled = false;
    const linkedYear = searchParams.get("year");
    apiDashboard
      .years(mode, level)
      .then(async (data) => {
        if (cancelled) return;
        setYears(data);
        const preferred =
          linkedYear && data.includes(linkedYear)
            ? linkedYear
            : data[data.length - 1] ?? "";
        setYear(preferred);
        if (preferred) setTree(await apiDashboard.tree(mode, level, preferred));
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, level]);

  // Year change within same level.
  useEffect(() => {
    if (!level || !year || !years.includes(year)) return;
    apiDashboard
      .tree(mode, level, year)
      .then((data) => {
        setTree(data);
        setError(null);
      })
      .catch((err) => setError(String(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year]);

  const rootNode =
    level === "federal" && tree?.children?.length === 1 ? tree.children[0] : tree;
  const currentNode = drillPath.length > 0 ? drillPath[drillPath.length - 1] : rootNode;
  const rawChildren = currentNode?.children ?? null;
  // Exclude Statement 6 / FBO navigation folders from pie/bar — they preserve the
  // parent amount and would double the chart total (e.g. Social protection $286B + FBO $286B).
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

  // After tree loads, drill/highlight from search deep-link.
  useEffect(() => {
    if (!rootNode) return;
    const factParam = searchParams.get("fact");
    const factId = factParam && Number.isFinite(Number(factParam)) ? Number(factParam) : null;
    const hl = searchParams.get("highlight") || highlightName;
    if (factId == null && !hl) return;
    const { path, leaf } = findDrillPath(rootNode, { factId, highlight: hl });
    if (path.length) setDrillPath(path);
    if (leaf?.id != null) {
      setSelectedItemId(leaf.id);
      setSourcePrompt("Opened from search — citation for the matched item.");
    } else if (factId != null) {
      setSelectedItemId(factId);
      setSourcePrompt("Opened from search — citation for the matched item.");
    }
    if (hl) setHighlightName(hl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rootNode, searchParams]);

  const relatedBreakdown = useMemo(() => {
    if (currentNode?.breakdown?.banner) return currentNode.breakdown;
    for (let i = drillPath.length - 1; i >= 0; i -= 1) {
      const meta = drillPath[i]?.breakdown;
      if (meta?.banner) return meta;
    }
    return null;
  }, [drillPath, currentNode]);

  const chartTotalNote = useMemo(() => {
    const kids = additiveChildren(rawChildren);
    if (!kids.length) return null;
    const parentVal = currentNode?.value ?? 0;
    const sum = kids.reduce((s, n) => s + n.value, 0);
    // When slices roughly partition the parent, amounts are parent-year consistent
    // even if nested related packs stamp fact_financial_year (e.g. AusTender 2019-20).
    if (parentVal > 0 && Math.abs(sum - parentVal) <= parentVal * 0.05) {
      return null;
    }
    const fys = new Set(
      kids
        .map((n) => n.breakdown?.fact_financial_year)
        .filter((y): y is string => !!y && y !== year),
    );
    if (fys.size === 1) {
      const fy = [...fys][0];
      return `Chart total is sum of FY ${fy} published estimates (selected dashboard year is ${year})`;
    }
    if (fys.size > 1) {
      return `Chart slices use mixed published years (${[...fys].sort().join(", ")}); not the selected ${year} total`;
    }
    return null;
  }, [rawChildren, year, currentNode]);

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
          : "Hover a leaf item to preview its source citation",
      );
      setDrillPath((path) => [...path, node]);
      setHighlightName(node.name);
    } else if (node.id !== null) {
      setSelectedItemId(node.id);
      setHighlightName(node.name);
      setSourcePrompt(
        "No deeper published breakdown in this measure family — citation for this leaf.",
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

  function handleModeChange(next: DashboardMode) {
    setMode(next);
    setSourcePrompt("Hover a leaf item to preview its source citation");
  }

  function handleLevelChange(nextLevel: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setHighlightName(null);
    setSourcePrompt("Hover a leaf item to preview its source citation");
    setLevel(nextLevel);
  }

  function handleYearChange(nextYear: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setHighlightName(null);
    setSourcePrompt("Hover a leaf item to preview its source citation");
    setYear(nextYear);
  }

  const highlightedChartNodes = useMemo(() => {
    if (!highlightName) return chartNodes;
    const hl = highlightName.toLowerCase();
    // Prefer showing the matching child at the current level when possible
    return chartNodes;
  }, [chartNodes, highlightName]);

  return (
    <div className="min-h-screen w-full px-4 py-8 sm:px-6 sm:py-10 lg:px-8" data-default-store="facts-dashboard">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          AusGov Budget Tracker
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Australian government spending — Federal, State, Territory &amp; Local.
          Charts use the citation-bearing facts store. Click any segment to drill
          down; hover a leaf to see original source links.
        </p>
        <DashboardNav />
      </header>

      {error && (
        <p className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error} — is the backend running at{" "}
          {process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}?
        </p>
      )}

      {highlightName ? (
        <p className="mb-3 rounded-md border border-blue-300/70 bg-blue-50 px-3 py-2 text-sm text-blue-950 dark:border-blue-700/50 dark:bg-blue-950/40 dark:text-blue-100">
          Highlighted from search: <span className="font-medium">{highlightName}</span>
        </p>
      ) : null}

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
          {DASHBOARD_MODES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => handleModeChange(m)}
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
          Outer rings are nested under the matching inner wedge. Click a segment to expand it
          into the center; use Back or the breadcrumb to zoom out. Use Depth −/+ (up to {maxRingDepth}){" "}
          for as many rings as this branch has.
        </p>
      )}

      <nav className="mb-4 flex flex-wrap items-center gap-1 text-sm text-zinc-500 dark:text-zinc-400">
        <button type="button" className="hover:underline" onClick={() => setDrillPath([])}>
          {LEVEL_LABELS[level] ?? level} — {modeLabel(mode)} — FY {year}
        </button>
        {drillPath.map((node, i) => (
          <span key={i} className="flex items-center gap-1">
            <span>/</span>
            <button
              type="button"
              className={`hover:underline ${
                highlightName && node.name.toLowerCase() === highlightName.toLowerCase()
                  ? "font-semibold text-blue-600 dark:text-blue-400"
                  : ""
              }`}
              onClick={() => setDrillPath((path) => path.slice(0, i + 1))}
            >
              {node.name}
            </button>
          </span>
        ))}
      </nav>

      {relatedBreakdown?.banner && (
        <div
          className="mb-4 rounded-md border border-amber-300/80 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100"
          role="status"
        >
          {relatedBreakdown.banner}
          {relatedBreakdown.match_quality === "approx" ? (
            <span className="ml-1 opacity-80">(approximate crosswalk)</span>
          ) : null}
          {relatedBreakdown.fact_financial_year ? (
            <span className="ml-1 opacity-80">
              (figures FY {relatedBreakdown.fact_financial_year})
            </span>
          ) : null}
        </div>
      )}

      {atLeaf && (
        <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
          No deeper published breakdown in this measure family for this item.
        </p>
      )}

      <ResizableSplitPane
        left={
          <section
            className="relative min-w-0 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900"
            aria-label="Spending chart"
          >
            {tree ? (
              <SpendingChart
                nodes={highlightedChartNodes}
                chartType={chartType}
                dark={dark}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                totalNote={chartTotalNote}
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
            aria-label="Source citation"
          >
            <FactCitationViewer factId={selectedItemId} emptyMessage={sourcePrompt} />
          </aside>
        }
      />

      {/* Keep a dedicated debt section when browsing spending modes. */}
      {mode !== "debt" ? <DebtViewer /> : null}
    </div>
  );
}

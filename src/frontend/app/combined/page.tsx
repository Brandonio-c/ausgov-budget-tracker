"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiDashboard, DashboardMode } from "@/lib/api";
import { LevelSummary, TreeNode } from "@/lib/types";
import { foldToTopN } from "@/lib/colors";
import {
  INTEGRITY_BANNER,
  LEVEL_LABELS,
  combineLevelTrees,
  intersectYears,
  unionYears,
} from "@/lib/combineTrees";
import { DASHBOARD_MODES, isDashboardMode, modeLabel } from "@/lib/dashboardMode";
import { useDarkMode } from "@/lib/useDarkMode";
import SpendingChart, { ChartType } from "@/components/SpendingChart";
import FactCitationViewer from "@/components/FactCitationViewer";
import ResizableSplitPane from "@/components/ResizableSplitPane";
import DashboardNav from "@/components/DashboardNav";
import RingDepthControl from "@/components/RingDepthControl";
import { maxVisibleDepth, additiveChildren } from "@/lib/sunburstTree";

function CombinedPageInner() {
  const dark = useDarkMode();
  const searchParams = useSearchParams();

  const [mode, setMode] = useState<DashboardMode>(() => {
    const m = searchParams.get("mode");
    return isDashboardMode(m) ? m : "actuals";
  });
  const [availableLevels, setAvailableLevels] = useState<LevelSummary[]>([]);
  const [selectedLevels, setSelectedLevels] = useState<string[]>([]);
  const [yearsByLevel, setYearsByLevel] = useState<Record<string, string[]>>({});
  const [year, setYear] = useState<string>("");
  const [combinedTree, setCombinedTree] = useState<TreeNode | null>(null);
  const [missingLevels, setMissingLevels] = useState<string[]>([]);
  const [chartType, setChartType] = useState<ChartType>("bar");
  const [ringDepth, setRingDepth] = useState(2);
  const [branchChoice, setBranchChoice] = useState("canonical");
  const [drillPath, setDrillPath] = useState<TreeNode[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [sourcePrompt, setSourcePrompt] = useState(
    "Hover a leaf item to preview its source citation",
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const m = searchParams.get("mode");
    if (isDashboardMode(m)) setMode(m);
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    setCombinedTree(null);
    setYearsByLevel({});
    setYear("");
    setDrillPath([]);
    setSelectedItemId(null);
    setMissingLevels([]);
    apiDashboard
      .levels(mode)
      .then((data) => {
        if (cancelled) return;
        setAvailableLevels(data);
        setSelectedLevels(data.map((l) => l.level));
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => {
    if (selectedLevels.length === 0) {
      setYearsByLevel({});
      setYear("");
      setCombinedTree(null);
      return;
    }
    let cancelled = false;
    Promise.all(selectedLevels.map((level) => apiDashboard.years(mode, level)))
      .then((lists) => {
        if (cancelled) return;
        const next: Record<string, string[]> = {};
        selectedLevels.forEach((level, i) => {
          next[level] = lists[i];
        });
        setYearsByLevel(next);
        const intersection = intersectYears(lists);
        const union = unionYears(lists);
        const pick =
          (year && intersection.includes(year)
            ? year
            : null) ||
          intersection[intersection.length - 1] ||
          union[union.length - 1] ||
          "";
        setYear(pick);
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, selectedLevels.join(",")]);

  useEffect(() => {
    if (!year || selectedLevels.length === 0) return;
    let cancelled = false;
    setLoading(true);
    setDrillPath([]);
    setSelectedItemId(null);
    Promise.all(
      selectedLevels.map(async (level) => {
        try {
          const tree = await apiDashboard.tree(mode, level, year);
          return { level, tree, ok: true as const };
        } catch {
          return { level, tree: null, ok: false as const };
        }
      }),
    )
      .then((results) => {
        if (cancelled) return;
        const ok = results.filter((r) => r.ok && r.tree) as Array<{
          level: string;
          tree: TreeNode;
          ok: true;
        }>;
        const missing = results.filter((r) => !r.ok).map((r) => r.level);
        setMissingLevels(missing);
        if (ok.length === 0) {
          setCombinedTree(null);
          setError(`No ${mode} data for FY ${year} in the selected levels`);
        } else {
          setCombinedTree(combineLevelTrees(ok, year));
          setError(null);
        }
      })
      .catch((err) => !cancelled && setError(String(err)))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, year, selectedLevels.join(",")]);

  const yearOptions = useMemo(() => {
    const lists = selectedLevels.map((l) => yearsByLevel[l] ?? []);
    const intersection = intersectYears(lists);
    if (intersection.length > 0) return intersection;
    return unionYears(lists);
  }, [selectedLevels, yearsByLevel]);

  const usingUnionYears = useMemo(() => {
    const lists = selectedLevels.map((l) => yearsByLevel[l] ?? []);
    return intersectYears(lists).length === 0 && unionYears(lists).length > 0;
  }, [selectedLevels, yearsByLevel]);

  const currentNode =
    drillPath.length > 0 ? drillPath[drillPath.length - 1] : combinedTree;
  const rawChildren = currentNode?.children ?? null;
  const displayedChildren = useMemo(
    () => (rawChildren?.length ? foldToTopN(additiveChildren(rawChildren)) : []),
    [rawChildren],
  );
  const chartNodes = chartType === "rings" ? rawChildren ?? [] : displayedChildren;
  const branchChoices = useMemo(() => {
    const found = new Set<string>();
    const walk = (nodes: TreeNode[] | null | undefined) => {
      for (const node of nodes ?? []) {
        const relation = node.relationship;
        if (relation?.branch_kind === "related" && relation.branch_family) {
          found.add(relation.branch_family);
        }
        walk(node.children);
      }
    };
    walk(rawChildren);
    return ["canonical", ...Array.from(found).sort()];
  }, [rawChildren]);
  const activeBranchChoice = branchChoices.includes(branchChoice)
    ? branchChoice
    : "canonical";
  const maxRingDepth = useMemo(
    () => Math.max(1, maxVisibleDepth(rawChildren, activeBranchChoice)),
    [rawChildren, activeBranchChoice],
  );
  const centerLabel =
    chartType === "rings"
      ? drillPath.length > 0
        ? drillPath[drillPath.length - 1].name
        : "Combined"
      : null;

  useEffect(() => {
    if (ringDepth > maxRingDepth) setRingDepth(maxRingDepth);
  }, [maxRingDepth, ringDepth]);

  const atLeaf =
    !!currentNode &&
    (!currentNode.children || currentNode.children.length === 0) &&
    drillPath.length > 0;

  function toggleLevel(level: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setSourcePrompt("Hover a leaf item to preview its source citation");
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

  function handleNodeClick(node: TreeNode) {
    if (node.children && node.children.length > 0) {
      setSelectedItemId(node.id);
      setSourcePrompt(
        node.id != null
          ? "Hover a deeper leaf for its citation, or keep this parent selected"
          : "Hover a leaf item to preview its source citation",
      );
      setDrillPath((path) => [...path, node]);
    } else if (node.id !== null) {
      setSelectedItemId(node.id);
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

  return (
    <div className="min-h-screen w-full px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Combined levels
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Compare Federal, State, Territory and Local in one chart for a single
          financial year. Levels are never added into one Australia total.
          Use Debt for GFS liability stocks.
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
              onClick={() => {
                setMode(m);
                setSourcePrompt("Hover a leaf item to preview its source citation");
              }}
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
          value={year}
          onChange={(e) => {
            setYear(e.target.value);
            setDrillPath([]);
            setSelectedItemId(null);
          }}
          className="rounded-md border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-50"
        >
          {yearOptions.map((y) => (
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
              safeDepth={2}
              onChange={setRingDepth}
            />
          )}
        </div>
      </div>

      {chartType === "rings" && (
        <div className="mb-3 space-y-2">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Ring branch">
            {branchChoices.map((choice) => (
              <button
                key={choice}
                type="button"
                onClick={() => setBranchChoice(choice)}
                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                  activeBranchChoice === choice
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-black/10 bg-white text-zinc-600 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-300"
                }`}
              >
                {choice === "canonical" ? "Canonical actual" : choice.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Canonical is the default; related source families are explicit alternatives.
          </p>
        </div>
      )}

      {(usingUnionYears || missingLevels.length > 0) && (
        <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
          {usingUnionYears
            ? "No shared year across all selected levels — showing the latest year available in at least one level."
            : null}
          {missingLevels.length > 0
            ? ` No ${mode} data for FY ${year}: ${missingLevels
                .map((l) => LEVEL_LABELS[l] ?? l)
                .join(", ")}.`
            : null}
        </p>
      )}

      <nav className="mb-4 flex flex-wrap items-center gap-1 text-sm text-zinc-500 dark:text-zinc-400">
        <button type="button" className="hover:underline" onClick={() => setDrillPath([])}>
          Combined — {modeLabel(mode)} — FY {year}
        </button>
        {drillPath.map((node, i) => (
          <span key={`${node.name}-${i}`} className="flex items-center gap-1">
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
          No deeper published breakdown in this measure family for this item.
        </p>
      )}

      <ResizableSplitPane
        left={
          <section
            className="relative min-w-0 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900"
            aria-label="Combined spending chart"
          >
            {combinedTree && !loading ? (
              <SpendingChart
                nodes={chartNodes}
                chartType={chartType}
                dark={dark}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                showTotal={drillPath.length > 0}
                isAdditive={drillPath.length > 0}
                totalLabel={drillPath.length === 0 ? "Non-consolidated comparison" : null}
                totalNote={
                  drillPath.length === 0
                    ? "Levels are shown side-by-side for comparison — not a consolidated Australian total"
                    : null
                }
                ringDepth={ringDepth}
                branchChoice={activeBranchChoice}
                centerLabel={centerLabel}
              />
            ) : (
              <p className="py-20 text-center text-sm text-zinc-500">
                {loading ? "Loading…" : "Select at least one level"}
              </p>
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
            className="min-w-0 rounded-lg border border-black/10 bg-white dark:border-white/10 dark:bg-zinc-900"
            aria-label="Source citation"
          >
            <FactCitationViewer
              key={selectedItemId ?? "empty"}
              factId={selectedItemId}
              emptyMessage={sourcePrompt}
            />
          </aside>
        }
      />
    </div>
  );
}

export default function CombinedPage() {
  return (
    <Suspense fallback={<div className="min-h-screen px-4 py-8 text-sm text-zinc-500">Loading…</div>}>
      <CombinedPageInner />
    </Suspense>
  );
}

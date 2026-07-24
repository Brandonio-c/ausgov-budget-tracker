"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { LevelSummary, TreeNode } from "@/lib/types";
import { foldToTopN } from "@/lib/colors";
import { useDarkMode } from "@/lib/useDarkMode";
import SpendingChart, { ChartType } from "@/components/SpendingChart";
import SourceViewer from "@/components/SourceViewer";
import ResizableSplitPane from "@/components/ResizableSplitPane";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";
import { appHref } from "@/lib/searchDisplay";

const LEVEL_LABELS: Record<string, string> = {
  federal: "Federal",
  state: "State",
  local: "Local",
};

export default function Home() {
  const dark = useDarkMode();

  const [levels, setLevels] = useState<LevelSummary[]>([]);
  const [level, setLevel] = useState<string>("");
  const [years, setYears] = useState<string[]>([]);
  const [year, setYear] = useState<string>("");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [chartType, setChartType] = useState<ChartType>("pie");
  const [drillPath, setDrillPath] = useState<TreeNode[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [sourcePrompt, setSourcePrompt] = useState("Hover a leaf item to preview its source evidence");
  const [error, setError] = useState<string | null>(null);

  // Level list on mount.
  useEffect(() => {
    api
      .levels()
      .then((data) => {
        setLevels(data);
        if (data.length > 0) setLevel(data[0].level);
        setError(null);
      })
      .catch((err) => setError(String(err)));
  }, []);

  // Years for the selected level. Fetches the tree for the default (most
  // recent) year directly, rather than going through `year` state, so a
  // level switch never fires a tree request with the previous level's year.
  useEffect(() => {
    if (!level) return;
    let cancelled = false;
    api
      .years(level)
      .then(async (data) => {
        if (cancelled) return;
        setYears(data);
        const latest = data[data.length - 1] ?? "";
        setYear(latest);
        if (latest) setTree(await api.tree(level, latest));
        setError(null);
      })
      .catch((err) => !cancelled && setError(String(err)));
    return () => {
      cancelled = true;
    };
  }, [level]);

  // Refetch the tree when the user picks a different year from the dropdown.
  // Guarded against firing with a year left over from a previous level.
  useEffect(() => {
    if (!level || !year || !years.includes(year)) return;
    api
      .tree(level, year)
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
  const displayedChildren = useMemo(
    () => (currentNode?.children ? foldToTopN(currentNode.children) : []),
    [currentNode]
  );

  function handleNodeClick(node: TreeNode) {
    if (node.children && node.children.length > 0) {
      setSelectedItemId(null);
      setSourcePrompt("Hover a leaf item to preview its source evidence");
      setDrillPath((path) => [...path, node]);
    } else if (node.id !== null) {
      setSelectedItemId(node.id);
    }
  }

  function handleNodeHover(node: TreeNode) {
    if ((!node.children || node.children.length === 0) && node.id !== null) {
      setSelectedItemId(node.id);
    } else {
      setSelectedItemId(null);
      setSourcePrompt(
        node.name.startsWith("Other (")
          ? `Drill into ${node.name} to see source evidence for each included category`
          : "Drill into this segment to reach its source evidence",
      );
    }
  }

  function handleLevelChange(nextLevel: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setSourcePrompt("Hover a leaf item to preview its source evidence");
    setLevel(nextLevel);
  }

  function handleYearChange(nextYear: string) {
    setDrillPath([]);
    setSelectedItemId(null);
    setSourcePrompt("Hover a leaf item to preview its source evidence");
    setYear(nextYear);
  }

  return (
    <div className="min-h-screen w-full px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          AusGov Budget Tracker
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Phase 1 fallback (spending.db only — no liability stocks). For citation-bearing
          spending and debt use the{" "}
          <a href={appHref("/")} className="underline">
            main dashboard
          </a>{" "}
          or{" "}
          <a href={appHref("/?mode=debt")} className="underline">
            Debt breakdown
          </a>
          .
        </p>
        <DashboardNav />
        <DebtNav />
      </header>

      {error && (
        <p className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error} — is the backend running at {process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}?
        </p>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
          {levels.map((l) => (
            <button
              key={l.level}
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

        <div className="ml-auto flex overflow-hidden rounded-md border border-black/10 dark:border-white/10">
          {(["pie", "bar"] as ChartType[]).map((t) => (
            <button
              key={t}
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
      </div>

      <nav className="mb-4 flex flex-wrap items-center gap-1 text-sm text-zinc-500 dark:text-zinc-400">
        <button className="hover:underline" onClick={() => setDrillPath([])}>
          {LEVEL_LABELS[level] ?? level} — FY {year}
        </button>
        {drillPath.map((node, i) => (
          <span key={i} className="flex items-center gap-1">
            <span>/</span>
            <button
              className="hover:underline"
              onClick={() => setDrillPath((path) => path.slice(0, i + 1))}
            >
              {node.name}
            </button>
          </span>
        ))}
      </nav>

      <ResizableSplitPane
        left={
          <section className="relative min-w-0 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900" aria-label="Spending chart">
            {tree ? (
              <SpendingChart
                nodes={displayedChildren}
                chartType={chartType}
                dark={dark}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
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
          <aside className="min-w-0 rounded-lg border border-black/10 bg-white dark:border-white/10 dark:bg-zinc-900" aria-label="Source viewer">
            <SourceViewer key={selectedItemId ?? "empty"} itemId={selectedItemId} emptyMessage={sourcePrompt} />
          </aside>
        }
      />
    </div>
  );
}

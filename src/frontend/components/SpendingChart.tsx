"use client";

import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { TreeNode } from "@/lib/types";
import { colorsFor, formatMeasureValue } from "@/lib/colors";
import {
  additiveSiblingTotal,
  commonUnit,
  reportedAriaSummary,
  reportedTooltip,
} from "@/lib/chartSemantics";
import {
  buildSunburst,
  resolveSunburstNode,
  sunburstLevelStyles,
} from "@/lib/sunburstTree";
import { useSplitPaneLayout } from "@/components/ResizableSplitPane";

export type ChartType = "pie" | "bar" | "rings";

interface Props {
  nodes: TreeNode[];
  chartType: ChartType;
  dark: boolean;
  onNodeClick: (node: TreeNode) => void;
  onNodeHover: (node: TreeNode) => void;
  totalNote?: string | null;
  ringDepth?: number;
  centerLabel?: string | null;
  /** When false, hide the total line entirely. */
  showTotal?: boolean;
  /** Override default "Total:" label (e.g. Combined non-consolidated). */
  totalLabel?: string | null;
  /** Unit for formatting (AUD | percent | …). */
  valueUnit?: string | null;
  /** When false, do not imply an additive national total. */
  isAdditive?: boolean;
}

const MIN_CHART_HEIGHT = 360;
const MAX_CHART_HEIGHT = 1600;
const DEFAULT_HEIGHT: Record<ChartType, number> = {
  pie: 480,
  rings: 680,
  bar: 480,
};

export default function SpendingChart({
  nodes,
  chartType,
  dark,
  onNodeClick,
  onNodeHover,
  totalNote,
  ringDepth = 2,
  centerLabel = null,
  showTotal = true,
  totalLabel = null,
  valueUnit = null,
  isAdditive = true,
}: Props) {
  const { chartMaximized } = useSplitPaneLayout();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartAreaRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReactECharts>(null);
  const dragStartY = useRef(0);
  const dragStartHeight = useRef(0);
  const manualHeight = useRef<number | null>(null);
  const [chartHeight, setChartHeight] = useState(() => DEFAULT_HEIGHT[chartType]);

  useEffect(() => {
    if (chartMaximized) return;
    setChartHeight((h) => {
      const next = Math.max(h, DEFAULT_HEIGHT[chartType]);
      manualHeight.current = next;
      return next;
    });
  }, [chartType, chartMaximized]);

  // Maximized: size from the flex chart area after layout (not a brittle viewport-top math).
  useEffect(() => {
    if (!chartMaximized) {
      if (manualHeight.current != null) setChartHeight(manualHeight.current);
      return;
    }

    const area = chartAreaRef.current;
    if (!area) return;

    function applySize(height: number) {
      const floor = Math.max(DEFAULT_HEIGHT[chartType], Math.round(window.innerHeight * 0.62));
      const next = Math.min(
        MAX_CHART_HEIGHT,
        Math.max(MIN_CHART_HEIGHT, floor, Math.floor(height)),
      );
      setChartHeight(next);
    }

    const ro = new ResizeObserver((entries) => {
      const h = entries[0]?.contentRect.height ?? 0;
      if (h > 0) applySize(h);
    });
    ro.observe(area);
    // Double-rAF so flex parents finish expanding before first read
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (area.clientHeight > 0) applySize(area.clientHeight);
        else applySize(window.innerHeight * 0.72);
      });
    });
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [chartMaximized, chartType]);

  const colors = useMemo(() => colorsFor(nodes, dark), [nodes, dark]);
  const total = useMemo(() => nodes.reduce((s, n) => s + n.value, 0), [nodes]);

  const sunburst = useMemo(() => {
    if (chartType !== "rings") return null;
    return buildSunburst(nodes, ringDepth, dark);
  }, [nodes, chartType, ringDepth, dark]);

  const lookupRef = useRef(sunburst?.lookup);
  lookupRef.current = sunburst?.lookup;

  const option: EChartsOption = useMemo(() => {
    const textColor = dark ? "#ffffff" : "#0b0b0b";
    const mutedColor = "#898781";
    const chartUnit = commonUnit(nodes, valueUnit);
    const accessibleSummary = nodes
      .map(
        (node) =>
          `${node.name}: ${formatMeasureValue(
            node.value,
            node.relationship?.unit ?? node.unit ?? chartUnit,
          )}`,
      )
      .join("; ");
    const semanticAccessibleSummary =
      chartType === "rings" && sunburst
        ? reportedAriaSummary(sunburst.data, chartUnit)
        : accessibleSummary;

    if (chartType === "rings" && sunburst) {
      const depth = Math.max(1, Math.round(ringDepth));
      return {
        backgroundColor: "transparent",
        tooltip: {
          trigger: "item",
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter: (p: any) => {
            const treePath = (p.treePathInfo || [])
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              .filter((x: any) => x.name)
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              .map((x: any) => x.name)
              .join(" › ");
            return reportedTooltip(
              treePath || p.name,
              p.data ?? {},
              p.value ?? 0,
              chartUnit,
            );
          },
        },
        aria: {
          enabled: true,
          label: { description: `Spending rings. ${semanticAccessibleSummary}` },
        },
        series: [
          {
            type: "sunburst",
            radius: chartMaximized ? ["8%", "96%"] : ["12%", "98%"],
            center: ["50%", "50%"],
            sort: undefined,
            // App-owned drill (re-root via drillPath); disable ECharts built-in zoom
            nodeClick: false,
            emphasis: {
              focus: "ancestor",
              itemStyle: { borderWidth: 2 },
            },
            levels: [{}, ...sunburstLevelStyles(dark, depth)],
            label: {
              color: textColor,
              minAngle: 8,
              overflow: "truncate",
            },
            data: sunburst.data,
          },
        ],
        graphic: centerLabel
          ? [
              {
                type: "text",
                left: "center",
                top: "middle",
                style: {
                  text: `${centerLabel}\n${
                    chartUnit === "mixed_units"
                      ? "Mixed units"
                      : formatMeasureValue(sunburst.total, chartUnit)
                  }`,
                  fill: textColor,
                  fontSize: 14,
                  fontWeight: 600,
                  align: "center",
                  lineHeight: 22,
                },
                z: 100,
              },
            ]
          : undefined,
      };
    }

    if (chartType === "pie") {
      return {
        backgroundColor: "transparent",
        tooltip: {
          trigger: "item",
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter: (p: any) =>
            reportedTooltip(p.name, p.data ?? {}, p.value ?? 0, chartUnit),
        },
        aria: {
          enabled: true,
          label: { description: `Spending pie chart. ${accessibleSummary}` },
        },
        series: [
          {
            type: "pie",
            // Maximized: use more of the plot so the ring isn't a small island
            radius: chartMaximized ? ["30%", "86%"] : ["38%", "72%"],
            center: ["50%", "50%"],
            avoidLabelOverlap: true,
            itemStyle: {
              borderColor: dark ? "#1a1a19" : "#fcfcfb",
              borderWidth: 2,
            },
            label: {
              color: textColor,
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter: (p: any) =>
                `${p.name}\n${formatMeasureValue(
                  p.data?.reportedValue ?? p.value ?? 0,
                  p.data?.reportedUnit ?? chartUnit,
                )}`,
              fontSize: chartMaximized ? 13 : 12,
            },
            labelLine: { lineStyle: { color: mutedColor } },
            data: nodes.map((n, i) => ({
              name: n.name,
              value: n.value,
              reportedValue: n.value,
              reportedUnit: n.relationship?.unit ?? n.unit ?? chartUnit,
              reportedParentValue: additiveSiblingTotal(nodes, n),
              relationship: n.relationship,
              isRelated:
                n.relationship?.branch_kind === "related" ||
                n.breakdown?.kind === "related_breakdown",
              itemStyle: { color: colors[i] },
            })),
          },
        ],
      };
    }

    const sorted = [...nodes].sort((a, b) => a.value - b.value);
    const sortedColors = colorsFor(sorted, dark);

    return {
      backgroundColor: "transparent",
      grid: { left: "2%", right: "12%", top: "4%", bottom: "4%", containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: {
          color: mutedColor,
          formatter: (v: number) => formatMeasureValue(v, chartUnit),
        },
        axisLine: { lineStyle: { color: dark ? "#383835" : "#c3c2b7" } },
        splitLine: { lineStyle: { color: dark ? "#2c2c2a" : "#e1e0d9" } },
      },
      yAxis: {
        type: "category",
        data: sorted.map((n) => n.name),
        axisLabel: { color: textColor, width: 160, overflow: "truncate" },
        axisLine: { lineStyle: { color: dark ? "#383835" : "#c3c2b7" } },
      },
      tooltip: {
        trigger: "item",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (p: any) =>
          reportedTooltip(p.name, p.data ?? {}, p.value ?? 0, chartUnit),
      },
      aria: {
        enabled: true,
        label: { description: `Spending bar chart. ${accessibleSummary}` },
      },
      series: [
        {
          type: "bar",
          data: sorted.map((n, i) => ({
            value: n.value,
            reportedValue: n.value,
            reportedUnit: n.relationship?.unit ?? n.unit ?? chartUnit,
            relationship: n.relationship,
            isRelated:
              n.relationship?.branch_kind === "related" ||
              n.breakdown?.kind === "related_breakdown",
            itemStyle: { color: sortedColors[i], borderRadius: [0, 4, 4, 0] },
          })),
          label: {
            show: true,
            position: "right",
            color: mutedColor,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter: (p: any) =>
              formatMeasureValue(
                p.data?.reportedValue ?? p.value ?? 0,
                p.data?.reportedUnit ?? chartUnit,
              ),
          },
          barMaxWidth: 28,
        },
      ],
    };
  }, [
    nodes,
    chartType,
    dark,
    colors,
    sunburst,
    ringDepth,
    centerLabel,
    chartMaximized,
    valueUnit,
  ]);

  const nodeForPieBar = (params: { dataIndex: number }) => {
    if (chartType === "bar") {
      const sorted = [...nodes].sort((a, b) => a.value - b.value);
      return sorted[params.dataIndex];
    }
    return nodes[params.dataIndex];
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleClick = (params: any) => {
    if (chartType === "rings") {
      const node = resolveSunburstNode(params, lookupRef.current);
      if (node) onNodeClick(node);
      return;
    }
    onNodeClick(nodeForPieBar(params));
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMouseOver = (params: any) => {
    if (chartType === "rings") {
      const node = resolveSunburstNode(params, lookupRef.current);
      if (node) onNodeHover(node);
      return;
    }
    onNodeHover(nodeForPieBar(params));
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => chartRef.current?.getEchartsInstance().resize());
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    chartRef.current?.getEchartsInstance().resize();
  }, [chartHeight]);

  function clampHeight(h: number) {
    return Math.min(MAX_CHART_HEIGHT, Math.max(MIN_CHART_HEIGHT, Math.round(h)));
  }

  function setManualHeight(h: number) {
    const next = clampHeight(h);
    manualHeight.current = next;
    setChartHeight(next);
  }

  function handleResizePointerDown(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragStartY.current = event.clientY;
    dragStartHeight.current = chartHeight;
  }

  function handleResizePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    const delta = event.clientY - dragStartY.current;
    setManualHeight(dragStartHeight.current + delta);
  }

  function handleResizePointerUp(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  if (nodes.length === 0) {
    return <p className="text-sm text-zinc-500">No data at this level.</p>;
  }

  const displayTotal = chartType === "rings" && sunburst ? sunburst.total : total;
  const displayUnit = commonUnit(nodes, valueUnit);
  const fmt = (v: number) =>
    displayUnit === "mixed_units"
      ? "Mixed units — no total"
      : formatMeasureValue(v, displayUnit);
  const showTotalLine =
    showTotal &&
    isAdditive &&
    displayUnit !== "percent" &&
    displayUnit !== "mixed_units";

  return (
    <div
      ref={containerRef}
      data-chart-panel
      className={
        chartMaximized
          ? "flex h-[calc(100dvh-9rem)] min-h-[calc(100dvh-9rem)] flex-col"
          : "flex flex-col"
      }
    >
      <div
        ref={chartAreaRef}
        className={chartMaximized ? "min-h-0 w-full flex-1" : "w-full"}
      >
        <ReactECharts
          ref={chartRef}
          option={option}
          style={{ height: chartHeight, width: "100%" }}
          onEvents={{ click: handleClick, mouseover: handleMouseOver }}
          notMerge
        />
      </div>
      {showTotalLine ? (
        <p className="mt-1 shrink-0 text-center text-sm text-zinc-500 dark:text-zinc-400">
          {totalLabel ?? "Total"}: {fmt(displayTotal)}
          {totalNote ? (
            <span className="block text-xs text-amber-700 dark:text-amber-300/90">{totalNote}</span>
          ) : null}
        </p>
      ) : (
        <p className="mt-1 shrink-0 text-center text-sm text-zinc-500 dark:text-zinc-400">
          {totalLabel ?? (!isAdditive ? "Non-consolidated comparison" : null)}
          {totalNote ? (
            <span className="block text-xs text-amber-700 dark:text-amber-300/90">{totalNote}</span>
          ) : null}
        </p>
      )}

      {!chartMaximized ? (
        <>
          <div
            role="separator"
            aria-orientation="horizontal"
            aria-label="Drag down to enlarge chart"
            aria-valuemin={MIN_CHART_HEIGHT}
            aria-valuemax={MAX_CHART_HEIGHT}
            aria-valuenow={chartHeight}
            tabIndex={0}
            title="Drag down to enlarge the chart; double-click to reset"
            onDoubleClick={() => setManualHeight(DEFAULT_HEIGHT[chartType])}
            onPointerDown={handleResizePointerDown}
            onPointerMove={handleResizePointerMove}
            onPointerUp={handleResizePointerUp}
            onPointerCancel={handleResizePointerUp}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setManualHeight(chartHeight + 40);
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setManualHeight(chartHeight - 40);
              } else if (e.key === "Home") {
                e.preventDefault();
                setManualHeight(DEFAULT_HEIGHT[chartType]);
              }
            }}
            className="group mt-3 flex h-5 touch-none cursor-row-resize items-center justify-center outline-none"
          >
            <div className="relative flex h-1 w-24 items-center justify-center rounded-full bg-black/15 transition-colors group-hover:bg-blue-500 group-focus:bg-blue-500 dark:bg-white/15">
              <span className="absolute flex h-6 w-6 items-center justify-center rounded-full border border-black/15 bg-white text-xs font-semibold text-zinc-500 shadow-sm group-hover:border-blue-500 group-hover:text-blue-600 group-focus:border-blue-500 group-focus:text-blue-600 dark:border-white/20 dark:bg-zinc-800 dark:text-zinc-300">
                ↕
              </span>
            </div>
          </div>
          <p className="mt-1 text-center text-[11px] text-zinc-400 dark:text-zinc-500">
            Drag ↕ down to enlarge
          </p>
        </>
      ) : null}
    </div>
  );
}

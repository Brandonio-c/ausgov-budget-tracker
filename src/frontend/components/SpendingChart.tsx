"use client";

import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { useEffect, useMemo, useRef } from "react";
import { TreeNode } from "@/lib/types";
import { colorsFor, formatAud, formatAudFull } from "@/lib/colors";

export type ChartType = "pie" | "bar";

interface Props {
  nodes: TreeNode[]; // already folded to top-N + "Other"
  chartType: ChartType;
  dark: boolean;
  onNodeClick: (node: TreeNode) => void;
  onNodeHover: (node: TreeNode) => void;
}

export default function SpendingChart({ nodes, chartType, dark, onNodeClick, onNodeHover }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReactECharts>(null);
  const colors = useMemo(() => colorsFor(nodes, dark), [nodes, dark]);
  const total = useMemo(() => nodes.reduce((s, n) => s + n.value, 0), [nodes]);

  const option: EChartsOption = useMemo(() => {
    const textColor = dark ? "#ffffff" : "#0b0b0b";
    const mutedColor = "#898781";

    if (chartType === "pie") {
      return {
        backgroundColor: "transparent",
        tooltip: {
          trigger: "item",
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter: (p: any) => `${p.name}<br/>${formatAudFull(p.value ?? 0)} (${p.percent}%)`,
        },
        series: [
          {
            type: "pie",
            radius: ["38%", "72%"],
            avoidLabelOverlap: true,
            itemStyle: {
              borderColor: dark ? "#1a1a19" : "#fcfcfb",
              borderWidth: 2,
            },
            label: {
              color: textColor,
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter: (p: any) => `${p.name}\n${formatAud(p.value ?? 0)}`,
              fontSize: 12,
            },
            labelLine: { lineStyle: { color: mutedColor } },
            data: nodes.map((n, i) => ({
              name: n.name,
              value: n.value,
              itemStyle: { color: colors[i] },
            })),
          },
        ],
      };
    }

    // Horizontal bar — long jurisdiction/category names read better this way,
    // and it keeps a single value axis (no dual-axis).
    const sorted = [...nodes].sort((a, b) => a.value - b.value); // ascending so largest ends up on top
    const sortedColors = colorsFor(sorted, dark);

    return {
      backgroundColor: "transparent",
      grid: { left: "2%", right: "12%", top: "4%", bottom: "4%", containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: mutedColor, formatter: (v: number) => formatAud(v) },
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
        formatter: (p: any) => `${p.name}<br/>${formatAudFull(p.value ?? 0)}`,
      },
      series: [
        {
          type: "bar",
          data: sorted.map((n, i) => ({
            value: n.value,
            itemStyle: { color: sortedColors[i], borderRadius: [0, 4, 4, 0] },
          })),
          label: {
            show: true,
            position: "right",
            color: mutedColor,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter: (p: any) => formatAud(p.value ?? 0),
          },
          barMaxWidth: 28,
        },
      ],
    };
  }, [nodes, chartType, dark, colors]);

  const nodeForEvent = (params: { dataIndex: number }) => {
    if (chartType === "bar") {
      const sorted = [...nodes].sort((a, b) => a.value - b.value);
      return sorted[params.dataIndex];
    }
    return nodes[params.dataIndex];
  };

  const handleClick = (params: { dataIndex: number }) => onNodeClick(nodeForEvent(params));

  const handleMouseOver = (params: { dataIndex: number }) => onNodeHover(nodeForEvent(params));

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => chartRef.current?.getEchartsInstance().resize());
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  if (nodes.length === 0) {
    return <p className="text-sm text-zinc-500">No data at this level.</p>;
  }

  return (
    <div ref={containerRef}>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: 480, width: "100%" }}
        onEvents={{ click: handleClick, mouseover: handleMouseOver }}
        notMerge
      />
      <p className="mt-1 text-center text-sm text-zinc-500 dark:text-zinc-400">
        Total: {formatAudFull(total)}
      </p>
    </div>
  );
}

"use client";

import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { CATEGORICAL_DARK, CATEGORICAL_LIGHT } from "@/lib/colors";
import { formatAud } from "@/lib/colors";

export type MfsChartSeries = {
  name: string;
  points: Array<{ x: string; y: number; factId?: string }>;
};

interface Props {
  series: MfsChartSeries[];
  dark: boolean;
  unit?: string;
  onPointClick?: (seriesName: string, pointIndex: number) => void;
  height?: number;
}

/** Single-axis line chart for MFS time series (YTD flows or point-in-time
 * stocks) - never a dual-axis chart, and never used to sum series together;
 * each named series is its own line, styled with the app's validated
 * categorical palette in fixed hue order. */
export default function MfsLineChart({ series, dark, unit = "AUD", onPointClick, height = 360 }: Props) {
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  const categories = series[0]?.points.map((p) => p.x) ?? [];
  const textColor = dark ? "#e5e5e5" : "#18181b";
  const gridColor = dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)";

  const option: EChartsOption = {
    backgroundColor: "transparent",
    textStyle: { color: textColor },
    grid: { left: 64, right: 24, top: series.length > 1 ? 40 : 16, bottom: 40 },
    legend:
      series.length > 1
        ? { top: 0, textStyle: { color: textColor }, data: series.map((s) => s.name) }
        : undefined,
    tooltip: {
      trigger: "axis",
      valueFormatter: (value) =>
        unit === "percent" ? `${Number(value).toFixed(2)}%` : formatAud(Number(value)),
    },
    xAxis: {
      type: "category",
      data: categories,
      axisLine: { lineStyle: { color: gridColor } },
      axisLabel: { color: textColor },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: textColor,
        formatter: (value: number) => (unit === "percent" ? `${value}%` : formatAud(value)),
      },
      splitLine: { lineStyle: { color: gridColor } },
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: "line",
      data: s.points.map((p) => p.y),
      lineStyle: { width: 2, color: palette[i % palette.length] },
      itemStyle: { color: palette[i % palette.length] },
      symbolSize: 8,
      showSymbol: true,
    })),
  };

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      onEvents={
        onPointClick
          ? {
              click: (params: { seriesName: string; dataIndex: number }) =>
                onPointClick(params.seriesName, params.dataIndex),
            }
          : undefined
      }
    />
  );
}

"use client";

import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { useEffect, useMemo, useRef } from "react";
import { DashboardSeries } from "@/lib/api";
import { CATEGORICAL_DARK, CATEGORICAL_LIGHT, formatAud, formatAudFull } from "@/lib/colors";
import { LEVEL_LABELS } from "@/lib/combineTrees";

export type TimelinePointClick = {
  level: string;
  financial_year: string;
  total_aud: number;
  fact_id: number | null;
};

interface Props {
  data: DashboardSeries;
  dark: boolean;
  onPointClick?: (point: TimelinePointClick) => void;
}

export default function TimelineChart({ data, dark, onPointClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReactECharts>(null);
  const textColor = dark ? "#ffffff" : "#0b0b0b";
  const mutedColor = "#898781";
  const palette = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;

  const years = data.years;

  const option: EChartsOption = useMemo(() => {
    return {
      backgroundColor: "transparent",
      legend: {
        top: 0,
        textStyle: { color: textColor },
      },
      grid: { left: "2%", right: "4%", top: 48, bottom: "8%", containLabel: true },
      tooltip: {
        trigger: "axis",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (params: any) => {
          const rows = Array.isArray(params) ? params : [params];
          const fy = rows[0]?.axisValueLabel ?? rows[0]?.name ?? "";
          const lines = rows.map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (p: any) =>
              `${p.marker}${p.seriesName}: ${formatAudFull(Number(p.value) || 0)}`,
          );
          return `FY ${fy}<br/>${lines.join("<br/>")}`;
        },
      },
      xAxis: {
        type: "category",
        data: years,
        axisLabel: { color: mutedColor, rotate: years.length > 8 ? 35 : 0 },
        axisLine: { lineStyle: { color: dark ? "#383835" : "#c3c2b7" } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: mutedColor, formatter: (v: number) => formatAud(v) },
        splitLine: { lineStyle: { color: dark ? "#2c2c2a" : "#e1e0d9" } },
        axisLine: { lineStyle: { color: dark ? "#383835" : "#c3c2b7" } },
      },
      series: data.series.map((s, i) => {
        const byYear = new Map(s.points.map((p) => [p.financial_year, p]));
        return {
          name: LEVEL_LABELS[s.level] ?? s.level,
          type: "line" as const,
          connectNulls: false,
          showSymbol: true,
          symbolSize: 8,
          itemStyle: { color: palette[i % palette.length] },
          lineStyle: { width: 2.5 },
          data: years.map((fy) => {
            const point = byYear.get(fy);
            return point ? point.total_aud : null;
          }),
        };
      }),
    };
  }, [data, dark, years, palette, textColor]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => chartRef.current?.getEchartsInstance().resize());
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  function handleClick(params: {
    seriesName?: string;
    name?: string;
    value?: number | null;
    dataIndex?: number;
    seriesIndex?: number;
  }) {
    if (!onPointClick || params.seriesIndex == null || params.dataIndex == null) return;
    const series = data.series[params.seriesIndex];
    if (!series) return;
    const fy = years[params.dataIndex];
    const point = series.points.find((p) => p.financial_year === fy);
    if (!point) return;
    onPointClick({
      level: series.level,
      financial_year: point.financial_year,
      total_aud: point.total_aud,
      fact_id: point.fact_id,
    });
  }

  if (years.length === 0 || data.series.every((s) => s.points.length === 0)) {
    return <p className="py-20 text-center text-sm text-zinc-500">No series data for this selection.</p>;
  }

  return (
    <div ref={containerRef}>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: 480, width: "100%" }}
        onEvents={{ click: handleClick }}
        notMerge
      />
      <p className="mt-1 text-center text-xs text-zinc-500 dark:text-zinc-400">{data.note}</p>
    </div>
  );
}

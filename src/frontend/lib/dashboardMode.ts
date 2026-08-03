import type { DashboardMode } from "@/lib/api";

/** Primary nav modes (Economy expands via submodes). */
export const DASHBOARD_MODES: DashboardMode[] = [
  "actuals",
  "budget",
  "debt",
  "revenue",
  "gdp_current",
];

export const ECONOMY_SUBMODES: DashboardMode[] = [
  "gdp_current",
  "gdp_chain_volume",
  "gdp_expenditure",
  "gva_current",
  "gva_chain_volume",
  "gsp_current",
  "gsp_chain_volume",
  "ratios",
];

export function modeLabel(mode: DashboardMode): string {
  const labels: Record<string, string> = {
    actuals: "Actuals",
    budget: "Budget",
    debt: "Debt",
    revenue: "Revenue",
    gdp: "GDP — nominal (legacy)",
    gdp_current: "GDP — nominal",
    gdp_chain_volume: "GDP — real",
    gdp_expenditure: "GDP expenditure",
    gva_current: "Industry GVA",
    gva_chain_volume: "Industry GVA (real)",
    gsp_current: "State GSP",
    gsp_chain_volume: "State GSP (real)",
    ratios: "Tax as % of GDP",
  };
  return labels[mode] ?? mode;
}

export function isDashboardMode(value: string | null | undefined): value is DashboardMode {
  return (
    value === "actuals" ||
    value === "budget" ||
    value === "debt" ||
    value === "revenue" ||
    value === "gdp" ||
    value === "gdp_current" ||
    value === "gdp_chain_volume" ||
    value === "gdp_expenditure" ||
    value === "gva_current" ||
    value === "gva_chain_volume" ||
    value === "gsp_current" ||
    value === "gsp_chain_volume" ||
    value === "ratios"
  );
}

export function isEconomyMode(mode: DashboardMode): boolean {
  return ECONOMY_SUBMODES.includes(mode) || mode === "gdp";
}

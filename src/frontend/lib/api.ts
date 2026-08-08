import {
  BreakdownMeta,
  DashboardAvailability,
  LevelSummary,
  SourceContext,
  SpendingItem,
  TreeNode,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    let detail = `${path} -> HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function getArrayBuffer(path: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  const res = await fetch(`${API_BASE}${path}`, { signal });
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return res.arrayBuffer();
}

export const api = {
  levels: () => getJson<LevelSummary[]>("/api/spending/levels"),
  years: (level: string) => getJson<string[]>(`/api/spending/years?level=${encodeURIComponent(level)}`),
  tree: (level: string, year: string) =>
    getJson<TreeNode>(`/api/spending/tree?level=${encodeURIComponent(level)}&year=${encodeURIComponent(year)}`),
  item: (id: number) => getJson<SpendingItem>(`/api/spending/item/${id}`),
  itemContext: (id: number) => getJson<SourceContext>(`/api/spending/item/${id}/context`),
  itemSourceFile: (id: number, signal?: AbortSignal) =>
    getArrayBuffer(`/api/spending/item/${id}/source-file`, signal),
};

export type DashboardMode =
  | "actuals"
  | "budget"
  | "debt"
  | "revenue"
  | "gdp"
  | "gdp_current"
  | "gdp_chain_volume"
  | "gdp_expenditure"
  | "gva_current"
  | "gva_chain_volume"
  | "gsp_current"
  | "gsp_chain_volume"
  | "ratios";

export type Citation = {
  fact_id: number;
  fact_key: string;
  landing_url: string;
  original_resource_url: string;
  cached_copy_url: string;
  locator: string;
  sha256?: string | null;
  retrieved_at?: string | null;
  amount_aud?: number | null;
  financial_year?: string;
  measure_type?: string;
};

export type DashboardItem = {
  id: number;
  financial_year: string;
  level_of_government: string;
  jurisdiction: string;
  category: string | null;
  amount_aud: number;
  measure_type: string;
  accounting_basis: string;
  estimate_status: string;
  source_document_name: string;
  citation: Citation;
};

export type EvidenceHighlight = {
  cell?: string | null;
  row_index?: number | null;
  column_index?: number | null;
} | null;

export type FactEvidence = {
  fact_id: number;
  media_type: "spreadsheet" | "pdf" | "text_chunk" | "unsupported";
  file_name: string | null;
  content_type: string | null;
  has_source_file: boolean;
  sheet_name: string | null;
  cell: string | null;
  cell_range: string | null;
  page_number: number | null;
  row_number: number | null;
  text_anchor: string | null;
  purpose: string | null;
  financial_year_label: string | null;
  unit: string | null;
  amount_aud: number | null;
  highlight: EvidenceHighlight;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  note: string | null;
  locator: string | null;
  breakdown_note?: string | null;
  citation: Citation;
  item: Omit<DashboardItem, "citation">;
};

export type V2Tree = {
  name: string;
  shape: "flat";
  value: number;
  total_count: number;
  total_value: number;
  next_cursor: string | null;
  children: Array<{ name: string; value: number; id: number; citation: Citation }>;
};

export type SeriesPoint = {
  financial_year: string;
  total_aud: number;
  fact_id: number | null;
};

export type SeriesLevel = {
  level: string;
  points: SeriesPoint[];
};

export type DashboardSeries = {
  mode: DashboardMode;
  category: string | null;
  years: string[];
  series: SeriesLevel[];
  note: string;
  warning?: string | null;
};

export type SearchSort = "amount_desc" | "amount_asc" | "fy_desc" | "name";

export type SearchParams = {
  q?: string;
  mode?: DashboardMode | "";
  level?: string;
  jurisdiction?: string;
  fy_from?: string;
  fy_to?: string;
  amount_min?: number | null;
  amount_max?: number | null;
  limit?: number;
  offset?: number;
  sort?: SearchSort;
};

export type SearchHit = {
  id: number;
  node_name: string;
  amount_aud: number;
  financial_year: string;
  jurisdiction: string | null;
  level: string;
  measure_type: string;
  accounting_basis: string;
  estimate_status: string;
  source_title: string | null;
};

export type SearchResponse = {
  total: number;
  limit: number;
  offset: number;
  items: SearchHit[];
};

export type UnifiedSearchHit = {
  kind: "spending" | "document";
  score: number;
  method: string;
  href?: string;
  fact_id?: number | null;
  node_name?: string;
  display_title?: string;
  matched_label?: string;
  matched_terms?: string[];
  source_title?: string | null;
  jurisdiction?: string | null;
  level?: string | null;
  financial_year?: string | null;
  measure_type?: string;
  accounting_basis?: string;
  estimate_status?: string;
  amount_aud?: number;
  mode?: DashboardMode | string | null;
  source_document_id?: number;
  source_key?: string;
  title?: string;
  publisher?: string | null;
  government_level?: string | null;
  landing_url?: string | null;
  local_path?: string | null;
  chunk_index?: number;
  snippet?: string | null;
};

export type UnifiedSearchResponse = {
  q: string;
  scope: string;
  index_ready: boolean;
  embed_model?: string | null;
  spending: UnifiedSearchHit[];
  documents: UnifiedSearchHit[];
  note?: string;
};

export const apiSearch = {
  unified: (q: string, scope: "all" | "spending" | "documents" = "all", limit = 20) => {
    const params = new URLSearchParams({
      q,
      scope,
      limit: String(limit),
    });
    return getJson<UnifiedSearchResponse>(`/v2/search?${params.toString()}`);
  },
  status: () => getJson<{ index_ready: boolean }>("/v2/search/status"),
};

export const apiDashboard = {
  levels: (mode: DashboardMode) =>
    getJson<LevelSummary[]>(`/v2/dashboard/levels?mode=${encodeURIComponent(mode)}`),
  years: (mode: DashboardMode, level: string) =>
    getJson<string[]>(
      `/v2/dashboard/years?mode=${encodeURIComponent(mode)}&level=${encodeURIComponent(level)}`,
    ),
  availability: (mode: DashboardMode, level: string) =>
    getJson<DashboardAvailability[]>(
      `/v2/dashboard/availability?mode=${encodeURIComponent(mode)}&level=${encodeURIComponent(level)}`,
    ),
  tree: (mode: DashboardMode, level: string, year: string) =>
    getJson<TreeNode>(
      `/v2/dashboard/tree?mode=${encodeURIComponent(mode)}&level=${encodeURIComponent(level)}&year=${encodeURIComponent(year)}`,
    ),
  series: (mode: DashboardMode, levels: string[], category?: string | null) => {
    const q = new URLSearchParams({
      mode,
      levels: levels.join(","),
    });
    if (category) q.set("category", category);
    return getJson<DashboardSeries>(`/v2/dashboard/series?${q.toString()}`);
  },
  item: (id: number) => getJson<DashboardItem>(`/v2/dashboard/item/${id}`),
  itemChildren: (id: number, year?: string) =>
    getJson<{
      fact_id: number;
      financial_year: string;
      kind: string;
      children: TreeNode[];
      breakdown: BreakdownMeta | null;
      breakdown_note?: string | null;
      parent_amount_aud?: number;
    }>(
      `/v2/dashboard/item/${id}/children${
        year ? `?year=${encodeURIComponent(year)}` : ""
      }`,
    ),
  itemEvidence: (id: number) => getJson<FactEvidence>(`/v2/dashboard/item/${id}/evidence`),
  itemSourceFile: (id: number, signal?: AbortSignal) =>
    getArrayBuffer(`/v2/dashboard/item/${id}/source-file`, signal),
};

export const apiV2 = {
  citation: (id: number) => getJson<Citation>(`/v2/facts/${id}/citation`),
  search: (params: SearchParams) => {
    const q = new URLSearchParams();
    if (params.q?.trim()) q.set("q", params.q.trim());
    if (params.mode) q.set("mode", params.mode);
    if (params.level) q.set("level", params.level);
    if (params.jurisdiction?.trim()) q.set("jurisdiction", params.jurisdiction.trim());
    if (params.fy_from?.trim()) q.set("fy_from", params.fy_from.trim());
    if (params.fy_to?.trim()) q.set("fy_to", params.fy_to.trim());
    if (params.amount_min != null && Number.isFinite(params.amount_min)) {
      q.set("amount_min", String(params.amount_min));
    }
    if (params.amount_max != null && Number.isFinite(params.amount_max)) {
      q.set("amount_max", String(params.amount_max));
    }
    q.set("limit", String(params.limit ?? 50));
    q.set("offset", String(params.offset ?? 0));
    q.set("sort", params.sort ?? "amount_desc");
    return getJson<SearchResponse>(`/v2/facts/search?${q.toString()}`);
  },
  tree: (params: {
    compatibility_group: string;
    accounting_basis: string;
    estimate_status: string;
    financial_year: string;
    limit?: number;
    cursor?: string | null;
  }) => {
    const q = new URLSearchParams({
      compatibility_group: params.compatibility_group,
      accounting_basis: params.accounting_basis,
      estimate_status: params.estimate_status,
      financial_year: params.financial_year,
      limit: String(params.limit ?? 50),
    });
    if (params.cursor) q.set("cursor", params.cursor);
    return getJson<V2Tree>(`/v2/tree?${q.toString()}`);
  },
};

export type MfsFlowOrStock = "flow" | "stock" | "balance" | "stock_balance";

export type MfsMeasureInfo = {
  measure_type: string;
  label: string;
  economic_meaning: string;
  flow_or_stock: MfsFlowOrStock;
  compatibility_group: string;
  accounting_basis: string;
  unit: string;
  sign_convention: string;
  dashboard_treatment: string;
  not_published_before_financial_year?: string | null;
  only_published_financial_years?: string[] | null;
  reserved_not_loaded_this_milestone?: boolean | null;
};

export type MfsCitation = {
  locator: string;
  cached_copy_path?: string | null;
};

export type MfsFact = {
  label: string;
  measure_type: string;
  flow_or_stock: MfsFlowOrStock;
  amount_aud: number;
  unit: string;
  financial_year: string;
  reporting_month: string;
  elapsed_months: number;
  period_start?: string | null;
  period_end: string;
  period_granularity: string;
  accounting_basis: string;
  estimate_status: string;
  compatibility_group: string;
  publication_date?: string | null;
  vintage: string;
  citation: MfsCitation;
};

export type MfsSeriesResponse = {
  measure_type: string;
  flow_or_stock: MfsFlowOrStock;
  facts: MfsFact[];
};

export type MfsCompareResponse = {
  measure_types: string[];
  series: MfsSeriesResponse[];
  warning?: string | null;
};

export const apiMfs = {
  measures: () => getJson<MfsMeasureInfo[]>("/v2/mfs/measures"),
  years: (measureType: string) =>
    getJson<string[]>(`/v2/mfs/years?measure_type=${encodeURIComponent(measureType)}`),
  series: (measureType: string, financialYear?: string) => {
    const q = new URLSearchParams({ measure_type: measureType });
    if (financialYear) q.set("financial_year", financialYear);
    return getJson<MfsSeriesResponse>(`/v2/mfs/series?${q.toString()}`);
  },
  compare: (measureTypes: string[], financialYear?: string) => {
    const q = new URLSearchParams({ measure_types: measureTypes.join(",") });
    if (financialYear) q.set("financial_year", financialYear);
    return getJson<MfsCompareResponse>(`/v2/mfs/compare?${q.toString()}`);
  },
};

export type VicAfsFlowOrStock = "flow" | "stock" | "balance" | "stock_balance";

export type VicAfsMeasureInfo = {
  measure_type: string;
  label: string;
  economic_meaning: string;
  flow_or_stock: VicAfsFlowOrStock;
  source_sheet: string;
  compatibility_group: string;
  accounting_basis: string;
  unit: string;
};

export type VicAfsCitation = {
  locator: string;
  cached_copy_path?: string | null;
};

export type VicAfsFact = {
  label: string;
  measure_type: string;
  flow_or_stock: VicAfsFlowOrStock;
  amount_aud: number;
  financial_year: string;
  period_end: string;
  accounting_basis: string;
  estimate_status: string;
  compatibility_group: string;
  vintage: string;
  citation: VicAfsCitation;
};

export type VicAfsSeriesResponse = {
  measure_type: string;
  flow_or_stock: VicAfsFlowOrStock;
  facts: VicAfsFact[];
};

export const apiVicAfs = {
  measures: () => getJson<VicAfsMeasureInfo[]>("/v2/vic-afs/measures"),
  series: (measureType: string) =>
    getJson<VicAfsSeriesResponse>(`/v2/vic-afs/series?measure_type=${encodeURIComponent(measureType)}`),
};

export type VicBpoFlowOrStock = "flow" | "stock" | "balance" | "stock_balance";

export type VicBpoMeasureInfo = {
  measure_type: string;
  label: string;
  economic_meaning: string;
  flow_or_stock: VicBpoFlowOrStock;
  source_sheet: string;
  compatibility_group: string;
  accounting_basis: string;
  unit: string;
};

export type VicBpoCitation = {
  locator: string;
  cached_copy_path?: string | null;
};

export type VicBpoFact = {
  label: string;
  measure_type: string;
  flow_or_stock: VicBpoFlowOrStock;
  amount_aud: number;
  financial_year: string;
  period_end: string;
  accounting_basis: string;
  estimate_status: string;
  compatibility_group: string;
  citation: VicBpoCitation;
};

export type VicBpoSeriesResponse = {
  measure_type: string;
  flow_or_stock: VicBpoFlowOrStock;
  facts: VicBpoFact[];
};

export const apiVicBpo = {
  measures: () => getJson<VicBpoMeasureInfo[]>("/v2/vic-bpo/measures"),
  series: (measureType: string) =>
    getJson<VicBpoSeriesResponse>(`/v2/vic-bpo/series?measure_type=${encodeURIComponent(measureType)}`),
};

// VIC BPO's deferred `SOCE`/`Admin` sheets - a separate backend endpoint
// and compatibility_group set (see src/backend/routers/v2/vic_bpo_soce_admin.py
// for why), but presented to the user as more measures within the same
// "VIC BPO" toggle on the GFS explorer page - merged client-side with
// apiVicBpo's own measures/series calls rather than getting a new
// dropdown or page.
export const apiVicBpoSoceAdmin = {
  measures: () => getJson<VicBpoMeasureInfo[]>("/v2/vic-bpo-soce-admin/measures"),
  series: (measureType: string) =>
    getJson<VicBpoSeriesResponse>(
      `/v2/vic-bpo-soce-admin/series?measure_type=${encodeURIComponent(measureType)}`,
    ),
};

// Tasmanian Treasury's "GGS Key Fiscal Measures Time Series" - a
// genuine multi-year time series (16 financial years, each with one
// vintage: actual / revised_estimate / forward_estimate), unlike
// vic_bpo_*'s single-year actual-vs-budget comparison. Its own
// dedicated toggle on the GFS explorer page (not merged into VIC BPO's
// dropdown - a different jurisdiction and a different measure family
// entirely).
export type TasGgsFlowOrStock = "flow" | "stock" | "balance" | "stock_balance";

export type TasGgsMeasureInfo = {
  measure_type: string;
  label: string;
  economic_meaning: string;
  flow_or_stock: TasGgsFlowOrStock;
  source_column: string;
  compatibility_group: string;
  accounting_basis: string;
  unit: string;
};

export type TasGgsCitation = {
  locator: string;
  cached_copy_path?: string | null;
};

export type TasGgsFact = {
  label: string;
  measure_type: string;
  flow_or_stock: TasGgsFlowOrStock;
  amount_aud: number;
  financial_year: string;
  period_end: string;
  accounting_basis: string;
  estimate_status: string;
  compatibility_group: string;
  citation: TasGgsCitation;
};

export type TasGgsSeriesResponse = {
  measure_type: string;
  flow_or_stock: TasGgsFlowOrStock;
  facts: TasGgsFact[];
};

export const apiTasGgs = {
  measures: () => getJson<TasGgsMeasureInfo[]>("/v2/tas-ggs/measures"),
  series: (measureType: string) =>
    getJson<TasGgsSeriesResponse>(`/v2/tas-ggs/series?measure_type=${encodeURIComponent(measureType)}`),
};

// Queensland Treasury's "Report on State Finances" - "Key UPF
// Financial Aggregates" table, General Government Sector only. Its
// available years are reported by the series response and formatted by
// the GFS explorer rather than duplicated here. Its own dedicated toggle on the GFS explorer
// page (not merged into an existing dropdown - a genuinely new
// jurisdiction/measure family). Vintage is "estimated_actual" (the
// outcome as projected in a LATER budget-cycle document) vs "actual" -
// a materially different concept from TAS's "budget".
export type QldRsfFlowOrStock = "flow" | "stock" | "balance" | "stock_balance";

export type QldRsfMeasureInfo = {
  measure_type: string;
  label: string;
  economic_meaning: string;
  flow_or_stock: QldRsfFlowOrStock;
  row_label: string;
  compatibility_group: string;
  accounting_basis: string;
  unit: string;
};

export type QldRsfCitation = {
  locator: string;
  cached_copy_path?: string | null;
};

export type QldRsfFact = {
  label: string;
  measure_type: string;
  flow_or_stock: QldRsfFlowOrStock;
  amount_aud: number;
  financial_year: string;
  period_end: string;
  accounting_basis: string;
  estimate_status: string;
  compatibility_group: string;
  citation: QldRsfCitation;
};

export type QldRsfSeriesResponse = {
  measure_type: string;
  flow_or_stock: QldRsfFlowOrStock;
  facts: QldRsfFact[];
};

export const apiQldRsf = {
  measures: () => getJson<QldRsfMeasureInfo[]>("/v2/qld-rsf/measures"),
  series: (measureType: string) =>
    getJson<QldRsfSeriesResponse>(`/v2/qld-rsf/series?measure_type=${encodeURIComponent(measureType)}`),
};

// Queensland MYFER current-year revised estimates. Kept separate from
// audited RSF actuals and exposed as its own GFS-explorer view.
export type QldMyferFlowOrStock = "flow" | "balance";

export type QldMyferMeasureInfo = {
  measure_type: string;
  label: string;
  flow_or_stock: QldMyferFlowOrStock;
  compatibility_group: string;
  accounting_basis: string;
  unit: string;
  period_granularity: string;
};

export type QldMyferCitation = {
  locator: string;
  cached_copy_path?: string | null;
};

export type QldMyferFact = {
  label: string;
  measure_type: string;
  flow_or_stock: QldMyferFlowOrStock;
  amount_aud: number;
  financial_year: string;
  period_start?: string | null;
  period_end: string;
  period_granularity: string;
  source_budget_year: string;
  publication_date?: string | null;
  estimate_status: string;
  compatibility_group: string;
  citation: QldMyferCitation;
};

export type QldMyferSeriesResponse = {
  measure_type: string;
  flow_or_stock: QldMyferFlowOrStock;
  facts: QldMyferFact[];
};

export const apiQldMyfer = {
  measures: () => getJson<QldMyferMeasureInfo[]>("/v2/qld-myfer/measures"),
  series: (measureType: string) =>
    getJson<QldMyferSeriesResponse>(`/v2/qld-myfer/series?measure_type=${encodeURIComponent(measureType)}`),
};

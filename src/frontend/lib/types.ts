export interface BreakdownMeta {
  kind: "same_group" | "related_breakdown";
  source_key?: string | null;
  compatibility_group?: string | null;
  match_quality?: string | null;
  banner?: string | null;
  fact_financial_year?: string | null;
  // Task 7 (semantic-defect milestone): explicit per-node year-fallback
  // disclosure - must be shown at the child itself, not only in a
  // folder-level banner.
  requested_financial_year?: string | null;
  is_year_fallback?: boolean | null;
  fallback_reason?: string | null;
  source_budget_edition?: string | null;
  estimate_status?: string | null;
}

export interface TreeNode {
  name: string;
  value: number;
  id: number | null;
  children: TreeNode[] | null;
  breakdown?: BreakdownMeta | null;
  mixed_observation_dates?: boolean | null;
  observation_dates?: string[] | null;
  valuation_basis?: string | null;
  valuation_bases?: string[] | null;
  mixed_valuation_bases?: boolean | null;
  amount_granularity?: string | null;
  warning?: string | null;
  is_aggregate?: boolean | null;
  unit?: string | null;
  view_family?: string | null;
  root_total_allowed?: boolean | null;
}

export interface SpendingItem {
  id: number;
  financial_year: string;
  level_of_government: string;
  jurisdiction: string;
  category: string;
  subcategory: string | null;
  department: string | null;
  amount_aud: number;
  source_document_name: string;
  source_url: string;
  retrieved_at: string;
}

export interface SourceContext {
  source_type: "spreadsheet" | "pdf" | "unsupported";
  sheet_name: string | null;
  cell_range: string | null;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  highlight: {
    row_index: number;
    column_index: number;
    cell: string;
  } | null;
  unit: string | null;
  note: string | null;
  viewer_url: string | null;
  page_number: number | null;
  text_anchor: string | null;
}

export interface LevelSummary {
  level: string;
  row_count: number;
}

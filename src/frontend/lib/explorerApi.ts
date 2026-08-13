import type { Citation } from "./api";

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

/**
 * Typed client for the item-6.1 explorer registry/family API
 * (src/backend/routers/v2/explorers.py). Every shape here mirrors a
 * backend response field-for-field - this file does not reconstruct or
 * infer anything the backend did not already compute (no hierarchy,
 * no rescaled values, no client-side re-aggregation).
 */
export type ExplorerFamilySummary = {
  id: string;
  label: string;
  compatibility_group: string;
  accounting_basis: string;
  estimate_statuses: string[];
  default_estimate_status: string;
  source_key: string | null;
  additive_note: string;
};

export type ExplorerAvailabilityRow = {
  financial_year: string;
  estimate_status: string;
  count: number;
  value: number;
};

export type ExplorerAvailability = {
  family: ExplorerFamilySummary;
  years: ExplorerAvailabilityRow[];
};

export type ExplorerSourceBreakdownRow = {
  source_key: string;
  count: number;
  value: number;
};

export type ExplorerTreeChild = {
  name: string;
  value: number | null;
  id: number;
  citation: Citation;
};

export type ExplorerTree = {
  name: string;
  shape: "flat";
  value: number;
  total_count: number;
  total_value: number;
  source_breakdown: ExplorerSourceBreakdownRow[];
  next_cursor: string | null;
  children: ExplorerTreeChild[];
  family: string;
};

export type ExplorerFacets = {
  family: ExplorerFamilySummary;
  years: Array<{ financial_year: string; count: number }>;
  estimate_statuses: Array<{ estimate_status: string; count: number }>;
  sources: Array<{ source_key: string; count: number }>;
  measures: Array<{ measure_type: string; count: number }>;
};

export type ExplorerItem = {
  family: string;
  name: string;
  value: number | null;
  financial_year: string;
  estimate_status: string;
  citation: Citation;
};

export const explorerApi = {
  list: () => getJson<{ families: ExplorerFamilySummary[] }>("/v2/explorers"),

  availability: (familyId: string) =>
    getJson<ExplorerAvailability>(`/v2/explorers/${encodeURIComponent(familyId)}/availability`),

  facets: (familyId: string) =>
    getJson<ExplorerFacets>(`/v2/explorers/${encodeURIComponent(familyId)}/facets`),

  tree: (
    familyId: string,
    params: {
      financial_year: string;
      estimate_status?: string;
      q?: string;
      limit?: number;
      cursor?: string | null;
    },
  ) => {
    const q = new URLSearchParams({ financial_year: params.financial_year });
    if (params.estimate_status) q.set("estimate_status", params.estimate_status);
    if (params.q?.trim()) q.set("q", params.q.trim());
    q.set("limit", String(params.limit ?? 200));
    if (params.cursor) q.set("cursor", params.cursor);
    return getJson<ExplorerTree>(
      `/v2/explorers/${encodeURIComponent(familyId)}/tree?${q.toString()}`,
    );
  },

  item: (familyId: string, factId: number) =>
    getJson<ExplorerItem>(
      `/v2/explorers/${encodeURIComponent(familyId)}/item/${encodeURIComponent(String(factId))}`,
    ),
};

import type { DashboardMode, SearchParams, SearchSort } from "./api";

export type SearchFormState = {
  q: string;
  mode: DashboardMode | "";
  level: string;
  jurisdiction: string;
  fy_from: string;
  fy_to: string;
  amount_min: string;
  amount_max: string;
  sort: SearchSort;
};

export const EMPTY_SEARCH_FORM: SearchFormState = {
  q: "",
  mode: "actuals",
  level: "",
  jurisdiction: "",
  fy_from: "",
  fy_to: "",
  amount_min: "",
  amount_max: "",
  sort: "amount_desc",
};

export function parseSearchForm(sp: URLSearchParams): SearchFormState {
  const modeRaw = sp.get("mode") || "actuals";
  const mode: DashboardMode | "" =
    modeRaw === "actuals" ||
    modeRaw === "budget" ||
    modeRaw === "debt" ||
    modeRaw === "revenue" ||
    modeRaw === "gdp" ||
    modeRaw === "gdp_current" ||
    modeRaw === "gdp_chain_volume" ||
    modeRaw === "gdp_expenditure" ||
    modeRaw === "gva_current" ||
    modeRaw === "gva_chain_volume" ||
    modeRaw === "gsp_current" ||
    modeRaw === "gsp_chain_volume" ||
    modeRaw === "ratios" ||
    modeRaw === ""
      ? (modeRaw as DashboardMode | "")
      : "actuals";
  const sortRaw = sp.get("sort") || "amount_desc";
  const sort: SearchSort = (
    ["amount_desc", "amount_asc", "fy_desc", "name"] as SearchSort[]
  ).includes(sortRaw as SearchSort)
    ? (sortRaw as SearchSort)
    : "amount_desc";
  return {
    q: sp.get("q") ?? "",
    mode,
    level: sp.get("level") ?? "",
    jurisdiction: sp.get("jurisdiction") ?? "",
    fy_from: sp.get("fy_from") ?? "",
    fy_to: sp.get("fy_to") ?? "",
    amount_min: sp.get("amount_min") ?? "",
    amount_max: sp.get("amount_max") ?? "",
    sort,
  };
}

export function hasAdvancedFilters(form: SearchFormState): boolean {
  return Boolean(
    form.level ||
      form.jurisdiction.trim() ||
      form.fy_from.trim() ||
      form.fy_to.trim() ||
      form.amount_min.trim() ||
      form.amount_max.trim() ||
      (form.sort && form.sort !== "amount_desc") ||
      (form.mode && form.mode !== "actuals"),
  );
}

export function formToSearchParams(form: SearchFormState, offset = 0, limit = 50): SearchParams {
  const amount_min = form.amount_min.trim() ? Number(form.amount_min) : null;
  const amount_max = form.amount_max.trim() ? Number(form.amount_max) : null;
  return {
    q: form.q.trim() || undefined,
    mode: form.mode || undefined,
    level: form.level || undefined,
    jurisdiction: form.jurisdiction.trim() || undefined,
    fy_from: form.fy_from.trim() || undefined,
    fy_to: form.fy_to.trim() || undefined,
    amount_min: amount_min != null && Number.isFinite(amount_min) ? amount_min : null,
    amount_max: amount_max != null && Number.isFinite(amount_max) ? amount_max : null,
    sort: form.sort,
    limit,
    offset,
  };
}

export function formToUrlQuery(form: SearchFormState): string {
  const q = new URLSearchParams();
  if (form.q.trim()) q.set("q", form.q.trim());
  if (form.mode) q.set("mode", form.mode);
  if (form.level) q.set("level", form.level);
  if (form.jurisdiction.trim()) q.set("jurisdiction", form.jurisdiction.trim());
  if (form.fy_from.trim()) q.set("fy_from", form.fy_from.trim());
  if (form.fy_to.trim()) q.set("fy_to", form.fy_to.trim());
  if (form.amount_min.trim()) q.set("amount_min", form.amount_min.trim());
  if (form.amount_max.trim()) q.set("amount_max", form.amount_max.trim());
  if (form.sort && form.sort !== "amount_desc") q.set("sort", form.sort);
  return q.toString();
}

export function canRunSearch(form: SearchFormState): boolean {
  const qOk = form.q.trim().length >= 2;
  const adv = Boolean(
    form.level ||
      form.jurisdiction.trim() ||
      form.fy_from.trim() ||
      form.fy_to.trim() ||
      form.amount_min.trim() ||
      form.amount_max.trim(),
  );
  // mode alone always set by default — don't count as "advanced only"
  return qOk || adv;
}

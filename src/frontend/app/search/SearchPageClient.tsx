"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  apiSearch,
  apiV2,
  DashboardMode,
  SearchHit,
  SearchResponse,
  SearchSort,
  UnifiedSearchHit,
  UnifiedSearchResponse,
} from "@/lib/api";
import { formatAudFull } from "@/lib/colors";
import { appHref, navigateApp, renderHighlighted } from "@/lib/searchDisplay";
import {
  EMPTY_SEARCH_FORM,
  SearchFormState,
  canRunSearch,
  formToSearchParams,
  formToUrlQuery,
  hasAdvancedFilters,
  parseSearchForm,
} from "@/lib/searchParams";
import DashboardNav from "@/components/DashboardNav";
import DebtNav from "@/components/DebtNav";
import FactCitationViewer from "@/components/FactCitationViewer";
import ResizableSplitPane from "@/components/ResizableSplitPane";

const LEVELS = [
  { value: "", label: "Any level" },
  { value: "federal", label: "Federal" },
  { value: "state", label: "State" },
  { value: "territory", label: "Territory" },
  { value: "local", label: "Local" },
];

const SORTS: { value: SearchSort; label: string }[] = [
  { value: "amount_desc", label: "Amount (high → low)" },
  { value: "amount_asc", label: "Amount (low → high)" },
  { value: "fy_desc", label: "Financial year" },
  { value: "name", label: "Name" },
];

const PAGE_SIZE = 50;

function fieldClass(): string {
  return "rounded-md border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-50";
}

export default function SearchPageClient() {
  const router = useRouter();
  const pathname = usePathname();
  const urlParams = useSearchParams();

  const initial = useMemo(() => parseSearchForm(urlParams), [urlParams]);
  const [form, setForm] = useState<SearchFormState>(initial);
  const [tab, setTab] = useState<"hybrid" | "advanced" | "documents">(
    urlParams.get("tab") === "documents"
      ? "documents"
      : hasAdvancedFilters(initial)
        ? "advanced"
        : "hybrid",
  );
  const [advancedOpen, setAdvancedOpen] = useState(() => hasAdvancedFilters(initial));
  const [hybrid, setHybrid] = useState<UnifiedSearchResponse | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<UnifiedSearchHit | null>(null);
  const [validation, setValidation] = useState<string | null>(null);

  const runHybrid = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setHybrid(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiSearch.unified(q.trim(), "all", 40);
      setHybrid(data);
      const firstSpend = data.spending[0];
      const firstDoc = data.documents[0];
      if (firstSpend?.fact_id != null) setSelectedId(firstSpend.fact_id);
      else if (firstDoc) setSelectedDoc(firstDoc);
    } catch (err) {
      setError(String(err));
      setHybrid(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const runAdvanced = useCallback(async (nextForm: SearchFormState, offset: number, append: boolean) => {
    if (!canRunSearch(nextForm)) {
      setValidation(
        "Enter at least 2 characters, or set an advanced filter (level, FY, amount, jurisdiction).",
      );
      setResults(null);
      return;
    }
    setValidation(null);
    setLoading(true);
    setError(null);
    try {
      const data = await apiV2.search(formToSearchParams(nextForm, offset, PAGE_SIZE));
      setResults((prev) =>
        append && prev ? { ...data, items: [...prev.items, ...data.items] } : data,
      );
      if (!append && data.items.length > 0) setSelectedId(data.items[0].id);
    } catch (err) {
      setError(String(err));
      if (!append) setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const parsed = parseSearchForm(urlParams);
    setForm(parsed);
    if (hasAdvancedFilters(parsed)) {
      setAdvancedOpen(true);
      setTab("advanced");
    }
    if (urlParams.get("tab") === "documents") setTab("documents");
    const q = parsed.q.trim();
    if (q.length >= 2 && tab !== "advanced") {
      void runHybrid(q);
    } else if (tab === "advanced" && canRunSearch(parsed)) {
      void runAdvanced(parsed, 0, false);
    }
  }, [urlParams, runHybrid, runAdvanced, tab]);

  function update<K extends keyof SearchFormState>(key: K, value: SearchFormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const qs = formToUrlQuery(form);
    const extra = tab === "documents" ? "tab=documents" : "";
    const joined = [qs, extra].filter(Boolean).join("&");
    router.push(joined ? `${pathname}?${joined}` : pathname);
  }

  function openSpending(hit: UnifiedSearchHit | SearchHit) {
    if ("kind" in hit && hit.kind === "spending" && hit.href) {
      navigateApp(router, hit.href);
      return;
    }
    if ("id" in hit) {
      setSelectedId(hit.id);
      setSelectedDoc(null);
    }
  }

  const docHits = hybrid?.documents ?? [];
  const spendHits = hybrid?.spending ?? [];

  return (
    <div className="min-h-screen w-full px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Corpus search
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Hybrid FTS + embeddings across spending categories, liability stocks, and the
          document corpus. Filter by Debt in advanced mode to scope to GFS liabilities.
        </p>
        <DashboardNav />
        {form.mode === "debt" ? <DebtNav /> : null}
      </header>

      <form onSubmit={submit} className="mb-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            value={form.q}
            onChange={(e) => update("q", e.target.value)}
            placeholder="Search categories, agencies, document text…"
            className={`${fieldClass()} min-w-[16rem] flex-1`}
            aria-label="Search query"
          />
          <button
            type="submit"
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white dark:bg-zinc-50 dark:text-zinc-900"
          >
            Search
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {(
            [
              ["hybrid", "Hybrid"],
              ["documents", "Documents"],
              ["advanced", "Advanced filters"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                tab === id
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "border border-black/10 text-zinc-600 dark:border-white/10 dark:text-zinc-300"
              }`}
            >
              {label}
            </button>
          ))}
          {tab === "advanced" ? (
            <button
              type="button"
              onClick={() => setAdvancedOpen((o) => !o)}
              className="rounded-md border border-black/10 px-3 py-1.5 text-sm dark:border-white/10"
            >
              Filters {advancedOpen ? "▴" : "▾"}
            </button>
          ) : null}
        </div>

        {tab === "advanced" && advancedOpen ? (
          <div className="grid gap-3 rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900 sm:grid-cols-2 lg:grid-cols-3">
            <label className="flex flex-col gap-1 text-xs text-zinc-500">
              Mode
              <select
                value={form.mode}
                onChange={(e) => update("mode", e.target.value as DashboardMode | "")}
                className={fieldClass()}
              >
                <option value="actuals">Actuals</option>
                <option value="budget">Budget</option>
                <option value="debt">Debt</option>
                <option value="">Any mode</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500">
              Government level
              <select
                value={form.level}
                onChange={(e) => update("level", e.target.value)}
                className={fieldClass()}
              >
                {LEVELS.map((l) => (
                  <option key={l.value || "any"} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500">
              Jurisdiction
              <input
                value={form.jurisdiction}
                onChange={(e) => update("jurisdiction", e.target.value)}
                placeholder="e.g. Commonwealth, NSW"
                className={fieldClass()}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500">
              Sort
              <select
                value={form.sort}
                onChange={(e) => update("sort", e.target.value as SearchSort)}
                className={fieldClass()}
              >
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500">
              FY from
              <input
                value={form.fy_from}
                onChange={(e) => update("fy_from", e.target.value)}
                placeholder="2020-21"
                className={fieldClass()}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-500">
              FY to
              <input
                value={form.fy_to}
                onChange={(e) => update("fy_to", e.target.value)}
                placeholder="2024-25"
                className={fieldClass()}
              />
            </label>
          </div>
        ) : null}
      </form>

      {validation ? <p className="mb-3 text-sm text-amber-700">{validation}</p> : null}
      {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
      {loading ? <p className="mb-3 text-sm text-zinc-500">Searching…</p> : null}
      {hybrid && !hybrid.index_ready ? (
        <p className="mb-3 text-sm text-amber-700">{hybrid.note}</p>
      ) : null}

      <ResizableSplitPane
        left={
          <section className="rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900">
            {tab === "advanced" ? (
              <ul className="space-y-2">
                {(results?.items ?? []).map((hit) => (
                  <li key={hit.id}>
                    <button
                      type="button"
                      className="w-full rounded-md px-2 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800"
                      onClick={() => openSpending(hit)}
                    >
                      <div className="text-sm font-medium">{hit.node_name}</div>
                      <div className="text-xs text-zinc-500">
                        {hit.level} · FY {hit.financial_year} · {formatAudFull(hit.amount_aud)}
                      </div>
                    </button>
                  </li>
                ))}
                {!loading && (results?.items.length ?? 0) === 0 ? (
                  <p className="text-sm text-zinc-500">No advanced-filter matches.</p>
                ) : null}
              </ul>
            ) : (
              <div className="space-y-4">
                {tab !== "documents" ? (
                  <div>
                    <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                      Spending ({spendHits.length})
                    </h2>
                    <ul className="space-y-1">
                      {spendHits.map((hit) => (
                        <li key={`s-${hit.fact_id}-${hit.node_name}`}>
                          <button
                            type="button"
                            className="w-full rounded-md px-2 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800"
                            onClick={() => {
                              setSelectedId(hit.fact_id ?? null);
                              setSelectedDoc(null);
                              if (hit.href) navigateApp(router, hit.href);
                            }}
                          >
                            <div
                              className="text-sm font-medium"
                              dangerouslySetInnerHTML={renderHighlighted(
                                hit.snippet && hit.snippet.includes("«")
                                  ? hit.snippet
                                  : hit.display_title || hit.node_name || "",
                              )}
                            />
                            <div className="text-xs text-zinc-500">
                              {hit.level} · FY {hit.financial_year} ·{" "}
                              {hit.amount_aud != null ? formatAudFull(hit.amount_aud) : ""}
                              {hit.matched_terms?.length
                                ? ` · matched: ${hit.matched_terms.join(", ")}`
                                : ""}
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div>
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                    Documents ({docHits.length})
                  </h2>
                  <ul className="space-y-1">
                    {docHits.map((hit) => (
                      <li key={`d-${hit.source_key}-${hit.chunk_index}`}>
                        <button
                          type="button"
                          className="w-full rounded-md px-2 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800"
                          onClick={() => {
                            setSelectedDoc(hit);
                            setSelectedId(null);
                          }}
                        >
                          <div className="text-sm font-medium">{hit.title}</div>
                          <div className="line-clamp-2 text-xs text-zinc-500">
                            {hit.snippet || hit.publisher} · {hit.method}
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </section>
        }
        right={
          <aside className="rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-zinc-900">
            {selectedDoc ? (
              <div className="space-y-3 text-sm">
                <h2 className="text-lg font-semibold">{selectedDoc.title}</h2>
                <p className="text-zinc-500">
                  {selectedDoc.publisher} · {selectedDoc.jurisdiction} · {selectedDoc.source_key}
                </p>
                {selectedDoc.snippet ? (
                  <p className="rounded bg-zinc-50 p-3 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
                    {selectedDoc.snippet}
                  </p>
                ) : null}
                {selectedDoc.landing_url ? (
                  <a
                    href={selectedDoc.landing_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 underline dark:text-blue-400"
                  >
                    Open publisher page
                  </a>
                ) : null}
              </div>
            ) : (
              <FactCitationViewer
                factId={selectedId}
                emptyMessage="Select a spending hit or document chunk"
              />
            )}
          </aside>
        }
      />
    </div>
  );
}

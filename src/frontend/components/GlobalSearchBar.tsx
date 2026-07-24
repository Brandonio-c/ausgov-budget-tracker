"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiSearch, UnifiedSearchResponse, UnifiedSearchHit } from "@/lib/api";
import { formatAud } from "@/lib/colors";
import { appHref, navigateApp, renderHighlighted } from "@/lib/searchDisplay";

function hitTitle(hit: UnifiedSearchHit): string {
  if (hit.kind === "spending") {
    return hit.display_title || hit.matched_label || hit.node_name || "Spending item";
  }
  return hit.display_title || hit.title || hit.source_key || "Document";
}

function hitSnippet(hit: UnifiedSearchHit): string | null {
  if (hit.snippet && hit.snippet !== hitTitle(hit)) return hit.snippet;
  if (hit.snippet) return hit.snippet;
  return null;
}

function hitMeta(hit: UnifiedSearchHit): string {
  if (hit.kind === "spending") {
    const bits = [
      hit.level,
      hit.financial_year ? `FY ${hit.financial_year}` : null,
      hit.amount_aud != null ? formatAud(hit.amount_aud) : null,
      hit.matched_terms?.length ? `matched: ${hit.matched_terms.join(", ")}` : null,
    ].filter(Boolean);
    return bits.join(" · ");
  }
  const bits = [
    hit.publisher,
    hit.jurisdiction,
    hit.matched_terms?.length ? `matched: ${hit.matched_terms.join(", ")}` : null,
  ].filter(Boolean);
  return bits.join(" · ");
}

export default function GlobalSearchBar() {
  const router = useRouter();
  const pathname = usePathname();
  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<UnifiedSearchResponse | null>(null);

  const run = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiSearch.unified(trimmed, "all", 12);
      setResults(data);
      setOpen(true);
    } catch (err) {
      setError(String(err));
      setResults(null);
      setOpen(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const trimmed = q.trim();
    if (trimmed.length < 2) {
      setResults(null);
      return;
    }
    const t = window.setTimeout(() => void run(trimmed), 280);
    return () => window.clearTimeout(t);
  }, [q, run]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function navigateTo(hit: UnifiedSearchHit) {
    setOpen(false);
    const href = appHref(hit.href || "/");
    if (hit.kind === "spending" && (pathname === "/timeline" || pathname === "/timeline/")) {
      const cat = hit.display_title || hit.node_name?.split(" / ").pop() || hit.node_name || "";
      const qs = new URLSearchParams();
      if (hit.mode) qs.set("mode", String(hit.mode));
      if (cat) qs.set("category", cat);
      if (hit.level) qs.set("level", hit.level);
      if (hit.fact_id != null) qs.set("fact", String(hit.fact_id));
      navigateApp(router, `/timeline?${qs.toString()}`);
      return;
    }
    if (hit.kind === "spending" && (pathname === "/combined" || pathname === "/combined/")) {
      const url = new URL(href, "https://local");
      navigateApp(router, `/combined?${url.searchParams.toString()}`);
      return;
    }
    navigateApp(router, href);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    setOpen(false);
    router.push(appHref(`/search?q=${encodeURIComponent(trimmed)}`));
  }

  const spending = results?.spending ?? [];
  const documents = results?.documents ?? [];
  const hasHits = spending.length > 0 || documents.length > 0;

  return (
    <div ref={rootRef} className="relative w-full max-w-xl">
      <form onSubmit={onSubmit} className="flex gap-2">
        <label className="sr-only" htmlFor={`${listId}-input`}>
          Search spending and documents
        </label>
        <input
          id={`${listId}-input`}
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          placeholder="Search spending, categories, documents…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (q.trim().length >= 2) setOpen(true);
          }}
          className="w-full rounded-md border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none ring-blue-500/30 placeholder:text-zinc-400 focus:ring-2 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-50"
        />
        <button
          type="submit"
          className="shrink-0 rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white dark:bg-zinc-50 dark:text-zinc-900"
        >
          Search
        </button>
      </form>

      {open && (loading || error || results) ? (
        <div
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-[28rem] w-full overflow-auto rounded-md border border-black/10 bg-white shadow-lg dark:border-white/10 dark:bg-zinc-900"
        >
          {loading ? (
            <p className="px-3 py-2 text-sm text-zinc-500">Searching…</p>
          ) : null}
          {error ? <p className="px-3 py-2 text-sm text-red-600">{error}</p> : null}
          {results && !results.index_ready ? (
            <p className="px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
              {results.note || "Search index not ready"}
            </p>
          ) : null}

          {!loading && results?.index_ready && !hasHits ? (
            <p className="px-3 py-2 text-sm text-zinc-500">No matches</p>
          ) : null}

          {spending.length > 0 ? (
            <div className="border-b border-black/5 dark:border-white/10">
              <p className="px-3 pt-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
                Spending
              </p>
              <ul>
                {spending.map((hit) => {
                  const snip = hitSnippet(hit);
                  return (
                    <li key={`s-${hit.fact_id}-${hit.node_name}-${hit.method}`}>
                      <button
                        type="button"
                        role="option"
                        className="flex w-full flex-col gap-0.5 px-3 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800"
                        onClick={() => navigateTo(hit)}
                      >
                        <span
                          className="text-sm font-medium text-zinc-900 dark:text-zinc-50"
                          dangerouslySetInnerHTML={renderHighlighted(
                            snip && snip.includes("«") ? snip : hitTitle(hit),
                          )}
                        />
                        <span className="text-xs text-zinc-500">{hitMeta(hit)}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          {documents.length > 0 ? (
            <div>
              <p className="px-3 pt-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
                Documents
              </p>
              <ul>
                {documents.map((hit) => (
                  <li key={`d-${hit.source_key}-${hit.chunk_index}-${hit.method}`}>
                    <button
                      type="button"
                      role="option"
                      className="flex w-full flex-col gap-0.5 px-3 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800"
                      onClick={() => navigateTo(hit)}
                    >
                      <span className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
                        {hitTitle(hit)}
                      </span>
                      <span
                        className="line-clamp-2 text-xs text-zinc-500"
                        dangerouslySetInnerHTML={renderHighlighted(
                          hit.snippet || hitMeta(hit),
                        )}
                      />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {q.trim().length >= 2 ? (
            <div className="border-t border-black/5 px-3 py-2 dark:border-white/10">
              <Link
                href={appHref(`/search?q=${encodeURIComponent(q.trim())}`)}
                className="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
                onClick={() => setOpen(false)}
              >
                Open full results for “{q.trim()}”
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

"use client";

import type { Citation } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Props = {
  citation: Citation | null | undefined;
  emptyLabel?: string;
};

function resolveHref(href: string): string {
  if (href.startsWith("http://") || href.startsWith("https://")) return href;
  if (href.startsWith("/")) return `${API_BASE}${href}`;
  return href;
}

/** Renders the three mandatory citation links for a published fact. */
export function CitationPanel({ citation, emptyLabel = "No citation" }: Props) {
  if (!citation) {
    return (
      <aside className="rounded-md border border-black/10 p-4 text-sm text-zinc-500 dark:border-white/10 dark:text-zinc-400">
        {emptyLabel}
      </aside>
    );
  }

  const links = [
    { key: "landing", label: "Publisher landing page", href: citation.landing_url },
    { key: "original", label: "Original resource", href: citation.original_resource_url },
    { key: "cached", label: "Cached copy", href: citation.cached_copy_url },
  ];

  return (
    <aside
      className="rounded-md border border-black/10 p-4 dark:border-white/10"
      data-fact-id={citation.fact_id}
    >
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Source citation</h3>
      {citation.locator ? (
        <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-300">
          Locator: <code className="break-all">{citation.locator}</code>
        </p>
      ) : null}
      <ul className="mt-3 space-y-2 text-sm">
        {links.map((link) => (
          <li key={link.key}>
            <a
              href={resolveHref(link.href)}
              data-citation-link={link.key}
              target="_blank"
              rel="noreferrer"
              className="text-sky-700 underline hover:text-sky-900 dark:text-sky-300 dark:hover:text-sky-200"
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
      {citation.sha256 ? (
        <p className="mt-3 break-all text-xs text-zinc-500 dark:text-zinc-400">
          sha256: <code>{citation.sha256}</code>
        </p>
      ) : null}
      {citation.retrieved_at ? (
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          Retrieved: {citation.retrieved_at}
        </p>
      ) : null}
    </aside>
  );
}

export default CitationPanel;

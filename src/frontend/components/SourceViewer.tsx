"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatAudFull } from "@/lib/colors";
import { SourceContext, SpendingItem } from "@/lib/types";
import WorkbookViewer, { ReconstructedContextTable } from "@/components/WorkbookViewer";

interface Props {
  itemId: number | null;
  emptyMessage?: string;
}

function isPdfUrl(url: string) {
  try {
    return new URL(url).pathname.toLowerCase().endsWith(".pdf");
  } catch {
    return false;
  }
}

export default function SourceViewer({ itemId, emptyMessage = "Click a leaf item to see its source" }: Props) {
  const [item, setItem] = useState<SpendingItem | null>(null);
  const [context, setContext] = useState<SourceContext | null>(null);
  const [itemError, setItemError] = useState<string | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (itemId === null) return () => { cancelled = true; };

    api.item(itemId).then(
      (data) => !cancelled && setItem(data),
      (error) => !cancelled && setItemError(String(error)),
    );
    api.itemContext(itemId).then(
      (data) => !cancelled && setContext(data),
      (error) => !cancelled && setContextError(String(error)),
    );

    return () => { cancelled = true; };
  }, [itemId]);

  if (itemId === null) {
    return (
      <div className="flex min-h-80 items-center justify-center p-8 text-center text-sm text-zinc-500 dark:text-zinc-400">
        {emptyMessage}
      </div>
    );
  }

  if (itemError) {
    return <p className="p-5 text-sm text-red-600 dark:text-red-400">Failed to load source detail: {itemError}</p>;
  }

  if (!item) {
    return <p className="p-5 text-sm text-zinc-500 dark:text-zinc-400">Loading source…</p>;
  }

  const pdfSource = context?.source_type === "pdf" || isPdfUrl(item.source_url);

  return (
    <div className="p-5">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Source evidence</h2>

      <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">Amount</dt>
          <dd className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">{formatAudFull(item.amount_aud)}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">Financial year</dt>
          <dd className="text-zinc-900 dark:text-zinc-50">{item.financial_year}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">Jurisdiction</dt>
          <dd className="text-zinc-900 dark:text-zinc-50">{item.jurisdiction}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">Department</dt>
          <dd className="text-zinc-900 dark:text-zinc-50">{item.department ?? "Uncategorized"}</dd>
        </div>
        <div className="sm:col-span-2 lg:col-span-1 xl:col-span-2">
          <dt className="text-zinc-500 dark:text-zinc-400">Category</dt>
          <dd className="text-zinc-900 dark:text-zinc-50">
            {item.category}{item.subcategory ? ` — ${item.subcategory}` : ""}
          </dd>
        </div>
      </dl>

      <div className="mt-5 border-t border-black/10 pt-4 dark:border-white/10">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Source document</p>
        <p className="mt-1 text-sm text-zinc-900 dark:text-zinc-50">{item.source_document_name}</p>
      </div>

      {!context && !contextError && (
        <p className="mt-4 text-sm text-zinc-500 dark:text-zinc-400">Loading captured evidence…</p>
      )}

      {context?.source_type === "spreadsheet" && (
        <WorkbookViewer itemId={itemId} context={context} sourceKey={item.source_url} />
      )}

      {context?.source_type === "unsupported" && (
        <div className="mt-4">
          <p className="mb-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
            The original file format cannot be rendered here. Showing the reconstructed source context instead.
          </p>
          <ReconstructedContextTable context={context} />
        </div>
      )}

      {context?.source_type === "pdf" && context.viewer_url && (
        <div className="mt-4">
          <iframe
            title="Captured source PDF"
            src={`${context.viewer_url}${context.page_number ? `#page=${context.page_number}` : "#page=1"}`}
            className="h-[520px] w-full rounded-md border border-black/10 dark:border-white/10"
          />
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
            {context.page_number ? `Opened at page ${context.page_number}.` : "Opened at page 1; no page anchor was captured."}
            {context.text_anchor ? ` Relevant text: “${context.text_anchor}”.` : " No reliable text highlight was captured."}
          </p>
        </div>
      )}

      {pdfSource && (!context || context.source_type !== "pdf" || !context.viewer_url) && (
        <p className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          This PDF has not been captured by the backend, so it is not embedded. The live government URL is not fetched inside the app.
        </p>
      )}

      {contextError && (
        <p className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          Captured row context is unavailable ({contextError}). Metadata and the original link remain available.
        </p>
      )}

      <div className="mt-5">
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 underline hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
        >
          Open original government dataset ↗
        </a>
        <p className="mt-1 text-xs text-zinc-400">
          Retrieved {new Date(item.retrieved_at).toLocaleDateString("en-AU")}
        </p>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiDashboard, FactEvidence } from "@/lib/api";
import { CitationPanel } from "@/components/CitationPanel";
import { formatAudFull } from "@/lib/colors";
import WorkbookViewer, { ReconstructedContextTable } from "@/components/WorkbookViewer";
import PdfEvidenceViewer from "@/components/PdfEvidenceViewer";
import { SourceContext } from "@/lib/types";

interface Props {
  factId: number | null;
  emptyMessage?: string;
}

function evidenceToSourceContext(evidence: FactEvidence): SourceContext {
  const cell = evidence.cell || evidence.highlight?.cell || null;
  let highlight: SourceContext["highlight"] = null;
  if (cell) {
    highlight = {
      cell,
      row_index: evidence.highlight?.row_index ?? 0,
      column_index: evidence.highlight?.column_index ?? 0,
    };
  } else if (
    evidence.highlight &&
    evidence.highlight.row_index != null &&
    evidence.highlight.column_index != null
  ) {
    highlight = {
      cell: evidence.highlight.cell || `R${evidence.highlight.row_index}C${evidence.highlight.column_index}`,
      row_index: evidence.highlight.row_index,
      column_index: evidence.highlight.column_index,
    };
  }

  return {
    source_type:
      evidence.media_type === "spreadsheet"
        ? "spreadsheet"
        : evidence.media_type === "pdf"
          ? "pdf"
          : "unsupported",
    sheet_name: evidence.sheet_name,
    cell_range: evidence.cell_range || cell,
    columns: evidence.columns ?? [],
    rows: evidence.rows ?? [],
    highlight,
    unit: evidence.unit,
    note: evidence.note,
    viewer_url: null,
    page_number: evidence.page_number,
    text_anchor: evidence.text_anchor,
  };
}

export default function FactCitationViewer({
  factId,
  emptyMessage = "Hover a leaf item to preview its source citation",
}: Props) {
  const [evidence, setEvidence] = useState<FactEvidence | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (factId === null) {
      setEvidence(null);
      setError(null);
      return () => {
        cancelled = true;
      };
    }
    setEvidence(null);
    setError(null);
    apiDashboard.itemEvidence(factId).then(
      (data) => {
        if (!cancelled) setEvidence(data);
      },
      (err) => {
        if (!cancelled) setError(String(err));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [factId]);

  const fetchSourceFile = useCallback(
    (id: number, signal?: AbortSignal) => apiDashboard.itemSourceFile(id, signal),
    [],
  );

  const context = useMemo(
    () => (evidence ? evidenceToSourceContext(evidence) : null),
    [evidence],
  );

  const resolveHints = useMemo(() => {
    if (!evidence) return undefined;
    return {
      purpose: evidence.purpose,
      financialYearLabel: evidence.financial_year_label,
      rowNumber: evidence.row_number,
      amountAud: evidence.amount_aud,
    };
  }, [evidence]);

  if (factId === null) {
    return (
      <div className="flex min-h-80 items-center justify-center p-8 text-center text-sm text-zinc-500 dark:text-zinc-400">
        {emptyMessage}
      </div>
    );
  }

  if (error) {
    return (
      <p className="p-5 text-sm text-red-600 dark:text-red-400">
        Failed to load citation: {error}
      </p>
    );
  }

  if (!evidence || !context) {
    return <p className="p-5 text-sm text-zinc-500 dark:text-zinc-400">Loading source document…</p>;
  }

  const item = evidence.item;

  return (
    <div className="space-y-4 p-5 text-sm text-zinc-800 dark:text-zinc-200">
      <div>
        <p className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {item.level_of_government} · {item.jurisdiction} · FY {item.financial_year}
        </p>
        <h2 className="mt-1 text-base font-semibold">{item.category}</h2>
        <p className="mt-1 text-lg font-medium">{formatAudFull(item.amount_aud)}</p>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          {item.measure_type} · {item.accounting_basis} · {item.estimate_status}
        </p>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
          {item.source_document_name}
          {evidence.file_name ? ` · ${evidence.file_name}` : ""}
        </p>
        {evidence.locator && (
          <p className="mt-1 font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
            {evidence.locator}
          </p>
        )}
        {evidence.breakdown_note && (
          <p className="mt-3 rounded-md border border-sky-500/30 bg-sky-50 p-3 text-xs text-sky-950 dark:border-sky-400/20 dark:bg-sky-950/40 dark:text-sky-100">
            {evidence.breakdown_note}
          </p>
        )}
      </div>

      {evidence.media_type === "spreadsheet" && evidence.has_source_file && (
        <WorkbookViewer
          itemId={factId}
          context={context}
          sourceKey={`fact:${factId}:${evidence.file_name ?? "workbook"}`}
          fetchSourceFile={fetchSourceFile}
          resolveHints={resolveHints}
        />
      )}

      {evidence.media_type === "pdf" && evidence.has_source_file && (
        <PdfEvidenceViewer
          factId={factId}
          pageNumber={evidence.page_number}
          textAnchor={evidence.text_anchor}
          amountAud={evidence.amount_aud}
          purpose={evidence.purpose}
          financialYearLabel={evidence.financial_year_label}
          fetchSourceFile={fetchSourceFile}
        />
      )}

      {(evidence.media_type === "text_chunk" ||
        evidence.media_type === "unsupported" ||
        !evidence.has_source_file) && (
        <div className="mt-2">
          {!evidence.has_source_file && (
            <p className="mb-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
              Cached source file is unavailable. Showing reconstructed locator context.
            </p>
          )}
          {evidence.has_source_file && (
            <p className="mb-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
              This file format is not rendered inline. Showing the cited locator fields; use the cached copy link below to download.
            </p>
          )}
          <ReconstructedContextTable context={context} />
        </div>
      )}

      <div className="border-t border-black/10 pt-4 dark:border-white/10">
        <CitationPanel citation={evidence.citation} emptyLabel="Citation unavailable" />
      </div>
    </div>
  );
}

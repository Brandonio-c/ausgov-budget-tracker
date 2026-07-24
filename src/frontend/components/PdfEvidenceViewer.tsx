"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  factId: number;
  pageNumber: number | null;
  textAnchor: string | null;
  amountAud: number | null;
  /** Function / purpose row label from the locator (preferred over raw text_anchor). */
  purpose?: string | null;
  /** Column year from locator, e.g. 2026-27. */
  financialYearLabel?: string | null;
  fetchSourceFile: (factId: number, signal?: AbortSignal) => Promise<ArrayBuffer>;
}

type HighlightRect = { left: number; top: number; width: number; height: number; score: number };

type GlyphRun = {
  str: string;
  transform: number[];
  width?: number;
};

function normalize(s: string): string {
  return s.replace(/\s+/g, " ").trim().toLowerCase();
}

function amountSearchStrings(amountAud: number | null): string[] {
  if (amountAud == null || !Number.isFinite(amountAud)) return [];
  const millions = amountAud / 1_000_000;
  const rounded = Math.round(millions);
  return [
    rounded.toLocaleString("en-AU"),
    String(rounded),
    millions.toLocaleString("en-AU", { maximumFractionDigits: 0 }),
  ];
}

/** Gate 6 `page:N` is often the printed footer page, not the PDF index. */
async function resolvePdfPageIndex(
  pdf: { numPages: number; getPage: (n: number) => Promise<{ getTextContent: () => Promise<{ items: unknown[] }> }> },
  printedOrIndex: number | null,
  purpose: string | null,
  amountAud: number | null,
): Promise<{ index: number; note: string }> {
  const numPages = pdf.numPages;
  if (!printedOrIndex || printedOrIndex < 1) {
    return { index: 1, note: "Opened at page 1" };
  }

  // Within bounds → treat as PDF index.
  if (printedOrIndex <= numPages) {
    return { index: printedOrIndex, note: `PDF page ${printedOrIndex}` };
  }

  const purposeNorm = purpose ? normalize(purpose) : "";
  const amounts = amountSearchStrings(amountAud).map(normalize);
  const pageMarker = new RegExp(
    `(?:page\\s*${printedOrIndex}\\b)|(?:\\|\\s*page\\s*${printedOrIndex}\\b)|(?:(?:^|\\n)\\s*${printedOrIndex}\\s*$)`,
    "i",
  );

  let bestByContent: { index: number; score: number } | null = null;

  for (let i = 1; i <= numPages; i += 1) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const text = content.items
      .map((item) => ("str" in (item as object) ? String((item as GlyphRun).str) : ""))
      .join(" ");
    const norm = normalize(text);

    let score = 0;
    if (pageMarker.test(text) || norm.includes(`page ${printedOrIndex}`)) score += 100;
    if (purposeNorm && norm.includes(purposeNorm)) score += 40;
    for (const amt of amounts) {
      if (amt && norm.includes(amt.replace(/,/g, ""))) score += 20;
      if (amt && norm.includes(amt)) score += 25;
    }
    if (score > 0 && (!bestByContent || score > bestByContent.score)) {
      bestByContent = { index: i, score };
    }
  }

  if (bestByContent) {
    return {
      index: bestByContent.index,
      note: `Printed page ${printedOrIndex} → PDF page ${bestByContent.index}`,
    };
  }

  // Last resort: clamp (legacy behaviour) but surface the mismatch.
  return {
    index: Math.min(printedOrIndex, numPages),
    note: `Could not map printed page ${printedOrIndex}; showing PDF page ${Math.min(printedOrIndex, numPages)}`,
  };
}

function itemRect(
  pdfjs: { Util: { transform: (a: number[], b: number[]) => number[] } },
  viewport: { transform: number[] },
  item: GlyphRun,
): HighlightRect {
  const tx = pdfjs.Util.transform(viewport.transform, item.transform);
  const fontHeight = Math.hypot(tx[2], tx[3]);
  const width = item.width ?? item.str.length * fontHeight * 0.45;
  return {
    left: tx[4],
    top: tx[5] - fontHeight,
    width: Math.max(width, 8),
    height: Math.max(fontHeight * 1.15, 10),
    score: 0,
  };
}

function findHighlights(
  pdfjs: { Util: { transform: (a: number[], b: number[]) => number[] } },
  viewport: { transform: number[] },
  items: GlyphRun[],
  purpose: string | null,
  amountAud: number | null,
  financialYearLabel: string | null,
): HighlightRect[] {
  const purposeNorm = purpose ? normalize(purpose) : "";
  const amounts = amountSearchStrings(amountAud);
  const fy = financialYearLabel ? normalize(financialYearLabel) : "";

  // Join nearby text items into a line bag for phrase search, but highlight by item.
  const found: HighlightRect[] = [];

  for (let i = 0; i < items.length; i += 1) {
    const item = items[i];
    if (!item.str || !item.str.trim()) continue;
    const lower = normalize(item.str);
    let score = 0;

    // Exact / strong purpose match on this glyph run or short window.
    if (purposeNorm) {
      if (lower === purposeNorm) score += 100;
      else if (lower.includes(purposeNorm) && purposeNorm.length >= 8) score += 80;
      else {
        // Rebuild a local phrase from adjacent items (PDFs split words).
        let window = lower;
        for (let j = i + 1; j < Math.min(items.length, i + 8); j += 1) {
          window = `${window} ${normalize(items[j].str)}`.trim();
          if (window.includes(purposeNorm)) {
            score += 90;
            // Also mark following glyphs in the matched phrase.
            for (let k = i + 1; k <= j; k += 1) {
              const extra = itemRect(pdfjs, viewport, items[k]);
              extra.score = 85;
              found.push(extra);
            }
            break;
          }
          if (window.length > purposeNorm.length + 20) break;
        }
      }
    }

    for (const amt of amounts) {
      const amtNorm = normalize(amt);
      const amtDigits = amtNorm.replace(/,/g, "");
      const itemDigits = lower.replace(/,/g, "");
      if (lower === amtNorm || itemDigits === amtDigits) score += 70;
      else if (itemDigits.includes(amtDigits) && amtDigits.length >= 4) score += 50;
    }

    // Year column header alone is weak — only keep if we already have a strong hit nearby.
    if (fy && lower === fy) score += 15;

    if (score >= 50) {
      const rect = itemRect(pdfjs, viewport, item);
      rect.score = score;
      found.push(rect);
    }
  }

  // If we matched a multi-item purpose phrase, also highlight following amount on same band.
  found.sort((a, b) => b.score - a.score);
  const top = found.filter((h) => h.score >= 70).slice(0, 4);
  if (top.length > 0) return top;
  return found.filter((h) => h.score >= 50).slice(0, 3);
}

export default function PdfEvidenceViewer({
  factId,
  pageNumber,
  textAnchor,
  amountAud,
  purpose = null,
  financialYearLabel = null,
  fetchSourceFile,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<string>("Loading PDF…");
  const [error, setError] = useState<string | null>(null);
  const [highlights, setHighlights] = useState<HighlightRect[]>([]);
  const [renderedPage, setRenderedPage] = useState<number | null>(null);
  const [pageNote, setPageNote] = useState<string | null>(null);

  // Prefer explicit purpose; fall back to text_anchor segments that look like labels.
  const resolvedPurpose =
    purpose ||
    (textAnchor
      ? textAnchor
          .split("|")
          .map((p) => p.trim())
          .find((p) => !/^table\b/i.test(p) && !/^\d{4}-\d{2}$/.test(p) && p.length >= 6) || null
      : null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function run() {
      setError(null);
      setHighlights([]);
      setStatus("Loading PDF…");
      setPageNote(null);
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc =
          `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

        const buffer = await fetchSourceFile(factId, controller.signal);
        if (cancelled) return;

        setStatus("Parsing PDF…");
        const loadingTask = pdfjs.getDocument({ data: new Uint8Array(buffer) });
        const pdf = await loadingTask.promise;
        if (cancelled) return;

        const resolved = await resolvePdfPageIndex(
          pdf,
          pageNumber,
          resolvedPurpose,
          amountAud,
        );
        if (cancelled) return;

        const page = await pdf.getPage(resolved.index);
        if (cancelled) return;

        const baseViewport = page.getViewport({ scale: 1 });
        const containerWidth = wrapRef.current?.clientWidth || 720;
        const scale = Math.min(1.5, Math.max(0.75, containerWidth / baseViewport.width));
        const viewport = page.getViewport({ scale });

        const canvas = canvasRef.current;
        if (!canvas) return;
        const context = canvas.getContext("2d");
        if (!context) return;

        canvas.height = viewport.height;
        canvas.width = viewport.width;
        await page.render({ canvasContext: context, viewport }).promise;
        if (cancelled) return;

        setRenderedPage(resolved.index);
        setPageNote(resolved.note);
        setStatus(`PDF page ${resolved.index} of ${pdf.numPages}`);

        const textContent = await page.getTextContent();
        const items: GlyphRun[] = [];
        for (const item of textContent.items) {
          if (typeof item === "object" && item !== null && "str" in item) {
            items.push(item as GlyphRun);
          }
        }
        const found = findHighlights(
          pdfjs,
          viewport,
          items,
          resolvedPurpose,
          amountAud,
          financialYearLabel ?? null,
        );
        setHighlights(found);

        // Scroll first highlight into view after paint.
        requestAnimationFrame(() => {
          const wrap = wrapRef.current;
          if (!wrap || found.length === 0) return;
          const h = found[0];
          wrap.scrollTo({
            top: Math.max(0, h.top - wrap.clientHeight / 3),
            left: Math.max(0, h.left - wrap.clientWidth / 3),
            behavior: "smooth",
          });
        });
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        setError(String(err));
        setStatus("PDF failed to load");
      }
    }

    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [
    amountAud,
    factId,
    fetchSourceFile,
    financialYearLabel,
    pageNumber,
    resolvedPurpose,
  ]);

  return (
    <div className="mt-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-zinc-500 dark:text-zinc-400">
        <p className="font-medium text-emerald-700 dark:text-emerald-400">Original cached PDF</p>
        <p>
          {status}
          {highlights.length ? ` · ${highlights.length} highlight(s)` : ""}
        </p>
      </div>
      {pageNote && (
        <p className="mb-1 text-xs text-zinc-500 dark:text-zinc-400">{pageNote}</p>
      )}
      {error && (
        <p className="mb-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          {error}
        </p>
      )}
      {(resolvedPurpose || amountAud != null) && (
        <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
          Highlighting
          {resolvedPurpose ? ` “${resolvedPurpose}”` : ""}
          {amountAud != null
            ? `${resolvedPurpose ? " /" : ""} ${(amountAud / 1_000_000).toLocaleString("en-AU", { maximumFractionDigits: 0 })}`
            : ""}
          {renderedPage != null ? ` on PDF page ${renderedPage}` : ""}
          {pageNumber != null && pageNumber > (renderedPage ?? 0)
            ? ` (locator printed page ${pageNumber})`
            : ""}
        </p>
      )}
      <div
        ref={wrapRef}
        className="relative max-h-[560px] overflow-auto rounded-md border border-black/10 bg-zinc-100 dark:border-white/10 dark:bg-zinc-900"
      >
        <div className="relative inline-block min-w-full">
          <canvas ref={canvasRef} className="mx-auto block max-w-full" />
          {highlights.map((h, index) => (
            <div
              key={`${h.left}-${h.top}-${index}`}
              className="pointer-events-none absolute bg-amber-300/45 ring-2 ring-amber-500"
              style={{
                left: h.left,
                top: h.top,
                width: h.width,
                height: h.height,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

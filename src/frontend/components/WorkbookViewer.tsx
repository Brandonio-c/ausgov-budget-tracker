"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";
import { api } from "@/lib/api";
import { SourceContext } from "@/lib/types";

export type WorkbookResolveHints = {
  purpose?: string | null;
  financialYearLabel?: string | null;
  rowNumber?: number | null;
  amountAud?: number | null;
};

interface Props {
  itemId: number;
  context: SourceContext;
  sourceKey: string;
  /** Override Phase 1 /api/spending source-file fetch (e.g. facts dashboard). */
  fetchSourceFile?: (itemId: number, signal?: AbortSignal) => Promise<ArrayBuffer>;
  resolveHints?: WorkbookResolveHints;
}

const ROW_WINDOW_SIZE = 200;
const workbookCache = new Map<string, Promise<XLSX.WorkBook>>();

function loadWorkbook(
  itemId: number,
  sourceKey: string,
  fetchSourceFile: (itemId: number, signal?: AbortSignal) => Promise<ArrayBuffer>,
) {
  const cached = workbookCache.get(sourceKey);
  if (cached) return cached;

  const request = fetchSourceFile(itemId)
    .then((buffer) => XLSX.read(buffer, { type: "array", cellDates: false }))
    .catch((error) => {
      workbookCache.delete(sourceKey);
      throw error;
    });
  workbookCache.set(sourceKey, request);
  return request;
}

function cellText(sheet: XLSX.WorkSheet, address: string): string {
  const cell = sheet[address];
  if (!cell) return "";
  return String(XLSX.utils.format_cell(cell) ?? "").trim();
}

function normalizeLabel(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function labelsMatch(cellTextValue: string, needle: string): boolean {
  if (!cellTextValue || !needle) return false;
  if (cellTextValue === needle) return true;
  // Prefer whole-label containment; reject tiny fragments matching long titles.
  if (needle.length >= 4 && cellTextValue.includes(needle)) return true;
  if (cellTextValue.length >= 8 && needle.includes(cellTextValue)) return true;
  return false;
}

function isFyToken(text: string): boolean {
  return /^\d{4}-\d{2}$/.test(text);
}

function amountCandidates(amountAud: number | null | undefined): number[] {
  if (amountAud == null || !Number.isFinite(amountAud)) return [];
  const millions = amountAud / 1_000_000;
  return [amountAud, millions, Math.round(millions)];
}

function numericMatchesAmount(value: number, amountAud: number | null | undefined): boolean {
  for (const candidate of amountCandidates(amountAud)) {
    if (Math.abs(value - candidate) < 0.51) return true;
  }
  return false;
}

/** Infer a highlight cell when Gate 6 gave sheet/purpose/fy/row but not A1. */
export function resolveHighlightCell(
  sheet: XLSX.WorkSheet,
  hints: WorkbookResolveHints | undefined,
  existing: string | null | undefined,
): string | null {
  if (existing) return existing;
  if (!hints) return null;

  const range = XLSX.utils.decode_range(sheet["!ref"] ?? "A1");
  const purpose = hints.purpose ? normalizeLabel(hints.purpose) : "";
  const fy = hints.financialYearLabel ? normalizeLabel(hints.financialYearLabel) : "";

  let targetRow: number | null = null;
  let targetCol: number | null = null;

  if (purpose) {
    for (let r = range.s.r; r <= range.e.r; r += 1) {
      for (let c = range.s.c; c <= Math.min(range.e.c, range.s.c + 2); c += 1) {
        const text = normalizeLabel(cellText(sheet, XLSX.utils.encode_cell({ r, c })));
        if (labelsMatch(text, purpose)) {
          targetRow = r;
          break;
        }
      }
      if (targetRow !== null) break;
    }
  }

  // FY headers must be exact year tokens (e.g. "2024-25"), never a title that merely
  // contains the year as a substring — that previously pinned highlights to column A.
  if (fy && isFyToken(fy)) {
    for (let r = range.s.r; r <= Math.min(range.e.r, range.s.r + 15); r += 1) {
      for (let c = range.s.c; c <= range.e.c; c += 1) {
        const text = normalizeLabel(cellText(sheet, XLSX.utils.encode_cell({ r, c })));
        if (text === fy) {
          targetCol = c;
          break;
        }
      }
      if (targetCol !== null) break;
    }
  }

  if (hints.rowNumber != null && hints.rowNumber > 0 && targetRow === null) {
    targetRow = hints.rowNumber - 1; // 1-based sheet row
  }

  if (targetRow !== null && targetCol !== null) {
    return XLSX.utils.encode_cell({ r: targetRow, c: targetCol });
  }

  // On a known purpose row, prefer the cell whose value matches the fact amount.
  if (targetRow !== null && hints.amountAud != null) {
    for (let c = range.s.c; c <= range.e.c; c += 1) {
      const address = XLSX.utils.encode_cell({ r: targetRow, c });
      const cell = sheet[address];
      if (cell && typeof cell.v === "number" && numericMatchesAmount(cell.v, hints.amountAud)) {
        return address;
      }
    }
  }

  if (targetRow !== null && targetCol === null) {
    for (let c = range.s.c + 1; c <= range.e.c; c += 1) {
      const address = XLSX.utils.encode_cell({ r: targetRow, c });
      const cell = sheet[address];
      if (cell && typeof cell.v === "number") return address;
    }
  }

  if (hints.amountAud != null) {
    for (let r = range.s.r; r <= range.e.r; r += 1) {
      for (let c = range.s.c; c <= range.e.c; c += 1) {
        const cell = sheet[XLSX.utils.encode_cell({ r, c })];
        if (!cell || typeof cell.v !== "number") continue;
        if (numericMatchesAmount(cell.v, hints.amountAud)) {
          return XLSX.utils.encode_cell({ r, c });
        }
      }
    }
  }

  return null;
}

/** Trim SheetJS's over-wide !ref (often A1:IV…) down to columns that actually hold values. */
export function usedSheetBounds(sheet: XLSX.WorkSheet) {
  const range = XLSX.utils.decode_range(sheet["!ref"] ?? "A1");
  let maxC = range.s.c;
  let maxR = range.s.r;
  for (const key of Object.keys(sheet)) {
    if (key.startsWith("!")) continue;
    const addr = XLSX.utils.decode_cell(key);
    if (addr.c > maxC) maxC = addr.c;
    if (addr.r > maxR) maxR = addr.r;
  }
  return {
    s: { r: range.s.r, c: range.s.c },
    e: { r: Math.min(range.e.r, maxR), c: Math.min(range.e.c, maxC) },
  };
}

function displayContextCell(value: string | number | boolean | null) {
  if (value === null || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString("en-AU", { maximumFractionDigits: 3 });
  return String(value);
}

export function ReconstructedContextTable({ context }: { context: SourceContext }) {
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
        {context.sheet_name && <span>Sheet: {context.sheet_name}</span>}
        {context.cell_range && <span>Range: {context.cell_range}</span>}
        {context.page_number != null && <span>Page: {context.page_number}</span>}
        {context.highlight && <span>Figure: {context.highlight.cell}</span>}
      </div>
      <div className="overflow-x-auto rounded-md border border-black/10 dark:border-white/10">
        <table className="min-w-full border-collapse text-left text-xs">
          <thead className="bg-zinc-100 dark:bg-zinc-800">
            <tr>
              {context.columns.map((column, columnIndex) => (
                <th key={`${column}-${columnIndex}`} className="border-b border-black/10 px-2 py-2 font-medium text-zinc-700 dark:border-white/10 dark:text-zinc-200">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {context.rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b border-black/5 last:border-0 dark:border-white/5">
                {row.map((value, columnIndex) => {
                  const highlighted = context.highlight?.row_index === rowIndex && context.highlight.column_index === columnIndex;
                  return (
                    <td
                      key={columnIndex}
                      className={`whitespace-nowrap px-2 py-2 text-zinc-700 dark:text-zinc-300 ${highlighted ? "bg-sky-100 font-semibold text-zinc-900 ring-2 ring-inset ring-sky-600 dark:bg-sky-950 dark:text-sky-50 dark:ring-sky-400" : ""}`}
                    >
                      {displayContextCell(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {context.note && <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">{context.note}</p>}
    </div>
  );
}

function sheetRange(sheet: XLSX.WorkSheet) {
  return usedSheetBounds(sheet);
}

function initialRowForSheet(sheet: XLSX.WorkSheet, targetCell: string | null) {
  const range = sheetRange(sheet);
  if (!targetCell) return range.s.r;
  const targetRow = XLSX.utils.decode_cell(targetCell).r;
  return Math.max(range.s.r, Math.min(targetRow - 40, range.e.r - ROW_WINDOW_SIZE + 1));
}

function contextSheetColumns(cellRange: string | null) {
  const columns: number[] = [];
  if (!cellRange) return columns;

  for (const part of cellRange.split(",")) {
    try {
      const range = XLSX.utils.decode_range(part.trim());
      for (let column = range.s.c; column <= range.e.c; column += 1) {
        if (!columns.includes(column)) columns.push(column);
      }
    } catch {
      // Keep the workbook usable when older evidence metadata has no valid range.
    }
  }

  return columns;
}

export default function WorkbookViewer({
  itemId,
  context,
  sourceKey,
  fetchSourceFile = api.itemSourceFile,
  resolveHints,
}: Props) {
  const gridScrollerRef = useRef<HTMLDivElement>(null);
  const [workbook, setWorkbook] = useState<XLSX.WorkBook | null>(null);
  const [activeSheet, setActiveSheet] = useState("");
  const [rowStart, setRowStart] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [resolvedCell, setResolvedCell] = useState<string | null>(context.highlight?.cell ?? null);

  useEffect(() => {
    let cancelled = false;

    loadWorkbook(itemId, sourceKey, fetchSourceFile).then(
      (parsed) => {
        if (cancelled) return;
        const selectedSheet = context.sheet_name && parsed.SheetNames.includes(context.sheet_name)
          ? context.sheet_name
          : parsed.SheetNames[0];
        const sheet = parsed.Sheets[selectedSheet];
        const cell = resolveHighlightCell(
          sheet,
          resolveHints,
          selectedSheet === context.sheet_name ? context.highlight?.cell ?? null : null,
        );
        setWorkbook(parsed);
        setActiveSheet(selectedSheet);
        setResolvedCell(cell);
        setRowStart(initialRowForSheet(sheet, cell));
      },
      (error) => {
        if (!cancelled) setLoadError(String(error));
      },
    );

    return () => { cancelled = true; };
  }, [context.highlight?.cell, context.sheet_name, fetchSourceFile, itemId, resolveHints, sourceKey]);

  const grid = useMemo(() => {
    if (!workbook || !activeSheet) return null;
    const sheet = workbook.Sheets[activeSheet];
    const range = sheetRange(sheet);
    const start = Math.max(range.s.r, Math.min(rowStart, range.e.r));
    const end = Math.min(range.e.r, start + ROW_WINDOW_SIZE - 1);
    const columns = Array.from({ length: range.e.c - range.s.c + 1 }, (_, index) => range.s.c + index);
    const rows = Array.from({ length: end - start + 1 }, (_, index) => start + index);
    return { sheet, range, start, end, columns, rows };
  }, [activeSheet, rowStart, workbook]);

  const targetCell = activeSheet === context.sheet_name || !context.sheet_name
    ? resolvedCell
    : null;
  const contextColumns = useMemo(
    () => contextSheetColumns(context.cell_range),
    [context.cell_range],
  );
  const contextHeaders = useMemo(
    () => new Map(contextColumns.map((column, index) => [column, context.columns[index]])),
    [context.columns, contextColumns],
  );
  // Always keep the leftmost label column readable (ABS purpose names were truncating).
  const frozenLabelColumn = grid?.range.s.c ?? 0;

  const yearHeaderByColumn = useMemo(() => {
    const map = new Map<number, string>();
    if (!grid) return map;
    for (let r = grid.range.s.r; r <= Math.min(grid.range.e.r, grid.range.s.r + 15); r += 1) {
      for (let c = grid.range.s.c; c <= grid.range.e.c; c += 1) {
        const text = cellText(grid.sheet, XLSX.utils.encode_cell({ r, c }));
        if (/^\d{4}-\d{2}$/.test(text) && !map.has(c)) map.set(c, text);
      }
    }
    return map;
  }, [grid]);

  useEffect(() => {
    const scroller = gridScrollerRef.current;
    if (!grid || !targetCell || !scroller) return;
    const target = document.getElementById(`source-workbook-cell-${targetCell}`);
    if (!target) return;
    const scrollerRect = scroller.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    scroller.scrollTo({
      top: scroller.scrollTop + targetRect.top - scrollerRect.top - scroller.clientHeight / 2 + targetRect.height / 2,
      left: scroller.scrollLeft + targetRect.left - scrollerRect.left - scroller.clientWidth / 2 + targetRect.width / 2,
    });
  }, [grid, targetCell]);

  if (loadError) {
    return (
      <div className="mt-4">
        <p className="mb-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          The original cached workbook could not be loaded ({loadError}). Showing the reconstructed source context instead.
        </p>
        <ReconstructedContextTable context={context} />
      </div>
    );
  }

  if (!workbook || !grid) {
    return (
      <div className="mt-4">
        <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">Loading the original cached government workbook…</p>
        <div className="mb-2 text-xs font-medium text-zinc-600 dark:text-zinc-300">Reconstructed preview while the original loads</div>
        <ReconstructedContextTable context={context} />
      </div>
    );
  }

  function selectSheet(sheetName: string) {
    if (!workbook) return;
    const sheet = workbook.Sheets[sheetName];
    const cell = resolveHighlightCell(
      sheet,
      resolveHints,
      sheetName === context.sheet_name ? context.highlight?.cell ?? null : null,
    );
    setActiveSheet(sheetName);
    setResolvedCell(cell);
    setRowStart(initialRowForSheet(sheet, cell));
  }

  return (
    <div className="mt-4">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400">Original cached government workbook</p>
          <label className="mt-1 block text-xs text-zinc-500 dark:text-zinc-400" htmlFor={`sheet-${itemId}`}>Sheet</label>
          <select
            id={`sheet-${itemId}`}
            value={activeSheet}
            onChange={(event) => selectSheet(event.target.value)}
            className="mt-1 max-w-full rounded-md border border-black/10 bg-white px-2 py-1 text-xs text-zinc-900 dark:border-white/10 dark:bg-zinc-800 dark:text-zinc-50"
          >
            {workbook.SheetNames.map((sheetName) => <option key={sheetName}>{sheetName}</option>)}
          </select>
        </div>
        <div className="text-right text-xs text-zinc-500 dark:text-zinc-400">
          <div>Rows {grid.start + 1}–{grid.end + 1} of {grid.range.e.r + 1}</div>
          {targetCell && <div>Highlighted source cell: {targetCell}</div>}
        </div>
      </div>

      <div ref={gridScrollerRef} className="max-h-[520px] overflow-auto rounded-md border border-black/10 dark:border-white/10">
        <table className="w-max table-fixed border-separate border-spacing-0 text-left text-xs" data-testid="original-workbook-grid">
          <thead className="sticky top-0 z-20 bg-zinc-100 dark:bg-zinc-800">
            <tr>
              <th className="sticky left-0 z-30 w-12 min-w-12 border-b border-r border-black/10 bg-zinc-100 px-2 py-1 dark:border-white/10 dark:bg-zinc-800" />
              {grid.columns.map((column) => (
                <th
                  key={column}
                  title={contextHeaders.get(column) || yearHeaderByColumn.get(column)}
                  className={`border-b border-r border-black/10 px-2 py-1 text-center font-medium text-zinc-600 dark:border-white/10 dark:text-zinc-300 ${
                    column === frozenLabelColumn
                      ? "sticky left-12 z-30 w-64 min-w-64 max-w-64 bg-zinc-100 text-left shadow-[2px_0_0_rgba(0,0,0,0.08)] dark:bg-zinc-800"
                      : contextHeaders.has(column) || yearHeaderByColumn.has(column)
                        ? "w-28 min-w-28 max-w-28"
                        : "w-20 min-w-20 max-w-20"
                  }`}
                >
                  <span className="block text-[10px] uppercase tracking-wide text-zinc-400">
                    {XLSX.utils.encode_col(column)}
                  </span>
                  {(contextHeaders.get(column) || yearHeaderByColumn.get(column)) && (
                    <span className="block truncate text-xs normal-case tracking-normal text-zinc-700 dark:text-zinc-200">
                      {contextHeaders.get(column) || yearHeaderByColumn.get(column)}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.rows.map((row) => (
              <tr key={row}>
                <th className="sticky left-0 z-10 w-12 min-w-12 border-b border-r border-black/10 bg-zinc-100 px-2 py-1 text-right font-medium text-zinc-500 dark:border-white/10 dark:bg-zinc-800 dark:text-zinc-400">
                  {row + 1}
                </th>
                {grid.columns.map((column) => {
                  const address = XLSX.utils.encode_cell({ r: row, c: column });
                  const cell = grid.sheet[address];
                  const highlighted = address === targetCell;
                  const frozenLabel = column === frozenLabelColumn;
                  return (
                    <td
                      id={`source-workbook-cell-${address}`}
                      key={column}
                      title={cell?.f ? `=${cell.f}` : address}
                      className={`overflow-hidden text-ellipsis whitespace-nowrap border-b border-r border-black/10 px-2 py-1 text-zinc-700 dark:border-white/10 dark:text-zinc-300 ${
                        frozenLabel
                          ? "sticky left-12 z-10 w-64 min-w-64 max-w-64 shadow-[2px_0_0_rgba(0,0,0,0.08)]"
                          : contextHeaders.has(column) || yearHeaderByColumn.has(column)
                            ? "w-28 min-w-28 max-w-28"
                            : "w-20 min-w-20 max-w-20"
                      } ${highlighted ? "bg-sky-100 font-semibold text-zinc-900 ring-2 ring-inset ring-sky-600 dark:bg-sky-950 dark:text-sky-50 dark:ring-sky-400" : "bg-white dark:bg-zinc-900"}`}
                    >
                      {cell ? XLSX.utils.format_cell(cell) : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(grid.start > grid.range.s.r || grid.end < grid.range.e.r) && (
        <div className="mt-2 flex items-center justify-between gap-2">
          <button
            type="button"
            disabled={grid.start <= grid.range.s.r}
            onClick={() => setRowStart(Math.max(grid.range.s.r, grid.start - ROW_WINDOW_SIZE))}
            className="rounded border border-black/10 px-2 py-1 text-xs text-zinc-600 disabled:opacity-40 dark:border-white/10 dark:text-zinc-300"
          >
            Previous rows
          </button>
          <button
            type="button"
            disabled={grid.end >= grid.range.e.r}
            onClick={() => setRowStart(Math.min(grid.range.e.r, grid.end + 1))}
            className="rounded border border-black/10 px-2 py-1 text-xs text-zinc-600 disabled:opacity-40 dark:border-white/10 dark:text-zinc-300"
          >
            Next rows
          </button>
        </div>
      )}
      <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
        This grid is parsed in your browser from the byte-for-byte cached download; only the active sheet’s current row window is rendered.
      </p>
    </div>
  );
}

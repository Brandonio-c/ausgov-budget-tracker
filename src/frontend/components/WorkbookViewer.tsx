"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";
import { api } from "@/lib/api";
import { SourceContext } from "@/lib/types";

interface Props {
  itemId: number;
  context: SourceContext;
  sourceKey: string;
}

const ROW_WINDOW_SIZE = 200;
const workbookCache = new Map<string, Promise<XLSX.WorkBook>>();

function loadWorkbook(itemId: number, sourceKey: string) {
  const cached = workbookCache.get(sourceKey);
  if (cached) return cached;

  const request = api
    .itemSourceFile(itemId)
    .then((buffer) => XLSX.read(buffer, { type: "array", cellDates: false }))
    .catch((error) => {
      workbookCache.delete(sourceKey);
      throw error;
    });
  workbookCache.set(sourceKey, request);
  return request;
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
        <span>Sheet: {context.sheet_name}</span>
        <span>Range: {context.cell_range}</span>
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
                      className={`whitespace-nowrap px-2 py-2 text-zinc-700 dark:text-zinc-300 ${highlighted ? "bg-amber-200 font-semibold text-amber-950 ring-1 ring-inset ring-amber-500 dark:bg-amber-400 dark:text-amber-950" : ""}`}
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
  return XLSX.utils.decode_range(sheet["!ref"] ?? "A1");
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

export default function WorkbookViewer({ itemId, context, sourceKey }: Props) {
  const gridScrollerRef = useRef<HTMLDivElement>(null);
  const [workbook, setWorkbook] = useState<XLSX.WorkBook | null>(null);
  const [activeSheet, setActiveSheet] = useState("");
  const [rowStart, setRowStart] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    loadWorkbook(itemId, sourceKey).then(
      (parsed) => {
        if (cancelled) return;
        const selectedSheet = context.sheet_name && parsed.SheetNames.includes(context.sheet_name)
          ? context.sheet_name
          : parsed.SheetNames[0];
        setWorkbook(parsed);
        setActiveSheet(selectedSheet);
        setRowStart(
          initialRowForSheet(
            parsed.Sheets[selectedSheet],
            selectedSheet === context.sheet_name ? context.highlight?.cell ?? null : null,
          ),
        );
      },
      (error) => {
        if (!cancelled) setLoadError(String(error));
      },
    );

    return () => { cancelled = true; };
  }, [context.highlight?.cell, context.sheet_name, itemId, sourceKey]);

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

  const targetCell = activeSheet === context.sheet_name ? context.highlight?.cell ?? null : null;
  const contextColumns = useMemo(
    () => contextSheetColumns(context.cell_range),
    [context.cell_range],
  );
  const contextHeaders = useMemo(
    () => new Map(contextColumns.map((column, index) => [column, context.columns[index]])),
    [context.columns, contextColumns],
  );
  const frozenLabelColumn = activeSheet === context.sheet_name ? contextColumns[0] : undefined;

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
    setActiveSheet(sheetName);
    setRowStart(
      initialRowForSheet(
        workbook.Sheets[sheetName],
        sheetName === context.sheet_name ? context.highlight?.cell ?? null : null,
      ),
    );
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
                  title={contextHeaders.get(column)}
                  className={`border-b border-r border-black/10 px-2 py-1 text-center font-medium text-zinc-600 dark:border-white/10 dark:text-zinc-300 ${
                    column === frozenLabelColumn
                      ? "sticky left-12 z-30 w-64 min-w-64 max-w-64 bg-zinc-100 text-left shadow-[2px_0_0_rgba(0,0,0,0.08)] dark:bg-zinc-800"
                      : contextHeaders.has(column)
                        ? "w-32 min-w-32 max-w-32"
                        : "w-20 min-w-20 max-w-20"
                  }`}
                >
                  <span className="block text-[10px] uppercase tracking-wide text-zinc-400">
                    {XLSX.utils.encode_col(column)}
                  </span>
                  {contextHeaders.get(column) && (
                    <span className="block truncate text-xs normal-case tracking-normal text-zinc-700 dark:text-zinc-200">
                      {contextHeaders.get(column)}
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
                          : contextHeaders.has(column)
                            ? "w-32 min-w-32 max-w-32"
                            : "w-20 min-w-20 max-w-20"
                      } ${highlighted ? "bg-amber-200 font-semibold text-amber-950 ring-2 ring-inset ring-amber-500 dark:bg-amber-400 dark:text-amber-950" : "bg-white dark:bg-zinc-900"}`}
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

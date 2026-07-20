"""Parser for the VAGO Victorian local government financial data workbook.

The 'Financial Data' sheet is already tidy: one row per
(council, year, composition category, sub-category) with a dollar Value.
We take only the 'Total expenses composition' rows, since this dashboard
tracks spending (revenue/asset/liability compositions in the same file are
out of scope). Figures are already in raw AUD dollars.
"""
import openpyxl

from .common import SpendingRow

EXPENSE_COMPOSITION = "Total expenses composition"


def parse(raw_file, meta: dict) -> list[SpendingRow]:
    wb = openpyxl.load_workbook(raw_file, read_only=True, data_only=True)
    ws = wb["Financial Data"]
    sheet_rows = list(ws.iter_rows(values_only=True))
    header = sheet_rows[0]
    idx = {name: i for i, name in enumerate(header)}

    rows: list[SpendingRow] = []
    for source_row_index, row in enumerate(sheet_rows[1:], start=2):
        if row[idx["Composition Selection"]] != EXPENSE_COMPOSITION:
            continue
        council = row[idx["Council and Benchmark Averages"]]
        year = row[idx["Year"]]
        subcategory = row[idx["Sub-Category"]]
        value = row[idx["Value"]]
        if not isinstance(council, str) or not isinstance(value, (int, float)):
            continue

        context_start = max(2, source_row_index - 1)
        context_end = min(len(sheet_rows), source_row_index + 1)
        context_rows = [list(sheet_rows[row_number - 1]) for row_number in range(context_start, context_end + 1)]
        rows.append(
            SpendingRow(
                financial_year=str(year),
                level_of_government="local",
                jurisdiction=f"VIC — {council}",
                category="Total expenses",
                subcategory=subcategory if isinstance(subcategory, str) else None,
                department=None,
                amount_aud=round(float(value), 2),
                source_document_name=meta["source_document_name"],
                source_url=meta["source_url"],
                retrieved_at=meta["retrieved_at"],
                source_context={
                    "source_type": "spreadsheet",
                    "sheet_name": ws.title,
                    "cell_range": f"A{context_start}:E{context_end}",
                    "columns": [str(value) for value in header],
                    "rows": context_rows,
                    "highlight": {
                        "row_index": source_row_index - context_start,
                        "column_index": idx["Value"],
                        "cell": f"E{source_row_index}",
                    },
                    "unit": "AUD",
                    "note": "The highlighted workbook value is already expressed in AUD.",
                },
            )
        )
    return rows

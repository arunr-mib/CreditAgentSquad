"""Spreadsheets as documents: one text page per sheet, one line per cell, each line naming its sheet and cell
so a figure can be cited to the cell it came from."""
import csv
import io
from dataclasses import dataclass, field

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


@dataclass
class SheetPage:
    name: str
    lines: list[str] = field(default_factory=list)
    cells: dict[str, str] = field(default_factory=dict)


def _rows_to_page(name: str, rows) -> SheetPage:
    page = SheetPage(name)
    for r, row in enumerate(rows, start=1):
        row = list(row)
        label_at = next((i for i, v in enumerate(row) if isinstance(v, str) and v.strip()), None)
        label = str(row[label_at]).strip() if label_at is not None else ""
        for c, value in enumerate(row):
            if value is None or str(value).strip() == "" or c == label_at:
                continue
            ref = f"{get_column_letter(c + 1)}{r}"
            page.cells[ref] = str(value)
            page.lines.append(f"{name}!{ref} | {label} | {value}")
    return page


def spreadsheet_pages(data: bytes, file_name: str) -> list[SheetPage]:
    if file_name.lower().endswith(".csv"):
        text = data.decode("utf-8-sig")
        return [_rows_to_page("Sheet1", list(csv.reader(io.StringIO(text))))]
    book = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    try:
        return [_rows_to_page(ws.title, ws.iter_rows(values_only=True)) for ws in book.worksheets]
    finally:
        book.close()

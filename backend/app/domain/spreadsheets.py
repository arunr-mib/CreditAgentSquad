"""Spreadsheets as documents: one text page per sheet, one line per cell, each line naming its sheet and cell
so a figure can be cited to the cell it came from."""
import csv
import io
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

MAX_SHEETS = 50
MAX_ROWS = 20_000
MAX_COLUMNS = 200
MAX_LINES = 200_000
MAX_ITERATED_CELLS = 2_000_000  # every cell walked, empty or not: a sheet of blanks costs time, not lines
MAX_UNCOMPRESSED = 100 * 1024 * 1024
NOT_CALCULATED = "(formula, not calculated)"


class SpreadsheetRefused(ValueError):
    """The file is too large or not a readable spreadsheet; the message is plain words for the person."""


@dataclass
class SheetPage:
    name: str
    lines: list[str] = field(default_factory=list)
    cells: dict[str, str] = field(default_factory=dict)
    uncalculated: list[str] = field(default_factory=list)  # cell references holding a formula with no stored result


def _text(value) -> str:
    """One canonical spelling for a cell value: ISO dates, plain decimal numbers, no trailing ".0"."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time(0) else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        text = format(Decimal(repr(value)), "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value).strip()


def _is_formula(value) -> bool:
    return isinstance(value, str) and value.startswith("=") and len(value) > 1


def _rows_to_page(name: str, rows, formulas=None, budget: list[int] | None = None,
                  walked: list[int] | None = None) -> SheetPage:
    page = SheetPage(name)
    budget = budget if budget is not None else [MAX_LINES]
    walked = walked if walked is not None else [MAX_ITERATED_CELLS]
    for r, row in enumerate(rows, start=1):
        if r > MAX_ROWS:
            raise SpreadsheetRefused(f"Sheet {name!r} has more than {MAX_ROWS:,} rows.")
        row = list(row)
        formula_row = list(next(formulas)) if formulas is not None else []
        if len(row) > MAX_COLUMNS:
            raise SpreadsheetRefused(f"Sheet {name!r} has more than {MAX_COLUMNS} columns.")
        walked[0] -= len(row)
        if walked[0] < 0:
            raise SpreadsheetRefused(f"The spreadsheet has more than {MAX_ITERATED_CELLS:,} cells to read, empty ones "
                                     "included.")
        label_at = next((i for i, v in enumerate(row) if isinstance(v, str) and v.strip()), None)
        label = _text(row[label_at]) if label_at is not None else ""
        for c, value in enumerate(row):
            ref = f"{get_column_letter(c + 1)}{r}"
            note = ""
            if value is None and c < len(formula_row) and _is_formula(formula_row[c]):
                page.uncalculated.append(ref)
                value, note = formula_row[c], f" {NOT_CALCULATED}"
            if value is None or str(value).strip() == "" or c == label_at:
                continue
            budget[0] -= 1
            if budget[0] < 0:
                raise SpreadsheetRefused(f"The spreadsheet has more than {MAX_LINES:,} filled cells.")
            shown = _text(value)
            page.cells[ref] = shown
            page.lines.append(f"{name}!{ref} | {label} | {shown}{note}")
    return page


def _decode_csv(data: bytes) -> str:
    if b"\x00" in data:
        raise SpreadsheetRefused("The file is not a text CSV (it contains binary data).")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _check_zip(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            total = sum(i.file_size for i in z.infolist())
    except zipfile.BadZipFile as exc:
        raise SpreadsheetRefused("The file is not a valid Excel workbook.") from exc
    if total > MAX_UNCOMPRESSED:
        raise SpreadsheetRefused(f"The workbook is too large once unpacked (over {MAX_UNCOMPRESSED // (1024 * 1024)} MB).")


def spreadsheet_pages(data: bytes, file_name: str) -> list[SheetPage]:
    if file_name.lower().endswith(".csv"):
        text = _decode_csv(data)
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","
        return [_rows_to_page("Sheet1", csv.reader(io.StringIO(text), delimiter=delimiter))]
    _check_zip(data)
    values = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    try:
        sheets = values.worksheets
        if len(sheets) > MAX_SHEETS:
            raise SpreadsheetRefused(f"The workbook has more than {MAX_SHEETS} sheets.")
        for ws in sheets:  # declared dimensions are read from the sheet header: refuse before iterating
            if (ws.max_row or 0) > MAX_ROWS:
                raise SpreadsheetRefused(f"Sheet {ws.title!r} has more than {MAX_ROWS:,} rows.")
            if (ws.max_column or 0) > MAX_COLUMNS:
                raise SpreadsheetRefused(f"Sheet {ws.title!r} has more than {MAX_COLUMNS} columns.")
        formulas = load_workbook(io.BytesIO(data), data_only=False, read_only=True)
        try:
            budget, walked = [MAX_LINES], [MAX_ITERATED_CELLS]
            return [_rows_to_page(ws.title, ws.iter_rows(values_only=True),
                                  formulas[ws.title].iter_rows(values_only=True), budget, walked) for ws in sheets]
        finally:
            formulas.close()
    finally:
        values.close()

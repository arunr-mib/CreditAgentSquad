"""Prove that every figure in a package's files resolves to a fact in its snapshot.

The verifier does not trust the renderers. It reopens each file, reads every figure back out
(cell values and recomputed formulas in Excel; text runs and table cells in Word; text, table
cells and chart data in PowerPoint), follows the figure's reference to a source listed in the
file, and checks the printed figure against the value frozen in the snapshot. A figure with no
reference, a reference with no source, a source that is not in the snapshot, or a value that does
not match is a problem. Dates, page numbers, reference numbers and identifiers are not figures.
It also checks the snapshot itself: its hash, its derived figures, and that each frozen fact still
equals the stored fact.
"""
import hashlib
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn as wqn
from docx.table import Table
from docx.text.paragraph import Paragraph
from openpyxl import load_workbook
from pptx import Presentation
from pptx.oxml.ns import qn as pqn
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.facts import Fact
from app.domain.reviews import Package, Snapshot
from app.guardrails.numbers import Figure, extract_figures
from app.publishing import deck as deck_format
from app.publishing import excel as excel_format
from app.publishing import word as word_format
from app.publishing.content import describe_source
from app.publishing.formula import FormulaError, evaluate

_HASH = re.compile(r"\b[0-9a-f]{64}\b")
_NUMBER = re.compile(r"\d[\d,]*(?:\.(\d+))?")
_NOTE = re.compile(r"^\[(\d+)\] .* \| (fact|derived) (\S+) \| ")
_CHART = re.compile(r'^Chart "(.*)", series "(.*)": (.*)$')
_POINT = re.compile(r"(.+?) \[(\d+)\](?:; |$)")
_EXACT = Decimal("0.000000001")


@dataclass
class Problem:
    file: str
    where: str
    figure: str
    reason: str

    def describe(self) -> str:
        return f"{self.file}, {self.where}: {self.figure!r} {self.reason}"

    def to_dict(self) -> dict[str, str]:
        return {"file": self.file, "where": self.where, "figure": self.figure, "reason": self.reason}


@dataclass
class VerifyReport:
    package_id: str
    snapshot_sha256: str | None = None
    figures_checked: int = 0
    files: list[dict[str, Any]] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict[str, Any]:
        return {"package_id": self.package_id, "ok": self.ok, "snapshot_sha256": self.snapshot_sha256,
                "figures_checked": self.figures_checked, "files": self.files,
                "problems": [p.to_dict() for p in self.problems]}


def figures_in(text: str) -> list[Figure]:
    """The figures in a piece of text. Hashes, like ids and dates, are not figures."""
    return extract_figures(_HASH.sub(lambda m: " " * len(m.group(0)), text or ""))


def figure_matches(figure: Figure, record: dict[str, Any]) -> bool:
    """A printed figure matches a fact when it is the fact's value rounded to the printed
    precision (a percentage is the fraction times one hundred; 'million' and 'thousand' scale)."""
    value = Decimal(record["value"])
    target = value * 100 if figure.kind == "percent" else value
    m = _NUMBER.search(figure.raw)
    if m is None:
        return False
    printed = Decimal(m.group(0).replace(",", ""))
    scale = abs(figure.value) / printed if printed != 0 else Decimal(1)
    unit = Decimal(1).scaleb(-len(m.group(1) or "")) * scale
    return abs(figure.value - target) <= unit / 2


def same_value(cell: Decimal, record: dict[str, Any]) -> bool:
    value = Decimal(record["value"])
    return abs(cell - value) <= _EXACT * max(Decimal(1), abs(value))


class _FileCheck:
    def __init__(self, name: str, sources: dict[str, dict[str, Any]], facts: dict[str, dict[str, Any]]):
        self.name, self.sources, self.facts = name, sources, facts
        self.problems: list[Problem] = []
        self.figures = 0

    def problem(self, where: str, figure: str, reason: str) -> None:
        self.problems.append(Problem(self.name, where, figure, reason))

    def check_runs(self, parts: list[tuple[str, bool]], refmap: dict[int, str], where: str) -> None:
        """One paragraph: every figure must be followed by a reference number, before the next
        figure, and the fact behind that reference must print as that figure."""
        plain, marks = "", []  # marks: (position in plain, reference text)
        for text, is_ref in parts:
            if is_ref:
                marks.append((len(plain), text.strip()))
            else:
                plain += text
        figures = figures_in(plain)
        used: set[int] = set()
        for i, fig in enumerate(figures):
            self.figures += 1
            limit = figures[i + 1].start if i + 1 < len(figures) else len(plain)
            found = next((k for k, (pos, _) in enumerate(marks) if k not in used and fig.end <= pos <= limit), None)
            if found is None:
                self.problem(where, fig.raw, "has no source reference")
                continue
            used.add(found)
            ref = marks[found][1]
            sid = refmap.get(int(ref)) if ref.isdigit() else None
            record = self.sources.get(sid) if sid else None
            if record is None:
                self.problem(where, fig.raw, f"cites reference {ref}, which is not a source in the snapshot")
            elif not figure_matches(fig, record):
                self.problem(where, fig.raw, f"does not match its source {sid} ({record['label']}: {record['value']})")
        for k, (_, ref) in enumerate(marks):
            if k not in used:
                self.problem(where, ref, "is a source reference with no figure beside it")

    def no_figures(self, text: str, where: str) -> None:
        for fig in figures_in(text):
            self.figures += 1
            self.problem(where, fig.raw, "is a figure in text that carries no source reference")


# Word ---------------------------------------------------------------------------------------------
def _docx_parts(paragraph: Paragraph) -> tuple[list[tuple[str, bool]], int]:
    parts, seen = [], 0
    for run in paragraph.runs:
        is_ref = run.style is not None and run.style.name == word_format.REF_STYLE
        parts.append((run.text, is_ref))
        seen += sum(len(t.text or "") for t in run._r.findall(wqn("w:t")))
    return parts, seen


def check_docx(check: _FileCheck, data: bytes) -> None:
    doc = Document(io.BytesIO(data))
    blocks: list[tuple[str, Any]] = []
    for child in doc.element.body.iterchildren():
        if child.tag == wqn("w:p"):
            blocks.append(("p", Paragraph(child, doc)))
        elif child.tag == wqn("w:tbl"):
            blocks.append(("t", Table(child, doc)))
    # the Sources table gives reference number -> source id; each row must say what the snapshot says
    refmap: dict[int, str] = {}
    source_tables = []
    for kind, block in blocks:
        if kind != "t" or tuple(c.text for c in block.rows[0].cells) != word_format.SOURCE_COLUMNS:
            continue
        source_tables.append(block._tbl)
        for row in block.rows[1:]:
            cells = [c.text for c in row.cells]
            ref, sid = cells[0], cells[1]
            record = check.sources.get(sid)
            if not ref.isdigit() or record is None:
                check.problem("Sources", ref, f"lists {sid!r}, which is not a source in the snapshot")
                continue
            d = describe_source(record, check.facts)
            if cells[2:] != [d["item"], d["document"], d["page"], d["detail"]]:
                check.problem("Sources", ref, f"describes source {sid} differently from the snapshot")
            if int(ref) in refmap:
                check.problem("Sources", ref, "is listed twice")
            refmap[int(ref)] = sid
    seen = 0

    def paragraph(p: Paragraph, where: str) -> None:
        nonlocal seen
        parts, n = _docx_parts(p)
        seen += n
        check.check_runs(parts, refmap, where)

    def table(t: Table, where: str) -> None:
        nonlocal seen
        if t._tbl in source_tables:
            seen += sum(len(x.text or "") for x in t._tbl.iter(wqn("w:t")))
            return
        for r, row in enumerate(t.rows, start=1):
            for c, cell in enumerate(row.cells, start=1):
                for p in cell.paragraphs:
                    paragraph(p, f"{where}, row {r}, column {c}")
                for inner in cell.tables:
                    table(inner, where)

    heading, tables = "start", 0
    for kind, block in blocks:
        if kind == "p":
            if block.style is not None and block.style.name.startswith(("Heading", "Title")) and block.text.strip():
                heading, tables = block.text.strip(), 0
            paragraph(block, f'section "{heading}"')
        else:
            tables += 1
            table(block, f'section "{heading}", table {tables}')
    total = sum(len(t.text or "") for t in doc.element.body.iter(wqn("w:t")))
    if total != seen:
        check.problem("document", "", f"holds {total - seen} character(s) of text outside the paragraphs that were read")
    for n, section in enumerate(doc.sections, start=1):
        for part, name in ((section.header, "header"), (section.footer, "footer")):
            for p in part.paragraphs:
                check.check_runs(_docx_parts(p)[0], refmap, f"{name} {n}")
            for t in part.tables:
                table(t, f"{name} {n}")


# Excel --------------------------------------------------------------------------------------------
def check_xlsx(check: _FileCheck, data: bytes) -> dict[tuple[str, str], Decimal]:
    """Returns every figure cell's value (formulas recomputed), for callers that want them."""
    wb = load_workbook(io.BytesIO(data), data_only=False)
    values: dict[tuple[str, str], Decimal] = {}
    if excel_format.SOURCES_SHEET not in wb.sheetnames:
        check.problem("workbook", "", "has no Sources sheet")
        return values
    # the Sources sheet: (sheet, cell) -> (fact id, what the cell holds)
    cellmap: dict[tuple[str, str], tuple[str, str]] = {}
    src = wb[excel_format.SOURCES_SHEET]
    header = excel_format.HEADER_ROW
    if tuple(c.value for c in src[header][:len(excel_format.SOURCE_COLUMNS)]) != excel_format.SOURCE_COLUMNS:
        check.problem("Sources", "", "does not have the expected columns")
        return values
    for row in src.iter_rows(min_row=header + 1, max_col=len(excel_format.SOURCE_COLUMNS), values_only=True):
        if row[0] is None:
            continue
        sheet, cell, item, sid, kind, role, document, page, detail = (("" if v is None else str(v)) for v in row)
        where = f"Sources, {sheet}!{cell}"
        if (sheet, cell) in cellmap:
            check.problem(where, cell, "is listed twice")
        cellmap[(sheet, cell)] = (sid, role)
        if not sid:
            if role != "formula":
                check.problem(where, cell, "is an input cell with no fact")
            continue
        record = check.facts.get(sid)
        if record is None:
            check.problem(where, sid, "is not a fact in the snapshot")
            continue
        d = describe_source(record, check.facts)
        if [kind, document, page, detail] != [d["kind"], d["document"], d["page"], d["detail"]] or (
                role == "input" and item != d["item"]):
            check.problem(where, sid, "is described differently from the snapshot")

    memo: dict[tuple[str, str], Decimal | None] = {}

    def cell_value(sheet: str, address: str) -> Decimal | None:
        key = (sheet, address)
        if key not in memo:
            if sheet not in wb.sheetnames:
                raise FormulaError(f"sheet {sheet!r} does not exist")
            raw = wb[sheet][address].value
            if raw is None:
                memo[key] = None
            elif isinstance(raw, bool) or isinstance(raw, datetime | date):
                raise FormulaError(f"{sheet}!{address} is not a number")
            elif isinstance(raw, int | float | Decimal):
                memo[key] = Decimal(repr(raw)) if isinstance(raw, float) else Decimal(raw)
            elif isinstance(raw, str) and raw.startswith("="):
                memo[key] = None  # guards against a formula that reads itself
                memo[key] = evaluate(raw, sheet, cell_value)
            else:
                raise FormulaError(f"{sheet}!{address} holds text")
        return memo[key]

    seen: set[tuple[str, str]] = set()
    for ws in wb.worksheets:
        if ws.title == excel_format.SOURCES_SHEET:
            continue
        for row in ws.iter_rows():
            for c in row:
                raw, where = c.value, f"{ws.title}!{c.coordinate}"
                if raw is None or isinstance(raw, bool | datetime | date):
                    continue
                is_formula = isinstance(raw, str) and raw.startswith("=")
                if isinstance(raw, str) and not is_formula:
                    check.no_figures(raw, where)
                    continue
                check.figures += 1
                key = (ws.title, c.coordinate)
                seen.add(key)
                sid, role = cellmap.get(key, (None, None))
                if role is None:
                    check.problem(where, str(raw), "is a figure cell that the Sources sheet does not list")
                    continue
                if is_formula != (role == "formula"):
                    check.problem(where, str(raw), f"is listed as {role} but holds {'a formula' if is_formula else 'a number'}")
                    continue
                try:
                    value = cell_value(ws.title, c.coordinate)
                except (FormulaError, InvalidOperation, ArithmeticError) as exc:
                    check.problem(where, str(raw), f"cannot be recomputed: {exc}")
                    continue
                if value is None:
                    check.problem(where, str(raw), "cannot be recomputed")
                    continue
                values[key] = value
                record = check.facts.get(sid) if sid else None
                if sid and record is None:
                    check.problem(where, str(raw), f"names fact {sid}, which is not in the snapshot")
                elif record is not None and not same_value(value, record):
                    check.problem(where, str(value), f"does not match its fact {sid} ({record['label']}: {record['value']})")
    for key in cellmap:
        if key not in seen:
            check.problem(f"Sources, {key[0]}!{key[1]}", key[1], "is listed but the cell holds no figure")
    return values


# PowerPoint ---------------------------------------------------------------------------------------
def _shapes(container: Any):
    for shape in container:
        if shape.shape_type is not None and getattr(shape, "shapes", None) is not None:
            yield from _shapes(shape.shapes)
        else:
            yield shape


def _pptx_parts(paragraph: Any) -> list[tuple[str, bool]]:
    parts = []
    for run in paragraph.runs:
        rpr = run._r.find(pqn("a:rPr"))
        baseline = rpr.get("baseline") if rpr is not None else None
        parts.append((run.text, baseline not in (None, "0")))
    for fld in paragraph._p.findall(pqn("a:fld")):
        if fld.get("type") != "slidenum":  # the slide number is not a figure
            parts.append(("".join(t.text or "" for t in fld.iter(pqn("a:t"))), False))
    return parts


def check_pptx(check: _FileCheck, data: bytes) -> None:
    prs = Presentation(io.BytesIO(data))
    slides = list(prs.slides)
    refmap: dict[int, str] = {}
    chart_refs: dict[tuple[int, str], dict[str, int]] = {}
    for idx, slide in enumerate(slides, start=1):
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        for line in notes.splitlines():
            where = f"slide {idx} notes"
            note, chart = _NOTE.match(line), _CHART.match(line)
            if note:
                n, sid = int(note.group(1)), note.group(3)
                record = check.sources.get(sid)
                if record is None:
                    check.problem(where, f"[{n}]", f"names {sid}, which is not a source in the snapshot")
                elif line != deck_format.note_line(n, record, check.facts):
                    check.problem(where, f"[{n}]", f"describes source {sid} differently from the snapshot")
                elif refmap.setdefault(n, sid) != sid:
                    check.problem(where, f"[{n}]", "is used for two different sources")
            elif chart:
                chart_refs[(idx, chart.group(2))] = {m.group(1): int(m.group(2)) for m in _POINT.finditer(chart.group(3))}
            else:
                check.no_figures(line, where)
    for idx, slide in enumerate(slides, start=1):
        for shape in _shapes(slide.shapes):
            where = f"slide {idx}"
            if getattr(shape, "has_chart", False) and shape.has_chart:
                for plot in shape.chart.plots:
                    labels = [str(c) for c in plot.categories]
                    for label in labels:
                        check.no_figures(label, f"{where}, chart categories")
                    for series in plot.series:
                        refs = chart_refs.get((idx, series.name), {})
                        for label, value in zip(labels, series.values, strict=False):
                            if value is None:
                                continue
                            check.figures += 1
                            spot = f'{where}, chart series "{series.name}", {label}'
                            record = check.sources.get(refmap.get(refs.get(label, -1), ""))
                            if record is None:
                                check.problem(spot, str(value), "is a chart value with no source in the slide notes")
                            elif not same_value(Decimal(repr(float(value))), record):
                                check.problem(spot, str(value), f"does not match its source ({record['label']}: {record['value']})")
            elif getattr(shape, "has_table", False) and shape.has_table:
                rows = [[cell.text_frame.text for cell in row.cells] for row in shape.table.rows]
                if tuple(rows[0]) == deck_format.SOURCE_COLUMNS:
                    for row in rows[1:]:
                        record = check.sources.get(refmap.get(int(row[0]), "")) if row[0].isdigit() else None
                        if record is None:
                            check.problem(f"{where}, Sources", row[0], "is not a reference used in this deck")
                        elif row != deck_format.source_row(int(row[0]), record):
                            check.problem(f"{where}, Sources", row[0], "describes its source differently from the snapshot")
                    continue
                for r, row in enumerate(shape.table.rows, start=1):
                    for c, cell in enumerate(row.cells, start=1):
                        for p in cell.text_frame.paragraphs:
                            check.check_runs(_pptx_parts(p), refmap, f"{where}, table row {r}, column {c}")
            elif shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    check.check_runs(_pptx_parts(p), refmap, where)


CHECKS = {"docx": check_docx, "xlsx": check_xlsx, "pptx": check_pptx}


def verify_file(name: str, fmt: str, data: bytes, content: dict[str, Any]) -> _FileCheck:
    """Check one file against a snapshot's content. Never raises on a damaged file."""
    facts, derived = content.get("facts", {}), content.get("derived", {})
    check = _FileCheck(name, {**facts, **derived}, facts)
    try:
        CHECKS[fmt](check, data)
    except Exception as exc:  # noqa: BLE001  a file that cannot be read has not been verified
        check.problem("file", "", f"could not be read back: {type(exc).__name__}: {exc}")
    return check


def check_snapshot(db: Session, snapshot: Snapshot) -> list[tuple[str, str, str]]:
    """Problems with the snapshot itself: (where, figure, reason)."""
    from app.publishing.service import content_hash

    content, out = snapshot.content, []
    if content_hash(content) != snapshot.sha256:
        out.append(("snapshot", snapshot.sha256, "is not the hash of the snapshot's content"))
    facts = content.get("facts", {})
    stored = {str(f.id): f for f in db.execute(select(Fact).where(
        Fact.id.in_([uuid.UUID(i) for i in facts]))).scalars()} if facts else {}
    for fid, record in facts.items():
        fact = stored.get(fid)
        if fact is None:
            out.append(("snapshot", fid, "is not a stored fact"))
        elif fact.value != Decimal(record["value"]):
            out.append(("snapshot", fid, f"is frozen as {record['value']} but stored as {fact.value}"))
    for did, record in content.get("derived", {}).items():
        if record["op"] == "sum":
            missing = [i for i in record["inputs"] if i not in facts]
            value = sum((Decimal(facts[i]["value"]) for i in record["inputs"] if i in facts), Decimal(0))
            if missing or value != Decimal(record["value"]):
                out.append(("snapshot", did, "is not the sum of its input facts"))
        elif Decimal(len(record["inputs"])) != Decimal(record["value"]):
            out.append(("snapshot", did, "is not the count of its inputs"))
    return out


def verify_package(db: Session, package: Package) -> VerifyReport:
    report = VerifyReport(package_id=str(package.id))
    snapshot = db.get(Snapshot, package.snapshot_id) if package.snapshot_id else None
    if snapshot is None:
        report.problems.append(Problem("package", "snapshot", "", "has no snapshot to verify against"))
        return report
    report.snapshot_sha256 = snapshot.sha256
    report.problems.extend(Problem("snapshot", w, f, r) for w, f, r in check_snapshot(db, snapshot))
    frozen = {f["name"]: f["sha256"] for f in snapshot.content.get("files", [])}
    if not package.files:
        report.problems.append(Problem("package", "files", "", "has no files"))
    for entry in package.files:
        name, path = entry["name"], Path(entry["path"])
        if not path.exists():
            report.problems.append(Problem(name, "file", "", "is missing from the file store"))
            report.files.append({"name": name, "format": entry["format"], "figures": 0, "problems": 1})
            continue
        data = path.read_bytes()
        before = len(report.problems)
        if hashlib.sha256(data).hexdigest() != frozen.get(name):
            report.problems.append(Problem(name, "file", "", "has changed since the snapshot was frozen"))
        check = verify_file(name, entry["format"], data, snapshot.content)
        report.problems.extend(check.problems)
        report.figures_checked += check.figures
        report.files.append({"name": name, "format": entry["format"], "figures": check.figures,
                             "problems": len(report.problems) - before})
    return report

"""Borrowing base reader: locate the certificate lines, the aging and the inventory listing.
Code verifies each figure on its page, checks that each aging row adds up, and hands verified
rows to the recalculation. Nothing the model typed is used as a number."""
import base64
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.tools import Scope, ToolGateway
from app.calc.borrowing_base import LINE_NAMES
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.documents_service import get_page, read_file
from app.domain.facts_service import store_extracted_cell
from app.domain.monitoring import Cycle
from app.guardrails.numbers import extract_figures, parse_printed_figure
from app.guardrails.quotes import _rows, quote_on_page, same_row
from app.guardrails.units import scale_of

BUCKETS = ("current", "days_31_60", "days_61_90", "over_90")  # aged from invoice date
_FLAGS = (("affiliate", "intercompany"), ("intercompany", "intercompany"), ("related", "intercompany"),
          ("government", "government"), ("foreign", "foreign"), ("export", "foreign"))
LINE_HELP = {
    "ar_total": "gross accounts receivable", "ar_ineligible_excluded": "excluded accounts (affiliate, foreign, government)",
    "ar_ineligible_age": "invoices over the age limit", "ar_ineligible_cross_aging": "cross-aged accounts",
    "ar_ineligible_contra": "contra accounts", "ar_ineligible_concentration": "concentration over the limit",
    "ar_ineligible_total": "total ineligible accounts", "ar_eligible": "eligible accounts",
    "ar_availability": "accounts receivable availability", "inventory_total": "gross inventory",
    "inventory_ineligible": "ineligible inventory", "inventory_eligible": "eligible inventory",
    "inventory_availability_before_sublimit": "inventory availability before the sublimit",
    "inventory_availability": "inventory availability", "reserves": "reserves", "borrowing_base": "borrowing base",
    "commitment": "revolving commitment", "borrowing_limit": "lesser of borrowing base and commitment",
    "outstanding": "revolving loans outstanding", "letters_of_credit": "letters of credit outstanding",
    "availability": "availability (excess or deficit)", "over_advance": "over-advance, if stated separately",
}
assert set(LINE_HELP) == set(LINE_NAMES), "every borrowing base line needs a description for the reader"


class CertLine(BaseModel):
    line: str
    page: int
    printed_label: str
    printed_figure: str


class AgingRow(BaseModel):
    page: int
    customer_printed: str
    figures_printed: list[str]
    note_printed: str


class InventoryLine(BaseModel):
    page: int
    category_printed: str
    amount_printed: str


class CollateralReading(BaseModel):
    certificate_lines: list[CertLine]
    aging_headers: list[str]
    aging_rows: list[AgingRow]
    inventory_rows: list[InventoryLine]
    scale_statement: str
    scale_page: int
    notes: list[str]


SPEC = AgentSpec(name="borrowing_base_reader", version="1",
                 purpose="Locate borrowing base certificate lines, aging rows and inventory rows.",
                 prompt_file="collateral.md", output_model=CollateralReading, tools=(), effort="medium",
                 max_tokens=32000)


@dataclass
class CollateralResult:
    run_id: uuid.UUID | None = None
    ar_rows: list[dict[str, Any]] = field(default_factory=list)
    inventory_rows: list[dict[str, Any]] = field(default_factory=list)
    certificate: dict[str, Decimal] = field(default_factory=dict)
    unverified: list[dict[str, Any]] = field(default_factory=list)
    fact_ids: dict[str, str] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return bool(self.ar_rows or self.inventory_rows) and not self.unverified


def _header_bucket(header: str) -> str | None:
    """Map an age column header to a bucket from its day range; the headers decide, not their order."""
    numbers = [int(n) for n in re.findall(r"\d+", header)]
    if "total" in header.lower():
        return "total"
    if numbers == [0, 30] or (numbers == [30] and "current" in header.lower()) or header.lower().strip() == "current":
        return "current"
    return {(31, 60): "days_31_60", (61, 90): "days_61_90"}.get(tuple(numbers)) or (
        "over_90" if numbers == [90] and re.search(r"over|more than|\+|>", header.lower()) else None)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


# Printed inventory categories -> the names used in terms. Eligibility turns on the category, so
# code decides it from words that are hard to mistake; anything else keeps its own name.
_CATEGORIES = ((r"consign", "consigned"), (r"work[\s-]*in[\s-]*(?:process|progress)|\bwip\b", "work_in_process"),
               (r"raw", "raw_materials"), (r"finished", "finished_goods"), (r"obsolete|slow[\s-]*moving", "obsolete"),
               (r"in[\s-]*transit", "in_transit"), (r"packag", "packaging"), (r"supplies", "supplies"))


# What a certificate line's printed label must say, and must not say, to be that line. The row's
# label is read from the page by code; a line whose label does not fit is held.
_LINE_WORDS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    # line: (all of, any of, none of)
    "ar_total": (("receivable",), ("gross", "total"), ("ineligible", "eligible", "availability")),
    "ar_ineligible_excluded": ((), ("affiliate", "foreign", "government", "excluded", "intercompany"), ()),
    "ar_ineligible_age": ((), ("days", "aged", "past"), ("cross",)),
    "ar_ineligible_cross_aging": (("cross",), (), ()),
    "ar_ineligible_contra": (("contra",), (), ()),
    "ar_ineligible_concentration": (("concentration",), (), ()),
    "ar_ineligible_total": (("ineligible",), ("total",), ("inventory",)),
    "ar_eligible": (("eligible",), ("accounts", "receivable", "receivables"), ("ineligible", "availability", "inventory")),
    "ar_availability": (("availability",), ("accounts", "receivable", "receivables"), ("inventory",)),
    "inventory_total": (("inventory",), ("gross", "total"), ("ineligible", "eligible", "availability")),
    "inventory_ineligible": (("ineligible", "inventory"), (), ()),
    "inventory_eligible": (("eligible", "inventory"), (), ("ineligible", "availability")),
    "inventory_availability_before_sublimit": (("inventory", "availability", "sublimit"), (), ()),
    "inventory_availability": (("inventory", "availability"), (), ("sublimit",)),
    "reserves": ((), ("reserve", "reserves"), ()),
    "borrowing_base": (("borrowing", "base"), (), ("lesser",)),
    "commitment": (("commitment",), (), ("lesser",)),
    "borrowing_limit": (("lesser",), (), ()),
    "outstanding": ((), ("loans", "advances", "outstanding", "borrowings"), ("letters", "letter")),
    "letters_of_credit": (("credit",), ("letters", "letter"), ()),
    "availability": (("availability",), (), ("inventory", "receivable", "receivables", "accounts", "sublimit")),
    "over_advance": (("advance",), ("over", "overadvance"), ("availability",)),
}
assert set(_LINE_WORDS) == set(LINE_NAMES), "every borrowing base line needs its label rule"


def _line_doubt(line: str, row_label: str) -> str | None:
    words = set(re.findall(r"[a-z]+", row_label.lower()))
    every, some, none = _LINE_WORDS[line]
    if all(w in words for w in every) and (not some or words & set(some)) and not words & set(none):
        return None
    return f"the row labelled {row_label!r} does not read as the certificate's {LINE_HELP[line]} line"


def _row_note(words, anchor) -> str:
    """Text printed on a row after its first figure that is not itself a figure: the note column."""
    row = sorted((w for w in words if same_row((float(w[0]), float(w[1]), float(w[2]), float(w[3])), anchor)),
                 key=lambda w: float(w[0]))
    first = next((i for i, w in enumerate(row) if parse_printed_figure(str(w[4])) is not None), None)
    if first is None:
        return ""
    return " ".join(str(w[4]) for w in row[first:] if parse_printed_figure(str(w[4])) is None
                    and any(ch.isalpha() for ch in str(w[4])) or
                    (parse_printed_figure(str(w[4])) is not None and float(w[0]) > anchor[2] + 1)).strip()


def _printed_total(words) -> Decimal | None:
    """The last figure on the aging's own "Total" row, if the page prints exactly one."""
    totals = []
    for row in _rows(words):
        if str(row[0][4]).strip().lower().rstrip(":") == "total" or " ".join(
                str(w[4]) for w in row[:2]).lower().startswith(("total accounts", "grand total")):
            figures = [parse_printed_figure(str(w[4])) for w in row]
            figures = [f for f in figures if f is not None]
            if figures:
                totals.append(figures[-1].value)
    return totals[0] if len(totals) == 1 else None


def inventory_category(printed: str) -> str:
    lowered = printed.lower()
    return next((name for pattern, name in _CATEGORIES if re.search(pattern, lowered)), _slug(printed))


def read_collateral(db: Session, *, borrower: Borrower, document: Document, period_end: date,
                    cycle: Cycle | None, llm: LLMClient) -> CollateralResult:
    result = CollateralResult()
    lines = "\n".join(f"- {name} | {LINE_HELP[name]}" for name in LINE_NAMES)
    content = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(read_file(document)).decode()}},
        {"type": "text", "text": f"Borrowing base certificate as of {period_end:%B %-d, %Y}. "
                                 f"Certificate line names (name | meaning):\n{lines}"}]
    scope = Scope(borrower_id=borrower.id, period_end=period_end, cycle_id=cycle.id if cycle else None,
                  document_ids=(document.id,))
    outcome = run_agent(db, SPEC, task="read_borrowing_base", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"collateral/{borrower.code}/{period_end}")
    result.run_id = outcome.run.id
    if not outcome.ok:
        result.unverified.append({"what": "document", "reason": outcome.reason or "no_answer"})
        return result
    out: CollateralReading = outcome.output  # type: ignore[assignment]

    page = get_page(db, document.id, out.scale_page) if out.scale_statement.strip() else None
    if out.scale_statement.strip() and (page is None or not quote_on_page(page.text, out.scale_statement)):
        result.unverified.append({"what": "units", "reason": "scale_quote"})
        return result
    scale = scale_of(out.scale_statement) if out.scale_statement.strip() else 1
    if scale is None:  # a units phrase code cannot read as thousands or dollars: a person decides
        result.unverified.append({"what": "units", "reason": "scale_not_understood"})
        return result

    found: dict[str, Any] = {}  # what code read on the page for each stored cell: row label and place

    def cell(key: str, page_number: int, figure: str, label: str, header: str | None,
             fits: Any = None) -> Decimal | None:
        """`fits` judges the row's label as code read it from the page; the label the reader
        reported only finds the row."""
        def doubt_for(check, _value):
            return fits(check.row_label) if fits is not None else None

        fact, check = store_extracted_cell(
            db, borrower_id=borrower.id, key=key, period_end=period_end, months=0, document=document,
            page_number=page_number, printed_figure=figure, printed_label=label, column_header=header,
            scale=scale, presentation_sign=1, agent_run_id=outcome.run.id, actor=("agent", "borrowing_base_reader"),
            doubt_for=doubt_for)
        if fact is None or not check.ok:
            result.unverified.append({"what": key, "label": label, "printed": figure, "reason": check.status,
                                      "detail": check.detail})
            return None
        result.fact_ids[key] = str(fact.id)
        found[key] = check
        return fact.value

    for line in out.certificate_lines:
        if line.line not in LINE_NAMES or line.line in result.certificate:
            continue
        value = cell(f"bbc.{line.line}", line.page, line.printed_figure, line.printed_label, None,
                     fits=lambda row_label, name=line.line: _line_doubt(name, row_label))
        if value is not None:
            result.certificate[line.line] = value

    buckets = [_header_bucket(h) for h in out.aging_headers]
    if sorted(b or "" for b in buckets) != sorted([*BUCKETS, "total"]):
        result.unverified.append({"what": "aging headers", "reason": "headers_not_recognised",
                                  "detail": f"cannot map {out.aging_headers} to age buckets"})
        return result
    aging_totals: list[tuple[int, Decimal]] = []
    for n, row in enumerate(out.aging_rows, start=1):
        if len(row.figures_printed) != len(buckets):
            result.unverified.append({"what": f"aging row {n}", "label": row.customer_printed, "reason": "wrong_width"})
            continue
        values = {}
        for bucket, header, figure in zip(buckets, out.aging_headers, row.figures_printed, strict=True):
            values[bucket] = cell(f"bbc.ar.{n:03d}.{bucket}", row.page, figure, row.customer_printed, header)
        if any(v is None for v in values.values()):
            continue
        if sum(values[b] for b in BUCKETS) != values["total"]:
            result.unverified.append({"what": f"aging row {n}", "label": row.customer_printed,
                                      "reason": "row_does_not_add_up"})
            continue
        place = found[f"bbc.ar.{n:03d}.total"]
        entry: dict[str, Any] = {"customer": place.row_label or row.customer_printed, "days_1_30": "0",
                                 **{b: str(values[b]) for b in BUCKETS}}
        page = get_page(db, document.id, row.page)
        # whatever else is printed on the customer's row is its note, reported or not: an
        # affiliate or a contra balance changes what is eligible
        note = _row_note(page.words, place.bbox) if page is not None else row.note_printed.strip()
        aging_totals.append((row.page, values["total"]))
        if note:
            lowered = note.lower()
            flag = next((flag for word, flag in _FLAGS if word in lowered), None)
            if flag:
                entry["flags"] = [flag]
            elif "contra" in lowered:
                amounts = extract_figures(note)
                if len(amounts) != 1:
                    result.unverified.append({"what": f"aging row {n} note", "label": row.customer_printed,
                                              "reason": "contra_amount_unclear"})
                    continue
                entry["contra"] = str(amounts[0].value * scale)
            else:
                result.unverified.append({"what": f"aging row {n} note", "label": row.customer_printed,
                                          "reason": "note_not_understood", "detail": note})
                continue
        result.ar_rows.append(entry)

    # a customer left out of the reading makes the rest more eligible: the rows must add up to the
    # total the aging itself prints
    for page_number in sorted({p for p, _ in aging_totals}):
        page = get_page(db, document.id, page_number)
        printed = _printed_total(page.words) if page is not None else None
        read = sum((v for p, v in aging_totals if p == page_number), Decimal(0))
        if printed is not None and printed * scale != read and len({p for p, _ in aging_totals}) == 1:
            result.unverified.append({"what": "aging", "reason": "rows_do_not_add_to_printed_total",
                                      "detail": "the customer rows read do not add up to the total the aging prints"})

    for n, item in enumerate(out.inventory_rows, start=1):
        value = cell(f"bbc.inventory.{n:03d}", item.page, item.amount_printed, item.category_printed, None)
        if value is not None:
            # eligibility turns on the category, so it is taken from the row as printed
            printed_category = found[f"bbc.inventory.{n:03d}"].row_label or item.category_printed
            result.inventory_rows.append({"category": inventory_category(printed_category), "amount": str(value),
                                          "printed_category": printed_category})
    db.flush()
    return result

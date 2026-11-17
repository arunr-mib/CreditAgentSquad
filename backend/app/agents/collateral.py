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
from app.agents.spreading import _THOUSANDS
from app.agents.tools import Scope, ToolGateway
from app.calc.borrowing_base import LINE_NAMES
from app.domain.credit import Borrower
from app.domain.documents import Document
from app.domain.documents_service import get_page, read_file
from app.domain.facts_service import store_extracted_cell
from app.domain.monitoring import Cycle
from app.guardrails.numbers import extract_figures
from app.guardrails.quotes import locate, quote_on_page, same_row

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
    "availability": "availability (excess or deficit)",
}


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
    scale = 1000 if _THOUSANDS.search(out.scale_statement) or "thousand" in out.scale_statement.lower() else 1

    def cell(key: str, page_number: int, figure: str, label: str, header: str | None) -> Decimal | None:
        fact, check = store_extracted_cell(
            db, borrower_id=borrower.id, key=key, period_end=period_end, months=0, document=document,
            page_number=page_number, printed_figure=figure, printed_label=label, column_header=header,
            scale=scale, presentation_sign=1, agent_run_id=outcome.run.id, actor=("agent", "borrowing_base_reader"))
        if fact is None or not check.ok:
            result.unverified.append({"what": key, "label": label, "printed": figure, "reason": check.status,
                                      "detail": check.detail})
            return None
        result.fact_ids[key] = str(fact.id)
        return fact.value

    for line in out.certificate_lines:
        if line.line not in LINE_NAMES or line.line in result.certificate:
            continue
        value = cell(f"bbc.{line.line}", line.page, line.printed_figure, line.printed_label, None)
        if value is not None:
            result.certificate[line.line] = value

    buckets = [_header_bucket(h) for h in out.aging_headers]
    if sorted(b or "" for b in buckets) != sorted([*BUCKETS, "total"]):
        result.unverified.append({"what": "aging headers", "reason": "headers_not_recognised",
                                  "detail": f"cannot map {out.aging_headers} to age buckets"})
        return result
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
        entry: dict[str, Any] = {"customer": row.customer_printed, "days_1_30": "0",
                                 **{b: str(values[b]) for b in BUCKETS}}
        note = row.note_printed.strip()
        if note:
            page = get_page(db, document.id, row.page)
            on_row = page is not None and any(
                same_row(hit.bbox, lab.bbox) for hit in locate(page.words, note)
                for lab in locate(page.words, row.customer_printed))
            if not on_row:
                result.unverified.append({"what": f"aging row {n} note", "label": row.customer_printed,
                                          "reason": "note_not_on_row"})
                continue
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

    for n, item in enumerate(out.inventory_rows, start=1):
        value = cell(f"bbc.inventory.{n:03d}", item.page, item.amount_printed, item.category_printed, None)
        if value is not None:
            result.inventory_rows.append({"category": _slug(item.category_printed), "amount": str(value)})
    db.flush()
    return result

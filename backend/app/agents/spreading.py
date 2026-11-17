"""Spreading Agent: locate the template's figures in a statement; code verifies and checks them.

The model is asked only where each figure is printed. Code reads the number from the page,
applies scale and sign, stores a fact with its citation, runs the footing and tie checks, and
raises a work item for anything it could not clear.
"""
import base64
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.tools import Scope, ToolGateway
from app.calc import template
from app.core import ledger
from app.domain.credit import Borrower
from app.domain.documents import Document, DocumentPage
from app.domain.documents_service import read_file
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact, store_extracted_cell
from app.domain.monitoring import Cycle, WorkItem
from app.domain.work_items import raise_item
from app.guardrails.narrative import check_narrative
from app.guardrails.quotes import quote_on_page

ENGINE_VERSION = f"template-{template.TEMPLATE_ID}"
PART_SUFFIX = "~part"


class Cell(BaseModel):
    key: str
    page: int
    printed_figure: str
    printed_label: str
    column_header: str


class SpreadExtraction(BaseModel):
    scale_statement: str
    scale_page: int
    cells: list[Cell]
    comparative_cells: list[Cell]
    absent_keys: list[str]
    notes: list[str]


SPEC = AgentSpec(
    name="spreading", version="1",
    purpose="Locate template figures in financial statements; code verifies each on its page.",
    prompt_file="spreading.md", output_model=SpreadExtraction, tools=(), effort="high", max_tokens=32000)

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], start=1)}
_DATE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b")
_THOUSANDS = re.compile(r"\bin\s+thousands\b|\(000s?\)|\$\s?000s?\b|\bthousands of (?:u\.s\. )?dollars\b", re.I)


def dates_in(text: str) -> list[date]:
    found = []
    for name, day, year in _DATE.findall(text):
        month = next((n for full, n in _MONTHS.items() if full.startswith(name.lower()[:3])), None)
        if month is None:
            continue
        try:
            found.append(date(int(year), month, int(day)))
        except ValueError:
            continue
    return found


def _allowed_key(key: str) -> bool:
    if key.startswith(template.STATED_PREFIX):
        line = template.LINE_BY_KEY.get(key[len(template.STATED_PREFIX):])
        return line is not None and line.computed
    line = template.LINE_BY_KEY.get(key)
    return line is not None and not line.computed


def _sign(key: str) -> int:
    if key.startswith(template.STATED_PREFIX):
        return 1
    return template.LINE_BY_KEY[key].presentation_sign


def _months_for(key: str, months: int) -> int:
    base = key[len(template.STATED_PREFIX):] if key.startswith(template.STATED_PREFIX) else key
    return months if template.LINE_BY_KEY[base].flow else 0


def template_listing() -> str:
    rows = []
    for line in template.LINES:
        kind = "total" if line.computed else "line"
        rows.append(f"- {line.key} | {line.label} | {kind}")
    return "\n".join(rows)


@dataclass
class SpreadResult:
    status: str  # spread | needs_person | failed
    run_id: uuid.UUID | None = None
    facts: dict[str, Fact] = field(default_factory=dict)  # usable line facts by key
    unverified: list[dict[str, Any]] = field(default_factory=list)
    failed_checks: list[dict[str, Any]] = field(default_factory=list)
    work_items: list[WorkItem] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)  # guardrail notes


def _item(db, result, borrower, cycle, document, **kw) -> None:
    result.work_items.append(raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id if cycle else None, stage="spreading",
        actor=("agent", "spreading"), agent_run_id=result.run_id,
        dedupe_key=f"{kw['item_type']}:{document.id}", **kw))
    result.status = "needs_person"


def _derive_scale(db: Session, document: Document, out: SpreadExtraction, result: SpreadResult) -> int | None:
    """Scale is decided by code from the printed phrase, and cross-checked against every page."""
    pages = list(db.execute(select(DocumentPage).where(DocumentPage.document_id == document.id)
                            .order_by(DocumentPage.page_number)).scalars())
    printed_thousands = any(_THOUSANDS.search(p.text) for p in pages)
    phrase = out.scale_statement.strip()
    if phrase:
        page = next((p for p in pages if p.page_number == out.scale_page), None)
        if page is None or not quote_on_page(page.text, phrase):
            result.notes.append({"layer": "spreading", "check": "scale_quote", "action": "person",
                                 "detail": "the units phrase reported by the agent is not on the cited page"})
            return None
        scale = 1000 if _THOUSANDS.search(phrase) or "thousand" in phrase.lower() else 1
    else:
        scale = 1
    if printed_thousands and scale == 1:
        result.notes.append({"layer": "spreading", "check": "scale_conflict", "action": "person",
                             "detail": "the document prints an 'in thousands' phrase but none was reported"})
        return None
    return scale


def _store_cells(db, *, cells, borrower, document, period_end, months, scale, run_id, result, suffix=""):
    """Verify and store each cell. Returns usable stored values by key (several cells per key are added)."""
    allowed = []
    for cell in cells:
        if _allowed_key(cell.key):
            allowed.append(cell)
        else:
            result.notes.append({"layer": "spreading", "check": "unknown_key", "action": "dropped",
                                 "detail": f"{cell.key} is not a line the agent may fill"})
    rows_per_key: dict[str, int] = {}
    for cell in allowed:
        rows_per_key[cell.key] = rows_per_key.get(cell.key, 0) + 1

    by_key: dict[str, list[tuple[Fact, bool]]] = {}
    for cell in allowed:
        # one printed row is the line itself; several rows are stored as parts and added by code
        part = PART_SUFFIX if rows_per_key[cell.key] > 1 else ""
        fact, check = store_extracted_cell(
            db, borrower_id=borrower.id, key=cell.key + suffix + part, period_end=period_end,
            months=_months_for(cell.key, months), document=document, page_number=cell.page,
            printed_figure=cell.printed_figure, printed_label=cell.printed_label,
            column_header=cell.column_header, scale=scale, presentation_sign=_sign(cell.key), agent_run_id=run_id)
        if fact is None or not check.ok:
            result.unverified.append({
                "key": cell.key + suffix, "page": cell.page, "printed_figure": cell.printed_figure,
                "printed_label": cell.printed_label, "reason": check.status, "detail": check.detail,
                "fact_id": str(fact.id) if fact else None})
            by_key.setdefault(cell.key, []).append((fact, False))
        else:
            by_key.setdefault(cell.key, []).append((fact, True))
    values: dict[str, Decimal] = {}
    for key, parts in by_key.items():
        if not all(ok for _, ok in parts):
            continue  # a line with any unverified part is not usable until a person clears it
        facts = [f for f, _ in parts]
        values[key] = sum((f.value for f in facts), Decimal(0))
        result.facts[key + suffix] = facts[0] if len(facts) == 1 else _sum_fact(db, borrower, key + suffix, facts)
    return values


def _sum_fact(db: Session, borrower: Borrower, key: str, parts: list[Fact]) -> Fact:
    """Several printed rows for one template line: code adds them and stores the sum as a
    calculated fact that names its parts."""
    first = parts[0]
    total = sum((p.value for p in parts), Decimal(0))
    calc = CalcRun(
        borrower_id=borrower.id, formula_key="sum_of_printed_rows", formula_version="1",
        period_end=first.period_end, engine_version=ENGINE_VERSION,
        inputs=[{"name": p.label_text, "key": p.key, "fact_id": str(p.id), "value": str(p.value)} for p in parts],
        outputs={key: str(total)}, created_by_type="agent", created_by_id="spreading")
    db.add(calc)
    db.flush()
    return add_fact(db, borrower_id=borrower.id, key=key, period_end=first.period_end, months=first.months,
                    value=total, kind="calculated", calc_run_id=calc.id, actor=("agent", "spreading"))


def spread_document(
    db: Session, *, borrower: Borrower, document: Document, period_end: date, months: int,
    cycle: Cycle | None, llm: LLMClient, prior_fye_cash: Decimal | None = None,
) -> SpreadResult:
    result = SpreadResult(status="spread")
    if document.status == "image_only":
        _item(db, result, borrower, cycle, document, item_type="spread.image_only", severity="medium",
              title=f"{document.title} has no readable text",
              question="This document is a scanned image and cannot be read. Request a text PDF, or key the figures by hand?",
              allowed_decisions=["request_new_document", "key_by_hand"], required_permission="confirm_spread",
              evidence={"document_id": str(document.id)})
        return result

    content = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(read_file(document)).decode()}},
        {"type": "text", "text": (
            f"Spread the statements for the period ended {period_end:%B %-d, %Y} "
            f"({months} months, fiscal year to date). Template lines (key | label | kind):\n"
            f"{template_listing()}")},
    ]
    scope = Scope(borrower_id=borrower.id, period_end=period_end, months=months,
                  cycle_id=cycle.id if cycle else None, document_ids=(document.id,))
    outcome = run_agent(db, SPEC, task="spread_statements", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"spreading/{borrower.code}/{period_end}/{document.sha256[:12]}")
    result.run_id = outcome.run.id
    if not outcome.ok:
        result.status = "failed"
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="medium",
              title=f"{document.title} could not be spread automatically",
              question="The Spreading Agent did not return a usable result for this document. Spread it by hand, or retry?",
              allowed_decisions=["retry", "key_by_hand"], required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "reason": outcome.reason})
        result.status = "failed"
        return result
    out: SpreadExtraction = outcome.output  # type: ignore[assignment]

    # notes are prose from the model: they may be shown only if they contain no typed figure
    for note in out.notes:
        problems = check_narrative(note, {})
        if problems:
            result.notes.append({"layer": "narrative", "check": "figure_untraceable", "action": "dropped",
                                 "detail": "a note from the agent contained a typed figure and was removed"})
        else:
            result.notes.append({"layer": "agent", "check": "note", "action": "shown", "detail": note})

    scale = _derive_scale(db, document, out, result)
    headers = {c.column_header for c in out.cells}
    period_ok = bool(out.cells) and all(period_end in dates_in(h) for h in headers)
    if scale is None or not period_ok:
        reason = "units could not be confirmed" if scale is None else "the column read is not the requested period"
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="high",
              title=f"{document.title}: {reason}",
              question=("The units of this statement could not be confirmed from the page. Is it in thousands or in whole dollars?"
                        if scale is None else
                        f"No column dated {period_end:%B %-d, %Y} was found in this document. Is this the right document for the period?"),
              allowed_decisions=["in_thousands", "in_dollars", "request_new_document"] if scale is None
              else ["wrong_document", "request_new_document"],
              required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "column_headers": sorted(headers)},
              guardrail_notes=result.notes)
        outcome.run.guardrail_notes = result.notes
        return result

    values = _store_cells(db, cells=out.cells, borrower=borrower, document=document, period_end=period_end,
                          months=months, scale=scale, run_id=outcome.run.id, result=result)
    absent = [k for k in out.absent_keys if k in template.LINE_BY_KEY and k not in values]
    report = template.check_statement(values, scale=scale, prior_fye_cash=prior_fye_cash, absent=absent)
    result.failed_checks = [e.to_dict() for e in report.errors]

    if result.unverified:
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="medium",
              title=f"{document.title}: {len(result.unverified)} figure(s) could not be verified on the page",
              question="These figures could not be found on the cited page exactly as reported. Confirm or correct each one?",
              allowed_decisions=["values_confirmed", "values_corrected", "request_new_document"],
              required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "cells": result.unverified})
    if report.errors:
        _item(db, result, borrower, cycle, document, item_type="spread.does_not_foot", severity="high",
              title=f"{document.title}: the statements do not foot or tie",
              question="One or more totals do not agree with their lines. Which figure is wrong?",
              allowed_decisions=["values_corrected", "accept_as_reported", "request_new_document"],
              required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "checks": result.failed_checks})

    # comparative column: verified and compared with what was confirmed a year ago
    if out.comparative_cells:
        prior_end = date(period_end.year - 1, period_end.month, period_end.day)
        comparative = _store_cells(db, cells=out.comparative_cells, borrower=borrower, document=document,
                                   period_end=prior_end, months=months, scale=scale, run_id=outcome.run.id,
                                   result=result, suffix="@comparative")
        confirmed = {}
        for key in comparative:
            prior = current_fact(db, borrower.id, key, prior_end, _months_for(key, months))
            if prior is not None:
                confirmed[key] = prior.value
        restated = [c for c in template.check_comparative(comparative, confirmed, scale=scale) if c.status == "fail"]
        if restated:
            _item(db, result, borrower, cycle, document, item_type="spread.restatement", severity="medium",
                  blocks_stage=False,
                  title=f"{document.title}: prior-period figures differ from the confirmed spread",
                  question="The comparative column differs from what was confirmed last year. Has the borrower restated, and should the prior spread be updated?",
                  allowed_decisions=["restated_update_prior", "keep_prior", "ask_borrower"],
                  required_permission="confirm_spread",
                  evidence={"document_id": str(document.id), "lines": [
                      {"key": c.key, "comparative": str(c.actual), "confirmed": str(c.expected)} for c in restated]})

    current_unverified = [u for u in result.unverified if "@comparative" not in u["key"]]
    if not report.errors and not current_unverified:
        _store_computed(db, borrower, period_end, months, report, result)
    outcome.run.guardrail_notes = result.notes
    ledger.record(db, actor_type="agent", actor_id="spreading@1", action="spread.finished",
                  entity_type="document", entity_id=document.id,
                  payload={"status": result.status, "lines": len(values), "unverified": len(result.unverified),
                           "failed_checks": len(result.failed_checks), "scale": scale})
    db.flush()
    return result


def _store_computed(db, borrower, period_end, months, report, result) -> None:
    """Totals are produced by code, stored as calculated facts that name their inputs."""
    calc = CalcRun(
        borrower_id=borrower.id, formula_key="template_totals", formula_version=template.TEMPLATE_ID,
        period_end=period_end, engine_version=ENGINE_VERSION,
        inputs=[{"key": k, "fact_id": str(f.id), "value": str(f.value)} for k, f in sorted(result.facts.items())
                if "@" not in k and not k.startswith(template.STATED_PREFIX)],
        outputs={k: str(v) for k, v in sorted(report.computed.items())},
        created_by_type="system", created_by_id="spreading")
    db.add(calc)
    db.flush()
    for key, value in report.computed.items():
        result.facts[key] = add_fact(
            db, borrower_id=borrower.id, key=key, period_end=period_end, months=_months_for(key, months),
            value=value, kind="calculated", calc_run_id=calc.id, actor=("system", "spreading"))

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
from app.domain.documents_service import get_page, read_file
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact, label_confirmed, store_extracted_cell
from app.domain.monitoring import Cycle, WorkItem
from app.domain.work_items import raise_item
from app.guardrails.labels import mapping_doubt, reads_as
from app.guardrails.narrative import check_narrative
from app.guardrails.quotes import dates_in, quote_on_page
from app.guardrails.units import scale_of, units_in

ENGINE_VERSION = f"template-{template.TEMPLATE_ID}"  # the engine; the borrower's template id goes in formula_version
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
    name="spreading", version="3",
    purpose="Locate template figures in financial statements; code verifies each on its page.",
    prompt_file="spreading.md", output_model=SpreadExtraction, tools=(), effort="high", max_tokens=32000)

# the final printed total of each statement; a spread is not usable until each one foots
REQUIRED_TOTALS: dict[str, tuple[str, ...]] = {
    "ci-1": ("is.net_income", "bs.total_assets", "bs.total_liabilities_and_equity", "cf.net_change_in_cash"),
    "vc-1": ("is.vc_net_loss", "bs.vc_total_assets", "bs.vc_total_liabilities_and_equity",
             "cf.vc_net_change_in_cash"),
}


def _mentions(text: str, period_end: date) -> bool:
    return period_end in dates_in(text) or (
        f"{period_end:%B} {period_end.day}" in text and str(period_end.year) in text)


_ENTITY_SUFFIX = re.compile(r"\b(?:inc|incorporated|llc|l\.l\.c|corp|corporation|co|company|ltd|limited|lp|l\.p|plc)\b\.?", re.I)


def _names(text: str, name: str) -> bool:
    """True when the page prints the borrower's name (legal suffix and punctuation aside)."""
    def squash(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", _ENTITY_SUFFIX.sub(" ", value.lower())))
    core = squash(name)
    return bool(core) and core in squash(text)


def _known_labels(template_id: str = template.TEMPLATE_ID) -> dict[str, tuple[str, ...]]:
    """Every name each line of the template is known by, across all statements; a printed total
    is known under its `stated.` key. A label is judged against all of them, so a row from
    another statement is recognised for what it is."""
    out = {}
    for line in template.template_lines(template_id):
        out[(template.STATED_PREFIX + line.key) if line.computed else line.key] = template.known_labels(line.key)
    return out


_LABELS_BY_TEMPLATE = {tid: _known_labels(tid) for tid in template.TEMPLATES}


def _mapping_doubt(key: str, row_label: str, confirmed: bool = False,
                   template_id: str = template.TEMPLATE_ID) -> str | None:
    """A reason to hold a cell: the row's label, as code read it from the page, is not a known
    name for the line it was filed under, and no person has confirmed it for this borrower."""
    labels = _LABELS_BY_TEMPLATE[template_id]
    doubt = mapping_doubt(row_label, key, labels, confirmed=confirmed)
    if doubt:  # say it in the template's own line names, which is what a person sees on screen
        for name in sorted(labels, key=len, reverse=True):
            base = name.removeprefix(template.STATED_PREFIX)
            printed = f"the printed total '{template.ALL_LINE_BY_KEY[base].label}'" if name != base \
                else f"'{template.ALL_LINE_BY_KEY[base].label}'"
            doubt = re.sub(rf"(?<![\w.]){re.escape(name)}(?![\w.])", printed, doubt)
    return doubt


def _fillable(key: str, lines: dict[str, template.TemplateLine]) -> bool:
    if key.startswith(template.STATED_PREFIX):
        line = lines.get(key[len(template.STATED_PREFIX):])
        return line is not None and line.computed
    line = lines.get(key)
    return line is not None and not line.computed


def _allowed_key(key: str, template_id: str = template.TEMPLATE_ID) -> bool:
    return _fillable(key, {line.key: line for line in template.template_lines(template_id)})


def _out_of_template(key: str, template_id: str) -> bool:
    """A line of some other template: a real line the agent may fill, but not for this borrower."""
    return not _allowed_key(key, template_id) and _fillable(key, template.ALL_LINE_BY_KEY)


def _sign(key: str) -> int:
    if key.startswith(template.STATED_PREFIX):
        return 1
    return template.ALL_LINE_BY_KEY[key].presentation_sign


_COMPARATIVE = "@comparative"


def line_the_label_names(db: Session, cell: dict[str, Any]) -> dict[str, Any] | None:
    """For a held figure whose row label, as code read it from the page, names another line of
    the template: that line, and the value the same printed figure has when it is filed there
    (lines differ in the sign they are stored with, so the stored value cannot simply be moved).

    Read-only: nothing is stored or changed. None when the label names no other line, when
    nothing was stored for the figure, or when the stored fact is one of several rows of its line.
    """
    key, fact_id, label = cell.get("key"), cell.get("fact_id"), cell.get("row_label")
    if not (isinstance(key, str) and isinstance(fact_id, str) and isinstance(label, str)):
        return None
    suffix = _COMPARATIVE if key.endswith(_COMPARATIVE) else ""
    assigned = key.removesuffix(_COMPARATIVE)
    try:
        fact = db.get(Fact, uuid.UUID(fact_id))
    except ValueError:
        return None
    if fact is None or fact.key != key:
        return None
    owner = db.get(Borrower, fact.borrower_id)
    labels = _LABELS_BY_TEMPLATE[owner.template_id if owner is not None else template.TEMPLATE_ID]
    if assigned not in labels:
        return None
    other = reads_as(label, assigned, labels)
    if other is None:
        return None
    return {"key": other + suffix, "value": fact.value * _sign(assigned) * _sign(other)}


def _months_for(key: str, months: int) -> int:
    base = key[len(template.STATED_PREFIX):] if key.startswith(template.STATED_PREFIX) else key
    return months if template.ALL_LINE_BY_KEY[base].flow else 0


def template_listing(template_id: str = template.TEMPLATE_ID) -> str:
    rows = []
    for line in template.template_lines(template_id):
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
    context: dict[str, Any] = field(default_factory=dict)  # what a later repair needs: units, absent lines
    out_of_template: list[str] = field(default_factory=list)  # lines read that are not the borrower's template's


def _item(db, result, borrower, cycle, document, **kw) -> None:
    kw["evidence"] = {**kw.get("evidence", {}), "spread": result.context}
    subject = document.id if document is not None else f"{borrower.id}:{result.context.get('period_end')}"
    kind = kw.pop("dedupe_kind", kw["item_type"])
    result.work_items.append(raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id if cycle else None, stage="spreading",
        actor=("agent", "spreading"), agent_run_id=result.run_id,
        dedupe_key=f"{kind}:{subject}", **kw))
    result.status = "needs_person"


def _derive_scale(db: Session, document: Document, out: SpreadExtraction, result: SpreadResult) -> int | None:
    """Units are decided by code: from the printed phrase the agent points to, read by code, and
    cross-checked against every page. A phrase that is not understood, or millions, goes to a person."""
    pages = list(db.execute(select(DocumentPage).where(DocumentPage.document_id == document.id)
                            .order_by(DocumentPage.page_number)).scalars())
    printed = set().union(*(units_in(p.text) for p in pages)) if pages else set()

    def refuse(check: str, detail: str) -> None:
        result.notes.append({"layer": "spreading", "check": check, "action": "person", "detail": detail})

    phrase = out.scale_statement.strip()
    if phrase:
        page = next((p for p in pages if p.page_number == out.scale_page), None)
        if page is None or not quote_on_page(page.text, phrase):
            refuse("scale_quote", "the units phrase reported by the agent is not on the cited page")
            return None
        scale = scale_of(phrase)
        if scale is None:
            refuse("scale_not_understood", "the units phrase on the page is not one code can read as thousands or dollars")
            return None
    else:
        scale = 1
    if "millions" in printed:
        refuse("scale_millions", "the document prints a 'millions' phrase; statements in millions are not taken")
        return None
    if "thousands" in printed and scale == 1:
        refuse("scale_conflict", "the document prints an 'in thousands' phrase but none was reported")
        return None
    return scale


def _store_cells(db, *, cells, borrower, document, period_end, months, scale, run_id, result, suffix=""):
    """Verify and store each cell. Returns usable stored values by key (several cells per key are added)."""
    tid = borrower.template_id
    allowed = []
    for cell in cells:
        if _allowed_key(cell.key, tid):
            allowed.append(cell)
        elif _out_of_template(cell.key, tid):
            # a real line, but not one of this borrower's template: refused, and a person is asked
            if cell.key not in result.out_of_template:
                result.out_of_template.append(cell.key)
            result.notes.append({"layer": "spreading", "check": "not_in_template", "action": "refused",
                                 "detail": f"{cell.key} is not a line of the {tid} template"})
        else:
            result.notes.append({"layer": "spreading", "check": "unknown_key", "action": "dropped",
                                 "detail": f"{cell.key} is not a line the agent may fill"})
    rows_per_key: dict[str, int] = {}
    for cell in allowed:
        rows_per_key[cell.key] = rows_per_key.get(cell.key, 0) + 1

    # pages of the document that name the borrower: a figure cited from a page that does not
    # may belong to another entity printed in the same file
    named = {p.page_number: _names(p.text, borrower.name) for p in db.execute(
        select(DocumentPage).where(DocumentPage.document_id == document.id)).scalars()}
    used: dict[tuple, str] = {}  # a printed figure can be reported for one line only
    by_key: dict[str, list[tuple[Fact, bool]]] = {}
    for cell in allowed:
        # one printed row is the line itself; several rows are stored as parts and added by code
        part = PART_SUFFIX if rows_per_key[cell.key] > 1 else ""

        def doubt_for(check, value: Decimal, key: str = cell.key, page: int = cell.page) -> str | None:
            place = (page, tuple(round(v) for v in check.bbox)) if check.bbox else None
            if place is not None and place in used:
                return f"the same printed figure was already reported for {used[place]}"
            if place is not None:
                used[place] = key
            if not named.get(page, False):
                return f"page {page} does not name {borrower.name}; it may belong to another entity"
            if value < 0 and key in template.NEVER_NEGATIVE:
                return f"{key} is negative as printed, where only a positive amount is expected"
            names = [key, key + PART_SUFFIX, key + suffix, key + suffix + PART_SUFFIX]
            return _mapping_doubt(key, check.row_label, label_confirmed(db, borrower.id, names, check.row_label), tid)

        fact, check = store_extracted_cell(
            db, borrower_id=borrower.id, key=cell.key + suffix + part, period_end=period_end,
            months=_months_for(cell.key, months), document=document, page_number=cell.page,
            printed_figure=cell.printed_figure, printed_label=cell.printed_label,
            column_header=cell.column_header, scale=scale, presentation_sign=_sign(cell.key), agent_run_id=run_id,
            doubt_for=doubt_for, column_period=period_end, column_months=_months_for(cell.key, months))
        if fact is None or not check.ok:
            result.unverified.append({
                "key": cell.key + suffix, "page": cell.page, "printed_figure": cell.printed_figure,
                "printed_label": cell.printed_label, "row_label": check.row_label, "reason": check.status,
                "detail": check.detail,
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
    scale_override: int | None = None,
) -> SpreadResult:
    """`scale_override` is a person's answer to a units question; it replaces the units check."""
    result = SpreadResult(status="spread")
    result.context = {"document_id": str(document.id), "period_end": period_end.isoformat(), "months": months}
    if document.status == "image_only" or document.meta.get("image_only_pages"):
        _item(db, result, borrower, cycle, document, item_type="spread.image_only", severity="medium",
              title=f"{document.title} has pages with no readable text",
              question="One or more pages of this document are scanned images and cannot be read. Request a text PDF, or key the figures by hand?",
              allowed_decisions=["request_new_document", "key_by_hand"], required_permission="confirm_spread",
              evidence={"document_id": str(document.id),
                        "image_only_pages": document.meta.get("image_only_pages", [])})
        return result

    content = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(read_file(document)).decode()}},
        {"type": "text", "text": (
            f"Spread the statements for the period ended {period_end:%B %-d, %Y} "
            f"({months} months, fiscal year to date). Template lines (key | label | kind):\n"
            f"{template_listing(borrower.template_id)}")},
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

    # a document that names the borrower nowhere is somebody else's, or cannot be told to be this
    # borrower's: nothing is read from it
    if not any(_names(p.text, borrower.name) for p in db.execute(
            select(DocumentPage).where(DocumentPage.document_id == document.id)).scalars()):
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="high",
              title=f"{document.title}: no page names {borrower.name}",
              question=f"No page of this document names {borrower.name}, so it may be another company's "
                       "statements. Is this the right document for this borrower?",
              allowed_decisions=["wrong_document", "request_new_document", "key_by_hand"],
              required_permission="confirm_spread", evidence={"document_id": str(document.id)},
              guardrail_notes=result.notes)
        outcome.run.guardrail_notes = result.notes
        return result
    scale = scale_override or _derive_scale(db, document, out, result)
    headers = {c.column_header for c in out.cells}
    # which column each figure sits in is decided cell by cell from the page's own headers; here
    # code only asks whether the pages the agent read mention the period at all
    cited = [get_page(db, document.id, n) for n in sorted({c.page for c in out.cells})]
    period_ok = bool(out.cells) and any(_mentions(p.text, period_end) for p in cited if p is not None)
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
    # when most of what was read sits outside the period's column, the reader took the wrong
    # column or the wrong document: nothing read that way is kept for a person to wave through
    off_column = [u for u in result.unverified if u["reason"] == "column_unconfirmed"]
    if len(off_column) * 2 > len(out.cells):
        for fact in db.execute(select(Fact).where(Fact.agent_run_id == outcome.run.id)).scalars():
            fact.status = "rejected"  # the whole reading is set aside, including what happened to match
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="high",
              title=f"{document.title}: the figures read are not in the column for the period",
              question=f"Most of the figures the reader took are not in a column headed {period_end:%B %-d, %Y}. "
                       "Is this the right document for the period?",
              allowed_decisions=["retry", "wrong_document", "request_new_document"],
              required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "reasons": sorted({u["detail"] for u in off_column})},
              guardrail_notes=result.notes)
        outcome.run.guardrail_notes = result.notes
        return result
    tid = borrower.template_id
    if result.out_of_template:
        listed = ", ".join(sorted(result.out_of_template))
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="medium",
              dedupe_kind="spread.not_in_template",
              title=f"{document.title}: figures filed under lines outside the {tid} template",
              question=f"The reader filed figures under {listed}, which are not lines of this borrower's {tid} "
                       "template, so they were not stored. Request a new document, or key the figures by hand?",
              allowed_decisions=["request_new_document", "key_by_hand"], required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "template": tid, "lines": sorted(result.out_of_template)},
              guardrail_notes=result.notes)
    absent = [k for k in out.absent_keys if template.in_template(k, tid) and k not in values]
    result.context = {**result.context, "scale": scale, "absent": sorted(absent)}
    report = template.check_statement(values, scale=scale, prior_fye_cash=prior_fye_cash, absent=absent,
                                      template_id=tid)
    result.failed_checks = [e.to_dict() for e in report.errors]
    # footing is the check that catches a misread line, so it may not be skipped: each statement
    # that was read must have its final printed total read and agreeing with the lines
    footed = {c.key for c in report.checks if c.check == "footing" and c.status == "pass"}
    lines = {line.key: line for line in template.template_lines(tid)}
    for total in (t for t in REQUIRED_TOTALS[tid] if t in lines):
        statement = lines[total].statement
        read = any(k in values for k, line in lines.items()
                   if line.statement == statement and not line.computed)
        failed = any(e.get("key") == total for e in result.failed_checks)
        if read and total not in footed and not failed:
            result.failed_checks.append({
                "code": "total_not_read", "key": total,
                "message": f"the printed {lines[total].label.lower()} was not read, so the "
                           f"{statement} lines cannot be checked against it"})

    if result.unverified:
        # say what is being asked: confirming a figure held for its label accepts the line it was
        # filed under, for this borrower, from now on
        mapping = [u for u in result.unverified if u["reason"] == "mapping_doubt"]
        if len(mapping) == len(result.unverified):
            title = f"{document.title}: {len(mapping)} row(s) filed under a line their label does not name"
            question = ("Each row listed was filed under a line that its printed label does not name. Confirming "
                        "accepts that label for that line for this borrower. Is each one filed under the right line?")
        elif mapping:
            title = f"{document.title}: {len(result.unverified)} figure(s) could not be verified on the page"
            question = ("Some figures could not be placed on the page as reported, and some rows were filed under a "
                        "line their label does not name. Is each figure right and filed under the right line?")
        else:
            title = f"{document.title}: {len(result.unverified)} figure(s) could not be verified on the page"
            question = "These figures could not be found on the cited page exactly as reported. Keep, replace or reject each one?"
        _item(db, result, borrower, cycle, document, item_type="spread.value_unverified", severity="medium",
              title=title, question=question,
              allowed_decisions=["values_confirmed", "values_corrected", "request_new_document"],
              required_permission="confirm_spread",
              evidence={"document_id": str(document.id), "cells": result.unverified})
    # a line held for a person is missing from the totals, so footing fails for that reason
    # alone; the footing question is asked once the held figures are cleared
    if result.failed_checks and not result.unverified:
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
    if not result.failed_checks and not current_unverified:
        _store_computed(db, borrower, period_end, months, report, result)
        _store_absent(db, borrower, period_end, months, absent, result)
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
        borrower_id=borrower.id, formula_key="template_totals", formula_version=borrower.template_id,
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


def _store_absent(db, borrower, period_end, months, absent, result) -> None:
    """A template line the statement does not print is zero only because the footing checks
    passed without it. That conclusion is stored as a calculated fact naming the printed totals
    that prove it, so a covenant reading the line finds a sourced zero instead of a gap."""
    if not absent:
        return
    proof = [(k, f) for k, f in sorted(result.facts.items()) if k.startswith(template.STATED_PREFIX)]
    calc = CalcRun(
        borrower_id=borrower.id, formula_key="absent_lines_verified_by_footing", formula_version=borrower.template_id,
        period_end=period_end, engine_version=ENGINE_VERSION,
        inputs=[{"key": k, "fact_id": str(f.id), "value": str(f.value)} for k, f in proof],
        outputs={key: "0" for key in sorted(absent)}, created_by_type="system", created_by_id="spreading")
    db.add(calc)
    db.flush()
    for key in sorted(absent):
        result.facts[key] = add_fact(
            db, borrower_id=borrower.id, key=key, period_end=period_end, months=_months_for(key, months),
            value=Decimal(0), kind="calculated", calc_run_id=calc.id, actor=("system", "spreading"),
            note="not printed on the statement; zero because every total foots without it")


def finalize_spread(db: Session, *, borrower: Borrower, document: Document | None, period_end: date, months: int,
                    scale: int, absent: list[str], cycle: Cycle | None) -> SpreadResult:
    """Finish a spread after a person has confirmed, corrected or keyed figures: read the usable
    facts for the period, run the footing and tie checks again, and store totals only if they
    pass. This is the repair path for a spread that was held, and the way totals are calculated
    again after a correction. `document` is None for history that came from a system of record."""
    from app.calc.periods import prior_fiscal_year_end
    from app.domain.facts_service import current_fact

    result = SpreadResult(status="spread")
    title = document.title if document is not None else f"{borrower.name} statements for {period_end.isoformat()}"
    result.context = {"document_id": str(document.id) if document is not None else None,
                      "period_end": period_end.isoformat(), "months": months, "scale": scale, "absent": sorted(absent)}
    values: dict[str, Decimal] = {}
    tid = borrower.template_id
    for line in template.template_lines(tid):
        keys = [template.STATED_PREFIX + line.key] if line.computed else [line.key]
        for key in keys:
            fact = current_fact(db, borrower.id, key, period_end, _months_for(key, months))
            if fact is not None:
                values[key] = fact.value
                result.facts[key] = fact
    still_absent = [k for k in absent if k not in values]
    prior = current_fact(db, borrower.id, template.cash_roll_keys(tid)[1],
                         prior_fiscal_year_end(period_end, borrower.fiscal_year_end_month), 0)
    report = template.check_statement(values, scale=scale, prior_fye_cash=prior.value if prior else None,
                                      absent=still_absent, template_id=tid)
    result.failed_checks = [e.to_dict() for e in report.errors]
    if report.errors:
        _item(db, result, borrower, cycle, document, item_type="spread.does_not_foot", severity="high",
              title=f"{title}: the statements still do not foot or are incomplete",
              question="After the changes, one or more totals still do not agree or a line is missing. Which figure is wrong?",
              allowed_decisions=["values_corrected", "accept_as_reported", "request_new_document"],
              required_permission="confirm_spread",
              evidence={"document_id": result.context["document_id"], "checks": result.failed_checks})
        return result
    if current_fact(db, borrower.id, template.balance_keys(tid)[0], period_end, 0) is None:
        _store_computed(db, borrower, period_end, months, report, result)
        _store_absent(db, borrower, period_end, months, still_absent, result)
    ledger.record(db, actor_type="system", actor_id="spreading", action="spread.finalized",
                  entity_type="document" if document is not None else "borrower",
                  entity_id=document.id if document is not None else borrower.id,
                  payload={"lines": len(values), "scale": scale, "period_end": period_end})
    db.flush()
    return result

"""Intake Agent: say what each received document is and which period it covers. Code checks the
answer against the page and its own rules, files the document on the calendar, and raises a
work item for anything that does not check out or is still missing."""
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.spreading import _names
from app.agents.tools import Scope, ToolGateway
from app.core import ledger
from app.domain import calendar
from app.domain.credit import Borrower
from app.domain.documents import Document, DocumentPage
from app.domain.monitoring import Cycle, WorkItem
from app.domain.work_items import raise_item
from app.guardrails.narrative import check_narrative
from app.guardrails.quotes import dates_in, quote_on_page

DocType = Literal[
    "credit_agreement", "amendment", "waiver", "annual_statements", "interim_statements",
    "compliance_certificate", "borrowing_base_certificate", "receivables_aging", "tax_return", "monthly_financials", "mrr_report", "bank_statement", "term_sheet",
    "investor_update", "other"]
# document types a venture client sends each month; they must name the client and sit in the cycle's month
MONTHLY_TYPES = ("monthly_financials", "mrr_report", "bank_statement")
NEW_TYPES = (*MONTHLY_TYPES, "term_sheet", "investor_update")
CLIENT_MONTH_QUESTION = "Which client is this, and which month?"
PAGES_SHOWN = 2
CHARS_SHOWN = 6000

# Code's own view of a document's type, from phrases that are hard to mistake. When these rules
# reach a view and the agent disagrees, a person decides.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("borrowing_base_certificate", re.compile(r"borrowing base certificate", re.I)),
    ("compliance_certificate", re.compile(r"compliance certificate|certificate of compliance", re.I)),
    ("amendment", re.compile(r"\b(?:first|second|third|fourth|fifth)\s+amendment\b|amendment no\.?\s*\d+ to", re.I)),
    ("waiver", re.compile(r"\bwaiver (?:letter|agreement)\b|\blimited waiver\b", re.I)),
    ("tax_return", re.compile(r"\bform\s+11(?:20|20-?s|65)\b|u\.s\. (?:corporation )?income tax return", re.I)),
    # Specific titles come before credit_agreement, and credit_agreement is a heading line only: a bank
    # statement note ("pledged under the venture loan agreement") or a term sheet condition ("where the loan
    # agreement requires it") mentions the agreement without being one. An investor update says "term sheet
    # signed", so it comes before term_sheet.
    ("bank_statement", re.compile(r"statement of account|account statement|bank statement", re.I)),
    ("investor_update", re.compile(r"investor update|letter to investors", re.I)),
    ("term_sheet", re.compile(r"term sheet|summary of terms", re.I)),
    ("credit_agreement", re.compile(
        r"^[ \t]*(?:venture[ \t]+)?(?:credit|loan(?:[ \t]+and[ \t]+security)?)\s+agreement[ \t]*$", re.I | re.M)),
    # only a report title files an MRR report ("MRR report", "recurring revenue report"): a bare
    # "ARR", "MRR" or "monthly recurring revenue" is a KPI line on page one of an investor update or
    # a monthly pack. It comes before the monthly rule because an MRR report is headed "month ended" too.
    ("mrr_report", re.compile(r"\b(?:mrr|arr) report\b|\brecurring revenue report\b", re.I)),
    ("monthly_financials", re.compile(
        r"\bmonth ended\b|\bfor the month of\b|\b(?:one|two|four|five|seven|eight|ten|eleven) months ended\b", re.I)),
    ("annual_statements", re.compile(r"independent auditor'?s'? report|for the years? ended|year ended", re.I)),
    ("interim_statements", re.compile(r"\b(?:three|six|nine) months ended\b|\bquarter ended\b", re.I)),
    ("receivables_aging", re.compile(r"\baccounts receivable aging\b|\baged receivables\b", re.I)),
]


_AUDITOR = re.compile(r"independent auditor'?s'? report|report of independent (?:registered )?(?:public )?account", re.I)


def has_auditors_report(db: Session, doc: Document) -> bool:
    """Statements count as audited only when an independent auditor's report is in the document."""
    return any(_AUDITOR.search(p.text) for p in db.execute(
        select(DocumentPage).where(DocumentPage.document_id == doc.id)).scalars())


def rule_type(text: str) -> str | None:
    head = text[:2500]
    for doc_type, pattern in _RULES:
        if pattern.search(head):
            return doc_type
    return None


class Classified(BaseModel):
    document_number: int
    doc_type: DocType
    period_end_text: str
    effective_date_text: str
    quality: Literal["audited", "reviewed", "compiled", "internal", "na"]
    title_as_printed: str
    concern: str


class IntakeAnswer(BaseModel):
    documents: list[Classified]


SPEC = AgentSpec(name="intake", version="3", purpose="Classify received documents and identify their period.",
                 prompt_file="intake.md", output_model=IntakeAnswer, tools=(), effort="low", max_tokens=8000)


@dataclass
class IntakeResult:
    run_id: uuid.UUID | None = None
    filed: list[Document] = field(default_factory=list)
    work_items: list[WorkItem] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)


def _head(db: Session, doc: Document) -> str:
    pages = db.execute(select(DocumentPage).where(
        DocumentPage.document_id == doc.id, DocumentPage.page_number <= PAGES_SHOWN)
        .order_by(DocumentPage.page_number)).scalars()
    return "\n".join(p.text for p in pages)[:CHARS_SHOWN]


def _one_date(text: str, head: str) -> date | None:
    """A date the agent copied counts only if the text is on the page and reads as exactly one date."""
    if not text.strip() or not quote_on_page(head, text):
        return None
    found = dates_in(text)
    return found[0] if len(found) == 1 else None


def classify_documents(
    db: Session, *, borrower: Borrower, documents: list[Document], llm: LLMClient, cycle: Cycle | None,
    batch_key: str,
) -> IntakeResult:
    result = IntakeResult()
    pending = [d for d in documents if d.doc_type is None]
    if not pending:
        return result
    heads = {d.id: _head(db, d) for d in pending}
    parts = [f"The borrower expected is {borrower.name}. Classify each of the {len(pending)} documents below."]
    for n, doc in enumerate(pending, start=1):
        parts.append(f"<document number=\"{n}\" file=\"{doc.file_name}\" pages=\"{doc.page_count}\">\n"
                     f"{heads[doc.id] or '[no readable text]'}\n</document>")
    scope = Scope(borrower_id=borrower.id, cycle_id=cycle.id if cycle else None,
                  period_end=cycle.period_end if cycle else None, document_ids=tuple(d.id for d in pending))
    outcome = run_agent(db, SPEC, task="classify_documents", scope=scope,
                        content=[{"type": "text", "text": "\n\n".join(parts)}], llm=llm, gateway=ToolGateway(),
                        record_key=f"intake/{borrower.code}/{batch_key}")
    result.run_id = outcome.run.id
    answers: dict[int, Classified] = {}
    if outcome.ok:
        for item in outcome.output.documents:  # type: ignore[union-attr]
            answers.setdefault(item.document_number, item)

    for n, doc in enumerate(pending, start=1):
        head = heads[doc.id]
        answer = answers.get(n)
        by_rule = rule_type(head)
        problem = None
        if answer is None:
            problem = "the Intake Agent gave no answer for this document"
        elif answer.doc_type == "other":
            problem = "the Intake Agent could not tell what this document is"
        elif by_rule is not None and by_rule != answer.doc_type:
            problem = f"the Intake Agent read this as {answer.doc_type}, the filing rules read it as {by_rule}"
        period_end = effective = None
        ask = "What is this document, and which period does it cover?"
        if problem is None:
            needs_period = answer.doc_type not in ("credit_agreement", "amendment", "waiver", "other",
                                                   "term_sheet", "investor_update")
            period_end = _one_date(answer.period_end_text, head)
            effective = _one_date(answer.effective_date_text, head)
            if needs_period and period_end is None:
                problem = "the period end the Intake Agent reported is not on the first pages as a single date"
            elif period_end is not None and date(period_end.year + 1, period_end.month, min(period_end.day, 28)) in {
                    date(d.year, d.month, min(d.day, 28)) for d in dates_in(head)}:
                # statements print the prior year beside the current one: the earlier of the pair
                # is the comparative column, not the period
                problem = ("the first pages also print the same date one year later, so the period end reported "
                           "looks like the comparative column")
            elif not _names(head, borrower.name):
                problem = f"the first pages do not name {borrower.name}; the document may be another company's"
                if answer.doc_type in NEW_TYPES:
                    ask = CLIENT_MONTH_QUESTION
            elif (answer.doc_type in MONTHLY_TYPES and cycle is not None and period_end is not None
                  and period_end != cycle.period_end):
                problem = (f"the period end on the page is {period_end:%B %-d, %Y}; the period expected is "
                           f"{cycle.period_end:%B %-d, %Y}")
                ask = CLIENT_MONTH_QUESTION
        concern = ""
        if answer is not None and answer.concern.strip():
            if check_narrative(answer.concern, {}):
                result.notes.append({"layer": "narrative", "check": "figure_untraceable", "action": "dropped",
                                     "detail": "a concern from the agent contained a typed figure and was removed"})
            else:
                concern = answer.concern.strip()

        if problem is not None:
            result.work_items.append(raise_item(
                db, borrower_id=borrower.id, cycle_id=cycle.id if cycle else None, stage="intake",
                item_type="intake.unclassified", severity="medium",
                title=f"{doc.file_name} could not be filed",
                question=ask,
                allowed_decisions=["classified_by_hand", "not_needed", "request_new_document"],
                required_permission="upload_document",
                evidence={"document_id": str(doc.id), "reason": problem, "agent_concern": concern,
                          "agent_answer": answer.model_dump() if answer else None, "rule_type": by_rule},
                agent_run_id=result.run_id, actor=("agent", "intake"), dedupe_key=f"intake.unclassified:{doc.id}"))
            continue

        quality = answer.quality
        if quality == "audited" and not has_auditors_report(db, doc):
            quality = "internal" if answer.doc_type == "interim_statements" else "unverified"
            result.notes.append({"layer": "intake", "check": "audited_without_report", "action": "quality_changed",
                                 "detail": f"{doc.file_name}: reported as audited but no auditor's report is in "
                                           f"the document; recorded as {quality}"})
        doc.doc_type = answer.doc_type
        doc.doc_type_source = "agent"
        doc.period_end = period_end
        doc.effective_date = effective
        doc.meta = {**doc.meta, "quality": quality, "title_as_printed": answer.title_as_printed,
                    "agent_concern": concern, "rule_type": by_rule}
        ledger.record(db, actor_type="agent", actor_id="intake@1", action="document.classified",
                      entity_type="document", entity_id=doc.id,
                      payload={"doc_type": doc.doc_type, "period_end": period_end, "effective_date": effective,
                               "agreed_with_rules": by_rule == answer.doc_type if by_rule else None})
        calendar.match_document(db, doc)
        result.filed.append(doc)
        if concern:
            result.work_items.append(raise_item(
                db, borrower_id=borrower.id, cycle_id=cycle.id if cycle else None, stage="intake",
                item_type="intake.unclassified", severity="low", blocks_stage=False,
                title=f"{doc.file_name}: the Intake Agent raised a concern",
                question="The document was filed, but a concern was raised. Does it need action?",
                allowed_decisions=["no_action", "request_new_document"], required_permission="upload_document",
                evidence={"document_id": str(doc.id), "agent_concern": concern},
                agent_run_id=result.run_id, actor=("agent", "intake"), dedupe_key=f"intake.concern:{doc.id}"))
    outcome.run.guardrail_notes = result.notes
    db.flush()
    return result


def chase_missing(db: Session, *, borrower: Borrower, cycle: Cycle, today: date) -> WorkItem | None:
    """If reporting for the cycle's period is past due, raise one item listing what is missing,
    with a draft chaser. The draft is written by code and is never sent automatically."""
    missing = [ob for ob in calendar.outstanding(db, borrower.id, cycle.period_end) if ob.due_date < today]
    if not missing:
        return None
    names = sorted({ob.document_type.replace("_", " ") for ob in missing})
    oldest_due = min(ob.due_date for ob in missing)
    draft = (
        f"Subject: Reporting due for the period ended {cycle.period_end:%B %-d, %Y}\n\n"
        f"Dear {borrower.name} team,\n\n"
        f"Our records show the following reporting items for the period ended {cycle.period_end:%B %-d, %Y} "
        f"have not yet been received: {', '.join(names)}. These were due on {oldest_due:%B %-d, %Y} under the "
        f"reporting requirements of your credit agreement.\n\n"
        f"Please send them at your earliest convenience, or let us know when we can expect them.\n\n"
        f"Thank you,\nBank of Stoic")
    return raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="awaiting_package",
        item_type="intake.missing_document", severity="high" if (today - oldest_due).days > 15 else "medium",
        title=f"{borrower.name}: reporting is {(today - oldest_due).days} days past due",
        question="Reporting for this period is past due. Send the chaser, or record why it is not needed?",
        allowed_decisions=["chaser_sent", "extension_granted", "received_elsewhere"],
        required_permission="upload_document",
        evidence={"missing": [{"document_type": ob.document_type, "due_date": ob.due_date.isoformat(),
                               "obligation_id": str(ob.id)} for ob in missing],
                  "days_past_due": (today - oldest_due).days, "draft_email": draft},
        actor=("system", "calendar"), dedupe_key=f"intake.missing:{cycle.id}")

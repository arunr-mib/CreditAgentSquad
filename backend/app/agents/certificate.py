"""Certificate reader: locate what the borrower reported for each covenant. Code verifies each
item on its page and stores it as a cited fact. The certificate is evidence to reconcile
against; it never decides a test."""
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
from app.calc.terms import Terms
from app.domain.credit import Borrower
from app.domain.documents import Document, DocumentPage
from app.domain.documents_service import get_page, read_file
from app.domain.facts_service import add_fact, store_extracted_cell
from app.domain.monitoring import Cycle
from app.guardrails.numbers import extract_figures
from app.guardrails.quotes import locate, quote_on_page, same_row, verify_cell
from app.guardrails.units import scale_of, units_in


class CertRow(BaseModel):
    covenant_id: str
    page: int
    printed_label: str
    actual_printed: str
    required_printed: str
    compliance_printed: str


class CertificateReading(BaseModel):
    rows: list[CertRow]
    scale_statement: str
    scale_page: int
    notes: list[str]


SPEC = AgentSpec(name="certificate_reader", version="1",
                 purpose="Locate the borrower's reported covenant values on a compliance certificate.",
                 prompt_file="certificate.md", output_model=CertificateReading, tools=(), effort="low",
                 max_tokens=8000)
_YES_NO = {"yes": 1, "no": 0, "y": 1, "n": 0, "in compliance": 1, "not in compliance": 0}


@dataclass
class CertificateResult:
    run_id: uuid.UUID | None = None
    stored: list[str] = field(default_factory=list)  # covenant ids with a verified reported value
    unverified: list[dict[str, Any]] = field(default_factory=list)


def _on_row(page, anchor, text: str) -> bool:
    """True when `text` is printed on the same row as `anchor`, the place where code found the
    covenant's reported figure. The row is never chosen by a label the reader reported: a label
    fragment such as "Ratio" sits on every row."""
    return any(same_row(hit.bbox, anchor) for hit in locate(page.words, text))


def _flag_on_row(page, anchor) -> str | None:
    """The yes or no printed on the figure's row, read by code; None unless there is exactly one."""
    found = [str(w[4]) for w in page.words
             if same_row((float(w[0]), float(w[1]), float(w[2]), float(w[3])), anchor)
             and str(w[4]).strip(".,;:()").lower() in ("yes", "no")]
    return found[0].strip(".,;:()") if len(found) == 1 else None


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _row_problem(row_label: str, covenant_id: str, names: dict[str, tuple[str, ...]]) -> str | None:
    """A certificate row belongs to the covenant whose name its label starts with. Returns why
    the row cannot be taken as this covenant's, or None."""
    row = _words(row_label)
    starts = {cid: max((len(_words(n)) for n in labels if _words(n) and row[:len(_words(n))] == _words(n)), default=0)
              for cid, labels in names.items()}
    best = max(starts.values(), default=0)
    if best == 0:
        return f"the row {row_label!r} does not start with the name of a covenant in the approved terms"
    if starts.get(covenant_id, 0) < best:
        other = next(cid for cid, n in starts.items() if n == best)
        return f"the row {row_label!r} reads as {other}, not {covenant_id}"
    return None


def read_certificate(db: Session, *, borrower: Borrower, document: Document, period_end: date, terms: Terms,
                     cycle: Cycle | None, llm: LLMClient) -> CertificateResult:
    result = CertificateResult()
    covenants = {c.id: c for c in terms.covenants}
    listing = "\n".join(f"- {c.id} | {c.name}" for c in terms.covenants)
    content = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(read_file(document)).decode()}},
        {"type": "text", "text": f"Compliance certificate for the period ended {period_end:%B %-d, %Y}. "
                                 f"Covenants in the approved terms (id | name):\n{listing}"}]
    scope = Scope(borrower_id=borrower.id, period_end=period_end, cycle_id=cycle.id if cycle else None,
                  document_ids=(document.id,))
    outcome = run_agent(db, SPEC, task="read_certificate", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"certificate/{borrower.code}/{period_end}")
    result.run_id = outcome.run.id
    if not outcome.ok:
        result.unverified.append({"reason": outcome.reason or "no_answer", "detail": "the reader returned no usable result"})
        return result
    out: CertificateReading = outcome.output  # type: ignore[assignment]

    scale = 1
    if out.scale_statement.strip():
        page = get_page(db, document.id, out.scale_page)
        if page is not None and quote_on_page(page.text, out.scale_statement):
            scale = scale_of(out.scale_statement) or 1
    # code's own check of the units: a "thousands" phrase printed anywhere must have been reported
    printed_thousands = any(units_in(p.text) & {"thousands", "millions"} for p in db.execute(
        select(DocumentPage).where(DocumentPage.document_id == document.id)).scalars())
    units_in_doubt = printed_thousands and scale == 1
    names = {c.id: (c.name,) for c in terms.covenants}
    seen: set[str] = set()
    for row in out.rows:
        covenant = covenants.get(row.covenant_id)
        page = get_page(db, document.id, row.page)
        problem = None
        if covenant is None or row.covenant_id in seen:
            problem = "the covenant is not in the approved terms, or was reported twice"
        elif page is None or not page.has_text:
            problem = "the cited page does not exist or has no text"
        else:
            # the row the figure sits on must be this covenant's row. Code reads the row's label
            # from the page; the label the reader reported is only used to find the row
            located = verify_cell(page.words, printed_figure=row.actual_printed, printed_label=row.printed_label)
            if located.value is not None:
                problem = _row_problem(located.row_label, row.covenant_id, names)
            if problem is None and units_in_doubt and covenant.test.unit == "usd":
                problem = "the certificate prints an 'in thousands' phrase that was not reported, so dollar amounts cannot be scaled"
        if problem:
            result.unverified.append({"covenant_id": row.covenant_id, "reason": "refused", "detail": problem})
            continue
        seen.add(row.covenant_id)
        unit = covenant.test.unit
        fact, check = store_extracted_cell(
            db, borrower_id=borrower.id, key=f"cert.{covenant.id}.value", period_end=period_end, months=0,
            document=document, page_number=row.page, printed_figure=row.actual_printed,
            printed_label=row.printed_label, column_header=None, scale=scale if unit == "usd" else 1,
            presentation_sign=1, agent_run_id=outcome.run.id, unit=unit, actor=("agent", "certificate_reader"))
        if fact is None or not check.ok:
            result.unverified.append({"covenant_id": covenant.id, "reason": check.status, "detail": check.detail})
            continue
        result.stored.append(covenant.id)
        common = dict(borrower_id=borrower.id, period_end=period_end, months=0, kind="extracted", status="verified",
                      document_id=document.id, page=row.page, label_text=check.row_label or row.printed_label,
                      agent_run_id=outcome.run.id, actor=("agent", "certificate_reader"))
        # the requirement and the compliance entry must sit on the covenant's own row
        figures = extract_figures(row.required_printed)
        if len(figures) == 1 and _on_row(page, check.bbox, row.required_printed):
            value = figures[0].value * (Decimal(scale) if unit == "usd" else Decimal(1))
            add_fact(db, key=f"cert.{covenant.id}.threshold", value=value, unit=unit, quote=row.required_printed, **common)
        else:
            result.unverified.append({"covenant_id": covenant.id, "reason": "requirement_unverified",
                                      "detail": "the printed requirement was not found on the covenant's row"})
        # the compliance entry is read from the figure's own row by code; what the reader
        # reported counts only if it is what that row prints
        printed = _flag_on_row(page, check.bbox)
        reported = row.compliance_printed.strip()
        if reported and _YES_NO.get(reported.lower()) is not None and _on_row(page, check.bbox, reported) \
                and (printed is None or _YES_NO[printed.lower()] == _YES_NO[reported.lower()]):
            add_fact(db, key=f"cert.{covenant.id}.in_compliance", value=Decimal(_YES_NO[reported.lower()]),
                     unit="count", quote=reported, **common)
        elif not reported and printed is not None:
            add_fact(db, key=f"cert.{covenant.id}.in_compliance", value=Decimal(_YES_NO[printed.lower()]),
                     unit="count", quote=printed, **common)
        else:
            result.unverified.append({"covenant_id": covenant.id, "reason": "compliance_unverified",
                                      "detail": "the compliance entry was not found on the covenant's row"})
    db.flush()
    return result

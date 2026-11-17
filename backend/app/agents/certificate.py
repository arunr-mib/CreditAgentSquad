"""Certificate reader: locate what the borrower reported for each covenant. Code verifies each
item on its page and stores it as a cited fact. The certificate is evidence to reconcile
against; it never decides a test."""
import base64
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
from app.agents.spreading import _THOUSANDS
from app.agents.tools import Scope, ToolGateway
from app.calc.terms import Terms
from app.domain.credit import Borrower
from app.domain.documents import Document, DocumentPage
from app.domain.documents_service import get_page, read_file
from app.domain.facts_service import add_fact, store_extracted_cell
from app.domain.monitoring import Cycle
from app.guardrails.labels import mapping_doubt
from app.guardrails.numbers import extract_figures
from app.guardrails.quotes import locate, quote_on_page, same_row


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


def _on_row(page, label: str, text: str) -> bool:
    labels = locate(page.words, label)
    return any(same_row(hit.bbox, lab.bbox) for hit in locate(page.words, text) for lab in labels)


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
            scale = 1000 if _THOUSANDS.search(out.scale_statement) or "thousand" in out.scale_statement.lower() else 1
    # code's own check of the units: a "thousands" phrase printed anywhere must have been reported
    printed_thousands = any(_THOUSANDS.search(p.text) for p in db.execute(
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
            # the row's printed label must not clearly name a different covenant
            problem = mapping_doubt(row.printed_label, row.covenant_id, names)
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
                      document_id=document.id, page=row.page, label_text=row.printed_label,
                      agent_run_id=outcome.run.id, actor=("agent", "certificate_reader"))
        # the requirement and the compliance entry must sit on the covenant's own row
        figures = extract_figures(row.required_printed)
        if len(figures) == 1 and _on_row(page, row.printed_label, row.required_printed):
            value = figures[0].value * (Decimal(scale) if unit == "usd" else Decimal(1))
            add_fact(db, key=f"cert.{covenant.id}.threshold", value=value, unit=unit, quote=row.required_printed, **common)
        else:
            result.unverified.append({"covenant_id": covenant.id, "reason": "requirement_unverified",
                                      "detail": "the printed requirement was not found on the covenant's row"})
        flag = _YES_NO.get(row.compliance_printed.strip().lower())
        if flag is not None and _on_row(page, row.printed_label, row.compliance_printed):
            add_fact(db, key=f"cert.{covenant.id}.in_compliance", value=Decimal(flag), unit="count",
                     quote=row.compliance_printed, **common)
        else:
            result.unverified.append({"covenant_id": covenant.id, "reason": "compliance_unverified",
                                      "detail": "the compliance entry was not found on the covenant's row"})
    db.flush()
    return result

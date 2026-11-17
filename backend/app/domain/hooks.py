"""Connect decisions on work items to the services that carry them out. Imported once at startup."""


from datetime import date

from sqlalchemy import select

from app.domain import review_service, stages, terms_service, workflow
from app.domain.credit import Facility
from app.domain.documents import Document


def on_unapproved_amendment(db, item, user, decision: str, reason: str) -> None:
    """Deciding to update the terms asks the Terms Agent to propose a new version from the
    agreement and every amendment on file. The proposal still needs a second person's approval;
    if nothing usable can be proposed, the agent raises an item asking a person to board the terms."""
    if decision != "terms_update_requested":
        if not reason.strip():
            raise ValueError("setting an amendment aside needs a reason")
        return
    from app.agents import terms_agent

    facility = db.get(Facility, item.facility_id) if item.facility_id else None
    if facility is None:
        raise ValueError("the item names no loan")
    documents = list(db.execute(select(Document).where(
        Document.borrower_id == facility.borrower_id,
        Document.doc_type.in_(("credit_agreement", "amendment")))).scalars())
    # the agreement first, then amendments in the order they took effect
    documents.sort(key=lambda d: (d.doc_type != "credit_agreement", d.effective_date or date.max, d.created_at))
    if not any(d.doc_type == "credit_agreement" for d in documents):
        raise ValueError("no credit agreement is on file for this borrower")
    terms_agent.extract_terms(db, facility=facility, documents=documents, llm=stages.LLM_FACTORY(),
                              cycle=db.get(workflow.Cycle, item.cycle_id) if item.cycle_id else None)


workflow.DECISION_HOOKS["terms.approval_needed"] = terms_service.on_decision
workflow.DECISION_HOOKS["review.commentary_approval"] = review_service.on_decision
workflow.DECISION_HOOKS["terms.unapproved_amendment"] = on_unapproved_amendment


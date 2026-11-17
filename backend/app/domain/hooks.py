"""Connect decisions on work items to the services that carry them out. Imported once at startup."""


import uuid
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


def _set_stage(db, cycle_id, stage: str, status: str, **detail) -> None:
    for st in workflow.stages(db, db.get(workflow.Cycle, cycle_id)):
        if st.stage == stage:
            st.status = status
            st.detail = {**st.detail, **detail}
    db.flush()


def on_spread_decision(db, item, user, decision: str, reason: str) -> None:
    """Carry out a person's decision on a held spread. Each decision has a repair path: a new
    document, the units, confirmed or corrected figures, or the totals as reported."""
    from decimal import Decimal

    from app.agents import spreading
    from app.calc import template
    from app.core import ledger
    from app.domain.credit import Borrower
    from app.domain.facts import Fact
    from app.domain.facts_service import add_fact, confirm_fact, current_fact

    if item.stage != "spreading":
        return  # the same item types are raised for certificates; those need no follow-up here
    context = item.evidence.get("spread") or {}
    document = db.get(Document, uuid.UUID(item.evidence["document_id"])) if item.evidence.get("document_id") else None
    if decision in ("request_new_document", "wrong_document"):
        if document is not None:
            document.status = "rejected"
            ledger.record(db, actor_type="user", actor_id=user.id, action="document.set_aside",
                          entity_type="document", entity_id=document.id, payload={"reason": reason or decision})
        if item.cycle_id is not None:
            _set_stage(db, item.cycle_id, "spreading", "pending")
        return
    if decision in ("in_thousands", "in_dollars", "retry"):
        override = {"in_thousands": 1000, "in_dollars": 1}.get(decision)
        if item.cycle_id is not None:
            _set_stage(db, item.cycle_id, "spreading", "pending", **({"scale_override": override} if override else {}))
        return
    if "scale" not in context:
        raise ValueError("this item does not carry what is needed to finish the spread; request a new document")
    borrower = db.get(Borrower, item.borrower_id)
    period_end, months = date.fromisoformat(context["period_end"]), context["months"]
    if decision == "values_confirmed":
        missing = [c["key"] for c in item.evidence.get("cells", []) if not c.get("fact_id")]
        if missing:
            raise ValueError("these figures were not found on the page and have no value to confirm; "
                             "enter them first: " + ", ".join(missing))
        for cell in item.evidence.get("cells", []):
            fact = db.get(Fact, uuid.UUID(cell["fact_id"]))
            if fact is not None and fact.status == "proposed":
                confirm_fact(db, fact, user.id)
    if decision == "accept_as_reported":
        if not reason.strip():
            raise ValueError("accepting totals as reported needs a reason")
        for line in template.LINES:
            stated = current_fact(db, borrower.id, template.STATED_PREFIX + line.key, period_end,
                                  months if line.flow else 0) if line.computed else None
            if stated is not None and current_fact(db, borrower.id, line.key, period_end,
                                                   months if line.flow else 0) is None:
                add_fact(db, borrower_id=borrower.id, key=line.key, period_end=period_end,
                         months=months if line.flow else 0, value=Decimal(stated.value), kind="manual",
                         entered_by=user.id, reason=f"total accepted as reported: {reason}",
                         document_id=stated.document_id, page=stated.page, actor=("user", str(user.id)))
        return
    result = spreading.finalize_spread(db, borrower=borrower, document=document, period_end=period_end, months=months,
                                       scale=context["scale"], absent=context.get("absent", []),
                                       cycle=db.get(workflow.Cycle, item.cycle_id) if item.cycle_id else None)
    if result.status == "spread":
        from app.domain import corrections
        corrections.refresh_after_repair(db, borrower, period_end)


workflow.DECISION_HOOKS["terms.approval_needed"] = terms_service.on_decision
workflow.DECISION_HOOKS["review.commentary_approval"] = review_service.on_decision
workflow.DECISION_HOOKS["terms.unapproved_amendment"] = on_unapproved_amendment

for _type in ("spread.value_unverified", "spread.does_not_foot", "spread.image_only"):
    workflow.DECISION_HOOKS[_type] = on_spread_decision

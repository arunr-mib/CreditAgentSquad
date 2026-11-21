"""Connect decisions on work items to the services that carry them out. Imported once at startup.

A decision a person is offered either does something here, or is a judgement whose record (who,
what, why, on the ledger) is its effect. A decision that claims the system changed ("input
provided", "terms approved", "retry") is checked or carried out by code; none is taken on trust.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core import ledger
from app.domain import review_service, stages, terms_service, workflow
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import Fact
from app.domain.monitoring import CovenantTest, Cycle
from app.domain.terms import TermsVersion


def _cycle(db, item) -> Cycle | None:
    return db.get(Cycle, item.cycle_id) if item.cycle_id else None


def _document(db, item) -> Document | None:
    reference = item.evidence.get("document_id")
    return db.get(Document, uuid.UUID(reference)) if reference else None


def _back_to_pending(db, item, stage: str, user, *, required: bool = True, **detail) -> None:
    """Queue a stage to run again. The change goes through the workflow, so it is on the ledger
    under the name of the person whose decision caused it. A decision whose whole effect is the
    re-run is refused when there is no open cycle to run it in."""
    cycle = _cycle(db, item)
    if cycle is None or cycle.status == "closed":
        if required:
            raise ValueError("this item is not part of an open monitoring cycle, so there is no stage to run again")
        return
    for st in workflow.stages(db, cycle):
        if st.stage == stage:
            workflow.set_stage(db, cycle, st, "pending", {**detail, "requeued_by_item": str(item.id)},
                               actor=("user", str(user.id)))
    db.flush()


def _set_aside(db, document: Document | None, user, reason: str) -> None:
    if document is None:
        return
    document.status = "rejected"
    ledger.record(db, actor_type="user", actor_id=user.id, action="document.set_aside",
                  entity_type="document", entity_id=document.id, payload={"reason": reason})


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
                              cycle=_cycle(db, item))


def on_terms_extraction_decision(db, item, user, decision: str, reason: str) -> None:
    """The Terms Agent could not build terms. `retry` runs it again on the same documents; if it
    fails again it raises the question again. `board_by_hand` is accepted only once a person has
    entered terms for the loan, which then wait for a second person's approval."""
    from app.agents import terms_agent

    facility = db.get(Facility, item.facility_id) if item.facility_id else None
    if facility is None:
        raise ValueError("the item names no loan")
    if decision == "retry":
        documents = [db.get(Document, uuid.UUID(ref)) for ref in item.evidence.get("document_ids", [])]
        documents = [d for d in documents if d is not None and d.status != "rejected"]
        if not documents:
            raise ValueError("the documents behind this item are no longer on file; upload the agreement first")
        terms_agent.extract_terms(db, facility=facility, documents=documents, llm=stages.LLM_FACTORY(),
                                  cycle=_cycle(db, item))
        return
    boarded = db.execute(select(TermsVersion.id).where(
        TermsVersion.facility_id == facility.id, TermsVersion.prepared_by_type == "user",
        TermsVersion.status.in_(("proposed", "approved")), TermsVersion.created_at > item.created_at)).first()
    if boarded is None:
        raise ValueError("no terms have been entered for this loan since the question was raised. Enter them "
                         f"first (POST /facilities/{facility.id}/terms), then record this decision; they "
                         "govern a test only after a second person approves them")


def on_certificate_decision(db, item, user, decision: str, reason: str) -> None:
    """Parts of a compliance certificate could not be verified. A new document sets this one
    aside. Confirming accepts the figures that were read but held, and the covenants are tested
    again so the certificate is reconciled; with nothing held, confirming is a judgement and
    needs a reason."""
    from app.domain.covenant_service import run_covenant_tests
    from app.domain.facts_service import confirm_fact

    document = _document(db, item)
    if decision == "request_new_document":
        _set_aside(db, document, user, reason or decision)
        return
    held = [] if document is None else list(db.execute(select(Fact).where(
        Fact.document_id == document.id, Fact.key.like("cert.%"), Fact.status == "proposed")).scalars())
    if not held:
        if not reason.strip():
            raise ValueError("no figure read from this certificate is waiting to be confirmed; say what was "
                             "checked, or request a new document")
        return
    for fact in held:
        confirm_fact(db, fact, user.id)
    facility = db.get(Facility, item.facility_id) if item.facility_id else None
    if facility is not None:
        run_covenant_tests(db, borrower=db.get(Borrower, item.borrower_id), facility=facility,
                           period_end=held[0].period_end, cycle=_cycle(db, item))


def on_spread_decision(db, item, user, decision: str, reason: str) -> None:
    """Carry out a person's decision on a held spread. Each decision has a repair path: a new
    document, the units, confirmed or corrected figures, figures keyed by hand, or the totals as
    reported."""
    from app.agents import spreading
    from app.calc import template
    from app.domain.facts_service import add_fact, confirm_fact, current_fact

    if item.stage != "spreading":
        # the same item type is raised when terms cannot be built and when a certificate is held
        if "document_ids" in item.evidence:
            return on_terms_extraction_decision(db, item, user, decision, reason)
        return on_certificate_decision(db, item, user, decision, reason)
    context = dict(item.evidence.get("spread") or {})
    document = _document(db, item)
    if decision in ("request_new_document", "wrong_document"):
        _set_aside(db, document, user, reason or decision)
        _back_to_pending(db, item, "spreading", user, required=False)
        return
    if decision in ("in_thousands", "in_dollars", "retry"):
        override = {"in_thousands": 1000, "in_dollars": 1}.get(decision)
        # the answer belongs to this one document, never to the other documents the stage reads
        key = f"scale_override:{document.id}" if override and document else None
        again = {f"retry:{document.id}": True} if document and not override else {}
        _back_to_pending(db, item, "spreading", user, **({key: override} if key else {}), **again)
        return
    if decision == "key_by_hand":
        # the figures are keyed through the facts route in whole dollars, and nothing is taken as
        # absent: the footing checks decide whether the spread is complete
        cycle = _cycle(db, item)
        period = {"period_end": cycle.period_end.isoformat(), "months": cycle.months} if cycle is not None else {}
        context = {"scale": 1, "absent": [], **period, **context}
    if "scale" not in context or "period_end" not in context:
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
        for line in template.template_lines(borrower.template_id):
            stated = current_fact(db, borrower.id, template.STATED_PREFIX + line.key, period_end,
                                  months if line.flow else 0) if line.computed else None
            if stated is not None and current_fact(db, borrower.id, line.key, period_end,
                                                   months if line.flow else 0) is None:
                add_fact(db, borrower_id=borrower.id, key=line.key, period_end=period_end,
                         months=months if line.flow else 0, value=Decimal(stated.value), kind="manual",
                         entered_by=user.id, reason=f"total accepted as reported: {reason}",
                         document_id=stated.document_id, page=stated.page, actor=("user", str(user.id)))
        return
    # If the figures still do not foot, or a line is missing, this raises the footing question
    # for a person; the decision itself is never refused for that.
    result = spreading.finalize_spread(db, borrower=borrower, document=document, period_end=period_end, months=months,
                                       scale=context["scale"], absent=context.get("absent", []),
                                       cycle=_cycle(db, item))
    if result.status == "spread":
        from app.domain import corrections
        corrections.refresh_after_repair(db, borrower, period_end)


def on_cannot_test_decision(db, item, user, decision: str, reason: str) -> None:
    """A covenant, or a whole loan, could not be tested.

    `not_applicable` is a named person's judgement: it needs a reason and is recorded against the
    test. `input_provided` and `terms_approved` say that what was missing is now on file; code
    checks by running the tests again, and asks again if the test still cannot be run."""
    from app.domain import corrections
    from app.domain.covenant_service import run_covenant_tests

    reference = item.evidence.get("covenant_test_id")
    test = db.get(CovenantTest, uuid.UUID(reference)) if reference else None
    if test is None:
        raise ValueError("the covenant test behind this item no longer exists")
    if decision == "not_applicable":
        if not reason.strip():
            raise ValueError("recording that a covenant test does not apply needs a reason")
        ledger.record(db, actor_type="user", actor_id=user.id, action="covenant.judged_not_applicable",
                      entity_type="covenant_test", entity_id=test.id,
                      payload={"covenant": test.covenant_id, "covenant_name": test.covenant_name,
                               "facility_id": test.facility_id, "period_end": test.period_end,
                               "outcome_left_as": test.outcome, "judged_by": user.name, "reason": reason,
                               "work_item_id": item.id})
        return
    borrower = db.get(Borrower, test.borrower_id)
    if test.covenant_id == "*":  # no terms were in force for the loan
        facility = db.get(Facility, test.facility_id)
        stages.retire_untestable_marker(db, facility, test.period_end)
        run_covenant_tests(db, borrower=borrower, facility=facility, period_end=test.period_end,
                           cycle=_cycle(db, item))
    else:
        corrections.refresh_after_repair(db, borrower, test.period_end)


def on_borrowing_base_decision(db, item, user, decision: str, reason: str) -> None:
    """`retry` reads the certificate again. When the certificate could not be read at all, asking
    the borrower to resubmit sets it aside and the stage waits for the new one. The other
    decisions are the bank's recorded response to a difference."""
    unread = "document_id" in item.evidence and "borrowing_base_review_id" not in item.evidence
    if decision == "retry":
        _back_to_pending(db, item, "borrowing_base", user)
    elif decision == "borrower_to_resubmit" and unread:
        _set_aside(db, _document(db, item), user, reason or decision)
        _back_to_pending(db, item, "borrowing_base", user, required=False)


def on_reading_review(db, item, user, decision: str, reason: str) -> None:
    """A person looked at a reading that passed every check. Confirming is their judgement, kept
    on the ledger against the document; asking for a new document sets this one aside and the
    stage waits for it."""
    document = _document(db, item)
    if decision == "request_new_document":
        _set_aside(db, document, user, reason or decision)
        if item.stage:
            _back_to_pending(db, item, item.stage, user)
        return
    ledger.record(db, actor_type="user", actor_id=user.id, action="reading.confirmed", entity_type="document",
                  entity_id=document.id if document is not None else item.id,
                  payload={"what": item.evidence.get("what"), "work_item_id": item.id, "confirmed_by": user.name})


workflow.DECISION_HOOKS["reading.review"] = on_reading_review
workflow.DECISION_HOOKS["terms.approval_needed"] = terms_service.on_decision
workflow.DECISION_HOOKS["review.commentary_approval"] = review_service.on_decision
workflow.DECISION_HOOKS["terms.unapproved_amendment"] = on_unapproved_amendment
workflow.DECISION_HOOKS["covenant.cannot_test"] = on_cannot_test_decision
workflow.DECISION_HOOKS["bb.certificate_mismatch"] = on_borrowing_base_decision

def on_spreadsheet_decision(db, item, user, decision: str, reason: str) -> None:
    """A spreadsheet no agent can read. A new document sets the sheet aside and queues the stage that met it. Keying
    by hand goes to that stage's own manual entry: the spread (spreading), the entered terms (a credit agreement
    or amendment) or the keyed certificate figures (covenant testing). A borrowing base has no manual entry."""
    document = _document(db, item)
    if decision == "request_new_document":
        _set_aside(db, document, user, reason or decision)
        if item.stage:
            _back_to_pending(db, item, item.stage, user, required=False)
        return
    if decision != "key_by_hand":
        raise ValueError(f"{decision} is not a response to an unreadable spreadsheet")
    if item.stage == "spreading":
        return on_spread_decision(db, item, user, "key_by_hand", reason)
    if item.stage == "covenant_testing" and document is not None and document.doc_type in ("credit_agreement", "amendment"):
        return on_terms_extraction_decision(db, item, user, "board_by_hand", reason)
    if item.stage == "covenant_testing":
        return _certificate_keyed_by_hand(db, item, user, document)
    raise ValueError("figures from this kind of spreadsheet cannot be keyed by hand here; request a new document")


def _certificate_keyed_by_hand(db, item, user, document) -> None:
    """The certificate figures are keyed through the facts route; the covenants are then tested again."""
    from app.domain.covenant_service import run_covenant_tests

    cycle = _cycle(db, item)
    if cycle is None:
        raise ValueError("this item is not part of an open monitoring cycle")
    keyed = db.execute(select(Fact.id).where(
        Fact.borrower_id == item.borrower_id, Fact.period_end == cycle.period_end, Fact.key.like("cert.%"),
        Fact.kind == "manual", Fact.status.notin_(("rejected", "superseded"))
    ).limit(1)).first()
    if keyed is None:
        raise ValueError("no certificate figure has been keyed by hand for this period. Enter "
                         "them first (POST /facts), then record this decision")
    facility = db.get(Facility, item.facility_id) if item.facility_id else None
    if facility is None:
        facility = db.execute(select(Facility).where(Facility.borrower_id == item.borrower_id)).scalars().first()
    if facility is not None:
        run_covenant_tests(db, borrower=db.get(Borrower, item.borrower_id), facility=facility,
                           period_end=cycle.period_end, cycle=cycle)


workflow.DECISION_HOOKS["document.spreadsheet_unreadable"] = on_spreadsheet_decision

for _type in ("spread.value_unverified", "spread.does_not_foot", "spread.image_only"):
    workflow.DECISION_HOOKS[_type] = on_spread_decision

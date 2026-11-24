"""Squad gathers what the officer asked for when returning a case. Code matches, no model is called:
- a need is a document type and a month end, stored in the `work_item.returned` ledger payload (`needs`);
- exactly one document of the client with that type and period that a person or the system classified is attached
  by Squad (`work_item.evidence_attached`, actor system/squad, with `matched_need`);
- no document: a draft request to the client, one per need; the analyst sends it as any draft;
- several documents, or one an agent classified and nobody confirmed: Squad asks the case's holder which
  (a question, topic `evidence_match`); the case cannot be sent back while it is open.
Every step is idempotent: running again attaches nothing twice and raises no second question or draft."""
import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.ledger import LedgerEvent
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.routing import MATCH_TOPIC, attached_ids
from app.domain.workflow import ATTACHED, RETURNED, latest_hand_off

NONE_OF_THESE = "none"
MAX_OPTIONS = 5  # a question offers at most six options, one of them "None of these"
CONFIDENT_SOURCES = ("person", "system")
RULE = "doc_type+period_end"

log = logging.getLogger(__name__)
COULD_NOT_GATHER = "Squad could not gather; please attach by hand"
GATHERING_FAILED = "work_item.gathering_failed"

NeedState = dict[str, Any]


def _month_words(period: date) -> str:
    return period.strftime("%B %Y")


def need_words(need: dict[str, Any]) -> str:
    from app.squad.words import document_type_words

    return f"{document_type_words(need['doc_type'])}, {_month_words(date.fromisoformat(need['period_end']))}"


def _asked(need: dict[str, Any]) -> str:
    from app.squad.words import document_type_words

    return f"{document_type_words(need['doc_type'])} for {_month_words(date.fromisoformat(need['period_end']))}"


def latest_return(db: Session, item: WorkItem) -> LedgerEvent | None:
    return db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id), LedgerEvent.action == RETURNED)
        .order_by(LedgerEvent.seq.desc()).limit(1)).scalar_one_or_none()


def _needs_of(ret: LedgerEvent | None) -> list[dict[str, Any]]:
    return list((ret.payload or {}).get("needs") or []) if ret is not None else []


def _attachments(db: Session, item: WorkItem) -> list[LedgerEvent]:
    return list(db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id), LedgerEvent.action == ATTACHED)
        .order_by(LedgerEvent.seq)).scalars())


def _met_by(db: Session, need: dict[str, Any], ret: LedgerEvent, attachments: list[LedgerEvent]) -> str | None:
    """The document that answers a need: attached after this return, for this need or of its type and period, and
    not set aside since. An attachment made before the return, or of a rejected document, answers nothing."""
    for e in attachments:
        if e.seq <= ret.seq:
            continue
        p = e.payload or {}
        doc = db.get(Document, uuid.UUID(str(p.get("document_id"))))
        if doc is None or doc.status == "rejected":
            continue
        if (p.get("matched_need") == need["index"] and p.get("return_seq") == ret.seq) or (
                doc.doc_type == need["doc_type"] and plain_date(doc.period_end) == need["period_end"]):
            return str(doc.id)
    return None


def plain_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _key(item: WorkItem, ret: LedgerEvent, need: dict[str, Any]) -> str:
    return f"{item.id}:{ret.seq}:{need['index']}"


def _questions(db: Session, item: WorkItem, key: str) -> list[WorkItem]:
    return [q for q in db.execute(select(WorkItem).where(
        WorkItem.borrower_id == item.borrower_id, WorkItem.item_type == "question")).scalars()
        if (q.evidence or {}).get("topic") == MATCH_TOPIC and (q.evidence or {}).get("need_key") == key]


def _requests(db: Session, item: WorkItem, key: str) -> list[LedgerEvent]:
    return list(db.execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "draft", LedgerEvent.action == "draft.created",
        LedgerEvent.payload["work_item_id"].astext == str(item.id),
        LedgerEvent.payload["need_key"].astext == key)).scalars())


def _live_requests(db: Session, item: WorkItem, key: str) -> list[LedgerEvent]:
    """Requests that still stand: a withdrawn one is history, not a request."""
    from app.squad import drafts

    return [e for e in _requests(db, item, key)
            if drafts.get_draft(db, uuid.UUID(e.entity_id))["status"] != "withdrawn"]


def _state(db: Session, item: WorkItem, ret: LedgerEvent, need: dict[str, Any],
           attachments: list[LedgerEvent]) -> NeedState:
    base = {"index": need["index"], "doc_type": need["doc_type"], "period_end": need["period_end"],
            "words": need_words(need), "document_id": None, "question_id": None, "draft_id": None}
    met = _met_by(db, need, ret, attachments)
    key = _key(item, ret, need)
    questions = _questions(db, item, key)
    drafts_ = _live_requests(db, item, key)
    if met:
        return {**base, "state": "attached", "state_words": f"Attached: {base['words']}", "document_id": met}
    open_q = next((q for q in questions if q.status == "open"), None)
    if open_q is not None:
        return {**base, "state": "waiting_for_you", "state_words": "Waiting for you to confirm",
                "question_id": str(open_q.id)}
    if drafts_:
        return {**base, "state": "requested_from_client", "state_words": "Asked the client",
                "draft_id": drafts_[0].entity_id}
    return {**base, "state": "not_gathered", "state_words": COULD_NOT_GATHER}


def need_states(db: Session, item: WorkItem) -> list[NeedState]:
    """What each need of the latest return stands at. Read only."""
    ret = latest_return(db, item)
    attachments = _attachments(db, item)
    return [_state(db, item, ret, n, attachments) for n in _needs_of(ret)]


def _candidates(db: Session, item: WorkItem, need: dict[str, Any]) -> list[Document]:
    taken = attached_ids(db, item)
    refused = {o["document_id"] for q in _earlier_none(db, item, need)
               for o in (q.evidence or {}).get("options", []) if q.decision == NONE_OF_THESE and o.get("document_id")}
    docs = db.execute(select(Document).where(
        Document.borrower_id == item.borrower_id, Document.doc_type == need["doc_type"],
        Document.period_end == date.fromisoformat(need["period_end"]), Document.status != "rejected")
        .order_by(Document.created_at.desc())).scalars()
    return [d for d in docs if str(d.id) not in taken and str(d.id) not in refused]


def _earlier_none(db: Session, item: WorkItem, need: dict[str, Any]) -> list[WorkItem]:
    """Questions of earlier asks about the same document type and month on this case that were answered "none"."""
    return [q for q in db.execute(select(WorkItem).where(
        WorkItem.borrower_id == item.borrower_id, WorkItem.item_type == "question", WorkItem.status == "decided")).scalars()
        if (q.evidence or {}).get("topic") == MATCH_TOPIC and (q.evidence or {}).get("case_id") == str(item.id)
        and (q.evidence or {}).get("doc_type") == need["doc_type"]
        and (q.evidence or {}).get("period_end") == need["period_end"]]


def _holder_name(db: Session, user_id: Any) -> str:
    user = db.get(User, uuid.UUID(str(user_id))) if user_id else None
    return user.name if user else "the credit officer"  # read mid-sentence: "…that the credit officer asked for"


def _attach(db: Session, item: WorkItem, ret: LedgerEvent, need: dict[str, Any], doc: Document,
            actor: tuple[str, str], note: str, rule: str | None = None) -> None:
    payload = {"borrower_id": item.borrower_id, "document_id": doc.id, "note": note[:500],
               "matched_need": need["index"], "return_seq": ret.seq}
    if rule:
        payload["rule"] = rule
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action=ATTACHED, entity_type="work_item",
                  entity_id=item.id, payload=payload)
    _withdraw_requests(db, item, ret, need)


def _withdraw_requests(db: Session, item: WorkItem, ret: LedgerEvent, need: dict[str, Any]) -> None:
    """The document is here, so a request made earlier for it is no longer needed. It is marked, never sent."""
    from app.squad import drafts

    for event in _requests(db, item, _key(item, ret, need)):
        if drafts.get_draft(db, uuid.UUID(event.entity_id))["status"] == "draft":
            drafts.withdraw_draft(db, uuid.UUID(event.entity_id))


def _ensure_request(db: Session, item: WorkItem, ret: LedgerEvent, need: dict[str, Any]) -> None:
    key = _key(item, ret, need)
    if _live_requests(db, item, key):
        return
    from app.domain.credit import Borrower
    from app.squad import drafts

    borrower = db.get(Borrower, item.borrower_id)
    what = _asked(need)
    drafts.create_draft(
        db, borrower_id=item.borrower_id, to=(borrower.profile or {}).get("contact_email") or f"{borrower.name} team",
        subject=what, body=f"Could you send the {what} when you have a moment?", kind="evidence_request",
        work_item_id=item.id, extra={"need_key": key, "need_index": need["index"]})


def _option_label(doc: Document) -> str:
    received = doc.received_date or doc.created_at.date()
    pages = f"{doc.page_count} page" + ("" if doc.page_count == 1 else "s")
    return f"{doc.title}, {pages}, received {received.day} {received.strftime('%B %Y')}"


def _ask(db: Session, item: WorkItem, ret: LedgerEvent, need: dict[str, Any], docs: list[Document]) -> None:
    from app.squad.questions import raise_question

    shown = docs[:MAX_OPTIONS]
    options = [{"id": f"doc_{d.id.hex}", "label": _option_label(d), "evidence": ""} for d in shown]
    options.append({"id": NONE_OF_THESE, "label": "None of these", "evidence": ""})
    officer = _holder_name(db, ret.actor_id)
    words = _asked(need)
    q = raise_question(
        db, borrower_id=item.borrower_id, title=f"Which {words}?",
        question=f"Which document is the {words} that {officer} asked for?", options=options, topic=MATCH_TOPIC,
        assigned_to=item.assigned_to,  # in the raise itself, so the ledger says whose question it is
        actor=("system", "squad"), written_by_code=True,  # labels are built here from stored fields, never by a model
        evidence={"case_id": str(item.id), "need_key": _key(item, ret, need), "need_index": need["index"],
                  "doc_type": need["doc_type"], "period_end": need["period_end"],
                  "option_documents": {o["id"]: str(d.id) for o, d in zip(options, shown, strict=False)}})
    # each option also names its document, so a refused ("None of these") ask is remembered
    q.evidence = {**q.evidence, "options": [{**o, "document_id": str(d.id)} if d is not None else o
                                            for o, d in zip(q.evidence["options"], [*shown, None], strict=True)]}
    db.flush()


def _gather_need(db: Session, item: WorkItem, ret: LedgerEvent, need: dict[str, Any], officer: str) -> None:
    if _met_by(db, need, ret, _attachments(db, item)):
        _withdraw_requests(db, item, ret, need)  # met by hand: the request is no longer needed
        return
    if any(q.status == "open" for q in _questions(db, item, _key(item, ret, need))):
        return  # waiting for the person; a new document does not change the question under them
    found = _candidates(db, item, need)
    if len(found) == 1 and found[0].doc_type_source in CONFIDENT_SOURCES:
        _attach(db, item, ret, need, found[0], ("system", "squad"),
                f"Attached the {_asked(need)} that {officer} asked for.", rule=RULE)
    elif not found:
        _ensure_request(db, item, ret, need)
    else:
        _ask(db, item, ret, need, found)


def gather_requested(db: Session, item: WorkItem) -> list[NeedState]:
    """Gather what the latest return asked for, then say where each need stands. Safe to run again."""
    # the ledger's lock first, as every writer takes it, then the case row: one gatherer per case at a time and no
    # lock-order inversion with a path that has already written to the ledger
    ledger.lock(db)
    db.execute(select(WorkItem.id).where(WorkItem.id == item.id).with_for_update())
    ret = latest_return(db, item)
    if item.status == "open" and ret is not None:
        officer = _holder_name(db, ret.actor_id)
        for need in _needs_of(ret):
            _gather_need(db, item, ret, need, officer)
    return need_states(db, item)


def gather_safely(db: Session, item: WorkItem) -> bool:
    """Gather without ever failing the caller: a failure is undone, logged and recorded in plain words on the case,
    and the needs read "Squad could not gather; please attach by hand"."""
    try:
        with db.begin_nested():
            gather_requested(db, item)
        return True
    except Exception:  # noqa: BLE001 - gathering is an aid; the return and the intake stage must stand without it
        log.exception("gathering failed for work item %s", item.id)
        ledger.record(db, actor_type="system", actor_id="squad", action=GATHERING_FAILED, entity_type="work_item",
                      entity_id=item.id, payload={"borrower_id": item.borrower_id, "reason": COULD_NOT_GATHER + "."})
        db.flush()
        return False


def gather_for_borrower(db: Session, borrower_id: uuid.UUID) -> int:
    """After a document of this client is classified: gather for every open case now sitting returned with needs."""
    n = 0
    for item in db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower_id, WorkItem.status == "open")).scalars():
        last = latest_hand_off(db, item)
        if last is not None and last.action == RETURNED and (last.payload or {}).get("needs"):
            gather_safely(db, item)
            n += 1
    return n


def refuse_unless_holder(db: Session, question: WorkItem, user: User) -> None:
    """Only the person the case is with may say which document it is: the question is theirs to answer."""
    item = db.get(WorkItem, uuid.UUID((question.evidence or {})["case_id"]))
    if item is not None and item.status == "open" and item.assigned_to != user.id:
        holder = db.get(User, item.assigned_to) if item.assigned_to else None
        raise PermissionError(f"Only {holder.name if holder else 'the person the case is with'} can answer this: "
                              "the case is with them.")


def apply_match_answer(db: Session, question: WorkItem, user: User, option_id: str) -> None:
    """A person answered Squad's "which document" question: attach their choice, or, for "None of these", look again
    and ask the client only if nothing else is on file. The person is the actor of the attachment, and their choice
    confirms the document's type for next time."""
    ev = question.evidence or {}
    item = db.get(WorkItem, uuid.UUID(ev["case_id"]))
    ret = latest_return(db, item) if item is not None else None
    if item is None or item.status != "open" or ret is None:
        return
    need = next((n for n in _needs_of(ret) if n["index"] == ev.get("need_index")), None)
    if need is None or ev.get("need_key") != _key(item, ret, need):
        return  # this question belongs to an earlier return
    if option_id == NONE_OF_THESE:
        _gather_need(db, item, ret, need, _holder_name(db, ret.actor_id))
        return
    doc = db.get(Document, uuid.UUID(ev["option_documents"][option_id]))
    if doc is None or doc.borrower_id != item.borrower_id:
        raise ValueError("That document is not on this client's file.")
    if doc.status == "rejected":
        raise ValueError("That document has been set aside; choose another, or None of these.")
    if str(doc.id) not in attached_ids(db, item):
        _attach(db, item, ret, need, doc, ("user", str(user.id)), f"Confirmed as the {_asked(need)}.")
    if doc.doc_type_source != "person":
        doc.doc_type_source = "person"
        ledger.record(db, actor_type="user", actor_id=user.id, action="document.classified", entity_type="document",
                      entity_id=doc.id, payload={"borrower_id": doc.borrower_id, "doc_type": doc.doc_type,
                                                 "period_end": doc.period_end, "confirmed_by_person": True})

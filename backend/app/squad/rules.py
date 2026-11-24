"""The one rule for "this is yours", shared by the briefing, the thread, the case view and Approvals, so a count and a
button can never disagree. Whether a person may decide is the engine's answer (`workflow.decision_refusal`, which
holds the rule that an analyst acts only on her own clients' cases); this module adds only whose turn it is
(assignment, an approver's permission, a return) and the words for it."""
from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.core.ledger import LedgerEvent
from app.core.roles import APPROVER_PERMISSIONS, Permission, Role, SecondPersonRequired, can
from app.domain import workflow
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.work_items import offered


def _refusal(user: User, item: WorkItem) -> Exception | None:
    return workflow.decision_refusal(object_session(item), item, user_id=user.id, user_role=user.role)


def holds_permission(user: User, item: WorkItem) -> bool:
    """For an open item: the person's role holds the permission the item needs."""
    try:
        return can(user.role, Permission(item.required_permission))
    except ValueError:  # an unknown permission is nobody's to act on
        return False


def prepared_by(user: User, item: WorkItem) -> bool:
    """The person prepared the item, or sent it for a decision with their view."""
    return item.prepared_by_id == str(user.id) or str(user.id) in workflow.routed_by(object_session(item), item)


def second_person_blocked(user: User, item: WorkItem) -> bool:
    return isinstance(_refusal(user, item), SecondPersonRequired)


def is_clients_analyst(user: User, borrower: Borrower) -> bool:
    """The engine's answer (`workflow.analyst_owns_client`): the client is this analyst's, or has no analyst yet."""
    return workflow.analyst_owns_client(user.id, user.role, borrower)


# A decision that only sends the work back to whoever wrote it does not, on its own, make a case wait for this person:
# the last editor of commentary may return it for rework but is not the approval it waits for.
SENDS_BACK = frozenset({"return_for_rework"})


def permitted_decisions(user: User, item: WorkItem) -> list[str]:
    """The offered decisions the engine would accept from this person (reason rule aside: a reason is typed later)."""
    db = object_session(item)
    return [d for d in offered(item.item_type, item.allowed_decisions)
            if workflow.decision_refusal(db, item, user_id=user.id, user_role=user.role, decision=d) is None]


def can_act(user: User, item: WorkItem, borrower: Borrower | None = None) -> bool:
    """The engine would accept at least one offered decision from this person. Nothing else: who owns a client is the
    engine's rule (`workflow.owner_refusal`), not this module's."""
    return bool(permitted_decisions(user, item))


def yours(user: User, item: WorkItem, borrower: Borrower) -> bool:
    """Waiting for this person: the engine accepts a decision from them that is not only a send-back, and it is their
    turn. For an analyst the engine's ownership rule already says whose turn it is. For other roles it is theirs when
    it is assigned or routed to them, or, assigned to no one, when it needs an approver's permission
    (`APPROVER_PERMISSIONS`) or its client has no analyst: an analyst's judgement on her own client is not counted
    for every officer, portfolio manager and administrator."""
    if not [d for d in permitted_decisions(user, item) if d not in SENDS_BACK]:
        return False
    if user.role == Role.ANALYST.value:
        return True
    if item.assigned_to is not None:
        return str(item.assigned_to) == str(user.id)
    return item.required_permission in APPROVER_PERMISSIONS or borrower is None or borrower.analyst_id is None


def awaits_reroute(user: User, item: WorkItem) -> bool:
    """A case returned to the person who routed it: theirs to answer and send back. Only a return makes it so (the
    latest routed-or-returned event on the ledger is a return to them), never a plain assignment."""
    if item.status != "open" or item.assigned_to != user.id:
        return False
    last = object_session(item).execute(select(LedgerEvent).where(
        LedgerEvent.entity_type == "work_item", LedgerEvent.entity_id == str(item.id),
        LedgerEvent.action.in_((workflow.ROUTED, workflow.RETURNED))).order_by(LedgerEvent.seq.desc()).limit(1)
    ).scalar_one_or_none()
    return last is not None and last.action == workflow.RETURNED and \
        str((last.payload or {}).get("returned_to")) == str(user.id)


def needs(user: User, item: WorkItem, borrower: Borrower) -> bool:
    """Counted as needing this person: theirs to decide, or theirs to answer and send back."""
    return yours(user, item, borrower) or awaits_reroute(user, item)


def state_words(item: WorkItem, names: dict[str, str], borrower: Borrower | None = None) -> str:
    """Where an open case stands for someone who cannot act on it."""
    if item.assigned_to:
        return f"With {names.get(str(item.assigned_to), 'a colleague')}"
    if item.required_permission == Permission.DECIDE_BREACH.value:
        return "Not yet sent to a credit officer, who decides it"
    if borrower is not None and borrower.analyst_id:
        return f"With {names.get(str(borrower.analyst_id), 'the client’s analyst')}"
    return "Open"

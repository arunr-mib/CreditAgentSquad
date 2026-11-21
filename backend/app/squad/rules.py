"""The one rule for "this is yours", shared by the briefing, the thread, the case view and Approvals, so a count and a
button can never disagree. Whether a person may decide is the engine's answer (`workflow.decision_refusal`); this
module adds only whose turn it is (assignment, the client's analyst, a return) and the words for it."""
from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.core.ledger import LedgerEvent
from app.core.roles import Permission, Role, SecondPersonRequired
from app.domain import workflow
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User


def _refusal(user: User, item: WorkItem) -> Exception | None:
    return workflow.decision_refusal(object_session(item), item, user_id=user.id, user_role=user.role)


def holds_permission(user: User, item: WorkItem) -> bool:
    """For an open item: the person's role holds the permission the item needs."""
    return not isinstance(_refusal(user, item), PermissionError)


def prepared_by(user: User, item: WorkItem) -> bool:
    """The person prepared the item, or sent it for a decision with their view."""
    return item.prepared_by_id == str(user.id) or str(user.id) in workflow.routed_by(object_session(item), item)


def second_person_blocked(user: User, item: WorkItem) -> bool:
    return isinstance(_refusal(user, item), SecondPersonRequired)


def is_clients_analyst(user: User, borrower: Borrower) -> bool:
    """An analyst owns a client's open work when the client is theirs or has no analyst yet."""
    return user.role == Role.ANALYST.value and borrower.analyst_id in (None, user.id)


def can_act(user: User, item: WorkItem, borrower: Borrower) -> bool:
    """The engine lets them decide it, and it is theirs: assigned to them, or unassigned and, for an analyst, on a
    client that is theirs (or has no analyst). Other roles are not split by client."""
    if _refusal(user, item) is not None:
        return False
    if item.assigned_to is not None:
        return item.assigned_to == user.id
    return user.role != Role.ANALYST.value or is_clients_analyst(user, borrower)


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
    return can_act(user, item, borrower) or awaits_reroute(user, item)


def state_words(item: WorkItem, names: dict[str, str], borrower: Borrower | None = None) -> str:
    """Where an open case stands for someone who cannot act on it."""
    if item.assigned_to:
        return f"With {names.get(str(item.assigned_to), 'a colleague')}"
    if item.required_permission == Permission.DECIDE_BREACH.value:
        return "With the credit officer"
    if borrower is not None and borrower.analyst_id:
        return f"With {names.get(str(borrower.analyst_id), 'the client’s analyst')}"
    return "Open"

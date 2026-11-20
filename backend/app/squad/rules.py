"""The one rule for "this is yours to decide", shared by the briefing and the thread so a count and a button
can never disagree. A person can act on an open item when they hold its permission, are not the preparer of
an item that needs a second person, and it is unassigned or assigned to them."""
from app.core.roles import Permission, Role, can
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User


def holds_permission(user: User, item: WorkItem) -> bool:
    try:
        return can(user.role, Permission(item.required_permission))
    except ValueError:  # an unknown permission is nobody's to act on
        return False


def prepared_by(user: User, item: WorkItem) -> bool:
    return item.prepared_by_id == str(user.id)


def second_person_blocked(user: User, item: WorkItem) -> bool:
    return item.requires_second_person and prepared_by(user, item)


def is_clients_analyst(user: User, borrower: Borrower) -> bool:
    """An analyst owns a client's open work when the client is theirs or has no analyst yet."""
    return user.role == Role.ANALYST.value and borrower.analyst_id in (None, user.id)


def can_act(user: User, item: WorkItem, borrower: Borrower) -> bool:
    """Open, permitted, not the preparer of a second-person item, and theirs: assigned to them, or unassigned and,
    for an analyst, on a client that is theirs (or has no analyst). Other roles are not split by client."""
    if not (item.status == "open" and holds_permission(user, item) and not second_person_blocked(user, item)):
        return False
    if item.assigned_to is not None:
        return item.assigned_to == user.id
    return user.role != Role.ANALYST.value or is_clients_analyst(user, borrower)


def state_words(item: WorkItem, names: dict[str, str]) -> str:
    """Where an open case stands for someone who cannot act on it."""
    if item.assigned_to:
        return f"With {names.get(str(item.assigned_to), 'a colleague')}"
    if item.required_permission == Permission.DECIDE_BREACH.value:
        return "With the credit officer"
    return "Open"

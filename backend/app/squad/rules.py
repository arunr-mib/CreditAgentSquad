"""The one rule for "this is yours to decide", shared by the briefing and the thread so a count and a button
can never disagree. A person can act on an open item when they hold its permission, are not the preparer of
an item that needs a second person, and it is unassigned or assigned to them."""
from app.core.roles import Permission, can
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


def can_act(user: User, item: WorkItem) -> bool:
    return (item.status == "open" and holds_permission(user, item) and not second_person_blocked(user, item)
            and item.assigned_to in (None, user.id))


def state_words(item: WorkItem, names: dict[str, str]) -> str:
    """Where an open case stands for someone who cannot act on it."""
    if item.assigned_to:
        return f"With {names.get(str(item.assigned_to), 'a colleague')}"
    if item.required_permission == Permission.DECIDE_BREACH.value:
        return "With the credit officer"
    return "Open"

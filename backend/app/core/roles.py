"""Roles and the permission table. Every permission check goes through `can()`."""
from enum import StrEnum


class Role(StrEnum):
    ANALYST = "analyst"
    PORTFOLIO_MANAGER = "portfolio_manager"
    CREDIT_OFFICER = "credit_officer"
    CREDIT_ADMIN = "credit_admin"
    CREDIT_REVIEW = "credit_review"
    ADMIN = "admin"


class Permission(StrEnum):
    VIEW = "view"
    UPLOAD_DOCUMENT = "upload_document"
    CONFIRM_SPREAD = "confirm_spread"
    PREPARE_TERMS = "prepare_terms"
    APPROVE_TERMS = "approve_terms"
    DECIDE_WORK_ITEM = "decide_work_item"
    DECIDE_BREACH = "decide_breach"
    EDIT_COMMENTARY = "edit_commentary"
    APPROVE_COMMENTARY = "approve_commentary"
    MANAGE_ACTIONS = "manage_actions"
    RELEASE_PACKAGE = "release_package"
    RECORD_QA_FINDING = "record_qa_finding"
    CHANGE_POLICY = "change_policy"
    MANAGE_USERS = "manage_users"
    RUN_AGENTS = "run_agents"
    ADVANCE_CLOCK = "advance_clock"


P = Permission
_GRANTS: dict[Role, frozenset[Permission]] = {
    Role.ANALYST: frozenset({
        P.VIEW, P.UPLOAD_DOCUMENT, P.CONFIRM_SPREAD, P.PREPARE_TERMS, P.DECIDE_WORK_ITEM,
        P.EDIT_COMMENTARY, P.MANAGE_ACTIONS, P.RUN_AGENTS,
    }),
    Role.PORTFOLIO_MANAGER: frozenset({
        P.VIEW, P.UPLOAD_DOCUMENT, P.DECIDE_WORK_ITEM, P.EDIT_COMMENTARY, P.APPROVE_COMMENTARY,
        P.MANAGE_ACTIONS, P.RELEASE_PACKAGE, P.RUN_AGENTS,
    }),
    Role.CREDIT_OFFICER: frozenset({
        P.VIEW, P.APPROVE_TERMS, P.DECIDE_WORK_ITEM, P.DECIDE_BREACH, P.APPROVE_COMMENTARY,
        P.MANAGE_ACTIONS, P.RELEASE_PACKAGE,
    }),
    Role.CREDIT_ADMIN: frozenset({
        P.VIEW, P.UPLOAD_DOCUMENT, P.PREPARE_TERMS, P.APPROVE_TERMS, P.DECIDE_WORK_ITEM,
        P.MANAGE_ACTIONS, P.RUN_AGENTS,
    }),
    Role.CREDIT_REVIEW: frozenset({P.VIEW, P.RECORD_QA_FINDING}),
    # Segregation of duties: the administrator runs the system (people, policy, the demonstration
    # clock) and takes no credit decision, so no one login can change a rule and then act under it.
    Role.ADMIN: frozenset({P.VIEW, P.CHANGE_POLICY, P.MANAGE_USERS, P.ADVANCE_CLOCK}),
}


def can(role: Role | str, permission: Permission) -> bool:
    try:
        return permission in _GRANTS[Role(role)]
    except ValueError:
        return False


# Decisions that belong to an approver rather than to the analyst who works the client. The one list the Approvals
# screen is built from; the server tells the browser whether to offer the screen (the briefing's `approvals`).
APPROVER_PERMISSIONS = frozenset({Permission.DECIDE_BREACH, Permission.APPROVE_TERMS, Permission.APPROVE_COMMENTARY})


def approves(role: Role | str) -> bool:
    return any(can(role, p) for p in APPROVER_PERMISSIONS)


class SecondPersonRequired(Exception):
    """Raised when the approver is the same person who prepared the work."""


def require_second_person(preparer_id, approver_id, message: str | None = None) -> None:
    """Four-eyes rule: an approval must come from a different authenticated user. The preparer is
    whoever last prepared or edited what is being approved. Ids are compared as text without
    regard to case, so the same person is recognised however the id was stored."""
    if preparer_id is None or approver_id is None or str(preparer_id).lower() == str(approver_id).lower():
        raise SecondPersonRequired(message or "This approval must come from a different person than the preparer.")

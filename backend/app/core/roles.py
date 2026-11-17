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
    Role.ADMIN: frozenset(Permission),
}


def can(role: Role | str, permission: Permission) -> bool:
    try:
        return permission in _GRANTS[Role(role)]
    except ValueError:
        return False


class SecondPersonRequired(Exception):
    """Raised when the approver is the same person who prepared the work."""


def require_second_person(preparer_id, approver_id) -> None:
    """Four-eyes rule: an approval must come from a different authenticated user."""
    if preparer_id is None or approver_id is None or str(preparer_id) == str(approver_id):
        raise SecondPersonRequired("This approval must come from a different person than the preparer.")

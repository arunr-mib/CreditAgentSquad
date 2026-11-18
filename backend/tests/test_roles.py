import uuid

import pytest
from app.core.roles import Permission, Role, SecondPersonRequired, can, require_second_person


def test_analyst_prepares_but_cannot_approve_terms():
    assert can(Role.ANALYST, Permission.PREPARE_TERMS)
    assert not can(Role.ANALYST, Permission.APPROVE_TERMS)


def test_credit_review_is_read_only_plus_findings():
    granted = {p for p in Permission if can(Role.CREDIT_REVIEW, p)}
    assert granted == {Permission.VIEW, Permission.RECORD_QA_FINDING}


def test_only_credit_officer_decides_breaches():
    assert {r for r in Role if can(r, Permission.DECIDE_BREACH)} == {Role.CREDIT_OFFICER}


def test_the_administrator_runs_the_system_and_takes_no_credit_decision():
    granted = {p for p in Permission if can(Role.ADMIN, p)}
    assert granted == {Permission.VIEW, Permission.CHANGE_POLICY, Permission.MANAGE_USERS, Permission.ADVANCE_CLOCK}
    # and nobody else can change the rules, manage people or move the clock
    for permission in (Permission.CHANGE_POLICY, Permission.MANAGE_USERS, Permission.ADVANCE_CLOCK):
        assert {r for r in Role if can(r, permission)} == {Role.ADMIN}


def test_unknown_role_has_no_permissions():
    assert not can("intern", Permission.VIEW)


def test_second_person_rule():
    a, b = uuid.uuid4(), uuid.uuid4()
    require_second_person(a, b)
    with pytest.raises(SecondPersonRequired):
        require_second_person(a, a)
    with pytest.raises(SecondPersonRequired):
        require_second_person(None, b)

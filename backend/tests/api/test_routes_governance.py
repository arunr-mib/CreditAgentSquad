"""The role and permission table, the policy register and the run fields the timeline reads."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.agents import covenant
from app.api.routes_governance import PERMISSIONS, SECOND_PERSON, signal_trigger
from app.calc import signals
from app.core.config import get_settings
from app.core.roles import _GRANTS, Permission, Role, can
from app.domain import covenant_service
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.seed_users import seed_users

ROLES = ["analyst", "portfolio_manager", "credit_officer", "credit_admin", "credit_review", "admin"]


@pytest.fixture()
def people(db, client):
    seed_users(db, password="pw")
    r = client.post("/api/v1/auth/login", json={"email": "ruth.calloway@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text  # credit review: the most restricted role can still read governance


def test_governance_requires_sign_in(client):
    for path in ("/governance/roles", "/governance/policy"):
        assert client.get("/api/v1" + path).status_code == 401


def test_the_six_roles_and_their_grants_come_from_the_permission_table(client, people):
    body = client.get("/api/v1/governance/roles").json()
    assert [r["id"] for r in body["roles"]] == ROLES
    assert [r["label"] for r in body["roles"]] == ["Credit analyst", "Portfolio manager", "Credit officer",
                                                    "Credit administration", "Credit review", "Administrator"]
    assert "credit_committee" not in body["grants"]
    # every permission is listed once, and the route adds none
    assert sorted(p["id"] for p in body["permissions"]) == sorted(p.value for p in Permission)
    # a known grant and a known non-grant
    assert "decide_breach" in body["grants"]["credit_officer"]
    assert "decide_breach" not in body["grants"]["analyst"]
    assert "approve_terms" not in body["grants"]["analyst"] and "prepare_terms" in body["grants"]["analyst"]
    assert body["grants"]["credit_review"] == ["view", "record_qa_finding"]
    # the whole table agrees with `can`, cell by cell
    for role in Role:
        for permission in Permission:
            assert (permission.value in body["grants"][role.value]) == can(role, permission)
    assert set(body["grants"]["admin"]) == {p.value for p in _GRANTS[Role.ADMIN]}


def test_people_are_counted_per_role(client, db, people):
    from app.domain.org import User
    from sqlalchemy import func, select

    body = client.get("/api/v1/governance/roles").json()
    for role in body["roles"]:
        counted = db.execute(select(func.count()).where(User.role == role["id"], User.is_active)).scalar()
        assert role["people"] == counted
    assert sum(r["people"] for r in body["roles"]) > 0


def test_the_second_person_rule_is_marked_on_the_approvals_it_binds(client, people):
    body = client.get("/api/v1/governance/roles").json()
    marked = {p["id"] for p in body["permissions"] if p["second_person"]}
    assert marked == {"approve_terms", "approve_commentary"} == {p.value for p in SECOND_PERSON}
    assert [a["permission"] for a in body["second_person"]["applies_to"]] == ["approve_terms", "approve_commentary"]
    assert "cannot approve their own work" in body["second_person"]["rule"]


def test_permission_labels_are_plain_words_for_every_permission():
    assert {p for p, _, _ in PERMISSIONS} == set(Permission)
    for _, label, group in PERMISSIONS:
        assert label and "_" not in label and group


def rules(body, section):
    return {r["id"]: r for s in body["sections"] if s["id"] == section for r in s["rules"]}


def test_the_policy_register_reads_its_figures_from_the_code_that_enforces_them(client, people, monkeypatch):
    body = client.get("/api/v1/governance/policy").json()
    limits = rules(body, "agent_limits")
    assert limits["margin_floor"]["setting"] == "15%" and covenant.POLICY.margin_floor_pct == Decimal("0.15")
    assert limits["step_cap"]["setting"] == f"{covenant.SPEC.max_exchanges} turns, {covenant.SPEC.max_steps} lookups"
    for phrase in covenant.POLICY.prohibited_phrases:
        assert phrase in limits["prohibited_phrases"]["effect"]
    tolerances = rules(body, "tolerances")
    assert tolerances["covenant_tolerance.ratio"]["setting"] == "0.005x"
    assert tolerances["covenant_tolerance.pct"]["setting"] == "0.05 points"
    assert set(covenant_service.DEFAULT_TOLERANCE) == {k.split(".")[1] for k in tolerances if k.startswith("covenant_")}
    versions = rules(body, "versions")
    assert versions["signals"]["setting"] == signals.SIGNALS_VERSION and versions["signals"]["kind"] == "ident"
    records = rules(body, "records")
    settings = get_settings()
    assert records["login_lockout"]["setting"] == (
        f"{settings.login_max_failures} failures in {settings.login_lockout_minutes} minutes")
    assert records["ledger_append_only"]["state"] in ("verified", "attention")
    for section in body["sections"]:
        for rule in section["rules"]:
            assert rule["rule"] and rule["setting"] and rule["effect"] and rule["source"].endswith(".py")


def test_the_reading_setting_shown_is_the_one_in_force(client, people, monkeypatch):
    for value, shown in (("assisted", "Assisted"), ("automatic", "Automatic")):
        monkeypatch.setenv("EXTRACTION_AUTONOMY", value)
        get_settings.cache_clear()
        body = client.get("/api/v1/governance/policy").json()
        assert rules(body, "people_decide")["extraction_autonomy"]["setting"] == shown
    monkeypatch.undo()
    get_settings.cache_clear()


def test_every_signal_rule_is_listed_with_its_own_threshold(client, people):
    body = client.get("/api/v1/governance/policy").json()
    listed = {r["id"]: r for r in body["signal_rules"]["rules"]}
    assert list(listed) == [r.id for r in signals.RULES]
    assert listed["covenant_headroom_low"]["trigger"] == "Headroom on a covenant below 10%"
    assert listed["leverage_increase"]["trigger"] == "Leverage up more than 0.5x on the same period a year earlier"
    assert listed["ebitda_margin_decline"]["trigger"] == (
        "EBITDA margin down more than 3 points on the same period a year earlier")
    assert listed["reporting_late"]["trigger"] == "A reporting requirement more than 15 days late"
    assert listed["net_loss"]["severity"] == "high"
    # a rule whose threshold changes in the table changes on the page
    moved = signals.SignalRule("covenant_headroom_low", "medium", "headroom_below", {"threshold": Decimal("0.125")})
    assert signal_trigger(moved) == "Headroom on a covenant below 12.5%"


def test_the_agent_versions_listed_are_the_ones_this_build_runs(client, people):
    body = client.get("/api/v1/governance/policy").json()
    by_name = {a["name"]: a for a in body["agents"]}
    assert by_name["covenant"]["version"] == covenant.SPEC.version
    assert by_name["covenant"]["max_steps"] == covenant.SPEC.max_steps
    assert by_name["covenant"]["prompt_sha256"] == covenant.SPEC.prompt_sha256()
    assert len(by_name) == len(body["agents"]) == 9


def test_a_run_says_whom_it_is_about_and_how_long_it_took(client, db, people):
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.", risk_rating=5)
    db.add(borrower)
    db.flush()
    started = datetime(2026, 11, 17, 14, 37, 0, tzinfo=UTC)
    finished = AgentRun(agent_name="covenant", agent_version="1", model="m", task="investigate_covenant_exception",
                        borrower_id=borrower.id, status="completed", created_at=started,
                        finished_at=started + timedelta(seconds=12, milliseconds=400),
                        guardrail_notes=[{"layer": "quotes", "check": "quote_not_on_page", "action": "claim_dropped",
                                          "detail": "x"}])
    running = AgentRun(agent_name="copilot", agent_version="1", model="m", task="answer_question", status="running",
                       created_at=started + timedelta(minutes=1))
    db.add_all([finished, running])
    db.flush()
    listed = {r["id"]: r for r in client.get("/api/v1/agent-runs").json()}
    row = listed[str(finished.id)]
    assert row["duration_ms"] == 12400 and row["borrower_code"] == "HTD" and row["borrower_name"] == borrower.name
    assert row["guardrail_notes"][0]["action"] == "claim_dropped"
    still = listed[str(running.id)]
    assert still["duration_ms"] is None and still["borrower_code"] is None and still["borrower_name"] is None
    detail = client.get(f"/api/v1/agent-runs/{finished.id}").json()
    assert detail["duration_ms"] == 12400 and detail["borrower_code"] == "HTD" and detail["steps"] == []

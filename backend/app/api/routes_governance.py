"""Governance, read-only: who may do what, and the rules code enforces without asking a model.

Nothing here is a second copy of a rule. The role table is read from `app.core.roles`, and every
figure in the policy register is read from the constant or setting the enforcing code uses, so
the page cannot say one thing while the code does another. The words around the figures are
written here; `source` names the module to read to check them.
"""
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents import (
    certificate,
    collateral,
    copilot,
    covenant,
    early_warning,
    intake,
    review,
    spreading,
    terms_agent,
)
from app.api.deps import current_user
from app.calc import expr, metrics, signals, template
from app.core import ledger
from app.core.config import MAX_UPLOAD_BYTES, get_settings
from app.core.db import get_db
from app.core.roles import _GRANTS, Permission, Role
from app.domain import collateral_service, covenant_service, work_items
from app.domain.org import User
from app.publishing import content

router = APIRouter(tags=["governance"])

P = Permission

ROLE_LABELS: dict[Role, str] = {
    Role.ANALYST: "Credit analyst",
    Role.PORTFOLIO_MANAGER: "Portfolio manager",
    Role.CREDIT_OFFICER: "Credit officer",
    Role.CREDIT_ADMIN: "Credit administration",
    Role.CREDIT_REVIEW: "Credit review",
    Role.ADMIN: "Administrator",
}

# The words the workspace already uses for a permission (frontend/src/domain/labels.ts), plus the
# five it had no words for. Grouped by the part of the work they belong to, in the order of the cycle.
PERMISSIONS: tuple[tuple[Permission, str, str], ...] = (
    (P.VIEW, "see the workspace", "Reading"),
    (P.UPLOAD_DOCUMENT, "file documents", "Documents and figures"),
    (P.CONFIRM_SPREAD, "confirm a spread", "Documents and figures"),
    (P.PREPARE_TERMS, "prepare terms", "Terms"),
    (P.APPROVE_TERMS, "approve terms", "Terms"),
    (P.DECIDE_WORK_ITEM, "decide work items", "Exceptions"),
    (P.DECIDE_BREACH, "decide the response to a breach", "Exceptions"),
    (P.EDIT_COMMENTARY, "write commentary", "Review"),
    (P.APPROVE_COMMENTARY, "approve commentary", "Review"),
    (P.MANAGE_ACTIONS, "manage actions", "Review"),
    (P.RELEASE_PACKAGE, "release a package", "Review"),
    (P.RECORD_QA_FINDING, "record a credit review finding", "Review"),
    (P.RUN_AGENTS, "run agents", "Agents"),
    (P.CHANGE_POLICY, "change policy", "Administration"),
    (P.MANAGE_USERS, "manage users", "Administration"),
    (P.ADVANCE_CLOCK, "set the simulated date", "Administration"),
)

# Where `require_second_person` is called with the permission that leads to it: approving terms
# (terms_service.approve_version, and the terms.approval_needed work item through
# workflow.decide_work_item) and approving a review's commentary (review_service).
SECOND_PERSON: dict[Permission, tuple[str, str, str]] = {
    P.APPROVE_TERMS: (
        "Loan terms",
        "The person who prepared a terms version cannot approve it. Until a different person does, the "
        "version governs no test.",
        "domain/terms_service.py",
    ),
    P.APPROVE_COMMENTARY: (
        "Review commentary",
        "Whoever last edited a section of the commentary cannot be the one who approves the review.",
        "domain/review_service.py",
    ),
}
SECOND_PERSON_RULE = (
    "A person cannot approve their own work. The rule compares the two people, not their roles, so it "
    "binds an administrator as it binds everyone else."
)


@router.get("/governance/roles")
def roles_and_permissions(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """The permission table as the code holds it: each role, each permission, and which role holds
    which. `people` counts the active users in a role."""
    people = dict(db.execute(select(User.role, func.count()).where(User.is_active).group_by(User.role)).all())
    return {
        "roles": [{"id": role.value, "label": ROLE_LABELS[role], "people": people.get(role.value, 0)} for role in Role],
        "permissions": [{"id": p.value, "label": label, "group": group, "second_person": p in SECOND_PERSON}
                        for p, label, group in PERMISSIONS],
        "grants": {role.value: [p.value for p, _, _ in PERMISSIONS if p in _GRANTS[role]] for role in Role},
        "second_person": {
            "rule": SECOND_PERSON_RULE,
            "applies_to": [{"permission": p.value, "what": what, "detail": detail, "source": source}
                           for p, (what, detail, source) in SECOND_PERSON.items()],
        },
    }


# ── The policy register ──────────────────────────────────────────────────────────────────────

def _num(value: Decimal | int) -> str:
    """A figure from code as plain digits: no exponent, no trailing zeros."""
    text = format(Decimal(value), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _pct(fraction: Decimal) -> str:
    return f"{_num(fraction * 100)}%"


def _rule(rule_id: str, rule: str, setting: str, effect: str, source: str, *, kind: str = "text",
          state: str | None = None) -> dict[str, Any]:
    """`kind` says how to set the setting in type ("ident" for a version or other identifier).
    `state` is "verified" where code checked the rule a moment ago and it holds, "attention" where
    it checked and it does not, and null for a rule that is simply always applied."""
    return {"id": rule_id, "rule": rule, "setting": setting, "effect": effect, "source": source,
            "kind": kind, "state": state}


_AUTONOMY = {
    "assisted": ("Assisted", "Every reading of statements, a compliance certificate or a borrowing base certificate "
                             "is confirmed by a person before the cycle goes on, even when it passed every check."),
    "automatic": ("Automatic", "A reading that passes every check is used without a person."),
}


def _people_decide() -> list[dict[str, Any]]:
    autonomy = get_settings().extraction_autonomy.strip().lower()
    # stages._review_reading skips the confirmation only for "automatic"; any other value is assisted
    setting, effect = _AUTONOMY["automatic" if autonomy == "automatic" else "assisted"]
    rows = [
        _rule("second_person", "A person cannot approve their own work", "Always",
              "An approval from the person who prepared the work is refused. The rule compares the two people, "
              "not their roles, so it binds an administrator as it binds everyone else.", "core/roles.py"),
        *[_rule(f"second_person.{p.value}", what, "Second person", detail, source)
          for p, (what, detail, source) in SECOND_PERSON.items()],
        _rule("extraction_autonomy", "Document readings", setting, effect, "domain/stages.py"),
        _rule("work_item_due", "Time to decide an exception",
              " · ".join(f"{severity.capitalize()} {days}" for severity, days in
                         sorted(work_items.DUE_BUSINESS_DAYS.items(), key=lambda kv: kv[1])) + " business days",
              "Each work item is due this many business days after it is raised, by its severity, counted from "
              "the workspace's date. A person may set a different date when assigning it.",
              "domain/work_items.py"),
    ]
    if covenant.POLICY.require_person:
        rows.append(_rule("require_person", "An agent recommends; a person decides", "Locked",
                          "A recommendation never records a decision. It is put to a person on a work item.",
                          "guardrails/policy.py"))
    return rows


def _agent_limits() -> list[dict[str, Any]]:
    policy = covenant.POLICY
    return [
        _rule("figures", "Figures in agent text", "Fact references only",
              "An agent writes a reference to a stored fact and code renders the figure. A figure that does not "
              "trace to a stored fact forces a retry, then an abstain.", "guardrails/narrative.py"),
        _rule("resolve_requires_evidence", "A recommendation to resolve", "Needs evidence",
              "It stands only with a passing governing calculation and at least one citation found on its page. "
              "Otherwise it becomes an escalate.", "guardrails/policy.py"),
        _rule("margin_floor", "Margin floor", _pct(policy.margin_floor_pct),
              "A resolve or a request becomes an escalate when the governing test misses its threshold by more "
              "than this share of the threshold.", "guardrails/policy.py"),
        _rule("step_cap", "Lookup allowance, covenant agent",
              f"{covenant.SPEC.max_exchanges} turns, {covenant.SPEC.max_steps} lookups",
              "When either is spent the agent is asked once for a final answer without tools. A resolve from "
              "such a run becomes an abstain.", "guardrails/policy.py"),
        _rule("prohibited_phrases", "Actions reserved for a person", f"{len(policy.prohibited_phrases)} phrases",
              "Agent text that proposes one becomes an escalate: " + ", ".join(policy.prohibited_phrases) + ".",
              "guardrails/policy.py"),
        _rule("policy_direction", "Direction of every policy change", "More cautious only",
              "Policy turns a resolve into an escalate or an abstain and a request into an escalate. "
              "An abstain is never promoted.", "guardrails/policy.py"),
    ]


_TOLERANCE_UNIT = {
    "ratio": ("Ratios", lambda v: f"{_num(v)}x"),
    "usd": ("Dollar amounts", lambda v: f"${_num(v)}"),
    "pct": ("Percentages", lambda v: f"{_num(v * 100)} points"),
    "days": ("Day counts", lambda v: f"{_num(v)} days"),
}


def _tolerances() -> list[dict[str, Any]]:
    rows = []
    for unit, value in covenant_service.DEFAULT_TOLERANCE.items():
        label, show = _TOLERANCE_UNIT.get(unit, (unit, _num))
        rows.append(_rule(f"covenant_tolerance.{unit}", f"Covenant certificate against the calculation: {label.lower()}",
                          show(value), "A reported value further than this from the calculated value is recorded "
                                       "as a variance against the certificate.",
                          "domain/covenant_service.py"))
    rows.append(_rule("borrowing_base_tolerance", "Borrowing base certificate against the recalculation",
                      f"${_num(collateral_service.DEFAULT_TOLERANCE)}",
                      "A certificate line further than this from the recalculated line is a mismatch.",
                      "domain/collateral_service.py"))
    return rows


_SIGNAL_NAME = {
    "covenant_headroom_low": "Covenant headroom low",
    "covenant_headroom_falling": "Covenant headroom falling",
    "revenue_ttm_decline": "Revenue decline",
    "ebitda_margin_decline": "EBITDA margin decline",
    "dso_increase": "Receivable days up",
    "dpo_increase": "Payable days up",
    "leverage_increase": "Leverage up",
    "net_loss": "Net loss",
    "cash_decline": "Cash decline",
    "line_usage_high": "Line usage high",
    "availability_low": "Availability low",
    "reporting_late": "Reporting late",
    "payment_past_due": "Payment past due",
    "auditor_opinion": "Auditor opinion",
}
_METRIC_WORDS = {
    "revenue_ttm": "Revenue over the trailing twelve months",
    "net_income_ttm": "Net income over the trailing twelve months",
    "cash": "Cash",
    "ebitda_margin": "EBITDA margin",
    "dso": "Receivable days",
    "dpo": "Payable days",
    "leverage": "Leverage",
    "avg_net_burn": "Average net burn",
}
_COMPARE = {"yoy": "on the same period a year earlier", "prior_period": "on the period before"}


def _plain(identifier: str) -> str:
    return identifier.replace("_", " ")


def _change(metric: str, threshold: Decimal) -> str:
    """A change in a metric, in the metric's own unit (a margin moves in points)."""
    unit = metrics.METRICS[metric].unit if metric in metrics.METRICS else "usd"
    if unit == "pct":
        return f"{_num(threshold * 100)} points"
    if unit == "days":
        return f"{_num(threshold)} days"
    if unit == "ratio":
        return f"{_num(threshold)}x"
    return f"${_num(threshold)}"


def signal_trigger(rule: signals.SignalRule) -> str:
    """When the rule fires, in words, with every figure read from the rule's own parameters."""
    p = rule.params
    metric = _METRIC_WORDS.get(p.get("metric", ""), _plain(p.get("metric", "")).capitalize())
    compare = _COMPARE.get(p.get("compare", ""), "")
    match rule.kind:
        case "headroom_below":
            return f"Headroom on a covenant below {_pct(p['threshold'])}"
        case "headroom_falling":
            return f"Headroom on a covenant falling {p['periods']} periods running"
        case "pct_decrease":
            return f"{metric} down more than {_pct(p['threshold'])} {compare}"
        case "abs_decrease":
            return f"{metric} down more than {_change(p['metric'], p['threshold'])} {compare}"
        case "abs_increase":
            return f"{metric} up more than {_change(p['metric'], p['threshold'])} {compare}"
        case "below":
            return f"{metric} below {_change(p['metric'], p['threshold'])}"
        case "usage_above":
            return f"Drawn balance above {_pct(p['threshold'])} of the commitment"
        case "availability_below":
            return f"Borrowing base availability below {_pct(p['threshold'])} of the commitment"
        case "reporting_late":
            return f"A reporting requirement more than {p['days']} days late"
        case "past_due":
            return f"A payment more than {p['days']} days past due"
        case "rml_below":
            return f"Runway below {_num(p['watch'])} months; high severity below {_num(p['high_below'])} months"
        case "rml_falling":
            return (f"Runway down by more than {_num(p['min_fall'])} {'month' if p['min_fall'] == 1 else 'months'} "
                    f"in each of {p['periods']} months running")
        case "pct_increase":
            return f"{metric} up more than {_pct(p['threshold'])} on the figure {p['compare_months']} months earlier"
        case "plan_ratio_below":
            return f"Revenue below {_pct(p['threshold'])} of plan"
        case "auditor_opinion":
            return "Auditor's opinion " + " or ".join(_plain(o) for o in p["opinions"])
    return _plain(rule.kind).capitalize()  # a kind added later is named, never left blank


def _signal_rules() -> list[dict[str, Any]]:
    return [{"id": rule.id, "name": _SIGNAL_NAME.get(rule.id) or content.SIGNAL_LABELS.get(rule.id) or _plain(rule.id).capitalize(),
             "severity": rule.severity, "severity_label": rule.severity.capitalize(),
             "trigger": signal_trigger(rule)} for rule in signals.RULES]


def _versions() -> list[dict[str, Any]]:
    def version(rule_id: str, rule: str, value: str, effect: str, source: str) -> dict[str, Any]:
        return _rule(rule_id, rule, value, effect, source, kind="ident")

    return [
        version("engine", "Formula engine", expr.ENGINE_VERSION,
                "Evaluates every covenant and metric formula. Decimals only; rounding once, at the end, half-up.",
                "calc/expr.py"),
        version("metrics", "Financial metrics", metrics.METRICS_VERSION,
                "The metric library: leverage, coverage, margins, working-capital days.", "calc/metrics.py"),
        version("signals", "Early warning rules", signals.SIGNALS_VERSION,
                "The rule table set out under Early warning rules.", "calc/signals.py"),
        version("template", "Spreading templates", ", ".join(template.TEMPLATES),
                "The lines a statement is spread onto, and the totals that must foot: ci-1 for commercial borrowers, vc-1 for venture borrowers.", "calc/template.py"),
        version("borrowing_base", "Borrowing base", collateral_service.ENGINE_VERSION,
                "Recalculates the borrowing base and reconciles the certificate to it.", "domain/collateral_service.py"),
        version("package", "Review package", content.CONTENT_VERSION,
                "The content of a prepared package.", "publishing/content.py"),
    ]


_AGENT_SPECS = (intake.SPEC, spreading.SPEC, certificate.SPEC, terms_agent.SPEC, covenant.SPEC, collateral.SPEC,
                early_warning.SPEC, review.SPEC, copilot.SPEC)


def _agents() -> list[dict[str, Any]]:
    """The agent versions this build would run, whether or not one has run yet. The inventory at
    `/agents` lists the versions that have been registered by a run."""
    return [{"name": s.name, "version": s.version, "purpose": s.purpose, "model": s.resolved_model(),
             "effort": s.effort, "max_steps": s.max_steps, "tools": list(s.tools),
             "prompt_sha256": s.prompt_sha256()} for s in _AGENT_SPECS]


def _records(db: Session) -> list[dict[str, Any]]:
    settings = get_settings()
    append_only = ledger.guard_status(db)["append_only_for_this_role"]
    return [
        _rule("ledger_append_only", "The ledger is append-only",
              "Holds for this connection" if append_only else "Not held for this connection",
              "The database refuses an update or a delete on the ledger, and the role the API connects as cannot "
              "switch that off." if append_only else
              "The database refuses an update or a delete on the ledger, but the role this API connects as owns the "
              "table or may change it, so it could switch that off. A deployment connects as a role that cannot.",
              "core/ledger.py", state="verified" if append_only else "attention"),
        _rule("ledger_chain", "Each ledger event carries the hash of the one before", "Always",
              "An edit or a removal breaks the chain. Verify the chain under Ledger.", "core/ledger.py"),
        _rule("facts", "Facts are never edited", "Always",
              "A correction is a new fact that supersedes the old one; the old one stays on file.",
              "domain/facts_service.py"),
        _rule("terms", "Terms are versioned", "Always",
              "An amendment creates a new version and never overwrites one. A proposed version governs no test.",
              "domain/terms_service.py"),
        _rule("login_lockout", "Sign-in lockout",
              f"{settings.login_max_failures} failures in {settings.login_lockout_minutes} minutes",
              "Further attempts are refused without checking the password, and the lockout is recorded in the ledger.",
              "api/auth.py"),
        _rule("session", "Session length", f"{settings.session_hours} hours",
              "After this a person signs in again.", "api/auth.py"),
        _rule("upload", "Largest upload", f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
              "A larger file is refused before it is stored.", "core/config.py"),
    ]


@router.get("/governance/policy")
def policy_register(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """The rules code applies without asking a model, each with the setting in force here."""
    return {
        "sections": [
            {"id": "people_decide", "title": "People decide",
             "summary": "Where a person must act, and where that person must be a second one.",
             "rules": _people_decide()},
            {"id": "agent_limits", "title": "Limits on agents",
             "summary": "Applied by code after the agent answers. An agent cannot argue its way past them.",
             "rules": _agent_limits()},
            {"id": "tolerances", "title": "Tolerances",
             "summary": "How far a reported figure may sit from the calculated one before code calls it a difference.",
             "rules": _tolerances()},
            {"id": "records", "title": "Records and access",
             "summary": "What is kept, and what cannot be changed afterwards.",
             "rules": _records(db)},
            {"id": "versions", "title": "Calculation versions",
             "summary": "Every calculation stores the version it ran under.",
             "rules": _versions()},
        ],
        "signal_rules": {"version": signals.SIGNALS_VERSION, "rules": _signal_rules()},
        "agents": _agents(),
    }

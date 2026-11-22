"""One mapping from a stored decision to the words people read, past tense, for the briefing and the thread."""
import re
from datetime import date
from typing import Any

from app.publishing.content import SIGNAL_LABELS

_PAST = {
    "approve": "approved", "reject": "rejected", "return_for_rework": "returned for rework",
    "acknowledged": "acknowledged", "rating_review_requested": "rating review requested",
    "add_to_watch_list": "added to the watch list", "bank_figures_stand": "kept the bank's figures",
    "borrower_to_resubmit": "asked the borrower to resubmit", "certificate_correct": "confirmed the certificate",
    "board_by_hand": "boarded by hand", "retry": "retried", "chaser_sent": "chaser sent",
    "extension_granted": "extension granted", "received_elsewhere": "marked received elsewhere",
    "classified_by_hand": "classified by hand", "not_needed": "marked not needed",
    "request_new_document": "requested a new document", "in_thousands": "read as thousands",
    "in_dollars": "read as dollars", "input_provided": "input provided", "not_applicable": "marked not applicable",
    "listing_corrected": "listing corrected", "no_action": "no action taken", "paydown_required": "paydown required",
    "temporary_overadvance_approved": "temporary overadvance approved", "escalate_to_committee": "escalated to committee",
    "escalate": "escalated", "reservation_of_rights": "reserved rights", "reserve_rights": "reserved the bank's rights", "reading_confirmed": "reading confirmed", "key_by_hand": "keyed by hand",
    "restated_update_prior": "updated the prior period", "keep_prior": "kept the prior period",
    "ask_borrower": "asked the borrower", "wrong_document": "marked the wrong document",
    "reviewed": "reviewed", "spread_in_error": "marked the spread in error",
    "certificate_in_error": "marked the certificate in error", "terms_approved": "terms approved",
    "terms_update_requested": "terms update requested", "amendment_not_applicable": "marked the amendment not applicable",
    "values_confirmed": "values confirmed", "values_corrected": "values corrected",
    "accept_as_reported": "accepted as reported", "waiver_requested": "waiver requested",
    "not_a_breach": "marked not a breach", "breach": "confirmed a breach",
}


def decision_words(decision: str | None) -> str:
    """"approved", "marked not a breach": what was done, not the stored key. An unknown key reads as its words."""
    if not decision:
        return "decided"
    return _PAST.get(decision, decision.replace("_", " "))


def question_choice(evidence: dict[str, Any] | None, decision: str | None) -> str | None:
    """The label of the option a question was answered with."""
    options = (evidence or {}).get("options", [])
    return next((o["label"] for o in options if o.get("id") == decision), None)


DOCUMENT_TYPE_WORDS = {
    "mrr_report": "MRR report", "bank_statement": "Bank statement", "bank_statements": "Bank statement",
    "monthly_financials": "Monthly financial statements", "credit_agreement": "Credit agreement",
    "compliance_certificate": "Compliance certificate", "borrowing_base_certificate": "Borrowing base certificate",
    "receivables_aging": "Receivables aging", "annual_statements": "Annual financial statements",
    "interim_statements": "Interim financial statements", "quarterly_statements": "Quarterly financial statements",
    "tax_return": "Tax return", "term_sheet": "Term sheet", "investor_update": "Investor update",
    "amendment": "Amendment", "waiver": "Waiver", "other": "Other document",
}


def document_type_words(doc_type: str | None) -> str:
    """"MRR report", "Bank statement": a document type as people say it. The document's own printed title
    ("Account statement, August 2026") is shown beside it unchanged. The one table: the browser is served it
    (`GET /words/document-types`) and keeps no list of its own."""
    if not doc_type:
        return "Not yet classified"
    return DOCUMENT_TYPE_WORDS.get(doc_type, doc_type.replace("_", " ").capitalize())


# Stored covenant-test notes in plain words: the one source for the client file's overview and covenants view.
NOTE_WORDS = {"not_meaningful_cash_flow_positive": "Not meaningful: cash-flow positive"}


def agent_words(recorded: str) -> str:
    """An agent's name in words: "Certificate reader agent". A name recorded with its version ("review@2") is the
    same agent. The one source for every screen that names an agent; the browser keeps no table."""
    name = recorded.split("@")[0]
    return "Copilot" if name == "copilot" else f"{name.replace('_', ' ').capitalize()} agent"


def task_words(task: str) -> str:
    return task.replace("_", " ").capitalize()


RUN_STATUS_WORDS = {"running": "Running", "completed": "Completed", "abstained": "Abstained", "failed": "Failed",
                    "refused": "Refused"}


def run_status_words(status: str) -> str:
    return RUN_STATUS_WORDS.get(status, status.replace("_", " ").capitalize())


def guardrail_note_words(note: dict[str, Any]) -> str:
    """"figure untraceable · dropped": what a guardrail check found and did."""
    check = str(note.get("check") or "").replace("_", " ")
    return f"{check} · {note.get('action') or ''}".strip(" ·")


# The families of ledger events (the part of an action before its first dot), in the words the Oversight filter shows.
LEDGER_FAMILY_WORDS = {
    "auth": "Sign-ins", "work_item": "Cases", "document": "Documents", "fact": "Facts", "cycle": "Cycles",
    "copilot": "Copilot", "draft": "Drafts", "lesson": "Lessons", "terms": "Terms", "clock": "Clock",
    "user": "People", "agent": "Agent runs", "obligation": "Reporting obligations", "covenant": "Covenant tests",
    "signal": "Signals", "borrowing_base": "Borrowing base", "funding_event": "Funding events",
    "review": "Reviews", "action": "Actions", "package": "Review packages", "facility": "Facilities",
    "borrower": "Clients",
}


def ledger_family_words(family: str) -> str:
    return LEDGER_FAMILY_WORDS.get(family, family.replace("_", " ").capitalize())


def actor_words(actor_type: str, actor_id: str, user_names: dict[str, str]) -> str:
    """Who acted: a person by name, an agent by its words, the system as "System"."""
    if actor_type == "agent":
        return agent_words(actor_id)
    if actor_type == "user":
        return user_names.get(actor_id, "A person")
    return "System"


def signal_words(rule: str) -> str:
    """A signal rule in words, from the same published labels the review sheet and the briefing use."""
    return SIGNAL_LABELS.get(rule) or rule.replace("_", " ").capitalize()


STAGE_WORDS = {"awaiting_package": "Awaiting package", "intake": "Intake", "spreading": "Spreading",
               "covenant_testing": "Covenant testing", "borrowing_base": "Borrowing base", "signals": "Signals",
               "review_prep": "Review preparation", "in_review": "In review", "actions_open": "Actions open",
               "closed": "Closed"}
STAGE_STATUS_WORDS = {"pending": "Not started", "running": "Running", "needs_person": "Needs a person",
                      "done": "Done", "skipped": "Skipped", "failed": "Failed"}
ROLE_WORDS = {"analyst": "Credit analyst", "portfolio_manager": "Portfolio manager", "credit_officer": "Credit officer",
              "credit_admin": "Credit administration", "credit_review": "Credit review", "admin": "Administrator"}
_STAGE_WORDS = STAGE_WORDS
_STAGE_STATUS_WORDS = {k: v.lower() for k, v in STAGE_STATUS_WORDS.items()}  # inside a sentence
_ROLE_WORDS = {k: v.lower() for k, v in ROLE_WORDS.items()}

# Final review I4: every table of words a screen shows lives here and is served (`GET /words/labels`); the browser
# keeps no table of its own. Colour, order and emphasis stay in the browser: they are presentation, not words.
SEVERITY_WORDS = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
COVENANT_OUTCOME_WORDS = {
    "breach_reported_compliant": {"label": "Breach, reported compliant",
                                  "explanation": "The calculated value fails the test and the certificate claims "
                                                 "compliance."},
    "breach": {"label": "Breach", "explanation": "The calculated value fails the test."},
    "cannot_test": {"label": "Cannot test", "explanation": "An input is missing or no terms are in force."},
    "compliant_variance": {"label": "Compliant, variance",
                           "explanation": "The calculated value passes but differs from the certificate beyond "
                                          "tolerance. The variance is logged; no decision is needed."},
    "compliant": {"label": "Compliant", "explanation": "The calculated value passes and agrees with the certificate. "
                                                       "Nothing is needed from a person."},
}
FUNDING_KIND_WORDS = {"equity_round": "Equity round", "extension": "Extension", "milestone_tranche": "Milestone tranche",
                      "venture_debt": "Venture debt"}
RECOMMENDATION_WORDS = {"resolve": "Recommends resolve", "escalate": "Recommends escalate",
                        "request": "Recommends request", "abstain": "Abstains", "draft": "Drafted for approval"}
DOCUMENT_READ_WORDS = {"indexed": "read page by page", "image_only": "image only, with no readable text",
                       "received": "received"}
CADENCE_WORDS = {"quarterly": "Quarterly", "monthly": "Monthly"}
STATEMENT_WORDS = {"is": "Income statement", "bs": "Balance sheet", "cf": "Cash flow statement", "sup": "Supplemental"}
HOLD_REASON_WORDS = {
    "mapping_doubt": "The check on the line this figure was filed under did not pass.",
    "label_mismatch": "The row label the reader reported is not on the page.",
    "not_found": "The figure the reader reported is not on the page it cited.",
    "column_unconfirmed": "The figure is on the page, but its column could not be confirmed as the one for this "
                          "period.",
    "ambiguous": "The figure appears more than once on the page, so its row could not be settled.",
    "unparseable": "The printed figure could not be read as a number.",
}
CHECK_FINDING_WORDS = {
    "missing_input": "No figure is on file for this line", "total_not_read": "The printed total was not read",
    "absent_not_verified": "Not shown to be absent from the statement",
    "does_not_foot": "The lines do not add to the printed total",
    "does_not_balance": "Assets do not equal liabilities and equity",
    "does_not_tie": "The cash flow statement does not tie to the income statement",
    "cash_roll_mismatch": "The change in cash does not match the balance sheet",
}
CHECK_COMPARED_WORDS = {
    "does_not_foot": ["Lines add to", "Printed total"],
    "does_not_balance": ["Total assets", "Total liabilities and equity"],
    "does_not_tie": ["Cash flow statement", "Income statement"],
    "cash_roll_mismatch": ["Net change in cash", "Change in the cash balance"],
}
FACT_STATUS_WORDS = {"verified": "Verified by code", "confirmed": "Confirmed by a person",
                     "proposed": "Proposed, not verified", "rejected": "Rejected", "superseded": "Superseded",
                     "from_terms": "From approved terms"}
VERIFIED_BY_KIND_WORDS = {"extracted": "Verified on the page by code", "calculated": "Calculated by code",
                          "system": "From a system of record", "seeded": "Loaded history, not extracted from a document"}
UNIT_WORDS = {"usd": "whole US dollars", "ratio": "a ratio", "pct": "a fraction: 0.072 is 7.2%", "days": "days",
              "count": "a count", "months": "months"}
CASE_HISTORY_WORDS = {"routed": "sent this to", "returned": "returned this to", "evidence_attached": "attached a document"}
CASE_STATUS_WORDS = {"open": "Open", "decided": "Decided", "withdrawn": "Withdrawn", "superseded": "Superseded"}


def label_tables() -> dict[str, Any]:
    """Every table of words the browser shows, in one payload (`GET /words/labels`)."""
    return {
        "severities": SEVERITY_WORDS, "stages": STAGE_WORDS, "stage_statuses": STAGE_STATUS_WORDS, "roles": ROLE_WORDS,
        "covenant_outcomes": COVENANT_OUTCOME_WORDS, "funding_kinds": FUNDING_KIND_WORDS,
        "recommendations": RECOMMENDATION_WORDS, "document_reads": DOCUMENT_READ_WORDS, "cadences": CADENCE_WORDS,
        "statements": STATEMENT_WORDS, "hold_reasons": HOLD_REASON_WORDS, "check_findings": CHECK_FINDING_WORDS,
        "check_compared": CHECK_COMPARED_WORDS, "fact_statuses": FACT_STATUS_WORDS,
        "verified_by_kind": VERIFIED_BY_KIND_WORDS, "units": UNIT_WORDS, "case_history": CASE_HISTORY_WORDS,
        "case_statuses": CASE_STATUS_WORDS, "decisions": {k: v for k, v in _PAST.items()},
    }


_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
_IDENTIFIER = re.compile(r"[a-z]+(?:_[a-z]+)*")
_PLAIN_KEYS = frozenset({"kind", "status", "type", "role", "severity", "source", "state", "result"})
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _date_words(iso: str) -> str:
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def stage_words(stage: str) -> str:
    return _STAGE_WORDS.get(stage, stage.replace("_", " ").capitalize())


def _plain(key: str) -> str:
    return key.replace("_", " ")


def figure_free(text: str) -> bool:
    """True when the text states no figure, by the guardrail's own detector (`check_narrative` with no facts in scope):
    dates, periods and section references pass; an amount, a ratio or a count does not."""
    from app.guardrails.narrative import check_narrative

    return not check_narrative(text, {})


def describe_event(action: str, payload: dict[str, Any] | None, document_title: str | None = None) -> str:
    """A ledger event's payload in a few plain words: the decision and its reason first, then whatever else is there.
    The one source for Oversight's ledger and the client file's history; the browser keeps no table of its own."""
    payload = payload or {}

    def text(key: str) -> str | None:
        value = payload.get(key)
        return value if isinstance(value, str) and value else None

    parts: list[str] = []
    if text("decision"):
        parts.append(decision_words(text("decision")))
    if text("reason") and not action.startswith("agent."):  # an agent event's reason is exception or model text: not shown
        parts.append(f"“{text('reason')}”")
    if text("title") and figure_free(str(text("title"))):  # a title is shown unsourced: one with a figure is dropped
        parts.append(str(text("title")))
    if text("key"):
        parts.append(str(text("key")))
    covenant = text("covenant") or text("covenant_id")
    if covenant:
        parts.append(_plain(covenant).capitalize())
    rule = text("rule") or text("rule_id")
    if rule:
        parts.append(f"{signal_words(rule)}{f' ({_plain(str(text('subject')))})' if text('subject') else ''}")
    if text("outcome"):
        parts.append(_plain(str(text("outcome"))))
    if text("stage"):
        def status(value: Any) -> str:
            return _STAGE_STATUS_WORDS.get(str(value), str(value if value is not None else ""))
        stage = str(text("stage"))
        parts.append(f"{_STAGE_WORDS.get(stage, _plain(stage).capitalize())}: {status(payload.get('from'))} to {status(payload.get('to'))}")
    if text("document_type"):
        parts.append(document_type_words(text("document_type")))
    if text("period_end"):
        parts.append(f"period ended {_date_words(str(text('period_end')))}")
    if action == "clock.set" and text("to"):
        parts.append(f"to {_date_words(str(text('to')))}")
    if text("received_date"):
        parts.append(f"received {_date_words(str(text('received_date')))}")
    if text("email"):
        role = text("role")
        parts.append(f"{text('email')}{f', {_ROLE_WORDS.get(role, _plain(role))}' if role else ''}")
    if document_title:
        parts.append(document_title)
    elif text("file_name"):
        parts.append(str(text("file_name")))
    if text("view"):
        parts.append(f"“{text('view')}”")
    if not parts and not action.startswith("agent."):
        # Last resort, deterministic: a short list of keys that hold a kind or a state, in key order, and only a value
        # that is a stored identifier (letters and underscores). Anything else in a payload (amounts, notes, ids, free text) is not shown here: a figure
        # is shown only from a stored fact, and prose only where a branch above knows what it is.
        for key in sorted(_PLAIN_KEYS & payload.keys()):
            value = payload[key]
            if isinstance(value, str) and _IDENTIFIER.fullmatch(value):  # a stored key such as equity_round, never prose or a figure
                parts.append(f"{_plain(key)} {_plain(value)}")
    return " · ".join(parts)


BASE_OUTCOME_WORDS = {"agrees": "Agrees with the certificate", "mismatch": "Certificate differs from the recalculation",
                      "over_advance": "Over-advanced", "cannot_compute": "Could not be recalculated"}


# What each decision is called on a button, and what it means: the one table (a person's decision in the past tense is `decision_words`).
DECISION_WORDS: dict[str, dict[str, str]] = {
    "waiver_requested": {"label": "Waiver requested", "hint": "The borrower has asked for a waiver; the breach stands until one is granted."},
    "reservation_of_rights": {"label": "Reserve rights", "hint": "Send a reservation of rights letter while the breach is worked through."},
    "escalate_to_committee": {"label": "Escalate to committee", "hint": "Take the breach to credit committee."},
    "ask_for_new_timeline": {"label": "Ask for a new timeline", "hint": "Ask the client for a new expected close. Squad drafts the email; a person sends it."},
    "note_and_watch": {"label": "Note and keep watching", "hint": "Noted; Squad keeps watching for the close."},
    "reserve_rights": {"label": "Reserve the bank’s rights", "hint": "The bank reserves its rights while the round is late."},
    "escalate": {"label": "Escalate", "hint": "Take it to the credit officer or committee."},
    "not_a_breach": {"label": "Not a breach", "hint": "The calculation is wrong or the terms differ. Say why."},
    "paydown_required": {"label": "Require a paydown", "hint": "The borrower must repay down to the borrowing base."},
    "temporary_overadvance_approved": {"label": "Approve a temporary over-advance", "hint": "Allow the excess for a stated period."},
    "bank_figures_stand": {"label": "The bank’s figures stand", "hint": "Use the recalculation; the certificate is wrong."},
    "borrower_to_resubmit": {"label": "Ask the borrower to resubmit", "hint": "Request a corrected certificate."},
    "certificate_correct": {"label": "The certificate is correct", "hint": "The recalculation is wrong. Say why."},
    "chaser_sent": {"label": "Chaser sent", "hint": "The reminder has gone to the borrower."},
    "extension_granted": {"label": "Extension granted", "hint": "The borrower has more time. Say until when."},
    "received_elsewhere": {"label": "Received elsewhere", "hint": "The document arrived outside the workspace."},
    "acknowledged": {"label": "Acknowledge", "hint": "Seen; no change to the risk rating."},
    "rating_review_requested": {"label": "Request a rating review", "hint": "The risk rating should be looked at again."},
    "add_to_watch_list": {"label": "Add to the watch list", "hint": "Monitor this borrower more closely."},
    "values_confirmed": {"label": "Values confirmed", "hint": "Every held figure is accepted as read, and the spread is finished from them."},
    "values_corrected": {"label": "Values corrected", "hint": "The figures have been corrected with a citation."},
    "accept_as_reported": {"label": "Accept as reported", "hint": "Use the statement as it stands. Say why."},
    "request_new_document": {"label": "Request a new document", "hint": "Ask the borrower for a complete, readable copy."},
    "key_by_hand": {"label": "Key by hand", "hint": "A person will enter the figures from the page."},
    "restated_update_prior": {"label": "Restated: update the prior period", "hint": "The borrower restated; supersede the earlier figures."},
    "keep_prior": {"label": "Keep the prior figures", "hint": "Leave last year’s confirmed spread as it is."},
    "ask_borrower": {"label": "Ask the borrower", "hint": "Find out why the comparative column changed."},
    "terms_update_requested": {"label": "Request a terms update", "hint": "Prepare a new terms version from the amendment for approval."},
    "amendment_not_applicable": {"label": "Amendment does not apply", "hint": "The amendment does not change the tested terms. Say why."},
    "terms_approved": {"label": "Approve the terms", "hint": "The proposed terms govern from their effective date."},
    "not_applicable": {"label": "Not applicable", "hint": "Say why this does not apply."},
    "approve": {"label": "Approve", "hint": "The commentary is approved as written."},
    "return_for_rework": {"label": "Return for rework", "hint": "Send it back with what needs to change."},
    "reject": {"label": "Reject", "hint": "Say why."},
    "no_action": {"label": "No action", "hint": "Nothing more is needed."},
}


def action_words(action: str) -> str:
    """A ledger action in words: "Cases: decided". The family is the part before the first dot."""
    family, _, rest = action.partition(".")
    return f"{ledger_family_words(family)}: {rest.replace('_', ' ')}" if rest else ledger_family_words(family)

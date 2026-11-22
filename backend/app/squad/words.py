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
    "escalate": "escalated", "reading_confirmed": "reading confirmed", "key_by_hand": "keyed by hand",
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


_STAGE_WORDS = {"awaiting_package": "Awaiting package", "intake": "Intake", "spreading": "Spreading",
                "covenant_testing": "Covenant testing", "borrowing_base": "Borrowing base", "signals": "Signals",
                "review_prep": "Review preparation", "in_review": "In review", "actions_open": "Actions open",
                "closed": "Closed"}
_STAGE_STATUS_WORDS = {"pending": "not started", "running": "running", "needs_person": "needs a person",
                       "done": "done", "skipped": "skipped", "failed": "failed"}
_ROLE_WORDS = {"analyst": "credit analyst", "portfolio_manager": "portfolio manager", "credit_officer": "credit officer",
               "credit_admin": "credit administration", "credit_review": "credit review", "admin": "administrator"}
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _date_words(iso: str) -> str:
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def _plain(key: str) -> str:
    return key.replace("_", " ")


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
    if text("reason"):
        parts.append(f"“{text('reason')}”")
    if text("title"):
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
    if not parts:
        for key, value in list(payload.items())[:3]:
            if value is not None and not isinstance(value, (dict, list)):
                parts.append(f"{_plain(key)} {_UUID.sub(lambda m: m.group(0)[:8], str(value))}")
    return " · ".join(parts)

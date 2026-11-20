"""One mapping from a stored decision to the words people read, past tense, for the briefing and the thread."""
from typing import Any

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

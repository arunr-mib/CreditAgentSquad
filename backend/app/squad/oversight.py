"""Oversight as people read it. The evaluation scorecard: a share (accuracy, a rate, precision, recall, the share of
cycles needing no person) is a percentage; anything else is a count. Converted here with Decimals, so the browser does
no arithmetic on a figure; an unmeasured metric stays null. Agent runs and agents carry their words from the one
source (`app.squad.words`); the browser builds no names."""
from decimal import Decimal
from typing import Any

from app.squad.words import agent_words, guardrail_note_words, run_status_words, task_words

OVERSIGHT_ROLES = frozenset({"admin", "credit_review", "credit_admin"})  # the one copy; the browser is told
SHARE_MARKERS = ("accuracy", "rate", "precision", "recall", "needing_no_person", "to_need_no_person")


def _label(key: str) -> str:
    text = key.replace("_", " ")
    return text[:1].upper() + text[1:]


def evaluation_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, value in metrics.items():
        share = any(m in key for m in SHARE_MARKERS)
        if value is None or isinstance(value, (dict, list, bool)):
            shown = None
        elif share:
            shown = format((Decimal(str(value)) * 100).normalize(), "f")
        else:
            shown = format(Decimal(str(value)).normalize(), "f")
        rows.append({"key": key, "label": _label(key), "value": shown, "unit": "pct" if share else "count"})
    return rows


def run_words(run: dict[str, Any]) -> dict[str, Any]:
    """A run's row with the words for its agent, task, outcome and each guardrail note."""
    return {**run, "agent_label": agent_words(run["agent_name"]), "task_label": task_words(run["task"]),
            "status_label": run_status_words(run["status"]),
            "guardrail_notes": [{**n, "words": guardrail_note_words(n)} for n in run.get("guardrail_notes") or []]}

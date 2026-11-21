"""Rules that override an agent's recommendation no matter how well it argued. Pure code."""
from dataclasses import dataclass, field
from decimal import Decimal

from app.guardrails.narrative import Note

PROHIBITED_PHRASES = (
    "waive the covenant", "waive covenant", "grant a waiver", "amend the terms", "amend terms",
    "amend the agreement", "contact the borrower", "contact borrower", "call the borrower",
)


@dataclass(frozen=True)
class PolicySettings:
    # a "resolve" or "request" is not allowed when the governing test misses by more than this
    # share of the threshold (0.15 = fifteen percent)
    margin_floor_pct: Decimal = Decimal("0.15")
    prohibited_phrases: tuple[str, ...] = PROHIBITED_PHRASES
    require_person: bool = True  # locked: every recommendation ends with a person


@dataclass
class PolicyResult:
    recommendation: str
    notes: list[Note] = field(default_factory=list)


def apply_policy(
    recommendation: str,
    *,
    text: str,
    cap_reached: bool = False,
    governing_passed: bool | None,
    governing_headroom_pct: Decimal | None,
    surviving_claims: int,
    settings: PolicySettings = PolicySettings(),
) -> PolicyResult:
    """Return the recommendation after policy. Only ever makes it more cautious:
    resolve -> escalate or abstain; request -> escalate; an abstain is never promoted."""
    result = PolicyResult(recommendation)
    if recommendation == "abstain":
        return result

    lowered = text.lower()
    hit = next((p for p in settings.prohibited_phrases if p in lowered), None)
    if hit is not None:
        result.recommendation = "escalate"
        result.notes.append(Note("policy", "prohibited_phrase", "escalate",
                                 f"the text proposes an action reserved for a person: {hit!r}"))
        return result

    if recommendation == "resolve":
        if cap_reached:
            result.recommendation = "abstain"
            result.notes.append(Note("policy", "step_cap", "abstain",
                                     "the run spent its allowance of lookups and was asked for a final answer"))
            return result
        if governing_passed is not True or surviving_claims < 1:
            result.recommendation = "escalate"
            result.notes.append(Note(
                "policy", "resolve_requires_evidence", "escalate",
                "a resolve needs a passing governing calculation and at least one verified citation"))
            return result

    if recommendation in ("resolve", "request") and governing_headroom_pct is not None:
        if governing_headroom_pct < -settings.margin_floor_pct:
            result.recommendation = "escalate"
            result.notes.append(Note("policy", "margin_floor", "escalate",
                                     "the governing test misses its threshold by more than the policy floor"))
    return result

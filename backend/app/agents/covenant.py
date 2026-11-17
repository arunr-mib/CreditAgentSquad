"""Covenant Agent: investigate a covenant exception the way a credit analyst would, then let
code check every part of the answer before anything is attached to the work item.

The model reads the agreement and its amendments, reruns the test through the calculation
engine, and recommends. Code then gathers the evidence itself (the calculations this run
logged and the facts behind them), drops any citation that is not verbatim on its page, refuses
any typed figure, checks terms drift, applies policy, and writes once. The work item's status
and decision are never touched: a person decides.
"""
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.covenant_tools import COVENANT_TOOLS, TERMS_DOCUMENT_TYPES, clause_figures, run_calcs
from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.tools import Scope, ToolGateway
from app.calc.terms import Terms, compare_terms
from app.core import ledger
from app.domain import covenant_service
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.facts import CalcRun, Fact
from app.domain.monitoring import CovenantTest, Cycle, WorkItem
from app.domain.terms import TermsVersion
from app.domain.terms_service import resolve_document
from app.guardrails.narrative import FactView, Note, check_narrative, render
from app.guardrails.numbers import extract_figures, same_number
from app.guardrails.policy import PolicySettings, apply_policy
from app.guardrails.quotes import quote_on_page

ITEM_TYPES = ("covenant.breach", "covenant.reported_mismatch")
MAX_EXPLANATION_WORDS = 150
Recommendation = Literal["resolve", "escalate", "request", "abstain"]
Tag = Literal["amendment_addback", "period_mismatch", "missing_waiver", "borrower_calc_error", "true_breach", "other"]

# Written by code, never by the model, and free of figures.
ABSTAIN_NO_ANSWER = ("The Covenant Agent did not complete its investigation, so it makes no recommendation. "
                     "Review the exception directly.")
ABSTAIN_UNVERIFIED = ("The Covenant Agent's answer did not pass verification and is not shown. "
                      "Review the exception directly; the notes say which check failed.")


class Claim(BaseModel):
    text: str
    document_id: str
    page: int
    quote: str


class CovenantAnswer(BaseModel):
    recommendation: Recommendation
    explanation: str
    claims: list[Claim]
    calc_ids: list[str]
    missing_evidence: list[str]
    suggested_tag: Tag

    @field_validator("explanation")
    @classmethod
    def _short(cls, text: str) -> str:
        if len(text.split()) > MAX_EXPLANATION_WORDS:
            raise ValueError(f"the explanation is longer than {MAX_EXPLANATION_WORDS} words")
        return text


SPEC = AgentSpec(
    name="covenant", version="1",
    purpose="Investigate a covenant exception and recommend; code verifies every claim and figure.",
    prompt_file="covenant.md", output_model=CovenantAnswer, tools=tuple(t.name for t in COVENANT_TOOLS),
    effort="high", max_steps=12, max_tokens=16000)
GATEWAY = ToolGateway(list(COVENANT_TOOLS))
POLICY = PolicySettings(max_steps=SPEC.max_steps)
AGENT_ID = f"{SPEC.name}@{SPEC.version}"


@dataclass
class Investigation:
    recommendation: str  # after guardrails
    model_recommendation: str | None = None  # what the model answered, if it answered
    run_id: uuid.UUID | None = None
    explanation: str = ""  # with fact references
    explanation_rendered: str = ""
    claims: list[dict[str, Any]] = field(default_factory=list)  # verified on their pages
    calc_ids: list[str] = field(default_factory=list)
    governing_calc_id: str | None = None
    suggested_tag: str | None = None
    missing_evidence: list[str] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)  # {layer, check, action, detail}


def _note(result: Investigation, layer: str, check: str, action: str, detail: str) -> None:
    result.notes.append({"layer": layer, "check": check, "action": action, "detail": detail})


def _take(result: Investigation, notes: list[Note]) -> None:
    for n in notes:
        _note(result, n.layer, n.check, n.action, n.detail)


def _brief(item: WorkItem, test: CovenantTest, borrower: Borrower, facility: Facility) -> str:
    return (
        f"Exception to investigate for {borrower.name}, {facility.name}.\n"
        f"Work item: {item.title}\nQuestion for the person who will decide: {item.question}\n"
        f"Covenant: {test.covenant_name}, tested for the period ended {test.period_end:%B %-d, %Y}. "
        f"Outcome recorded by the bank's calculation: {test.outcome}.\n"
        "This brief only tells you what to look into. It is not evidence and cannot be cited; "
        "start with get_exception.")


# ---- evidence, gathered by code --------------------------------------------------------------


def _evidence_facts(db: Session, test: CovenantTest, calcs: list[CalcRun]) -> dict[str, FactView]:
    """The facts behind the calculations in evidence: every input, every result they produced,
    and what the certificate reported for this covenant and period."""
    input_ids = {uuid.UUID(i["fact_id"]) for c in calcs for i in c.inputs if i.get("fact_id")}
    calc_ids = [c.id for c in calcs]
    rows = list(db.execute(select(Fact).where(Fact.id.in_(input_ids))).scalars()) if input_ids else []
    rows += list(db.execute(select(Fact).where(Fact.calc_run_id.in_(calc_ids))).scalars())
    rows += list(db.execute(select(Fact).where(
        Fact.borrower_id == test.borrower_id, Fact.period_end == test.period_end,
        Fact.key.in_((f"cert.{test.covenant_id}.value", f"cert.{test.covenant_id}.threshold")),
        Fact.status.in_(("verified", "confirmed")))).scalars())
    return {str(f.id): FactView(str(f.id), f.value, f.unit) for f in rows if f.borrower_id == test.borrower_id}


def _thresholds(calcs: list[CalcRun], approved: Terms, covenant_id: str) -> list[Decimal]:
    known = [Decimal(str(c.outputs["threshold"])) for c in calcs if c.outputs.get("threshold") is not None]
    covenant = approved.covenant(covenant_id)
    if covenant is not None:
        known += [covenant.test.threshold, *(s.value for s in covenant.test.steps)]
    return known


def _verify_claims(db: Session, borrower_id: uuid.UUID, claims: list[Claim], result: Investigation,
                   ) -> list[tuple[Claim, Document]]:
    surviving = []
    for claim in claims:
        doc = resolve_document(db, borrower_id, claim.document_id)
        page = db.execute(select(DocumentPage).where(
            DocumentPage.document_id == doc.id, DocumentPage.page_number == claim.page)).scalar_one_or_none() \
            if doc is not None else None
        if doc is None:
            problem = "the cited document is not on file for this borrower"
        elif page is None or not quote_on_page(page.text, claim.quote):
            problem = f"the quote is not on page {claim.page} of {doc.title}"
        else:
            surviving.append((claim, doc))
            continue
        _note(result, "quotes", "quote_not_on_page", "claim_dropped", problem)
    return surviving


def _numbers(value: Any) -> list[Decimal]:
    """The numbers inside one side of a terms difference."""
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, Decimal | int):
        return [Decimal(value)]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in _numbers(v)]
    return []


def _stated(number: Decimal, quote: str) -> bool:
    """True when the quoted clause states this number (a percentage may be printed as 85%)."""
    for fig in clause_figures(quote):
        if same_number(fig.value, number):
            return True
        if fig.kind == "percent" and same_number(fig.value / Decimal(100), number):
            return True
    return False


def _terms_drift(governing: CalcRun, approved_row: TermsVersion, approved: Terms,
                 surviving: list[tuple[Claim, Document]], result: Investigation) -> bool:
    """True when the governing calculation used terms that differ from the approved version and a
    difference is not backed. A difference is backed when its figures are stated in a surviving
    claim that quotes an agreement or amendment on file; when the calculation was a cited
    what-if, the claim must quote the same page of the same document the what-if read."""
    agent = (governing.trace or {}).get("agent", {})
    used, cited = agent.get("terms"), agent.get("citation")
    if used is None:
        if governing.terms_version_id == approved_row.id:
            return False
        _note(result, "terms_drift", "terms_unknown", "escalate",
              "the governing calculation used terms that could not be compared with the approved version")
        return True
    differences = compare_terms(used, approved)
    if not differences:
        return False
    quotes = [c.quote for c, doc in surviving if doc.doc_type in TERMS_DOCUMENT_TYPES
              and (cited is None or (str(doc.id) == cited["document_id"] and c.page == cited["page"]))]
    unbacked = []
    for d in differences:
        numbers = _numbers(d.used)
        if not numbers or not all(any(_stated(n, q) for q in quotes) for n in numbers):
            unbacked.append(d.path)
    if unbacked:
        _note(result, "terms_drift", "difference_unbacked", "escalate",
              "the governing calculation differs from the approved terms without a verified quote from an "
              "agreement or amendment: " + ", ".join(unbacked))
        return True
    _note(result, "terms_drift", "terms_differ_from_approved", "flagged",
          "the governing calculation used terms that differ from the approved version; each difference is "
          "backed by a verified quote: " + ", ".join(d.path for d in differences))
    return False


# ---- the pipeline ----------------------------------------------------------------------------


def _write(db: Session, item: WorkItem, result: Investigation, run) -> Investigation:
    """The single write: the recommendation and its notes on the item, and a ledger event."""
    item.recommendation = {
        "agent": AGENT_ID, "agent_run_id": str(result.run_id) if result.run_id else None,
        "recommendation": result.recommendation, "model_recommendation": result.model_recommendation,
        "explanation": result.explanation, "explanation_rendered": result.explanation_rendered,
        "claims": result.claims, "calc_ids": result.calc_ids, "governing_calc_id": result.governing_calc_id,
        "suggested_tag": result.suggested_tag, "missing_evidence": result.missing_evidence}
    item.guardrail_notes = list(result.notes)
    if run is not None:
        run.guardrail_notes = list(result.notes)
        run.output = dict(item.recommendation)
    ledger.record(db, actor_type="agent", actor_id=AGENT_ID, action="covenant.recommendation_recorded",
                  entity_type="work_item", entity_id=item.id,
                  payload={"recommendation": result.recommendation,
                           "model_recommendation": result.model_recommendation,
                           "agent_run_id": result.run_id, "governing_calc_id": result.governing_calc_id,
                           "suggested_tag": result.suggested_tag, "claims": len(result.claims),
                           "notes": [{"check": n["check"], "action": n["action"]} for n in result.notes]})
    db.flush()
    return result


def investigate(db: Session, work_item: WorkItem, llm: LLMClient) -> Investigation:
    """Investigate one open covenant exception and attach a recommendation to it."""
    if work_item.item_type not in ITEM_TYPES:
        raise ValueError(f"the Covenant Agent does not investigate {work_item.item_type} items")
    if work_item.status != "open":
        raise ValueError("only an open work item is investigated")
    reference = work_item.evidence.get("covenant_test_id")
    test = db.get(CovenantTest, uuid.UUID(reference)) if reference else None
    if test is None or test.borrower_id != work_item.borrower_id:
        raise ValueError("the work item does not name a covenant test")
    borrower = db.get(Borrower, test.borrower_id)
    facility = db.get(Facility, test.facility_id)
    cycle = db.get(Cycle, work_item.cycle_id) if work_item.cycle_id else None
    months = cycle.months if cycle else ((test.period_end.month - borrower.fiscal_year_end_month) % 12) or 12
    scope = Scope(borrower_id=borrower.id, facility_id=facility.id, period_end=test.period_end, months=months,
                  cycle_id=cycle.id if cycle else None)

    outcome = run_agent(
        db, SPEC, task="investigate_covenant_exception", scope=scope,
        content=[{"type": "text", "text": _brief(work_item, test, borrower, facility)}], llm=llm, gateway=GATEWAY,
        record_key=f"covenant/{borrower.code}/{test.period_end}/{test.covenant_id}",
        state={"work_item_id": str(work_item.id), "covenant_test_id": str(test.id),
               "item_type": work_item.item_type})
    run = outcome.run
    result = Investigation(recommendation="abstain", run_id=run.id)

    # evidence is gathered by code: the originating test's calculation, then every calculation
    # this run logged, in order. The last one logged governs.
    origin = db.get(CalcRun, test.calc_run_id) if test.calc_run_id else None
    logged = run_calcs(db, run.id)
    calcs = ([origin] if origin is not None else []) + logged
    governing = logged[-1] if logged else origin
    known_calcs = {str(c.id) for c in calcs}
    result.governing_calc_id = str(governing.id) if governing is not None else None

    if not outcome.ok:
        # a failed, refused or capped run never reads as a recommendation
        _note(result, "runtime", outcome.reason or outcome.status, "abstain",
              {"step_cap": "the run reached its step cap before giving an answer",
               "schema": "the answer did not have the required shape",
               "refusal": "the model declined to answer"}.get(outcome.reason or "", "the run did not finish"))
        result.explanation = result.explanation_rendered = ABSTAIN_NO_ANSWER
        result.calc_ids = [str(c.id) for c in logged]
        return _write(db, work_item, result, run)

    answer: CovenantAnswer = outcome.output  # type: ignore[assignment]
    recommendation = result.model_recommendation = answer.recommendation
    approved_row, approved_version = covenant_service.governing_terms(db, facility, test.period_end)
    approved = approved_version.terms if approved_row is not None else None
    facts = _evidence_facts(db, test, calcs)
    thresholds = _thresholds(calcs, approved, test.covenant_id) if approved is not None else []
    ratios = thresholds if test.unit == "ratio" else []

    # 1. every quote is on the page it cites, or the claim goes
    surviving = _verify_claims(db, borrower.id, answer.claims, result)
    if answer.claims and not surviving:
        _note(result, "quotes", "no_claim_survived", "abstain", "none of the cited quotes was found on its page")
        recommendation = "abstain"

    # 2. no typed figure: fact references, figures inside verified quotes and known thresholds only
    allowed = thresholds + [f.value for c, _ in surviving for f in extract_figures(c.quote, ratios)]
    problems = check_narrative(answer.explanation, facts, allowed_figures=allowed, known_ratios=ratios)
    kept: list[tuple[Claim, Document]] = []
    for claim, doc in surviving:
        claim_problems = check_narrative(claim.text, facts, known_ratios=ratios,
                                         allowed_figures=thresholds + [f.value for f in extract_figures(claim.quote, ratios)])
        if claim_problems:
            _note(result, "narrative", claim_problems[0].check, "claim_dropped",
                  "a claim stated a figure that is not a fact reference: " + claim_problems[0].detail)
        else:
            kept.append((claim, doc))
    surviving = kept
    if problems:
        for p in problems:
            _note(result, p.layer, p.check, "abstain", p.detail)
        recommendation = "abstain"
    explanation_verified = not problems
    for entry in answer.missing_evidence:
        if check_narrative(entry, facts, allowed_figures=thresholds, known_ratios=ratios):
            _note(result, "narrative", "figure_untraceable", "dropped",
                  "an entry under missing evidence contained a typed figure and was removed")
        else:
            result.missing_evidence.append(entry)

    # 3. calculations the answer names must be ones in evidence
    for calc_id in answer.calc_ids:
        if calc_id.lower() in known_calcs:
            result.calc_ids.append(calc_id.lower())
        else:
            _note(result, "evidence", "unknown_calc_id", "flagged",
                  "the answer names a calculation that was not run for this exception")

    # 4. terms drift: a resolve cannot rest on terms that differ from the approved version
    #    unless every difference is quoted from an agreement or amendment on file
    passed = headroom_pct = None
    if governing is not None:
        passed = governing.outputs.get("passed")
        raw = governing.outputs.get("headroom_pct")
        headroom_pct = Decimal(str(raw)) if raw is not None else None
        if approved is None:
            drifted = True
            _note(result, "terms_drift", "no_terms_in_force", "escalate", "no approved terms cover this period")
        else:
            drifted = _terms_drift(governing, approved_row, approved, surviving, result)
        if drifted and recommendation == "resolve":
            recommendation = "escalate"

    # 5. policy has the last word and only ever makes the recommendation more cautious
    text = " ".join([answer.explanation, *(c.text for c, _ in surviving), *result.missing_evidence])
    policy = apply_policy(recommendation, text=text, steps_count=run.steps_count, governing_passed=passed,
                          governing_headroom_pct=headroom_pct, surviving_claims=len(surviving), settings=POLICY)
    _take(result, policy.notes)
    result.recommendation = policy.recommendation

    result.claims = [{"text": c.text, "document_id": str(doc.id), "document_title": doc.title,
                      "document_type": doc.doc_type, "page": c.page, "quote": c.quote} for c, doc in surviving]
    if result.recommendation == "abstain" and not (answer.recommendation == "abstain" and explanation_verified):
        # an abstain forced by a guardrail shows nothing the model wrote
        result.explanation = result.explanation_rendered = ABSTAIN_UNVERIFIED
    else:
        result.explanation = answer.explanation
        result.explanation_rendered = render(answer.explanation, facts)
        result.suggested_tag = answer.suggested_tag
    return _write(db, work_item, result, run)

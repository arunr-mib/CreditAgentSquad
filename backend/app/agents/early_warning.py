"""Early Warning Agent: explain and rank the signals that code already fired.

One model call, no tools. Rules in code decide what fires; the agent may only say why a signal
matters and in what order to read them. It cannot create, change or suppress a signal: an id it
invents is ignored, and a signal it leaves out keeps its place. Every figure in an explanation
must be a reference to a fact that code gathered from the signal's basis.
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.tools import Scope, ToolGateway
from app.calc import signals as sig
from app.calc.expr import ENGINE_VERSION
from app.core import ledger
from app.domain.covenant_service import fact_provider
from app.domain.credit import Borrower
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import Signal
from app.guardrails.narrative import FactView, check_narrative, format_fact, render
from app.guardrails.numbers import same_number
from app.guardrails.policy import PROHIBITED_PHRASES

MAX_WORDS = 80
ACTOR = ("system", "early_warning")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
RULES = {rule.id: rule for rule in sig.RULES}
METRIC_UNITS = {"revenue_ttm": "usd", "net_income_ttm": "usd", "cash": "usd", "ebitda_margin": "pct",
                "dso": "days", "dpo": "days", "leverage": "ratio"}
METRIC_WORDS = {"revenue_ttm": "revenue, trailing twelve months", "net_income_ttm": "net income, trailing twelve months",
                "cash": "cash", "ebitda_margin": "EBITDA margin", "dso": "days sales outstanding",
                "dpo": "days payables outstanding", "leverage": "debt to EBITDA"}
SYSTEM_KEYS = {"revolver_outstanding": ("sys.revolver_outstanding", "revolver balance in the loan system"),
               "commitment": ("sys.commitment", "revolver commitment in the loan system"),
               "past_due_days": ("sys.past_due_days", "days past due in the loan system")}
RULE_WORDS = {
    "covenant_headroom_low": "a covenant's headroom is below the bank's trigger",
    "covenant_headroom_falling": "a covenant's headroom has fallen two periods running",
    "revenue_ttm_decline": "trailing revenue is down on a year earlier by more than the trigger",
    "ebitda_margin_decline": "EBITDA margin is down on a year earlier by more than the trigger",
    "dso_increase": "receivables are being collected more slowly than a year earlier",
    "dpo_increase": "suppliers are being paid more slowly than a year earlier",
    "leverage_increase": "debt to EBITDA is up on a year earlier by more than the trigger",
    "net_loss": "the borrower made a net loss over the trailing twelve months",
    "cash_decline": "cash is down on a year earlier by more than the trigger",
    "line_usage_high": "the revolver is drawn beyond the trigger share of its commitment",
    "availability_low": "borrowing base availability is below the trigger share of the commitment",
    "reporting_late": "a required report is late beyond the trigger",
    "payment_past_due": "a payment is past due beyond the trigger",
    "auditor_opinion": "the auditor's opinion is qualified or raises going concern doubt",
}


class SignalExplanation(BaseModel):
    signal_id: str
    explanation: str


class EarlyWarningAnswer(BaseModel):
    explanations: list[SignalExplanation]
    ranking: list[str]  # signal ids, the one a reviewer should read first at the top


SPEC = AgentSpec(name="early_warning", version="1",
                 purpose="Explain and rank the early warning signals that code fired; cannot add or remove one.",
                 prompt_file="early_warning.md", output_model=EarlyWarningAnswer, tools=(), effort="medium",
                 max_tokens=8000)
AGENT_ID = f"{SPEC.name}@{SPEC.version}"


@dataclass
class ExplainResult:
    run_id: uuid.UUID | None = None
    explained: list[str] = field(default_factory=list)  # signal ids whose explanation was stored
    ranking: list[str] = field(default_factory=list)  # signal ids in stored rank order
    notes: list[dict[str, Any]] = field(default_factory=list)  # {layer, check, action, detail}


# ---- the facts behind a signal, gathered by code ---------------------------------------------


@dataclass
class _Gatherer:
    """Finds, and where needed stores, the facts behind each figure in a signal's basis. A figure
    the rules computed (a trailing metric, a year-on-year change) becomes a calculated fact with
    a calculation record naming the facts it was computed from, so it can be referenced like any
    other figure. Code only stores a figure it can recompute to the same value."""

    db: Session
    borrower: Borrower
    inputs: dict[date, sig.SignalInputs] = field(default_factory=dict)

    def _measured(self, end: date) -> sig.SignalInputs:
        if end not in self.inputs:
            self.inputs[end] = sig.compute_signal_inputs(
                end, fact_provider(self.db, self.borrower.id), fye_month=self.borrower.fiscal_year_end_month)
        return self.inputs[end]

    def _own(self, fact_id: Any) -> Fact | None:
        try:
            fact = self.db.get(Fact, uuid.UUID(str(fact_id)))
        except ValueError:
            return None
        return fact if fact is not None and fact.borrower_id == self.borrower.id else None

    def _derived(self, *, key: str, end: date, value: Decimal, unit: str, formula_key: str,
                 inputs: list[dict[str, Any]]) -> Fact:
        value = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        existing = current_fact(self.db, self.borrower.id, key, end, 0)
        if existing is not None and existing.kind == "calculated" and same_number(existing.value, value):
            return existing
        calc = CalcRun(borrower_id=self.borrower.id, formula_key=formula_key, formula_version=sig.SIGNALS_VERSION,
                       period_end=end, inputs=inputs, outputs={key: str(value)}, engine_version=ENGINE_VERSION,
                       created_by_type=ACTOR[0], created_by_id=ACTOR[1])
        self.db.add(calc)
        self.db.flush()
        return add_fact(self.db, borrower_id=self.borrower.id, key=key, period_end=end, months=0, value=value,
                        unit=unit, kind="calculated", calc_run_id=calc.id, actor=ACTOR)

    def _metric(self, metric: str, point: dict[str, Any]) -> Fact | None:
        if point.get("fact_id"):
            return self._own(point["fact_id"])
        if metric not in METRIC_UNITS:
            return None
        end, value = date.fromisoformat(point["period_end"]), Decimal(str(point["value"]))
        measured = self._measured(end)
        if measured.values.get(metric) is None or not same_number(measured.values[metric], value):
            return None
        return self._derived(key=f"signal.{metric}", end=end, value=value, unit=METRIC_UNITS[metric],
                             formula_key=f"signal_input.{metric}",
                             inputs=[i.to_dict() for i in measured.traces[metric].inputs])

    def facts(self, signal: Signal) -> list[tuple[str, Fact]]:
        basis, out = signal.basis or {}, []
        rule = RULES.get(signal.rule_id)
        covenant_id, metric = basis.get("covenant_id"), basis.get("metric")
        if covenant_id:
            for point in basis.get("values") or [basis.get("current")]:
                end = date.fromisoformat(point["period_end"])
                fact = current_fact(self.db, self.borrower.id, f"cov.{covenant_id}.headroom_pct", end, 0)
                if fact is not None and same_number(fact.value, Decimal(str(point["value"]))):
                    out.append((f"{covenant_id} headroom at {end.isoformat()}", fact))
            for name in ("value", "threshold"):
                fact = current_fact(self.db, self.borrower.id, f"cov.{covenant_id}.{name}", signal.period_end, 0)
                if fact is not None:
                    out.append((f"{covenant_id} {name} at {signal.period_end.isoformat()}", fact))
        elif metric:
            points = [(name, basis[name]) for name in ("current", "prior") if isinstance(basis.get(name), dict)]
            found = [(name, point, self._metric(metric, point)) for name, point in points]
            for _name, point, fact in found:
                if fact is not None:
                    out.append((f"{METRIC_WORDS.get(metric, metric)} at {point['period_end']}", fact))
            if basis.get("change") is not None and len(found) == 2 and all(f is not None for _, _, f in found):
                unit = "pct" if rule is not None and rule.kind == "pct_decrease" else METRIC_UNITS.get(metric, "count")
                change = self._derived(
                    key=f"signal.{signal.rule_id}.change", end=signal.period_end, value=Decimal(str(basis["change"])),
                    unit=unit, formula_key=f"signal.{signal.rule_id}",
                    inputs=[{"key": f.key, "period_end": f.period_end.isoformat(), "months": f.months,
                             "value": str(f.value), "fact_id": str(f.id)} for _, _, f in found])
                out.append((f"change in {METRIC_WORDS.get(metric, metric)} on a year earlier", change))
        if basis.get("date"):
            day, system = date.fromisoformat(str(basis["date"])), []
            for name, (key, words) in SYSTEM_KEYS.items():
                if basis.get(name) is None:
                    continue
                fact = current_fact(self.db, self.borrower.id, key, day, 0)
                if fact is not None and same_number(fact.value, Decimal(str(basis[name]))):
                    system.append(fact)
                    out.append((f"{words} at {day.isoformat()}", fact))
            availability = basis.get("availability")
            if isinstance(availability, dict) and availability.get("fact_id"):
                fact = self._own(availability["fact_id"])
                if fact is not None:
                    system.append(fact)
                    out.append((f"borrowing base availability at {availability['period_end']}", fact))
            for name, words in (("usage", "share of the commitment drawn"), ("ratio", "availability as a share of the commitment")):
                if basis.get(name) is not None and len(system) >= 2:
                    out.append((words, self._derived(
                        key=f"signal.{signal.rule_id}.{name}", end=signal.period_end, value=Decimal(str(basis[name])),
                        unit="pct", formula_key=f"signal.{signal.rule_id}",
                        inputs=[{"key": f.key, "period_end": f.period_end.isoformat(), "months": f.months,
                                 "value": str(f.value), "fact_id": str(f.id)} for f in system])))
        if basis.get("fact_id"):  # a fact the rule itself carried, such as a quoted auditor's opinion
            fact = self._own(basis["fact_id"])
            if fact is not None:
                out.append((f"{signal.rule_id.replace('_', ' ')} as recorded", fact))
        return out


def _threshold(signal: Signal) -> list[Decimal]:
    value = (signal.basis or {}).get("threshold")
    return [] if value is None else [Decimal(str(value))]


# ---- explain and rank ------------------------------------------------------------------------


def _note(result: ExplainResult, layer: str, check: str, action: str, detail: str) -> None:
    result.notes.append({"layer": layer, "check": check, "action": action, "detail": detail})


def _code_order(signals: list[Signal]) -> list[Signal]:
    return sorted(signals, key=lambda s: (SEVERITY_ORDER.get(s.severity, 9), s.rule_id,
                                          str((s.basis or {}).get("subject") or ""), str(s.id)))


def explain_signals(db: Session, borrower: Borrower, period_end: date, llm: LLMClient) -> ExplainResult:
    """Ask the agent to explain and rank the period's signals; store what passes the checks."""
    result = ExplainResult()
    signals = _code_order(list(db.execute(select(Signal).where(
        Signal.borrower_id == borrower.id, Signal.period_end == period_end)).scalars()))
    if not signals:
        return result
    gatherer = _Gatherer(db, borrower)
    views: dict[str, FactView] = {}
    listing = []
    for signal in signals:
        facts = gatherer.facts(signal)
        for _label, fact in facts:
            views[str(fact.id)] = FactView(str(fact.id), fact.value, fact.unit)
        listing.append({
            "signal_id": str(signal.id), "rule_id": signal.rule_id, "severity": signal.severity,
            "subject": (signal.basis or {}).get("subject"),
            "what_fired": RULE_WORDS.get(signal.rule_id, signal.rule_id.replace("_", " ")),
            "facts": [{"fact_id": str(f.id), "what": label, "value": format_fact(views[str(f.id)])}
                      for label, f in facts]})
    content = [
        {"type": "text", "text": (
            f"Borrower: {borrower.name} ({borrower.industry}). Period ended {period_end:%B %-d, %Y}. "
            f"The bank's rules fired the {len(signals)} early warning signals listed below as JSON. Explain "
            "each one and rank them all.")},
        {"type": "text", "text": json.dumps({"signals": listing}, indent=1)}]
    cycle_id = next((s.cycle_id for s in signals if s.cycle_id), None)
    scope = Scope(borrower_id=borrower.id, period_end=period_end, cycle_id=cycle_id)
    outcome = run_agent(db, SPEC, task="explain_signals", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"early_warning/{borrower.code}/{period_end}")
    result.run_id = outcome.run.id
    if not outcome.ok:
        _note(result, "runtime", outcome.reason or outcome.status, "nothing_stored",
              "the Early Warning Agent returned no usable answer; the signals stand as code fired them")
        outcome.run.guardrail_notes = list(result.notes)
        db.flush()
        return result
    answer: EarlyWarningAnswer = outcome.output  # type: ignore[assignment]
    known = {str(s.id): s for s in signals}

    seen: set[str] = set()
    for entry in answer.explanations:
        signal_id, text = entry.signal_id.strip().lower(), entry.explanation.strip()
        signal = known.get(signal_id)
        if signal is None:
            _note(result, "scope", "unknown_signal", "ignored",
                  "the answer explained a signal that code did not fire; it was ignored")
            continue
        if signal_id in seen or not text:
            continue
        seen.add(signal_id)
        problems = check_narrative(text, views, allowed_figures=_threshold(signal))
        phrase = next((p for p in PROHIBITED_PHRASES if p in text.lower()), None)
        if problems:
            _note(result, "narrative", problems[0].check, "explanation_dropped",
                  f"{signal.rule_id}: {problems[0].detail}")
        elif phrase:
            _note(result, "policy", "prohibited_phrase", "explanation_dropped",
                  f"{signal.rule_id}: proposes an action reserved for a person ({phrase})")
        elif len(text.split()) > MAX_WORDS:
            _note(result, "narrative", "too_long", "explanation_dropped",
                  f"{signal.rule_id}: the explanation is longer than {MAX_WORDS} words")
        else:
            signal.explanation = {"text": text, "rendered": render(text, views), "agent": AGENT_ID,
                                  "agent_run_id": str(outcome.run.id)}
            result.explained.append(signal_id)

    # the ranking orders the signals code fired, all of them and nothing else
    order: list[str] = []
    for raw in answer.ranking:
        signal_id = raw.strip().lower()
        if signal_id not in known:
            _note(result, "scope", "unknown_signal", "ignored", "the ranking named a signal that code did not fire")
        elif signal_id not in order:
            order.append(signal_id)
    left_out = [str(s.id) for s in signals if str(s.id) not in order]
    if left_out:
        _note(result, "scope", "ranking_incomplete", "completed_by_code",
              f"{len(left_out)} signal(s) were left out of the ranking and were placed after the rest by severity")
    result.ranking = order + left_out
    for position, signal_id in enumerate(result.ranking, start=1):
        known[signal_id].rank = position

    outcome.run.guardrail_notes = list(result.notes)
    ledger.record(db, actor_type="agent", actor_id=AGENT_ID, action="signals.explained", entity_type="borrower",
                  entity_id=borrower.id,
                  payload={"period_end": period_end, "agent_run_id": outcome.run.id, "signals": len(signals),
                           "explained": len(result.explained), "ranking": result.ranking,
                           "notes": [{"check": n["check"], "action": n["action"]} for n in result.notes]})
    db.flush()
    return result

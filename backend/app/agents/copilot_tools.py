"""Read-only tools for the Copilot: look things up about one borrower or across the portfolio.

- Every tool is registered with `writes=False`. None of them changes a borrower, loan, fact,
  term, test, signal, work item or document. The one thing a tool may add is a derived metric:
  `metrics` asks the metrics service for a library metric, and that service keeps the result as
  a calculated fact on first use (so the figure has an id to reference, like any other figure).
  Nothing that already exists is touched.
- No tool takes a borrower, loan or cycle id. The borrower is the one the conversation is
  scoped to, or the one `find_borrower` opened, and `find_borrower` only ever opens a borrower
  that exists. A period end is the only scope a tool input may choose, and a period that has
  nothing on file comes back empty or refused, never guessed.
- Every figure a tool returns comes with the id of its stored fact. Each such fact is recorded
  in the run's working memory; after the run, only those facts are in scope for the answer.
"""
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select

from app.agents.doc_tools import DOCUMENT_TOOLS, borrower_in_scope
from app.agents.tools import Refusal, Tool, ToolContext, ToolGateway, ToolInput
from app.api.serialize import plain
from app.calc import metrics as lib
from app.calc import template
from app.core import clock
from app.domain import metrics_service, review_service
from app.domain.covenant_service import fact_provider, governing_terms
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import current_fact
from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, CycleStage, Signal, WorkItem
from app.domain.org import User
from app.domain.reviews import ReviewSheet
from app.domain.terms import ReportingObligation, TermsVersion
from app.guardrails.narrative import FactView

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
OUTCOME_RANK = {"breach_reported_compliant": 4, "breach": 3, "cannot_test": 2, "compliant_variance": 1, "compliant": 0}
_NAME_NOISE = {"inc", "llc", "corp", "corporation", "company", "co", "ltd", "lp", "the", "and"}
_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
          "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")
MAX_KEYS, MAX_PERIODS, MAX_ROWS = 40, 8, 50
NOT_A_FACT = "not a stored fact: describe it in words, do not type it as a figure"


# ---- working memory -------------------------------------------------------------------------

def facts_seen(ctx: ToolContext) -> dict[str, FactView]:
    """Facts returned by tools in this run, by id. Shared with the caller of the run."""
    return ctx.state.setdefault("facts", {})


def borrowers_seen(ctx: ToolContext) -> set[uuid.UUID]:
    return ctx.state.setdefault("borrowers", set())


def ref(ctx: ToolContext, fact: Fact | None) -> dict[str, Any] | None:
    """A fact as the model sees it. Recording it here is what puts it in scope for the answer."""
    if fact is None:
        return None
    facts_seen(ctx)[str(fact.id)] = FactView(str(fact.id), fact.value, fact.unit)
    return {"fact_id": str(fact.id), "value": plain(fact.value), "unit": fact.unit}


def _fact_by_id(ctx: ToolContext, reference: Any, borrower_id: uuid.UUID) -> Fact | None:
    try:
        fact = ctx.db.get(Fact, uuid.UUID(str(reference)))
    except ValueError:
        return None
    return fact if fact is not None and fact.borrower_id == borrower_id else None


def _borrower(ctx: ToolContext) -> Borrower:
    borrower = ctx.db.get(Borrower, borrower_in_scope(ctx))
    if borrower is None:
        raise Refusal("no borrower is open; open a borrower first")
    borrowers_seen(ctx).add(borrower.id)
    return borrower


def in_words(n: int | None) -> str | None:
    if n is None:
        return None
    return _WORDS[n] if 0 <= n < len(_WORDS) else "more than twenty"


def _period(text: str | None) -> date | None:
    if text is None or not text.strip():
        return None
    try:
        return date.fromisoformat(text.strip())
    except ValueError as exc:
        raise Refusal("a period end is written as a date, for example 2026-09-30") from exc


def _latest_cycle(ctx: ToolContext, borrower_id: uuid.UUID) -> Cycle | None:
    return ctx.db.execute(select(Cycle).where(Cycle.borrower_id == borrower_id)
                          .order_by(Cycle.period_end.desc())).scalars().first()


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


class NoInput(ToolInput):
    pass


class PeriodInput(ToolInput):
    period_end: str | None = None


# ---- find and open a borrower ---------------------------------------------------------------

class FindInput(ToolInput):
    name: str


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _NAME_NOISE and len(w) > 1]


def _find_borrower(ctx: ToolContext, args: FindInput) -> dict:
    wanted = _tokens(args.name)
    if not wanted:
        raise Refusal("the name has no searchable words")
    matches = []
    for b in ctx.db.execute(select(Borrower).order_by(Borrower.name)).scalars():
        have = _tokens(b.name) + _tokens(b.code)
        if all(any(h.startswith(w) for h in have) for w in wanted):
            matches.append(b)
    exact = [b for b in matches if _tokens(b.name) == wanted or b.code.lower() == args.name.strip().lower()]
    chosen = exact[0] if len(exact) == 1 else matches[0] if len(matches) == 1 else None
    listed = [{"name": b.name, "industry": b.industry} for b in matches[:10]]
    if not matches:
        return {"found": False, "matches": [], "opened": None,
                "message": "not found: no borrower on file matches this name. Say so; do not guess."}
    if chosen is None:
        return {"found": True, "matches": listed, "opened": None,
                "message": "several borrowers match; ask which one is meant, or search with the full name"}
    fixed = ctx.scope.borrower_id
    if fixed is not None and fixed != chosen.id:
        raise Refusal("this conversation is about another borrower, so a different one cannot be opened here; "
                      "use portfolio_query to compare borrowers, or ask in a portfolio conversation")
    ctx.state["borrower_id"] = chosen.id
    ctx.state.setdefault("opened", []).append(chosen.id)
    borrowers_seen(ctx).add(chosen.id)
    return {"found": True, "matches": listed, "opened": {"name": chosen.name, "industry": chosen.industry},
            "message": "this borrower is now open; the other tools read it"}


# ---- overview -------------------------------------------------------------------------------

def _system_fact(ctx: ToolContext, borrower_id: uuid.UUID, key: str) -> Fact | None:
    """The latest system-of-record fact for a key."""
    return ctx.db.execute(select(Fact).where(
        Fact.borrower_id == borrower_id, Fact.key == key, Fact.status.in_(("verified", "confirmed")))
        .order_by(Fact.period_end.desc(), Fact.seq.desc()).limit(1)).scalar_one_or_none()


def _exposure(ctx: ToolContext, borrower_id: uuid.UUID) -> dict[str, Any]:
    out = {}
    for name, key in (("revolver_commitment", "sys.commitment"), ("revolver_outstanding", "sys.revolver_outstanding"),
                      ("term_loan_outstanding", "sys.term_loan_outstanding")):
        fact = _system_fact(ctx, borrower_id, key)
        if fact is not None:
            out[name] = {**ref(ctx, fact), "as_of": fact.period_end.isoformat()}
    return out


def _item_out(ctx: ToolContext, item: WorkItem, *, detail: bool = False) -> dict[str, Any]:
    out = {"type": item.item_type, "severity": item.severity, "title": item.title, "stage": item.stage,
           "status": item.status, "due_date": _iso(item.due_date)}
    if detail:
        evidence = item.evidence or {}
        facts = [ref(ctx, _fact_by_id(ctx, evidence.get(k), item.borrower_id))
                 for k in ("value_fact_id", "reported_fact_id") if evidence.get(k)]
        out.update({
            "question": item.question, "decisions_a_person_may_take": item.allowed_decisions,
            "needs_a_second_person": item.requires_second_person, "decision": item.decision,
            "calculation_id": evidence.get("calc_run_id"), "evidence_facts": [f for f in facts if f],
            "agent_recommendation": (item.recommendation or {}).get("recommendation"),
            "note": "figures inside a title or question are " + NOT_A_FACT})
    return out


def _overview(ctx: ToolContext, args: NoInput) -> dict:
    b = _borrower(ctx)
    db = ctx.db
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    loans = [{"name": f.name, "type": f.facility_type, "has_borrowing_base": f.has_borrowing_base,
              "origination_date": _iso(f.origination_date), "maturity_date": _iso(f.maturity_date)}
             for f in db.execute(select(Facility).where(Facility.borrower_id == b.id).order_by(Facility.code)).scalars()]
    cycle = _latest_cycle(ctx, b.id)
    stage = None
    if cycle is not None:
        stages = db.execute(select(CycleStage).where(CycleStage.cycle_id == cycle.id)
                            .order_by(CycleStage.position)).scalars()
        stage = {"period_end": cycle.period_end.isoformat(), "stage": cycle.stage, "status": cycle.status,
                 "due_date": _iso(cycle.due_date),
                 "stages": [{"stage": s.stage, "status": s.status} for s in stages]}
    items = sorted(db.execute(select(WorkItem).where(WorkItem.borrower_id == b.id, WorkItem.status == "open")).scalars(),
                   key=lambda w: (SEVERITY_RANK.get(w.severity, 9), w.created_at))
    signals = db.execute(select(func.count()).select_from(Signal).where(
        Signal.borrower_id == b.id, Signal.status == "open")).scalar_one()
    return {
        "name": b.name, "industry": b.industry, "fiscal_year_end_month": f"{date(2000, b.fiscal_year_end_month, 1):%B}",
        "risk_rating": {"in_words": in_words(b.risk_rating), "note": NOT_A_FACT},
        "relationship_manager": users.get(b.relationship_manager_id), "analyst": users.get(b.analyst_id),
        "loans": loans, "exposure_from_the_system_of_record": _exposure(ctx, b.id), "latest_cycle": stage,
        "open_work_items": {"count_in_words": in_words(len(items)), "items": [_item_out(ctx, w) for w in items]},
        "open_signals": {"count_in_words": in_words(signals)},
    }


# ---- covenant tests and calculations --------------------------------------------------------

def _test_out(ctx: ToolContext, test: CovenantTest, loans: dict[uuid.UUID, str]) -> dict[str, Any]:
    db = ctx.db
    cid, end = test.covenant_id, test.period_end
    return {
        "covenant": test.covenant_name, "loan": loans.get(test.facility_id), "period_end": end.isoformat(),
        "outcome": test.outcome, "passed": test.passed, "operator": test.operator,
        "value": ref(ctx, db.get(Fact, test.value_fact_id) if test.value_fact_id else None),
        "threshold": ref(ctx, current_fact(db, test.borrower_id, f"cov.{cid}.threshold", end, 0)),
        "headroom_pct": ref(ctx, current_fact(db, test.borrower_id, f"cov.{cid}.headroom_pct", end, 0)),
        "reported_on_certificate": ref(ctx, db.get(Fact, test.reported_fact_id) if test.reported_fact_id else None),
        "certificate_claims_compliance": test.reported_in_compliance,
        "calculation_id": str(test.calc_run_id) if test.calc_run_id else None,
        "cannot_test_because": test.error,
    }


def _covenant_tests(ctx: ToolContext, args: PeriodInput) -> dict:
    b = _borrower(ctx)
    db = ctx.db
    base = select(CovenantTest).where(CovenantTest.borrower_id == b.id, CovenantTest.superseded.is_(False))
    periods = sorted({t for t in db.execute(select(CovenantTest.period_end).where(
        CovenantTest.borrower_id == b.id, CovenantTest.superseded.is_(False))).scalars()})
    end = _period(args.period_end) or (periods[-1] if periods else None)
    if end is None:
        return {"tests": [], "periods_tested": [], "message": "no covenant test is on file for this borrower"}
    loans = {f.id: f.name for f in db.execute(select(Facility).where(Facility.borrower_id == b.id)).scalars()}
    tests = [_test_out(ctx, t, loans) for t in db.execute(
        base.where(CovenantTest.period_end == end).order_by(CovenantTest.covenant_name)).scalars()]
    return {"period_end": end.isoformat(), "tests": tests, "periods_tested": [p.isoformat() for p in periods],
            "message": None if tests else "no covenant test is on file for this period",
            "note": "headroom_pct is a fraction of the threshold; reference it with the pct format"}


class CalculationInput(ToolInput):
    calculation_id: str


def _calculation(ctx: ToolContext, args: CalculationInput) -> dict:
    b = _borrower(ctx)
    try:
        calc = ctx.db.get(CalcRun, uuid.UUID(args.calculation_id.strip()))
    except ValueError:
        calc = None
    if calc is None or calc.borrower_id != b.id:
        raise Refusal("no such calculation for this borrower; use a calculation_id returned by another tool")
    inputs: list[dict[str, Any]] = []
    if isinstance(calc.inputs, list):
        for item in calc.inputs:
            if not isinstance(item, dict):
                continue
            fact = _fact_by_id(ctx, item.get("fact_id"), b.id)
            line = template.line_info(str(item.get("key", "")))
            inputs.append({
                "line": item.get("key"), "label": line.label if line else None, "period_end": item.get("period_end"),
                "months": item.get("months"), "fact": ref(ctx, fact),
                "role": "subtracted" if item.get("sign") == -1 else "added",
                **({} if fact else {"note": "this input is not a stored fact"})})
    results = [{"key": f.key, **ref(ctx, f)} for f in ctx.db.execute(
        select(Fact).where(Fact.calc_run_id == calc.id, Fact.borrower_id == b.id).order_by(Fact.key)).scalars()]
    trace = calc.trace or {}
    return {
        "calculation_id": str(calc.id), "formula": calc.formula_key, "formula_version": calc.formula_version,
        "engine_version": calc.engine_version, "period_end": calc.period_end.isoformat(),
        "inputs": inputs, "results": results, "error": calc.error,
        "outcome": {k: (calc.outputs or {}).get(k) for k in ("passed", "operator") if k in (calc.outputs or {})},
        "addbacks": [{"name": a.get("name"), "capped": a.get("capped"), "cap_type": a.get("cap_type")}
                     for a in trace.get("addbacks", [])],
        "steps": [{"op": s.get("op"), "label": s.get("label")} for s in trace.get("steps", []) if s.get("label")],
        "note": ("a trailing-twelve-month line is the year-to-date fact, plus the prior full year, less the "
                 "prior-year year-to-date fact. Intermediate totals are not stored facts: for totals such as "
                 "EBITDA or total debt use the metrics tool."),
    }


# ---- spread lines ---------------------------------------------------------------------------

class SpreadInput(ToolInput):
    keys: list[str]
    period_ends: list[str]


def _spread_lines(ctx: ToolContext, args: SpreadInput) -> dict:
    b = _borrower(ctx)
    if not args.keys:
        return {"lines_available": [{"key": line.key, "label": line.label, "statement": line.statement}
                                    for line in template.template_lines(b.template_id)],
                "message": "call again with the keys you need"}
    if len(args.keys) > MAX_KEYS or len(args.period_ends) > MAX_PERIODS:
        raise Refusal("ask for fewer lines or periods at a time")
    unknown = [k for k in args.keys if template.line_info(k) is None
               or (k in template.ALL_LINE_BY_KEY and not template.in_template(k, b.template_id))]
    if unknown:
        raise Refusal(f"not template lines: {', '.join(unknown[:8])}; call with an empty keys list to see the lines")
    ends = [_period(p) for p in args.period_ends]
    if not ends or any(e is None for e in ends):
        raise Refusal("give at least one period end")
    fye = b.fiscal_year_end_month
    lines = []
    for key in dict.fromkeys(args.keys):
        line = template.line_info(key)
        values = []
        for end in ends:
            months = (((end.month - fye) % 12) or 12) if line.flow else 0
            fact = current_fact(ctx.db, b.id, key, end, months)
            entry: dict[str, Any] = {"period_end": end.isoformat(),
                                     "covers": f"fiscal year to date, {in_words(months)} months" if line.flow else "balance at the date"}
            if fact is None:
                entry["fact"] = None
                entry["note"] = "not on file for this period"
            else:
                entry["fact"] = ref(ctx, fact)
                entry["source"] = {"kind": fact.kind, "status": fact.status,
                                   "document_id": str(fact.document_id) if fact.document_id else None,
                                   "page": fact.page}
            values.append(entry)
        lines.append({"key": key, "label": line.label, "statement": line.statement, "values": values})
    return {"lines": lines}


# ---- metrics --------------------------------------------------------------------------------

class MetricsInput(ToolInput):
    names: list[str]
    period_end: str | None = None


METRIC_NAMES = tuple(dict.fromkeys([*lib.METRICS, *metrics_service.EXTRA]))


def _metrics(ctx: ToolContext, args: MetricsInput) -> dict:
    b = _borrower(ctx)
    names = list(dict.fromkeys(args.names)) or list(metrics_service.REVIEW_METRICS)
    unknown = [n for n in names if n not in METRIC_NAMES]
    if unknown:
        raise Refusal(f"unknown metrics: {', '.join(unknown[:8])}. Available: {', '.join(METRIC_NAMES)}")
    cycle = _latest_cycle(ctx, b.id)
    end = _period(args.period_end) or (cycle.period_end if cycle else None)
    if end is None:
        raise Refusal("no monitoring period is on file for this borrower; give a period end")
    out = []
    for name in names:
        fact = metrics_service.store_metric(ctx.db, b, name, end)
        entry: dict[str, Any] = {"metric": name, "fact": ref(ctx, fact)}
        if fact is None:
            entry["note"] = "cannot be measured from the facts on file for this period; it is unmeasured, not zero"
            if name in lib.METRICS:
                errors = lib.compute_metric(name, end, fact_provider(ctx.db, b.id), fye_month=b.fiscal_year_end_month).errors
                entry["missing"] = sorted({e.key for e in errors if e.key})
        else:
            entry["calculation_id"] = str(fact.calc_run_id) if fact.calc_run_id else None
        out.append(entry)
    return {"period_end": end.isoformat(), "library": lib.METRICS_VERSION, "metrics": out,
            "note": ("library definitions: flows are trailing twelve months, balances are at the date, percentages "
                     "are fractions. A covenant may define a ratio differently; for a covenant use covenant_tests.")}


# ---- signals --------------------------------------------------------------------------------

class SignalsInput(ToolInput):
    period_end: str | None = None
    include_closed: bool = False


def _basis_out(ctx: ToolContext, borrower_id: uuid.UUID, basis: dict[str, Any]) -> tuple[dict[str, Any], list[dict]]:
    """The basis in words, and the stored facts behind it."""
    facts: list[dict] = []
    covenant = basis.get("covenant_id")

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            fact = _fact_by_id(ctx, node.get("fact_id"), borrower_id) if node.get("fact_id") else None
            if fact is None and covenant and basis.get("metric") == "headroom_pct" and node.get("period_end"):
                try:
                    fact = current_fact(ctx.db, borrower_id, f"cov.{covenant}.headroom_pct",
                                        date.fromisoformat(str(node["period_end"])), 0)
                except ValueError:
                    fact = None
            if fact is not None:
                facts.append({"key": fact.key, "period_end": fact.period_end.isoformat(), **ref(ctx, fact)})
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(basis)
    words = {k: basis[k] for k in ("metric", "compare", "subject", "covenant_id", "requirement_id", "document_type")
             if basis.get(k) is not None}
    return words, facts


def _signals(ctx: ToolContext, args: SignalsInput) -> dict:
    b = _borrower(ctx)
    query = select(Signal).where(Signal.borrower_id == b.id)
    end = _period(args.period_end)
    if end is not None:
        query = query.where(Signal.period_end == end)
    if not args.include_closed:
        query = query.where(Signal.status == "open")
    rows = sorted(ctx.db.execute(query).scalars(),
                  key=lambda s: (-s.period_end.toordinal(), SEVERITY_RANK.get(s.severity, 9), s.rank or 999))
    out = []
    for s in rows[:MAX_ROWS]:
        words, facts = _basis_out(ctx, b.id, s.basis or {})
        out.append({"rule": s.rule_id, "severity": s.severity, "status": s.status,
                    "period_end": s.period_end.isoformat(), "about": words, "facts": facts,
                    "explanation": (s.explanation or {}).get("text")})
    return {"signals": out, "message": None if out else "no early warning signal matches",
            "note": ("signals are raised by rules in code. Where a signal lists no fact, get the figure from "
                     "metrics or covenant_tests for the period before stating it.")}


# ---- work items -----------------------------------------------------------------------------

class WorkItemsInput(ToolInput):
    include_decided: bool = False


def _work_items(ctx: ToolContext, args: WorkItemsInput) -> dict:
    b = _borrower(ctx)
    query = select(WorkItem).where(WorkItem.borrower_id == b.id)
    if not args.include_decided:
        query = query.where(WorkItem.status == "open")
    items = sorted(ctx.db.execute(query).scalars(), key=lambda w: (SEVERITY_RANK.get(w.severity, 9), w.created_at))
    return {"work_items": [_item_out(ctx, w, detail=True) for w in items[:MAX_ROWS]],
            "message": None if items else "no work item matches",
            "note": "decisions on work items are taken by a person in the work queue, never here"}


# ---- borrowing base -------------------------------------------------------------------------

def _borrowing_base(ctx: ToolContext, args: PeriodInput) -> dict:
    b = _borrower(ctx)
    query = select(BorrowingBaseReview).where(BorrowingBaseReview.borrower_id == b.id)
    end = _period(args.period_end)
    if end is not None:
        query = query.where(BorrowingBaseReview.period_end == end)
    reviews = list(ctx.db.execute(query.order_by(BorrowingBaseReview.period_end.desc(),
                                                 BorrowingBaseReview.created_at.desc())).scalars())
    if not reviews:
        return {"review": None, "message": "no borrowing base review is on file" + (" for this period" if end else "")}
    review = reviews[0]
    facility = ctx.db.get(Facility, review.facility_id)
    mismatched = [d.get("line") for d in review.differences or [] if d.get("status") != "match"]
    return {
        "review": {
            "loan": facility.name if facility else None, "period_end": review.period_end.isoformat(),
            "outcome": review.outcome,
            "availability": ref(ctx, current_fact(ctx.db, b.id, "bb.availability", review.period_end, 0)),
            "over_advanced": review.over_advance is not None and review.over_advance > 0,
            "lines_recalculated": sorted(review.computed or {}),
            "lines_that_differ_from_the_certificate": mismatched,
            "calculation_id": str(review.calc_run_id) if review.calc_run_id else None,
        },
        "other_review_dates": sorted({r.period_end.isoformat() for r in reviews[1:]}),
        "note": ("availability is negative when the line is over-advanced. The individual lines of the base are "
                 "not stored facts: to state one, quote it from the borrowing base certificate with a citation."),
    }


# ---- reporting calendar ---------------------------------------------------------------------

class CalendarInput(ToolInput):
    outstanding_only: bool = False


def _calendar(ctx: ToolContext, args: CalendarInput) -> dict:
    b = _borrower(ctx)
    query = select(ReportingObligation).where(ReportingObligation.borrower_id == b.id)
    if args.outstanding_only:
        query = query.where(ReportingObligation.status.in_(("due", "overdue")))
    rows = list(ctx.db.execute(query.order_by(ReportingObligation.due_date.desc())).scalars())
    return {
        "as_of": clock.today(ctx.db).isoformat(),
        "obligations": [{"requirement": ob.requirement_id, "document_type": ob.document_type,
                         "period_end": ob.period_end.isoformat(), "due_date": ob.due_date.isoformat(),
                         "status": ob.status, "received_date": _iso(ob.received_date),
                         "received_document_id": str(ob.received_document_id) if ob.received_document_id else None}
                        for ob in rows[:MAX_ROWS]],
        "message": None if rows else "no reporting obligation matches",
        "note": "dates may be written out; a count of days late is " + NOT_A_FACT,
    }


# ---- terms ----------------------------------------------------------------------------------

class TermsInput(ToolInput):
    version: int | None = None


def _citation_out(ctx: ToolContext, borrower_id: uuid.UUID, citation: dict[str, Any] | None) -> dict[str, Any] | None:
    if not citation:
        return None
    reference = citation.get("document_id")
    doc = ctx.db.execute(select(Document).where(
        Document.borrower_id == borrower_id, Document.meta["external_id"].astext == str(reference))).scalars().first()
    if doc is None:
        try:
            doc = ctx.db.get(Document, uuid.UUID(str(reference)))
        except ValueError:
            doc = None
        if doc is not None and doc.borrower_id != borrower_id:
            doc = None
    return {"document_id": str(doc.id) if doc else None, "document": doc.title if doc else "not on file",
            "page": citation.get("page"), "section": citation.get("section"), "quote": citation.get("quote")}


def _terms_body(ctx: ToolContext, borrower_id: uuid.UUID, terms: dict[str, Any]) -> dict[str, Any]:
    def cite(c):
        return _citation_out(ctx, borrower_id, c)

    covenants = [{"id": c.get("id"), "name": c.get("name"), "archetype": c.get("archetype"),
                  "operator": (c.get("test") or {}).get("operator"),
                  "has_step_changes": bool((c.get("test") or {}).get("steps")),
                  "measured": c.get("measurement"),
                  "clauses": [cite(x) for x in c.get("citations") or []]} for c in terms.get("covenants") or []]
    definitions = {name: {"base": d.get("base"),
                          "addbacks": [{"name": a.get("name"), "capped": a.get("cap") is not None,
                                        "clause": cite(a.get("citation"))} for a in d.get("addbacks") or []]}
                   for name, d in (terms.get("definitions") or {}).items()}
    reporting = [{"id": r.get("id"), "document_type": r.get("document_type"), "frequency": r.get("frequency"),
                  "quality": r.get("quality"), "clause": cite(r.get("citation"))}
                 for r in terms.get("reporting_requirements") or []]
    bb = terms.get("borrowing_base")
    base = None
    if bb:
        base = {"components": [c.get("collateral") for c in bb.get("components") or []],
                "reserves": [r.get("name") for r in bb.get("reserves") or []],
                "clauses": [cite(c) for c in [bb.get("citation"), *(bb.get("citations") or [])] if c]}
    return {"covenants": covenants, "definitions": definitions, "reporting_requirements": reporting,
            "borrowing_base": base}


def _terms(ctx: ToolContext, args: TermsInput) -> dict:
    b = _borrower(ctx)
    db = ctx.db
    cycle = _latest_cycle(ctx, b.id)
    as_of = cycle.period_end if cycle else clock.today(db)
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    loans = []
    for facility in db.execute(select(Facility).where(Facility.borrower_id == b.id).order_by(Facility.code)).scalars():
        versions = list(db.execute(select(TermsVersion).where(TermsVersion.facility_id == facility.id)
                                   .order_by(TermsVersion.version)).scalars())
        if not versions:
            continue
        governing, _ = governing_terms(db, facility, as_of)
        shown = governing
        if args.version is not None:
            shown = next((v for v in versions if v.version == args.version), None)
            if shown is None:
                continue
        loans.append({
            "loan": facility.name,
            "versions": [{"version": f"version {v.version}", "status": v.status, "effective_from": _iso(v.effective_from),
                          "effective_to": _iso(v.effective_to), "approved_by": users.get(v.approved_by),
                          "governs_the_latest_period": governing is not None and v.id == governing.id,
                          "note": "proposed terms never govern a test" if v.status == "proposed" else None}
                         for v in versions],
            "shown": None if shown is None else {
                "version": f"version {shown.version}", "status": shown.status,
                **_terms_body(ctx, b.id, shown.terms or {})},
        })
    if not loans:
        return {"loans": [], "message": "no terms are on file for this borrower"
                + (" with that version" if args.version is not None else "")}
    return {"as_of_period": as_of.isoformat(), "loans": loans,
            "note": ("thresholds, caps, rates and day counts in the terms are not stored facts: state one by quoting "
                     "its clause with a citation, or use the threshold fact from covenant_tests.")}


# ---- review sheet ---------------------------------------------------------------------------

def _review_sheet(ctx: ToolContext, args: NoInput) -> dict:
    b = _borrower(ctx)
    db = ctx.db
    found = db.execute(select(ReviewSheet, Cycle).join(Cycle, Cycle.id == ReviewSheet.cycle_id).where(
        ReviewSheet.borrower_id == b.id).order_by(Cycle.period_end.desc())).first()
    if found is None:
        return {"review_sheet": None, "message": "no review sheet has been prepared for this borrower"}
    sheet, cycle = found
    content = dict(sheet.content or {})
    labels = content.pop("fact_labels", {}) or {}
    facts = []
    for fid, label in labels.items():
        fact = _fact_by_id(ctx, fid, b.id)
        if fact is not None:
            facts.append({"what": label, **ref(ctx, fact)})
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    commentary = []
    for c in review_service.current_commentary(db, sheet):
        for fid in c.fact_ids or []:
            ref(ctx, _fact_by_id(ctx, fid, b.id))
        approved = c.status == "approved"
        commentary.append({
            "section": c.section, "status": c.status,
            "standing": (f"approved by {users.get(c.approved_by, 'a person')}" if approved else
                         "DRAFT, not approved" + (", written by the Review Agent" if c.author_type == "agent" else "")),
            "text_with_references": c.body})
    return {"review_sheet": {"period_end": cycle.period_end.isoformat(), "status": sheet.status,
                             "approved_by": users.get(sheet.approved_by), "content": content, "facts": facts,
                             "commentary": commentary},
            "note": "when you draw on draft commentary, say that it is a draft that no person has approved"}


# ---- portfolio ------------------------------------------------------------------------------

class PortfolioInput(ToolInput):
    covenant_status: Literal["any", "breach", "cannot_test", "variance", "compliant"] = "any"
    headroom_below_percent: int | None = None
    min_signal_severity: Literal["any", "low", "medium", "high"] = "any"
    open_items_only: bool = False
    rank_by: Literal["headroom", "covenant_status", "signals", "open_items", "exposure", "name"] = "covenant_status"
    limit: int = 25


_STATUS_FILTER = {"breach": ("breach", "breach_reported_compliant"), "cannot_test": ("cannot_test",),
                  "variance": ("compliant_variance",), "compliant": ("compliant", "compliant_variance")}


def _portfolio(ctx: ToolContext, args: PortfolioInput) -> dict:
    db = ctx.db
    if args.headroom_below_percent is not None and not 0 <= args.headroom_below_percent <= 100:
        raise Refusal("headroom_below_percent is a whole percentage between 0 and 100")
    latest: dict[uuid.UUID, Cycle] = {}
    for cycle in db.execute(select(Cycle).order_by(Cycle.period_end)).scalars():
        latest[cycle.borrower_id] = cycle
    tests: dict[uuid.UUID, list[CovenantTest]] = {}
    for test in db.execute(select(CovenantTest).where(CovenantTest.superseded.is_(False))).scalars():
        cycle = latest.get(test.borrower_id)
        if cycle is not None and test.period_end == cycle.period_end:
            tests.setdefault(test.borrower_id, []).append(test)
    signals: dict[uuid.UUID, list[Signal]] = {}
    for s in db.execute(select(Signal).where(Signal.status == "open")).scalars():
        signals.setdefault(s.borrower_id, []).append(s)
    items: dict[uuid.UUID, list[WorkItem]] = {}
    for w in db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars():
        items.setdefault(w.borrower_id, []).append(w)
    commitments = dict(db.execute(select(Facility.borrower_id, func.sum(Facility.commitment))
                                  .group_by(Facility.borrower_id)).all())
    limit_pct = None if args.headroom_below_percent is None else Decimal(args.headroom_below_percent) / Decimal(100)
    floor = SEVERITY_RANK.get(args.min_signal_severity)

    chosen = []
    for b in db.execute(select(Borrower).order_by(Borrower.name)).scalars():
        mine = tests.get(b.id, [])
        worst = max((t.outcome for t in mine), key=lambda o: OUTCOME_RANK.get(o, 0), default=None)
        measured = [t for t in mine if t.headroom_pct is not None]
        tightest = min(measured, key=lambda t: t.headroom_pct, default=None)
        sigs, open_items = signals.get(b.id, []), items.get(b.id, [])
        if args.covenant_status != "any" and not any(t.outcome in _STATUS_FILTER[args.covenant_status] for t in mine):
            continue
        if limit_pct is not None and not any(t.headroom_pct < limit_pct for t in measured):
            continue
        if floor is not None and not any(SEVERITY_RANK.get(s.severity, 9) <= floor for s in sigs):
            continue
        if args.open_items_only and not open_items:
            continue
        chosen.append((b, mine, worst, tightest, sigs, open_items))

    def worst_severity(rows) -> int:
        return min((SEVERITY_RANK.get(r.severity, 9) for r in rows), default=9)

    order = {
        "name": lambda r: r[0].name,
        "headroom": lambda r: (r[3] is None, r[3].headroom_pct if r[3] else Decimal(0), r[0].name),
        "covenant_status": lambda r: (-OUTCOME_RANK.get(r[2] or "", -1),
                                      r[3].headroom_pct if r[3] else Decimal(999), r[0].name),
        "signals": lambda r: (worst_severity(r[4]), -len(r[4]), r[0].name),
        "open_items": lambda r: (worst_severity(r[5]), -len(r[5]), r[0].name),
        "exposure": lambda r: (-(commitments.get(r[0].id) or Decimal(0)), r[0].name),
    }[args.rank_by]
    chosen.sort(key=order)
    limit = max(1, min(args.limit, MAX_ROWS))
    loans = {f.id: f.name for f in db.execute(select(Facility)).scalars()}
    rows = []
    for b, mine, worst, _tightest, sigs, open_items in chosen[:limit]:
        borrowers_seen(ctx).add(b.id)
        cycle = latest.get(b.id)
        shown = [t for t in mine if limit_pct is None or (t.headroom_pct is not None and t.headroom_pct < limit_pct)
                 or t.outcome in ("breach", "breach_reported_compliant", "cannot_test")]
        by_severity: dict[str, int] = {}
        for s in sigs:
            by_severity[s.severity] = by_severity.get(s.severity, 0) + 1
        rows.append({
            "borrower": b.name, "industry": b.industry, "risk_rating_in_words": in_words(b.risk_rating),
            "latest_cycle": {"period_end": cycle.period_end.isoformat(), "stage": cycle.stage} if cycle else None,
            "covenant_status": worst,
            "covenants": [{k: v for k, v in _test_out(ctx, t, loans).items()
                           if k in ("covenant", "outcome", "operator", "value", "threshold", "headroom_pct")}
                          for t in sorted(shown, key=lambda t: (t.headroom_pct is None, t.headroom_pct or 0))],
            "open_signals": {"count_in_words": in_words(len(sigs)),
                             "by_severity_in_words": {k: in_words(v) for k, v in by_severity.items()},
                             "rules": sorted({s.rule_id for s in sigs})},
            "open_work_items": {"count_in_words": in_words(len(open_items)),
                                "most_severe": min((w.severity for w in open_items),
                                                   key=lambda s: SEVERITY_RANK.get(s, 9), default=None),
                                "types": sorted({w.item_type for w in open_items})},
            "exposure_from_the_system_of_record": _exposure(ctx, b.id),
        })
    return {
        "matched_in_words": in_words(len(chosen)), "shown_in_words": in_words(len(rows)),
        "ranked_by": args.rank_by, "borrowers": rows,
        "message": None if rows else "no borrower in the portfolio matches these filters",
        "note": ("covenants are those tested in each borrower's latest cycle; with a headroom filter only the "
                 "covenants under the limit, or failing, are listed. Counts are given in words: " + NOT_A_FACT + "."),
    }


# ---- registry -------------------------------------------------------------------------------

FIND_BORROWER = Tool(
    "find_borrower",
    "Find a borrower by name. When exactly one borrower matches it is opened, and the other tools then read that "
    "borrower. Returns found=false when no borrower on file matches.", FindInput, _find_borrower)
BORROWER_OVERVIEW = Tool(
    "borrower_overview",
    "The open borrower at a glance: loans, risk rating, exposure, the stage of the latest monitoring cycle, and "
    "open work items.", NoInput, _overview)
COVENANT_TESTS = Tool(
    "covenant_tests",
    "Covenant tests for the open borrower for one period end (YYYY-MM-DD), or the latest tested period when "
    "period_end is null. Each test gives the calculated value, threshold and headroom as facts, the outcome, what "
    "the certificate reported, and a calculation_id.", PeriodInput, _covenant_tests)
CALCULATION_BREAKDOWN = Tool(
    "calculation_breakdown",
    "The inputs and results of one calculation, by a calculation_id that another tool returned. Each input is a "
    "stored fact.", CalculationInput, _calculation)
SPREAD_LINES = Tool(
    "spread_lines",
    "Financial statement lines for the open borrower: give template line keys (for example is.revenue, bs.cash) "
    "and period ends (YYYY-MM-DD). Call with an empty keys list to see the available lines.", SpreadInput, _spread_lines)
METRICS = Tool(
    "metrics",
    "Standard metrics for the open borrower for one period end (the latest cycle when null), calculated by the "
    "metric library from stored facts: " + ", ".join(METRIC_NAMES) + ". An empty names list returns the usual "
    "review set.", MetricsInput, _metrics)
SIGNALS = Tool(
    "signals", "Early warning signals for the open borrower: the rule, severity, period and the facts behind each.",
    SignalsInput, _signals)
WORK_ITEMS = Tool(
    "work_items", "Work items for the open borrower: the question waiting for a person, its severity, and the "
    "decisions a person may take.", WorkItemsInput, _work_items)
BORROWING_BASE_REVIEW = Tool(
    "borrowing_base_review",
    "The borrowing base review for the open borrower for one date, or the latest when period_end is null: outcome, "
    "availability, and which certificate lines differ from the recalculation.", PeriodInput, _borrowing_base)
REPORTING_CALENDAR = Tool(
    "reporting_calendar", "What the open borrower must deliver and when: each reporting obligation with its due "
    "date, status and the date received.", CalendarInput, _calendar)
TERMS = Tool(
    "terms",
    "The terms on file for the open borrower's loans: every version with its status and dates, and the content of "
    "the version in force (or of the version number given), with the clause quoted for each covenant, definition "
    "and reporting requirement.", TermsInput, _terms)
REVIEW_SHEET = Tool(
    "review_sheet", "The latest review sheet for the open borrower and its commentary, each section marked as "
    "approved or as a draft.", NoInput, _review_sheet)
PORTFOLIO_QUERY = Tool(
    "portfolio_query",
    "Filter and rank all borrowers. Filters: covenant_status, headroom_below_percent (a whole percentage: a "
    "borrower matches when any covenant in its latest cycle has less headroom), min_signal_severity, "
    "open_items_only. rank_by: headroom, covenant_status, signals, open_items, exposure or name. Needs no open "
    "borrower.", PortfolioInput, _portfolio)

COPILOT_TOOLS: tuple[Tool, ...] = (
    FIND_BORROWER, BORROWER_OVERVIEW, COVENANT_TESTS, CALCULATION_BREAKDOWN, SPREAD_LINES, METRICS, SIGNALS,
    WORK_ITEMS, BORROWING_BASE_REVIEW, REPORTING_CALENDAR, TERMS, REVIEW_SHEET, PORTFOLIO_QUERY, *DOCUMENT_TOOLS)
TOOL_NAMES: tuple[str, ...] = tuple(t.name for t in COPILOT_TOOLS)


def copilot_gateway() -> ToolGateway:
    """The Copilot's tools. A write tool can never be registered here."""
    for tool in COPILOT_TOOLS:
        if tool.writes:
            raise RuntimeError(f"the Copilot may not be given the write tool {tool.name!r}")
    return ToolGateway(list(COPILOT_TOOLS))

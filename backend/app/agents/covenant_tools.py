"""Tools of the Covenant Agent: read the failing test, the terms on file, and rerun the test.

- No tool input names a borrower, loan, period or covenant. The exception under investigation
  is set by code when the run starts (`ctx.state`) and checked against the run's scope.
- The model never types a number. A what-if names what changes and cites where the new figure
  is printed; code finds the quote on the page, reads the one figure in it, applies it to a
  copy of the governing terms and runs the calculation engine.
- A recalculation here is never a covenant test: it writes a calculation record (and facts
  under their own keys so the result can be referenced), never a CovenantTest row, and it
  never changes a terms version.
"""
import copy
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import select

from app.agents.doc_tools import DOCUMENT_TOOLS, NoInput
from app.agents.tools import Refusal, Tool, ToolContext, ToolInput
from app.calc import covenants as calc_cov
from app.calc.terms import Citation, Terms, compare_terms, threshold_in_force
from app.core import ledger
from app.domain import covenant_service
from app.domain.agents import Lesson
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import CovenantTest
from app.domain.terms import TermsVersion
from app.domain.terms_service import resolve_document, unapproved_amendments
from app.guardrails.numbers import Figure, extract_figures
from app.guardrails.quotes import quote_on_page

TERMS_DOCUMENT_TYPES = ("credit_agreement", "amendment")
MIN_QUOTE_WORDS = 8  # a citation is a clause, not a bare figure lifted from somewhere on the page
MAX_LESSONS = 5
ACTOR = ("agent", "covenant")
WHAT_IF_PREFIX, RERUN_PREFIX = "whatif", "rerun"


@dataclass
class Case:
    """The exception under investigation, loaded from what code put in the run's state."""

    test: CovenantTest
    borrower: Borrower
    facility: Facility
    version_row: TermsVersion  # the terms in force for the period
    terms: Terms


def load_case(ctx: ToolContext) -> Case:
    reference = ctx.state.get("covenant_test_id")
    test = ctx.db.get(CovenantTest, uuid.UUID(str(reference))) if reference else None
    scope = ctx.scope
    if (test is None or test.borrower_id != scope.borrower_id or test.facility_id != scope.facility_id
            or test.period_end != scope.period_end):
        raise Refusal("no covenant exception is open in this run")
    borrower = ctx.db.get(Borrower, test.borrower_id)
    facility = ctx.db.get(Facility, test.facility_id)
    version_row, version = covenant_service.governing_terms(ctx.db, facility, test.period_end)
    if version_row is None:
        raise Refusal("no approved terms are in force for this period")
    return Case(test, borrower, facility, version_row, version.terms)


def _plain(value: Any) -> Any:
    return ledger._jsonable(value)


def result_fact_ids(ctx: ToolContext, calc_id: uuid.UUID) -> dict[str, str]:
    """The facts a calculation produced (value, threshold, headroom_pct), by name."""
    facts = ctx.db.execute(select(Fact).where(Fact.calc_run_id == calc_id)).scalars()
    return {f.key.rsplit(".", 1)[-1]: str(f.id) for f in facts}


def _citation(ctx: ToolContext, borrower_id: uuid.UUID, citation: Citation | None) -> dict[str, Any] | None:
    """A citation from the terms, with the id the document tools accept."""
    if citation is None:
        return None
    doc = resolve_document(ctx.db, borrower_id, citation.document_id)
    return {"document_id": str(doc.id) if doc else None, "document_title": doc.title if doc else None,
            "section": citation.section, "page": citation.page, "quote": citation.quote, "field": citation.field}


def _version_summary(row: TermsVersion) -> dict[str, Any]:
    return {"version": row.version, "status": row.status, "effective_from": _plain(row.effective_from),
            "effective_to": _plain(row.effective_to), "source_documents": list(row.source_document_ids or [])}


# ---- get_exception ---------------------------------------------------------------------------


def _get_exception(ctx: ToolContext, args: NoInput) -> dict[str, Any]:
    case = load_case(ctx)
    test = case.test
    calc = ctx.db.get(CalcRun, test.calc_run_id) if test.calc_run_id else None
    covenant = case.terms.covenant(test.covenant_id)
    reported_threshold = current_fact(ctx.db, test.borrower_id, f"cert.{test.covenant_id}.threshold", test.period_end, 0)
    out: dict[str, Any] = {
        "covenant": {"id": test.covenant_id, "name": test.covenant_name, "period_end": test.period_end,
                     "outcome": test.outcome, "error": test.error},
        "test": {"calc_id": test.calc_run_id, "value": test.value, "threshold": test.threshold,
                 "operator": test.operator, "unit": test.unit, "passed": test.passed, "headroom": test.headroom,
                 "headroom_pct": test.headroom_pct,
                 "fact_ids": result_fact_ids(ctx, test.calc_run_id) if test.calc_run_id else {}},
        "inputs": [{k: i.get(k) for k in ("key", "period_end", "months", "value", "fact_id", "sign")}
                   for i in (calc.inputs if calc else [])],
        "addbacks": [{"name": a.get("name"), "raw_amount": a.get("raw"), "cap_type": a.get("cap_type"),
                      "cap": a.get("cap_limit"), "applied_amount": a.get("applied"), "capped": a.get("capped")}
                     for a in ((calc.trace or {}).get("addbacks", []) if calc else [])],
        "certificate": {"reported_value": test.reported_value, "reported_in_compliance": test.reported_in_compliance,
                        "reported_value_fact_id": test.reported_fact_id,
                        "reported_threshold": reported_threshold.value if reported_threshold else None,
                        "reported_threshold_fact_id": reported_threshold.id if reported_threshold else None},
        "terms_in_force": _version_summary(case.version_row),
    }
    if covenant is not None:
        out["covenant"]["definition"] = {
            "archetype": covenant.archetype, "params": covenant.params, "operator": covenant.test.operator,
            "threshold": covenant.test.threshold, "unit": covenant.test.unit,
            "steps": [{"from": s.from_, "value": s.value} for s in covenant.test.steps],
            "measurement": covenant.measurement.model_dump(),
            "citations": [_citation(ctx, test.borrower_id, c) for c in covenant.citations]}
        out["addback_definitions"] = [
            {"name": a.name, "source_line": a.source_key, "cap": a.cap.model_dump() if a.cap else None,
             "citation": _citation(ctx, test.borrower_id, a.citation)}
            for definition in case.terms.definitions.values() for a in definition.addbacks]
    return _plain(out)


# ---- terms on file ---------------------------------------------------------------------------


def _list_terms_versions(ctx: ToolContext, args: NoInput) -> dict[str, Any]:
    case = load_case(ctx)
    rows = ctx.db.execute(select(TermsVersion).where(TermsVersion.facility_id == case.facility.id)
                          .order_by(TermsVersion.version)).scalars()
    versions = []
    for row in rows:
        entry = {**_version_summary(row), "governs_this_period": row.id == case.version_row.id,
                 "warnings": row.warnings}
        if row.id != case.version_row.id:
            try:
                entry["differences_from_governing"] = [
                    {"path": d.path, "kind": d.kind, "this_version": d.used, "governing": d.approved}
                    for d in compare_terms(row.terms, case.terms)]
            except ValidationError:
                entry["differences_from_governing"] = None
                entry["note"] = "this version is not well formed and cannot be compared"
        versions.append(entry)
    return _plain({"versions": versions})


def _list_unapproved_amendments(ctx: ToolContext, args: NoInput) -> dict[str, Any]:
    case = load_case(ctx)
    return _plain({"amendments": [
        {"document_id": d.id, "title": d.title, "pages": d.page_count, "effective_date": d.effective_date,
         "received_date": d.received_date}
        for d in unapproved_amendments(ctx.db, case.facility)]})


# ---- recalculation ---------------------------------------------------------------------------


def run_calcs(db, run_id: uuid.UUID) -> list[CalcRun]:
    """The calculations logged by one agent run, in the order they ran."""
    rows = db.execute(select(CalcRun).where(CalcRun.trace["agent"]["run_id"].astext == str(run_id))).scalars()
    return sorted(rows, key=lambda c: c.trace["agent"]["seq"])


def _recalculate(ctx: ToolContext, case: Case, terms: Terms, terms_json: dict[str, Any],
                 version_row: TermsVersion, *, what_if: bool, basis: str,
                 change: dict[str, Any] | None = None, citation: dict[str, Any] | None = None) -> dict[str, Any]:
    test, borrower = case.test, case.borrower
    covenant = terms.covenant(test.covenant_id)
    if covenant is None:
        raise Refusal(f"terms version {version_row.version} has no covenant {test.covenant_id!r}")
    calc_id = uuid.uuid4()
    result = calc_cov.test_covenant(
        covenant, test.period_end, covenant_service.fact_provider(ctx.db, borrower.id), terms.definitions,
        fye_month=borrower.fiscal_year_end_month,
        step_up_from=case.facility.origination_date or version_row.effective_from, calc_id=str(calc_id))
    calc = covenant_service._calc_run(ctx.db, borrower, version_row, covenant, test.period_end, result, calc_id, ACTOR)
    seq = len(run_calcs(ctx.db, ctx.run.id)) + 1
    if what_if:
        calc.formula_key = f"covenant.{covenant.id}.what_if"
    calc.trace = {**calc.trace, "agent": _plain({
        "run_id": ctx.run.id, "seq": seq, "what_if": what_if, "basis": basis, "change": change,
        "citation": citation, "terms_version": version_row.version, "terms": terms_json})}
    fact_ids: dict[str, str] = {}
    if result.value is not None:
        prefix = WHAT_IF_PREFIX if what_if else RERUN_PREFIX
        unit = result.unit or covenant.test.unit
        note = ("what-if calculated by the Covenant Agent; not a covenant test" if what_if
                else "recalculation by the Covenant Agent under the terms in force")
        produced = [("value", result.value, unit), ("threshold", result.threshold, unit)]
        if result.headroom_pct is not None:
            produced.append(("headroom_pct", result.headroom_pct, "pct"))
        for name, value, fact_unit in produced:
            fact = add_fact(ctx.db, borrower_id=borrower.id, facility_id=case.facility.id,
                            key=f"{prefix}.{covenant.id}.{name}", period_end=test.period_end, months=0,
                            value=value, unit=fact_unit, kind="calculated", calc_run_id=calc.id, note=note,
                            actor=ACTOR)
            fact_ids[name] = str(fact.id)
    ctx.db.flush()
    return _plain({
        "calc_id": calc.id, "what_if": what_if, "terms_version": version_row.version, "change": change,
        "value": result.value, "threshold": result.threshold, "operator": result.operator, "unit": result.unit,
        "passed": result.passed, "headroom": result.headroom, "headroom_pct": result.headroom_pct,
        "fact_ids": fact_ids,
        "addbacks": [{"name": a.name, "raw_amount": a.raw, "cap": a.cap_limit, "applied_amount": a.applied,
                      "capped": a.capped} for a in result.trace.addbacks],
        "errors": [e.message for e in result.errors]})


class UnderVersionInput(ToolInput):
    version: int


def _recalculate_under_version(ctx: ToolContext, args: UnderVersionInput) -> dict[str, Any]:
    case = load_case(ctx)
    row = ctx.db.execute(select(TermsVersion).where(
        TermsVersion.facility_id == case.facility.id, TermsVersion.version == args.version)).scalar_one_or_none()
    if row is None:
        raise Refusal(f"there is no terms version {args.version} for this loan; list the versions first")
    if row.status == "rejected":
        raise Refusal(f"terms version {args.version} was rejected by a person and cannot be used")
    try:
        terms = Terms.model_validate(row.terms)
    except ValidationError as exc:
        raise Refusal(f"terms version {args.version} is not well formed") from exc
    governing = row.id == case.version_row.id
    return _recalculate(ctx, case, terms, row.terms, row, what_if=not governing, basis="version")


class CitedChangeInput(ToolInput):
    change: Literal["addback_cap", "threshold"]
    addback_name: str | None  # which add-back's cap changes; null for a threshold change
    document_id: str
    page: int
    quote: str


_PUNCTUATION_AFTER_FIGURE = re.compile(r"(?<=\d)[.,;:](?=\s|$)")


def clause_figures(quote: str) -> list[Figure]:
    """The figures a quoted clause states. In a covenant clause "3.25 to 1.00" states one ratio,
    3.25, so every "N to 1" is read as N. Punctuation that closes a phrase is set apart from the
    figure before it first, because the number guardrail does not recognise "to 1.00." or
    "to 1.00," when the ratio ends a sentence or a phrase."""
    text = _PUNCTUATION_AFTER_FIGURE.sub(lambda m: " " + m.group(0), quote)
    candidates = [f.value for f in extract_figures(text)]
    return extract_figures(text, known_ratios=candidates)


def read_single_figure(quote: str) -> Figure:
    """The one figure a cited clause states. Zero or several figures is a refusal: code does not
    choose between them."""
    figures = clause_figures(quote)
    if len(figures) != 1:
        raise Refusal(f"the quote must state exactly one figure; it states {len(figures)}. "
                      "Quote only the clause that states the changed figure")
    return figures[0]


def _cited_page(ctx: ToolContext, case: Case, args: CitedChangeInput) -> tuple[Document, DocumentPage]:
    doc = resolve_document(ctx.db, case.borrower.id, args.document_id)
    if doc is None:
        raise Refusal("no such document on file for this borrower")
    if doc.doc_type not in TERMS_DOCUMENT_TYPES:
        raise Refusal("terms can only be read from a credit agreement or an amendment on file")
    if doc.effective_date is not None and doc.effective_date > case.test.period_end:
        raise Refusal("this document is dated after the period under test")
    page = ctx.db.execute(select(DocumentPage).where(
        DocumentPage.document_id == doc.id, DocumentPage.page_number == args.page)).scalar_one_or_none()
    if page is None or not page.has_text:
        raise Refusal(f"{doc.title} has no readable page {args.page}")
    if len(args.quote.split()) < MIN_QUOTE_WORDS:
        raise Refusal(f"quote the whole clause (at least {MIN_QUOTE_WORDS} words), not a fragment")
    if not quote_on_page(page.text, args.quote):
        raise Refusal(f"the quote is not on page {args.page} of {doc.title}; quote the page verbatim")
    return doc, page


def _apply_cap(terms_json: dict[str, Any], name: str | None, figure: Figure) -> dict[str, Any]:
    if not name:
        raise Refusal("name the add-back whose cap changes")
    found = [(def_name, a) for def_name, d in terms_json.get("definitions", {}).items()
             for a in d.get("addbacks", []) if a.get("name") == name]
    if len(found) != 1:
        raise Refusal(f"the governing terms have {len(found)} add-backs named {name!r}")
    def_name, addback = found[0]
    before = addback.get("cap")
    if figure.value < 0 or figure.kind == "ratio":
        raise Refusal("the figure in the quote is not a cap amount or percentage")
    if figure.kind == "percent":
        if not before or before.get("type") != "pct_of":
            raise Refusal("the governing cap is not a percentage, so its base is not on file; a person must update the terms")
        after = {"type": "pct_of", "value": str(figure.value / Decimal(100)), "of": before["of"]}
    else:
        after = {"type": "amount", "value": str(figure.value)}
    addback["cap"] = after
    return {"field": f"definitions[{def_name}].addbacks[{name}].cap", "from": before, "to": after}


def _apply_threshold(terms_json: dict[str, Any], case: Case, figure: Figure) -> dict[str, Any]:
    covenant = case.terms.covenant(case.test.covenant_id)
    target = next(c for c in terms_json["covenants"] if c["id"] == case.test.covenant_id)
    unit = covenant.test.unit
    if figure.kind == "percent":
        if unit != "pct":
            raise Refusal(f"the quote states a percentage but this covenant is measured in {unit}")
        value = figure.value / Decimal(100)
    elif figure.kind == "ratio" and unit != "ratio":
        raise Refusal(f"the quote states a ratio but this covenant is measured in {unit}")
    else:
        value = figure.value
    before = threshold_in_force(covenant.test, case.test.period_end)
    # the figure replaces whichever threshold is in force at the period end: a step, or the base
    steps = [s for s in target["test"].get("steps", []) if s["from"] <= case.test.period_end.isoformat()]
    if steps:
        step = max(steps, key=lambda s: s["from"])
        step["value"] = str(value)
        field = f"covenants[{covenant.id}].test.steps[{step['from']}]"
    else:
        target["test"]["threshold"] = str(value)
        field = f"covenants[{covenant.id}].test.threshold"
    return {"field": field, "from": str(before), "to": str(value)}


def _recalculate_with_cited_change(ctx: ToolContext, args: CitedChangeInput) -> dict[str, Any]:
    case = load_case(ctx)
    covenant = case.terms.covenant(case.test.covenant_id)
    if covenant is None:
        raise Refusal("the governing terms no longer contain this covenant")
    doc, _page = _cited_page(ctx, case, args)
    figure = read_single_figure(args.quote)
    # the clause must be about the thing it is said to change: a threshold clause names the
    # covenant, a cap clause names the add-back. Code cannot read meaning, but it can refuse a
    # figure taken from a clause about something else.
    said = " ".join(args.quote.lower().split())
    if args.change == "threshold" and " ".join(covenant.name.lower().split()) not in said:
        raise Refusal(f"the quoted clause does not name the {covenant.name}; quote the clause that sets its threshold")
    name_words = re.findall(r"[a-z]{4,}", (args.addback_name or "").lower())
    if args.change == "addback_cap" and name_words and not any(word in said for word in name_words):
        raise Refusal(f"the quoted clause does not mention the {args.addback_name} add-back")
    terms_json = copy.deepcopy(case.version_row.terms)
    if args.change == "addback_cap":
        change = _apply_cap(terms_json, args.addback_name, figure)
    else:
        change = _apply_threshold(terms_json, case, figure)
    try:
        terms = Terms.model_validate(terms_json)
    except ValidationError as exc:
        problem = exc.errors()[0]
        raise Refusal(f"the change does not give valid terms: {problem['msg']}") from exc
    change = {"kind": args.change, **change, "figure_as_printed": figure.raw}
    citation = {"document_id": str(doc.id), "document_title": doc.title, "document_type": doc.doc_type,
                "page": args.page, "quote": args.quote}
    out = _recalculate(ctx, case, terms, terms_json, case.version_row, what_if=True, basis="cited_change",
                       change=change, citation=citation)
    out["citation"] = citation
    out["note"] = ("A what-if: the terms on file are unchanged and no covenant test was recorded. "
                   "Cite this same clause as a claim if your answer relies on it.")
    return out


# ---- lessons ---------------------------------------------------------------------------------


class LessonsInput(ToolInput):
    tag: str | None  # optionally only lessons a person filed under this tag


def _search_lessons(ctx: ToolContext, args: LessonsInput) -> dict[str, Any]:
    case = load_case(ctx)
    covenant = case.terms.covenant(case.test.covenant_id)
    topics = {t for t in (ctx.state.get("item_type"), covenant.archetype if covenant else None) if t}
    query = select(Lesson).where(Lesson.topic.in_(topics))
    if args.tag:
        query = query.where(Lesson.tag == args.tag)
    rows = list(ctx.db.execute(query).scalars())
    rows.sort(key=lambda r: (r.borrower_id != case.borrower.id, -r.created_at.timestamp()))
    return _plain({"lessons": [
        {"topic": r.topic, "tag": r.tag, "same_borrower": r.borrower_id == case.borrower.id,
         "written_on": r.created_at.date(), "text": r.text} for r in rows[:MAX_LESSONS]],
        "note": "Written by the bank's analysts on earlier cases. Precedent for reasoning, not evidence for this case."})


GET_EXCEPTION = Tool(
    "get_exception",
    "The covenant test under investigation: its value, threshold, operator and headroom, every input of the "
    "calculation with its fact id, each add-back with its raw amount, cap and applied amount, what the "
    "borrower's certificate reported, and the terms version in force.",
    NoInput, _get_exception)
LIST_TERMS_VERSIONS = Tool(
    "list_terms_versions",
    "Every terms version on file for this loan with its status and effective dates. For versions other than "
    "the one in force, the differences from the version in force.",
    NoInput, _list_terms_versions)
LIST_UNAPPROVED_AMENDMENTS = Tool(
    "list_unapproved_amendments",
    "Amendments on file for the borrower that no approved terms version names as a source.",
    NoInput, _list_unapproved_amendments)
RECALCULATE_UNDER_VERSION = Tool(
    "recalculate_under_version",
    "Rerun this covenant for this period under an existing terms version, named by its version number.",
    UnderVersionInput, _recalculate_under_version, writes=True)
RECALCULATE_WITH_CITED_CHANGE = Tool(
    "recalculate_with_cited_change",
    "Rerun this covenant with one change to the terms in force: an add-back's cap (give addback_name) or the "
    "covenant's threshold. You give no number. Cite the clause that states the new figure: the document id, "
    "the page, and the clause quoted verbatim, containing exactly one figure. Software finds the quote on the "
    "page, reads the figure from it and recalculates. The terms on file do not change.",
    CitedChangeInput, _recalculate_with_cited_change, writes=True)
SEARCH_LESSONS = Tool(
    "search_lessons",
    "Reasoning the bank's analysts wrote when they decided earlier exceptions of this kind.",
    LessonsInput, _search_lessons)

COVENANT_TOOLS = (*DOCUMENT_TOOLS, GET_EXCEPTION, LIST_TERMS_VERSIONS, LIST_UNAPPROVED_AMENDMENTS,
                  RECALCULATE_UNDER_VERSION, RECALCULATE_WITH_CITED_CHANGE, SEARCH_LESSONS)

"""Terms Agent: read a credit agreement and its amendments and propose covenant terms.

The model is asked only where each term is stated and how it is printed. Code confirms every
quoted clause on the cited page of the cited document, reads every number from the quote itself,
merges amendments over the agreement, builds the terms JSON and hands it to `propose_terms`.
The result is a proposed version: it governs nothing until a second person approves it.

What code could not verify never becomes a governing term silently. A numeric item that fails
is left out, listed in the result and on the approval item, and recorded as a warning on the
version (so approval needs a written reason). A clause with no number that fails (a definition,
an exclusion list) is kept as reported, so the citation check in `propose_terms` warns about it.
If valid terms cannot be built at all, nothing is proposed and a person is asked to board them.
"""
import base64
import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.tools import Scope, ToolGateway
from app.calc.terms import Terms
from app.core import clock, ledger
from app.core.roles import Permission
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.documents_service import get_page, read_file
from app.domain.monitoring import Cycle, WorkItem
from app.domain.terms import TermsVersion
from app.domain.terms_service import TermsRefused, propose_terms
from app.domain.work_items import due_date_for, raise_item
from app.guardrails.narrative import check_narrative
from app.guardrails.numbers import blank_non_figures, extract_figures, same_number
from app.guardrails.quotes import dates_in, quote_on_page

PREPARED_BY = ("agent", "terms@1")
# The agreements state rounding in words; the convention applied here is shown to the approver.
ROUNDING_DP = {"ratio": 2, "usd": 0, "pct": 2, "days": 0, "count": 0}

Operator = Literal[">=", "<=", ">", "<"]
Unit = Literal["ratio", "usd", "pct", "days", "count"]
Basis = Literal["ttm", "ytd", "point", "fy"]
Frequency = Literal["monthly", "quarterly", "semiannual", "annual"]
Collateral = Literal["accounts_receivable", "inventory", "other"]


class DocumentDate(BaseModel):
    """Where one document states the date its terms take effect."""
    document_id: str
    page: int
    quote: str
    printed_date: str


class CovenantRow(BaseModel):
    covenant_id: str
    name: str
    archetype: Literal["coverage", "leverage", "current_ratio", "min_tangible_net_worth", "min_liquidity",
                       "max_capex", "debt_to_tnw", "other"]
    operator: Operator
    unit: Unit
    basis: Basis
    frequency: Frequency
    earnings: Literal["ebitda", "adjusted_ebitda", "not_applicable"]
    debt: Literal["total_debt", "senior_debt", "not_applicable"]
    deductions: list[Literal["unfinanced_capex", "cash_taxes", "distributions"]]
    denominator: list[Literal["cash_interest", "interest_expense", "scheduled_principal"]]
    include_availability: Literal["yes", "no", "not_applicable"]
    threshold_printed: str
    net_income_step_up_printed: str
    document_id: str
    page: int
    section: str
    quote: str
    definition_document_id: str
    definition_page: int
    definition_section: str
    definition_quote: str


class StepRow(BaseModel):
    covenant_id: str
    from_date_printed: str
    threshold_printed: str
    document_id: str
    page: int
    section: str
    quote: str


class AddbackRow(BaseModel):
    name: str
    source: Literal["is.nonrecurring_expense", "is.other_operating_expense", "other"]
    cap_type: Literal["none", "amount", "pct_of_ebitda"]
    cap_printed: str
    document_id: str
    page: int
    section: str
    quote: str


class ReportingRow(BaseModel):
    document_type: Literal["annual_statements", "interim_statements", "compliance_certificate",
                           "borrowing_base_certificate", "receivables_aging", "tax_return", "other"]
    frequency: Frequency
    quality: Literal["audited", "reviewed", "compiled", "internal", "tax_return", "not_stated"]
    due_days_printed: str
    document_id: str
    page: int
    section: str
    quote: str


class BorrowingBaseValue(BaseModel):
    item: Literal["commitment", "advance_rate", "sublimit", "max_age_days", "cross_aging_pct",
                  "concentration_limit_pct", "reserve"]
    collateral: Literal["accounts_receivable", "inventory", "other", "not_applicable"]
    name: str
    printed: str
    document_id: str
    page: int
    section: str
    quote: str


class BorrowingBaseExclusions(BaseModel):
    collateral: Collateral
    excluded: list[Literal["intercompany", "foreign", "government", "contra", "work_in_process", "consigned",
                           "other"]]
    document_id: str
    page: int
    section: str
    quote: str


class TermsReading(BaseModel):
    documents: list[DocumentDate]
    covenants: list[CovenantRow]
    steps: list[StepRow]
    addbacks: list[AddbackRow]
    reporting: list[ReportingRow]
    borrowing_base_values: list[BorrowingBaseValue]
    borrowing_base_exclusions: list[BorrowingBaseExclusions]
    borrowing_base_frequency: Literal["monthly", "quarterly", "semiannual", "annual", "none"]
    notes: list[str]


SPEC = AgentSpec(
    name="terms", version="1",
    purpose="Locate covenant terms in a credit agreement and its amendments; code verifies each clause and number.",
    prompt_file="terms.md", output_model=TermsReading, tools=(), effort="high", max_tokens=32000)

_AR_EXCLUSIONS = ("intercompany", "foreign", "government", "contra")
_INVENTORY_EXCLUSIONS = ("work_in_process", "consigned")
_RATIO_TEXT = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:x|x?\s*(?:to|:)\s*1(?:\.0+)?x?)\s*$", re.I)
_RATIO_IN_QUOTE = re.compile(r"(?<![\w.,])(\d+(?:\.\d+)?)x?\s*(?:to|:)\s*1(?:\.0+)?x?(?![\d,]|\.\d|\w)", re.I)
_EFFECTIVE = re.compile(r"\beffective\s+(?:date\s+(?:of|is|shall\s+be)\s+|as\s+of\s+|on\s+|from\s+)?(?=[A-Z0-9])", re.I)
_DATE_MARKER = re.compile(r"\b(?:dated|effective|entered\s+into|made)\s+(?:as\s+of|on|from)\s+", re.I)
_SLUG = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
_FIGURE_KIND = {"ratio": "ratio", "pct": "percent", "usd": "amount", "count": "amount"}
_REASONS = {
    "document_not_supplied": "the cited document is not one of the documents given to the agent",
    "quote_not_on_page": "the quoted clause is not on the cited page of the cited document",
    "no_figure_in_quote": "the quoted clause states no figure",
    "no_figure": "the printed text is not a figure of the kind this term needs",
    "ambiguous_figure": "more than one figure could be meant and code will not choose between them",
    "printed_disagrees_with_quote": "the printed text reported for this term is not what the quoted clause states",
    "date_unverified": "the date could not be read from the quoted clause",
    "not_supported": "this term does not fit a formula code can calculate; a person must write it",
    "incomplete": "the row leaves out a choice its archetype needs",
    "duplicate": "the same term was reported twice from one document",
    "covenant_missing": "the covenant this step belongs to is not in the terms",
    "amendment_not_applied": "something cited to this amendment could not be verified, so none of it was applied",
    "amendment_states_nothing": "no term was reported from this amendment, so it was not applied",
    "cap_not_reported": "the quoted definition states a figure but no cap was reported",
}


def _flat(text: str) -> str:
    return "".join(text.split()).lower()


def _plain(value: Decimal) -> str:
    return format(value, "f")


def _ratios(quote: str) -> list[Decimal]:
    """Every ratio a clause states, as "N to 1.00", "N:1" or "Nx". Read here because the number
    guardrail keeps the 1.00 of "N to 1.00" when the sentence ends straight after it."""
    stated = [Decimal(n) for n in _RATIO_IN_QUOTE.findall(blank_non_figures(quote))]
    return stated + [f.value for f in extract_figures(quote) if f.kind == "ratio"]


def reference(document: Document) -> str:
    """How a document is named to the model and in citations: the id it arrived with, or its own."""
    return (document.meta or {}).get("external_id") or str(document.id)


@dataclass
class _Clause:
    ref: str
    page: int
    section: str
    quote: str
    order: int = -1  # position of the document in date order; -1 when it was not supplied
    problem: str | None = None

    @property
    def key(self) -> tuple[str, int, str]:
        return (self.ref, self.page, _flat(self.quote))

    def citation(self, name: str) -> dict[str, Any]:
        return {"field": name, "document_id": self.ref or "unknown", "section": self.section or None,
                "page": self.page, "quote": self.quote}


@dataclass
class _Reading:
    """One number read by code from a quoted clause."""
    path: str
    clause: _Clause
    printed: str
    kind: str  # ratio | usd | pct | count
    value: Decimal | None = None  # as the terms store it (a percentage as a fraction)
    figure: Decimal | None = None  # as the clause prints it
    problem: str | None = None

    @property
    def ok(self) -> bool:
        return self.problem is None and self.value is not None


@dataclass
class TermsResult:
    status: str  # proposed | needs_person | failed
    run_id: uuid.UUID | None = None
    version: TermsVersion | None = None
    work_item: WorkItem | None = None
    unverified: list[dict[str, Any]] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    terms: dict[str, Any] | None = None
    effective_from: date | None = None
    source_document_ids: list[str] = field(default_factory=list)


class _Reader:
    """Confirms clauses on their pages and reads numbers and dates from them."""

    def __init__(self, db: Session, documents: list[Document]):
        self.db = db
        self.documents = {reference(d): d for d in documents}
        self.order = {reference(d): i for i, d in enumerate(documents)}
        self.readings: list[_Reading] = []
        self._checked: dict[tuple[str, int, str], str | None] = {}

    def effective_dates(self, ref: str) -> set[date]:
        """Dates the document itself calls effective, read by code from every page."""
        document = self.documents.get(ref)
        if document is None:
            return set()
        found: set[date] = set()
        for page in self.db.execute(select(DocumentPage).where(DocumentPage.document_id == document.id)).scalars():
            text = " ".join(page.text.split())
            for match in _EFFECTIVE.finditer(text):
                found.update(dates_in(text[match.end():match.end() + 40])[:1])
        return found

    def clause(self, document_id: str, page: int, section: str, quote: str) -> _Clause:
        ref = document_id.strip()
        clause = _Clause(ref, page, section.strip(), quote, order=self.order.get(ref, -1))
        if clause.key not in self._checked:
            document = self.documents.get(ref)
            if document is None:
                problem = "document_not_supplied"
            else:
                found = get_page(self.db, document.id, page)
                problem = None if found is not None and quote_on_page(found.text, quote) else "quote_not_on_page"
            self._checked[clause.key] = problem
        clause.problem = self._checked[clause.key]
        return clause

    def number(self, path: str, clause: _Clause, printed: str, kind: str) -> _Reading:
        reading = _Reading(path, clause, printed, kind)
        self.readings.append(reading)
        if clause.problem:
            reading.problem = clause.problem
            return reading
        if not extract_figures(clause.quote):
            reading.problem = "no_figure_in_quote"
            return reading
        if kind == "ratio":
            match = _RATIO_TEXT.match(printed)
            if match is None:
                reading.problem = "ambiguous_figure" if len(extract_figures(printed)) > 1 else "no_figure"
                return reading
            target = Decimal(match.group(1))
            stated = [value for value in _ratios(clause.quote) if same_number(value, target)]
        else:
            figures = extract_figures(printed)
            if len(figures) != 1:
                reading.problem = "ambiguous_figure" if figures else "no_figure"
                return reading
            target = figures[0].value
            if figures[0].kind != _FIGURE_KIND[kind] or target < 0 or (kind == "count" and target != int(target)):
                reading.problem = "no_figure"
                return reading
            stated = [f.value for f in extract_figures(clause.quote)
                      if f.kind == _FIGURE_KIND[kind] and same_number(f.value, target)]
        if not stated or _flat(printed) not in _flat(clause.quote):
            reading.problem = "printed_disagrees_with_quote"
            return reading
        reading.figure = stated[0]
        reading.value = reading.figure.scaleb(-2) if kind == "pct" else reading.figure
        return reading

    def settle(self) -> None:
        """Every figure in a quoted clause must be accounted for by a term that cites it. A clause
        that states another figure of the same kind which no term claims is ambiguous: code cannot
        tell which figure the term is, so no reading of that kind from the clause is accepted."""
        groups: dict[tuple[tuple[str, int, str], str], list[_Reading]] = {}
        for reading in self.readings:
            if reading.ok:
                groups.setdefault((reading.clause.key, _FIGURE_KIND[reading.kind]), []).append(reading)
        for (_key, figure_kind), readings in groups.items():
            quote = readings[0].clause.quote
            stated = _ratios(quote) if figure_kind == "ratio" else [
                f.value for f in extract_figures(quote) if f.kind == figure_kind]
            claimed = [r.figure for r in readings]
            if any(not any(same_number(value, c) for c in claimed) for value in stated):
                for reading in readings:
                    reading.problem = "ambiguous_figure"

    def day(self, clause: _Clause, printed: str, *, marked: bool) -> date | None:
        """A date read from the clause. With `marked`, it must follow "dated as of", "effective as
        of" or similar; the printed text must be that same date."""
        if clause.problem:
            return None
        text = " ".join(clause.quote.split())
        printed_dates = set(dates_in(printed))
        if len(printed_dates) != 1 or _flat(printed) not in _flat(text):
            return None
        if marked:
            stated = set()
            for match in _DATE_MARKER.finditer(text):
                following = dates_in(text[match.end():match.end() + 28])
                stated.update(following[:1])
        else:
            stated = set(dates_in(text)) & printed_dates
        return next(iter(stated)) if len(stated) == 1 and stated == printed_dates else None


def _ordered(documents: list[Document]) -> tuple[list[Document], str | None]:
    agreements = [d for d in documents if d.doc_type == "credit_agreement"]
    amendments = [d for d in documents if d.doc_type == "amendment"]
    if len(agreements) != 1 or len(agreements) + len(amendments) != len(documents):
        return documents, "exactly one credit agreement, and otherwise only amendments, must be given"
    amendments.sort(key=lambda d: (d.effective_date or d.received_date or date.max, d.created_at))
    return agreements + amendments, None


def _known_names(db: Session, facility: Facility) -> tuple[dict[str, str], dict[str, str]]:
    """Covenant ids and add-back names already used by this facility's terms, so a later version
    keeps the identities that tests and certificates are stored under."""
    latest = db.execute(select(TermsVersion).where(
        TermsVersion.facility_id == facility.id, TermsVersion.status.in_(("approved", "superseded")))
        .order_by(TermsVersion.version.desc())).scalars().first()
    covenants: dict[str, str] = {}
    addbacks: dict[str, str] = {}
    if latest is not None:
        for covenant in latest.terms.get("covenants", []):
            covenants[covenant["name"].strip().lower()] = covenant["id"]
        for definition in latest.terms.get("definitions", {}).values():
            for addback in definition.get("addbacks", []):
                addbacks[addback["source_key"]] = addback["name"]
    return covenants, addbacks


def _slug(text: str, fallback: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")[:40]
    return candidate if _SLUG.match(candidate) else fallback


def _requirement_id(row: ReportingRow) -> str:
    if row.document_type in ("annual_statements", "interim_statements"):
        return f"{row.frequency}_statements"
    return row.document_type


@dataclass
class _Item:
    """One reported term after verification: where it is stated, whether it holds, and its JSON."""
    path: str
    key: Any
    clause: _Clause
    readings: list[_Reading]
    build: Any  # () -> dict
    problem: str | None = None  # a problem that is not a failed reading
    printed: str = ""

    @property
    def failure(self) -> str | None:
        return self.problem or self.clause.problem or next((r.problem for r in self.readings if not r.ok), None)


class _Draft:
    """Everything the agent reported, verified and merged in document order."""

    def __init__(self, db: Session, facility: Facility, documents: list[Document], out: TermsReading):
        self.out = out
        self.facility = facility
        self.reader = _Reader(db, documents)
        self.refs = [reference(d) for d in documents]
        self.unverified: list[dict[str, Any]] = []
        self.left_out: list[str] = []  # warning codes recorded on the proposed version
        self.reasons: list[str] = []  # why no valid terms can be built
        self.notes: list[dict[str, Any]] = []
        self.known_covenants, self.known_addbacks = _known_names(db, facility)

    # ---- reporting what failed

    def _unverified(self, path: str, clause: _Clause | None, reason: str, printed: str = "", *,
                    warn: bool = True, detail: str | None = None) -> None:
        self.unverified.append({
            "item": path, "reason": reason, "detail": detail or _REASONS.get(reason, reason), "printed": printed,
            "document_id": clause.ref if clause else None, "page": clause.page if clause else None,
            "section": clause.section if clause else None, "quote": clause.quote if clause else None})
        if warn:
            self.left_out.append(f"unverified_left_out:{path}")

    # ---- reading the rows

    def _items(self) -> dict[str, list[_Item]]:
        out, read = self.out, self.reader
        items: dict[str, list[_Item]] = {"covenants": [], "steps": [], "addbacks": [], "reporting": [], "bb": []}
        reported_as: dict[str, str] = {}  # the id the agent used -> the id the terms use
        units: dict[str, str] = {}

        for row in out.covenants:
            cid = self.known_covenants.get(row.name.strip().lower()) or _slug(row.covenant_id, _slug(row.name, "covenant"))
            reported_as[_slug(row.covenant_id, cid)] = cid
            units[cid] = row.unit
            path = f"covenants.{cid}"
            clause = read.clause(row.document_id, row.page, row.section, row.quote)
            definition = read.clause(row.definition_document_id, row.definition_page, row.definition_section,
                                     row.definition_quote)
            kind = row.unit if row.unit in ("ratio", "usd", "pct") else "count"
            threshold = read.number(f"{path}.test.threshold", clause, row.threshold_printed, kind)
            readings = [threshold]
            step_up = None
            if row.net_income_step_up_printed.strip():
                step_up = read.number(f"{path}.params.step_up_pct_of_net_income", clause,
                                      row.net_income_step_up_printed, "pct")
                readings.append(step_up)
            params, problem = self._params(row, step_up)
            items["covenants"].append(_Item(
                path, cid, clause, readings, problem=problem, printed=row.threshold_printed,
                build=lambda row=row, cid=cid, clause=clause, definition=definition, threshold=threshold,
                params=params: {
                    "id": cid, "name": row.name.strip(), "archetype": row.archetype, "params": params,
                    "test": {"operator": row.operator, "threshold": _plain(threshold.value), "steps": [],
                             "unit": row.unit},
                    "measurement": {"basis": row.basis, "frequency": row.frequency},
                    "rounding": {"dp": ROUNDING_DP[row.unit], "mode": "half_up"},
                    "citations": [clause.citation("test.threshold"), definition.citation("definition")]}))

        for row in out.steps:
            cid = _slug(row.covenant_id, "covenant")
            cid = reported_as.get(cid, cid)
            unit = units.get(cid, "ratio")
            clause = read.clause(row.document_id, row.page, row.section, row.quote)
            value = read.number(f"covenants.{cid}.test.steps", clause, row.threshold_printed,
                                unit if unit in ("ratio", "usd", "pct") else "count")
            start = read.day(clause, row.from_date_printed, marked=False)
            items["steps"].append(_Item(
                f"covenants.{cid}.test.steps[{row.from_date_printed.strip()}]", (cid, start), clause, [value],
                problem=None if start or clause.problem else "date_unverified", printed=row.threshold_printed,
                build=lambda value=value, start=start: {"from": start.isoformat(), "value": _plain(value.value)}))

        for row in out.addbacks:
            name = self.known_addbacks.get(row.source) or _slug(row.name, "addback")
            path = f"definitions.ebitda.addbacks.{name}"
            clause = read.clause(row.document_id, row.page, row.section, row.quote)
            readings, problem = [], None
            if row.source == "other":
                problem = "not_supported"
            elif row.cap_type == "none":
                # an absent cap means uncapped, so a figure in the quoted definition must be explained
                if not clause.problem and extract_figures(clause.quote):
                    problem = "cap_not_reported"
            else:
                readings.append(read.number(f"{path}.cap", clause, row.cap_printed,
                                            "usd" if row.cap_type == "amount" else "pct"))
            items["addbacks"].append(_Item(
                path, row.source, clause, readings, problem=problem, printed=row.cap_printed,
                build=lambda row=row, name=name, clause=clause, readings=readings, path=path: {
                    "name": name, "source_key": row.source,
                    "cap": None if row.cap_type == "none" else (
                        {"type": "amount", "value": _plain(readings[0].value)} if row.cap_type == "amount" else
                        {"type": "pct_of", "value": _plain(readings[0].value), "of": {"op": "named", "name": "ebitda"}}),
                    "citation": clause.citation(path)}))

        for row in out.reporting:
            rid = _requirement_id(row)
            path = f"reporting_requirements.{rid}"
            clause = read.clause(row.document_id, row.page, row.section, row.quote)
            days = read.number(f"{path}.due_days_after_period_end", clause, row.due_days_printed, "count")
            items["reporting"].append(_Item(
                path, rid, clause, [days], problem="not_supported" if row.document_type == "other" else None,
                printed=row.due_days_printed,
                build=lambda row=row, rid=rid, clause=clause, days=days, path=path: {
                    "id": rid, "document_type": row.document_type, "frequency": row.frequency,
                    "due_days_after_period_end": int(days.value),
                    "quality": None if row.quality == "not_stated" else row.quality,
                    "citation": clause.citation(path)}))

        for row in out.borrowing_base_values:
            scope = "" if row.item in ("commitment", "reserve") else f"components[{row.collateral}]."
            name = row.name.strip()
            path = f"borrowing_base.{scope}{row.item}" + (f"[{name}]" if row.item == "reserve" else "")
            clause = read.clause(row.document_id, row.page, row.section, row.quote)
            kind = {"commitment": "usd", "sublimit": "usd", "reserve": "usd", "max_age_days": "count"}.get(row.item, "pct")
            value = read.number(path, clause, row.printed, kind)
            problem = None
            if scope and row.collateral in ("other", "not_applicable"):
                problem = "not_supported"
            elif row.item == "reserve" and (not name or (not clause.problem and _flat(name) not in _flat(clause.quote))):
                problem = "printed_disagrees_with_quote"
            items["bb"].append(_Item(path, (row.item, row.collateral if scope else "", name.lower()), clause,
                                     [value], problem=problem, printed=row.printed,
                                     build=lambda row=row, value=value, name=name: (row, value, name)))
        self.reader.settle()
        return items

    @staticmethod
    def _params(row: CovenantRow, step_up: _Reading | None) -> tuple[dict[str, Any], str | None]:
        if row.archetype == "other":
            return {}, "not_supported"
        if row.archetype == "coverage":
            if row.earnings == "not_applicable" or not row.denominator:
                return {}, "incomplete"
            return {"numerator_base": row.earnings, "deductions": list(row.deductions),
                    "denominator": list(row.denominator)}, None
        if row.archetype == "leverage":
            if "not_applicable" in (row.debt, row.earnings):
                return {}, "incomplete"
            return {"debt": row.debt, "ebitda": row.earnings}, None
        if row.archetype == "min_tangible_net_worth":
            value = step_up.value if step_up is not None and step_up.ok else None
            return {"step_up_pct_of_net_income": None if value is None else _plain(value)}, None
        if row.archetype == "min_liquidity":
            if row.include_availability == "not_applicable":
                return {}, "incomplete"
            return {"include_availability": row.include_availability == "yes"}, None
        return {}, None

    # ---- dates and which documents apply

    def _dates(self) -> dict[str, date | None]:
        found: dict[str, date | None] = dict.fromkeys(self.refs)
        for row in self.out.documents:
            clause = self.reader.clause(row.document_id, row.page, "", row.quote)
            if clause.ref in found and found[clause.ref] is None:
                found[clause.ref] = self.reader.day(clause, row.printed_date, marked=True)
        # a document that states when it takes effect is taken at its word: a date read from its
        # signing line ("entered into as of") does not stand when another date is called effective
        for ref, chosen in found.items():
            stated = self.reader.effective_dates(ref)
            if chosen is not None and stated and chosen not in stated:
                found[ref] = None
        return found

    def build(self) -> tuple[dict[str, Any] | None, date | None, list[str]]:
        """The merged terms, their effective date and the documents they rest on; or None with
        `reasons` filled when valid terms cannot be built."""
        items = self._items()
        dates = self._dates()
        agreement, amendments = self.refs[0], self.refs[1:]
        if dates[agreement] is None:
            self.reasons.append("the agreement's date could not be verified on the page")
            self._unverified("effective_from", None, "date_unverified", warn=False)

        # an amendment is applied whole or not at all: a half-applied amendment would be named as a
        # source and so stop being reported as an amendment missing from the approved terms
        applied = [agreement]
        everything = [i for group in items.values() for i in group]
        exclusions = [(row, self.reader.clause(row.document_id, row.page, row.section, row.quote))
                      for row in self.out.borrowing_base_exclusions]
        for ref in amendments:
            cited = [i for i in everything if i.clause.ref == ref]
            failed = [i for i in cited if i.failure]
            bad_clauses = [c for _row, c in exclusions if c.ref == ref and c.problem]
            states = bool(cited) or any(c.ref == ref for _row, c in exclusions)
            if states and not failed and not bad_clauses and dates[ref] is not None:
                applied.append(ref)
                continue
            for item in failed:
                self._unverified(item.path, item.clause, item.failure, item.printed, warn=False)
            reason = "amendment_not_applied" if states else "amendment_states_nothing"
            detail = _REASONS[reason]
            if states and not failed and not bad_clauses:
                detail = "the amendment's effective date could not be verified, so it was not applied"
            self._unverified(f"documents.{ref}", None, reason, detail=detail, warn=False)
            self.left_out.append(f"amendment_not_applied:{ref}")
        in_force = {ref: n for n, ref in enumerate(self.refs) if ref in applied}

        def usable(group: str) -> list[_Item]:
            """Items from applied documents, in document order; failures from the agreement, and
            anything citing a document that was not supplied, are listed as left out."""
            keep = []
            for item in sorted(items[group], key=lambda i: i.clause.order):
                if item.clause.ref in amendments and item.clause.ref not in applied:
                    continue
                if item.failure:
                    self._unverified(item.path, item.clause, item.failure, item.printed)
                else:
                    keep.append(item)
            return keep

        def merged(group: str) -> dict[Any, _Item]:
            """The latest statement of each term. The same term twice in one document is refused."""
            latest: dict[Any, _Item] = {}
            twice = set()
            for item in usable(group):
                earlier = latest.get(item.key)
                if earlier is not None and earlier.clause.order == item.clause.order:
                    twice.add(item.key)
                    self._unverified(item.path, item.clause, "duplicate", item.printed)
                latest[item.key] = item
            return {key: item for key, item in latest.items() if key not in twice}

        covenants: dict[str, tuple[int, dict[str, Any]]] = {}
        for key, item in merged("covenants").items():
            covenants[key] = (item.clause.order, item.build())
        steps: dict[str, dict[date, tuple[_Item, dict[str, Any]]]] = {}
        for (cid, start), item in merged("steps").items():
            if cid not in covenants:
                self._unverified(item.path, item.clause, "covenant_missing", item.printed)
            elif item.clause.order < covenants[cid][0]:
                # the covenant was restated by a later document that did not restate this step
                self.notes.append({"layer": "terms", "check": "step_superseded", "action": "dropped",
                                   "detail": f"a step of {cid} stated before its restatement was not carried forward"})
                self.left_out.append(f"step_not_carried_forward:covenants.{cid}")
            else:
                steps.setdefault(cid, {})[start] = (item, item.build())
        for cid, (_order, covenant) in covenants.items():
            in_order = sorted(steps.get(cid, {}).items(), key=lambda pair: pair[0])
            for index, (_start, (item, step)) in enumerate(in_order):
                covenant["test"]["steps"].append(step)
                covenant["citations"].append(item.clause.citation(f"test.steps[{index}]"))

        addbacks = {key: item.build() for key, item in merged("addbacks").items()}
        reporting = {key: item.build() for key, item in merged("reporting").items()}

        terms = {
            "definitions": {"ebitda": {"base": "ebitda", "addbacks": list(addbacks.values())}},
            "covenants": [covenant for _order, covenant in covenants.values()],
            "reporting_requirements": list(reporting.values()),
            "borrowing_base": self._borrowing_base(list(merged("bb").values()), [
                (row, clause) for row, clause in exclusions if clause.ref not in amendments or clause.ref in applied]),
        }
        if self.reasons:
            return None, None, applied
        try:
            Terms.model_validate(terms)
        except ValidationError as exc:
            self.reasons.extend(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:8])
            return None, None, applied
        effective = dates[max(applied, key=lambda ref: in_force[ref])]
        return terms, effective, applied

    def _borrowing_base(self, values: list[_Item], exclusions) -> dict[str, Any] | None:
        frequency = self.out.borrowing_base_frequency
        reported = bool(self.out.borrowing_base_values or self.out.borrowing_base_exclusions)
        if not reported and frequency == "none":
            if self.facility.has_borrowing_base:
                self.reasons.append("the facility has a borrowing base but none was reported from the documents")
            return None
        latest: dict[Any, tuple[BorrowingBaseValue, _Reading, str, _Item]] = {
            item.key: (*item.build(), item) for item in values}
        commitment = latest.get(("commitment", "", ""))
        if commitment is None:
            self.reasons.append("the borrowing base commitment could not be verified")
        if frequency == "none":
            self.reasons.append("the borrowing base reporting frequency was not reported")
        excluded: dict[str, tuple[list[str], _Clause]] = {}
        for row, clause in sorted(exclusions, key=lambda pair: pair[1].order):
            allowed = _AR_EXCLUSIONS if row.collateral == "accounts_receivable" else _INVENTORY_EXCLUSIONS
            names = [name for name in dict.fromkeys(row.excluded) if name in allowed]
            if len(names) != len(set(row.excluded)) or row.collateral == "other":
                self._unverified(f"borrowing_base.components[{row.collateral}].eligibility.exclude", clause,
                                 "not_supported", ", ".join(sorted(set(row.excluded) - set(names))))
            if row.collateral != "other":
                # a clause with no number is kept as reported: the citation check warns if it is not on the page
                excluded[row.collateral] = (names, clause)

        components, clauses = [], []

        def cite(clause: _Clause, name: str) -> None:
            if all(clause.key != seen.key for seen, _name in clauses):
                clauses.append((clause, name))

        for collateral in ("accounts_receivable", "inventory"):
            rate = latest.get(("advance_rate", collateral, ""))
            mine = {k[0]: v for k, v in latest.items() if k[1] == collateral}
            if rate is None:
                if mine or collateral in excluded:
                    self.reasons.append(f"the {collateral} advance rate could not be verified")
                continue
            names, exclusion_clause = excluded.get(collateral, ([], None))
            eligibility: dict[str, Any] = {"exclude": names}
            component: dict[str, Any] = {"collateral": collateral, "advance_rate": _plain(rate[1].value),
                                         "eligibility": eligibility}
            cite(rate[3].clause, "borrowing_base")
            if "sublimit" in mine:
                component["sublimit"] = _plain(mine["sublimit"][1].value)
                cite(mine["sublimit"][3].clause, "borrowing_base")
            for name in ("max_age_days", "cross_aging_pct", "concentration_limit_pct"):
                if name in mine:
                    value = mine[name][1].value
                    eligibility[name] = int(value) if name == "max_age_days" else _plain(value)
                    cite(mine[name][3].clause, f"borrowing_base.components[{collateral}].eligibility")
            if exclusion_clause is not None:
                cite(exclusion_clause, f"borrowing_base.components[{collateral}].eligibility")
            components.append(component)
        reserves = []
        for key, (_row, value, name, item) in latest.items():
            if key[0] == "reserve":
                reserves.append({"name": name[:1].upper() + name[1:], "amount": _plain(value.value)})
                cite(item.clause, "borrowing_base.reserves")
        if not components:
            self.reasons.append("no borrowing base component could be verified")
        if commitment is None or frequency == "none" or not components:
            return None
        cite(commitment[3].clause, "borrowing_base.commitment")
        return {"commitment": _plain(commitment[1].value), "components": components, "reserves": reserves,
                "frequency": frequency, "citation": clauses[0][0].citation(clauses[0][1]),
                "citations": [clause.citation(name) for clause, name in clauses[1:]]}


def _board_by_hand(db: Session, result: TermsResult, facility: Facility, documents: list[Document],
                   cycle: Cycle | None, reasons: list[str]) -> TermsResult:
    """Nothing is proposed: a person is asked to board the terms, with the reasons as evidence."""
    result.status = "needs_person" if result.status != "failed" else "failed"
    result.work_item = raise_item(
        db, borrower_id=facility.borrower_id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
        stage="covenant_testing", item_type="spread.value_unverified", severity="high",
        title=f"{facility.name}: terms could not be built from the agreement",
        question="The Terms Agent could not build verified terms from these documents. Board the terms by hand, or retry?",
        allowed_decisions=["board_by_hand", "retry"], required_permission=Permission.PREPARE_TERMS.value,
        evidence={"document_ids": [str(d.id) for d in documents], "reasons": reasons, "unverified": result.unverified},
        guardrail_notes=result.notes, agent_run_id=result.run_id, actor=("agent", "terms"),
        dedupe_key=f"terms.extraction:{facility.id}")
    return result


def extract_terms(db: Session, *, facility: Facility, documents: list[Document], llm: LLMClient,
                  cycle: Cycle | None = None) -> TermsResult:
    """Propose terms for `facility` from its credit agreement and any amendments.

    Returns the proposed version and its approval item, or, when valid terms cannot be built, no
    version and an item asking a person to board the terms. `unverified` lists everything the
    agent reported that code could not confirm.
    """
    result = TermsResult(status="proposed")
    borrower = db.get(Borrower, facility.borrower_id)
    documents, problem = _ordered(list(documents))
    if problem is None and any(d.status == "image_only" for d in documents):
        problem = "a document is a scanned image with no readable text"
    if problem is not None:
        return _board_by_hand(db, result, facility, documents, cycle, [problem])

    content: list[dict[str, Any]] = []
    listing = []
    for document in documents:
        kind = "credit agreement" if document.doc_type == "credit_agreement" else "amendment"
        listing.append(f"- {reference(document)} | {kind} | {document.title}")
        content.append({"type": "text", "text": f"Document {reference(document)} ({kind}): {document.title}"})
        content.append({"type": "document", "title": document.title,
                        "source": {"type": "base64", "media_type": "application/pdf",
                                   "data": base64.standard_b64encode(read_file(document)).decode()}})
    known_covenants, _ = _known_names(db, facility)
    known = "\n".join(f"- {cid} | {name}" for name, cid in known_covenants.items()) or "- none"
    content.append({"type": "text", "text": (
        f"Extract the terms of the facility \"{facility.name}\". Documents, oldest first (id | kind | title):\n"
        + "\n".join(listing) + "\nUse these ids exactly in `document_id`.\n"
        f"Covenant ids already in use for this facility (id | name), to be reused for the same covenant:\n{known}")})

    digest = hashlib.sha256("".join(d.sha256 for d in documents).encode()).hexdigest()[:12]
    scope = Scope(borrower_id=facility.borrower_id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
                  document_ids=tuple(d.id for d in documents))
    outcome = run_agent(db, SPEC, task="extract_terms", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"terms/{borrower.code}/{digest}")
    result.run_id = outcome.run.id
    if not outcome.ok:
        result.status = "failed"
        return _board_by_hand(db, result, facility, documents, cycle,
                              [f"the Terms Agent returned no usable answer ({outcome.reason})"])
    out: TermsReading = outcome.output  # type: ignore[assignment]

    draft = _Draft(db, facility, documents, out)
    for note in out.notes:  # prose from the model is shown only if it types no figure
        if check_narrative(note, {}):
            draft.notes.append({"layer": "narrative", "check": "figure_untraceable", "action": "dropped",
                                "detail": "a note from the agent contained a typed figure and was removed"})
        else:
            draft.notes.append({"layer": "agent", "check": "note", "action": "shown", "detail": note})
    terms, effective_from, sources = draft.build()
    result.unverified, result.notes = draft.unverified, draft.notes
    for entry in draft.unverified:
        result.notes.append({"layer": "terms", "check": entry["reason"], "action": "left_out",
                             "detail": f"{entry['item']}: {entry['detail']}"})
    outcome.run.guardrail_notes = result.notes

    version = None
    if terms is not None and effective_from is not None:
        try:
            version, item = propose_terms(
                db, facility=facility, terms=terms, effective_from=effective_from, source_document_ids=sources,
                prepared_by=PREPARED_BY, agent_run_id=outcome.run.id, cycle_id=cycle.id if cycle else None)
        except TermsRefused as exc:
            draft.reasons.append(str(exc))
    if version is None:
        _board_by_hand(db, result, facility, documents, cycle, draft.reasons)
    else:
        # what was left out is recorded on the version, so approving it needs a written reason,
        # and shown on the approval item beside the citation warnings
        extra = list(dict.fromkeys(draft.left_out))
        if extra:
            version.warnings = [*(version.warnings or []), *extra]
            item.severity = "high"
            item.due_date = due_date_for("high", clock.today(db))  # the item is due as a high one now
            item.question = ("Some terms could not be verified and were left out. Approve these terms as they "
                             "stand, or reject them for correction?")
        item.evidence = {**item.evidence, "warnings": version.warnings, "unverified": result.unverified}
        item.guardrail_notes = result.notes
        result.version, result.work_item, result.terms = version, item, terms
        result.effective_from, result.source_document_ids = effective_from, sources
    ledger.record(db, actor_type="agent", actor_id="terms@1", action="terms.extracted",
                  entity_type="facility", entity_id=facility.id,
                  payload={"status": result.status, "version": version.version if version else None,
                           "unverified": len(result.unverified), "left_out": list(dict.fromkeys(draft.left_out)),
                           "reasons": draft.reasons, "documents": sources})
    db.flush()
    return result

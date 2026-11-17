"""Assemble what a package says, as a structure whose every figure is a reference to a stored fact.

A figure is `{"fig": <source id>, "fmt": <format or None>}`. A source id is a fact id, or the id
of a derived figure (a recorded sum or count over facts). Free text is a list of segments: strings
and figures. Nothing here formats a number or does arithmetic on values: values come from facts,
from calculation records, or from `app.calc`.

Where a displayed number was not yet a fact, it is stored as one first:
- loan terms and the risk rating held on the borrower and loan records become `system` facts
  that name the record they were read from;
- recalculated borrowing base lines become `calculated` facts linked to the review's calculation;
- certificate borrowing base lines use the extracted `bbc.<line>` facts, or for seeded history a
  `seeded` fact that names the review it was loaded with;
- differences between the two become `calculated` facts under a reconciliation record.
Covenant thresholds, headroom and library metrics are already facts (covenant and metrics services).
"""
import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc import template
from app.calc.borrowing_base import LINE_NAMES
from app.core import clock, ledger
from app.domain import review_service
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import USABLE_STATUSES, CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact
from app.domain.metrics_service import REVIEW_METRICS, store_metrics
from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, Signal, WorkItem
from app.domain.org import User
from app.domain.reviews import Action, Commentary, ReviewMeeting, ReviewSheet
from app.domain.signals_service import quarter_ends
from app.guardrails.narrative import FACT_REF
from app.guardrails.numbers import extract_figures
from app.publishing.style import WITHHELD

CONTENT_VERSION = "package-1"
ACTOR = ("system", "publishing")
TREND_QUARTERS = 8
MAX_INPUTS_SHOWN = 12

BB_LABELS = {
    "ar_total": "Accounts receivable", "ar_ineligible_excluded": "Less: excluded accounts",
    "ar_ineligible_age": "Less: over-age accounts", "ar_ineligible_cross_aging": "Less: cross-aged accounts",
    "ar_ineligible_contra": "Less: contra accounts", "ar_ineligible_concentration": "Less: concentration excess",
    "ar_ineligible_total": "Total ineligible receivables", "ar_eligible": "Eligible receivables",
    "ar_availability": "Receivables availability", "inventory_total": "Inventory",
    "inventory_ineligible": "Less: ineligible inventory", "inventory_eligible": "Eligible inventory",
    "inventory_availability_before_sublimit": "Inventory availability before sublimit",
    "inventory_availability": "Inventory availability", "reserves": "Less: reserves",
    "borrowing_base": "Borrowing base", "commitment": "Commitment",
    "borrowing_limit": "Lesser of borrowing base and commitment", "outstanding": "Less: loans outstanding",
    "letters_of_credit": "Less: letters of credit", "availability": "Availability",
    "over_advance": "Over-advance",
}
BB_TOTALS = ("ar_ineligible_total", "ar_eligible", "inventory_eligible", "borrowing_base", "borrowing_limit",
             "availability")
SIGNAL_LABELS = {
    "covenant_headroom_low": "Covenant cushion below the policy floor",
    "covenant_headroom_falling": "Covenant cushion falling two periods running",
    "revenue_ttm_decline": "Revenue down year on year", "ebitda_margin_decline": "EBITDA margin down year on year",
    "dso_increase": "Receivable days up year on year", "dpo_increase": "Payable days up year on year",
    "leverage_increase": "Leverage up year on year", "net_loss": "Net loss, trailing twelve months",
    "cash_decline": "Cash down year on year", "line_usage_high": "Line of credit usage high",
    "availability_low": "Availability low against the commitment", "reporting_late": "Reporting received late",
    "payment_past_due": "Payment past due", "auditor_opinion": "Auditor opinion qualified",
}
SIGNAL_METRIC = {"revenue_ttm_decline": "revenue_ttm", "ebitda_margin_decline": "ebitda_margin", "dso_increase": "dso",
                 "dpo_increase": "dpo", "leverage_increase": "leverage", "net_loss": "net_income_ttm",
                 "cash_decline": "cash"}
OUTCOME_RANK = {"breach_reported_compliant": 4, "breach": 3, "cannot_test": 2, "compliant_variance": 1, "compliant": 0}
SECTION_ORDER = ("summary", "performance", "covenants", "collateral", "risks", "outlook", "note")
_MARGIN = re.compile(r"^(?P<base>.*\+\s*)(?P<pct>\d+(?:\.\d+)?)%$")


class ContentError(ValueError):
    """The package cannot be assembled; the message says what is missing."""


def fig(source_id: str | uuid.UUID | None, fmt: str | None = None) -> dict[str, Any] | None:
    return None if source_id is None else {"fig": str(source_id), "fmt": fmt}


def is_fig(value: Any) -> bool:
    return isinstance(value, dict) and "fig" in value


def plain_decimal(value: Decimal) -> str:
    """A decimal as fixed-point text with no trailing zeros, so equal values hash equally."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def day(value: date) -> str:
    return f"{value.day} {value:%b %Y}"


class Registry:
    """Every fact and derived figure a package uses, frozen with its provenance."""

    def __init__(self, db: Session):
        self.db = db
        self.facts: dict[str, dict[str, Any]] = {}
        self.derived: dict[str, dict[str, Any]] = {}
        self.warnings: list[str] = []
        self._docs: dict[uuid.UUID, Document | None] = {}
        self._calcs: dict[uuid.UUID, CalcRun | None] = {}
        self._users: dict[uuid.UUID, str] = {}

    def user_name(self, user_id: uuid.UUID | None) -> str | None:
        if user_id is None:
            return None
        if user_id not in self._users:
            user = self.db.get(User, user_id)
            self._users[user_id] = user.name if user else str(user_id)
        return self._users[user_id]

    def add(self, fact: Fact | None, label: str, fmt: str | None = None) -> dict[str, Any] | None:
        """Register a fact and return a figure that points at it."""
        if fact is None:
            return None
        fid = str(fact.id)
        if fid not in self.facts:
            self.facts[fid] = self._freeze(fact, label)
        return fig(fid, fmt)

    def add_id(self, fact_id: str | None, label: str, fmt: str | None = None) -> dict[str, Any] | None:
        if not fact_id:
            return None
        if fact_id in self.facts:
            return fig(fact_id, fmt)
        return self.add(self.db.get(Fact, uuid.UUID(fact_id)), label, fmt)

    def derive(self, name: str, label: str, op: str, inputs: list[str], unit: str) -> dict[str, Any]:
        """A sum over registered facts, or a count of named things. The value is recomputed by
        the verifier from the snapshot, so a derived figure cannot drift from its inputs."""
        if op == "sum":
            value = sum((Decimal(self.facts[i]["value"]) for i in inputs), Decimal(0))
        elif op == "count":
            value = Decimal(len(inputs))
        else:
            raise ValueError(f"unknown derivation {op!r}")
        did = f"derived:{name}"
        self.derived[did] = {"id": did, "label": label, "op": op, "inputs": list(inputs),
                             "value": plain_decimal(value), "unit": unit, "kind": "derived"}
        return fig(did)

    def record(self, source_id: str) -> dict[str, Any]:
        return self.facts.get(source_id) or self.derived[source_id]

    def _freeze(self, fact: Fact, label: str) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": str(fact.id), "key": fact.key, "label": label, "period_end": fact.period_end.isoformat(),
            "months": fact.months, "value": plain_decimal(fact.value), "unit": fact.unit, "kind": fact.kind,
            "status": fact.status, "facility_id": str(fact.facility_id) if fact.facility_id else None,
        }
        if fact.document_id:
            if fact.document_id not in self._docs:
                self._docs[fact.document_id] = self.db.get(Document, fact.document_id)
            doc = self._docs[fact.document_id]
            out["document"] = {"id": str(fact.document_id), "title": doc.title if doc else None,
                               "doc_type": doc.doc_type if doc else None, "sha256": doc.sha256 if doc else None}
            out["page"], out["quote"], out["label_text"] = fact.page, fact.quote, fact.label_text
        if fact.calc_run_id:
            if fact.calc_run_id not in self._calcs:
                self._calcs[fact.calc_run_id] = self.db.get(CalcRun, fact.calc_run_id)
            calc = self._calcs[fact.calc_run_id]
            if calc is not None:
                out["calculation"] = {
                    "id": str(calc.id), "formula_key": calc.formula_key, "formula_version": calc.formula_version,
                    "engine_version": calc.engine_version, "period_end": calc.period_end.isoformat(),
                    "terms_version_id": str(calc.terms_version_id) if calc.terms_version_id else None,
                    "inputs": calc.inputs, "outputs": calc.outputs}
        if fact.kind == "system":
            out["connector"], out["record_ref"] = fact.connector, fact.record_ref
            out["as_of"] = fact.as_of.astimezone(UTC).isoformat() if fact.as_of else None
        if fact.kind == "manual":
            out["entered_by"] = self.user_name(fact.entered_by)
            out["reason"] = fact.reason
        if fact.quote and "quote" not in out:
            out["quote"] = fact.quote
        if fact.note:
            out["note"] = fact.note
        if fact.supersedes_fact_id:
            out["supersedes_fact_id"] = str(fact.supersedes_fact_id)
        return out

    # free text -----------------------------------------------------------------------------
    def plain_text(self, text: str | None, where: str) -> list[Any]:
        """Text typed by a person or carried on a record. A figure in it has no source, so it is
        withheld from the published file and reported."""
        text = text or ""
        figures = extract_figures(text)
        if not figures:
            return [text] if text else []
        out, cursor = [], 0
        for f in figures:
            out.append(text[cursor:f.start] + WITHHELD)
            cursor = f.end
        out.append(text[cursor:])
        self.warnings.append(f"{where}: {len(figures)} typed figure(s) with no source were withheld "
                             f"({', '.join(f.raw for f in figures)})")
        return ["".join(out)]

    def narrative(self, body: str, where: str) -> list[Any]:
        """Commentary: text with `{{fact:<id>}}` references becomes text and figures."""
        segments: list[Any] = []
        cursor = 0
        for m in FACT_REF.finditer(body):
            segments.extend(self.plain_text(body[cursor:m.start()], where))
            fact = self.db.get(Fact, uuid.UUID(m.group(1)))
            figure = self.add(fact, f"Referenced in {where}", m.group(2)) if fact is not None else None
            if figure is None:
                segments.append("[reference unavailable]")
                self.warnings.append(f"{where}: a referenced fact no longer exists")
            else:
                segments.append(figure)
            cursor = m.end()
        segments.extend(self.plain_text(body[cursor:], where))
        return segments


def _tidy(value: Any) -> str:
    """A stored input value without padding zeros."""
    try:
        return plain_decimal(Decimal(str(value)))
    except ArithmeticError:
        return str(value)


def describe_source(record: dict[str, Any], facts: dict[str, dict[str, Any]] | None = None) -> dict[str, str]:
    """How a figure's source is written in a Sources list. A pure function of the frozen record,
    so the verifier can rebuild the text and compare it with what a file says."""
    kind = record["kind"]
    out = {"id": record["id"], "kind": kind, "item": record["label"], "document": "", "page": "", "detail": ""}
    if kind == "derived":
        refs = record["inputs"]
        if record["op"] == "sum":
            out["detail"] = "Sum of " + "; ".join(
                f"{(facts or {}).get(i, {}).get('label', 'fact')} [{i}]" for i in refs[:MAX_INPUTS_SHOWN])
        else:
            out["detail"] = "Count of: " + "; ".join(refs[:MAX_INPUTS_SHOWN])
        if len(refs) > MAX_INPUTS_SHOWN:
            out["detail"] += f"; and {len(refs) - MAX_INPUTS_SHOWN} more, listed in the snapshot"
        return out
    doc = record.get("document")
    if doc:
        out["document"] = doc.get("title") or ""
        out["page"] = "" if record.get("page") is None else str(record["page"])
    calc = record.get("calculation")
    if kind == "extracted":
        out["detail"] = f'Printed as "{record.get("quote") or ""}"' + (
            f' beside "{record["label_text"]}"' if record.get("label_text") else "")
    elif kind == "calculated" and calc:
        inputs = calc.get("inputs")
        if isinstance(inputs, list):
            shown = "; ".join(
                f"{i.get('key') or i.get('name')}"
                + (f" at {i['period_end']}" if i.get("period_end") else "")
                + f" = {_tidy(i.get('value'))}" + (f" [fact {str(i['fact_id'])[:8]}]" if i.get("fact_id") else "")
                for i in inputs[:MAX_INPUTS_SHOWN])
            more = f"; and {len(inputs) - MAX_INPUTS_SHOWN} more, on the calculation record" \
                if len(inputs) > MAX_INPUTS_SHOWN else ""
            out["detail"] = f"Calculation {calc['formula_key']} ({calc['formula_version']}), record {calc['id']}. " \
                            f"Inputs: {shown or 'none'}{more}"
        else:
            out["detail"] = f"Calculation {calc['formula_key']} ({calc['formula_version']}), record {calc['id']}. " \
                            "Inputs: the collateral listing held on the calculation record"
    elif kind == "system":
        out["detail"] = f"System of record {record.get('connector')}, record {record.get('record_ref')}, " \
                        f"as of {(record.get('as_of') or '')[:10]}"
        if record.get("quote"):
            out["detail"] += f'; held as "{record["quote"]}"'
    elif kind == "manual":
        out["detail"] = f"Entered by {record.get('entered_by')}: {record.get('reason')}"
    elif kind == "seeded":
        out["detail"] = record.get("note") or "Loaded from synthetic ground truth, not extracted"
    return out


# facts that did not exist yet -----------------------------------------------------------------
def _own_fact(db: Session, borrower_id: uuid.UUID, key: str, period_end: date,
              facility_id: uuid.UUID | None = None) -> Fact | None:
    query = select(Fact).where(Fact.borrower_id == borrower_id, Fact.key == key, Fact.period_end == period_end,
                               Fact.months == 0, Fact.status.in_(USABLE_STATUSES))
    query = query.where(Fact.facility_id == facility_id) if facility_id else query.where(Fact.facility_id.is_(None))
    return db.execute(query.order_by(Fact.created_at.desc(), Fact.id.desc()).limit(1)).scalar_one_or_none()


def record_fact(db: Session, borrower: Borrower, key: str, value: Decimal, unit: str, period_end: date, *,
                record_ref: str, facility: Facility | None = None, quote: str | None = None) -> Fact:
    """A number held on the borrower or loan record, as a `system` fact naming that record.
    Reused while the record still says the same; a change supersedes the earlier fact."""
    existing = _own_fact(db, borrower.id, key, period_end, facility.id if facility else None)
    if existing is not None and existing.value == value and existing.kind == "system":
        return existing
    as_of = datetime.combine(clock.today(db), datetime.min.time(), UTC)
    new = add_fact(db, borrower_id=borrower.id, facility_id=facility.id if facility else None, key=key,
                   period_end=period_end, months=0, value=value, unit=unit, kind="system",
                   connector="credit_agent_squad.loan_record", record_ref=record_ref, as_of=as_of, quote=quote,
                   supersedes_fact_id=existing.id if existing else None, actor=ACTOR)
    if existing is not None:
        existing.status = "superseded"
        ledger.record(db, actor_type=ACTOR[0], actor_id=ACTOR[1], action="fact.superseded", entity_type="fact",
                      entity_id=existing.id, payload={"by": new.id, "old_value": existing.value, "new_value": value,
                                                      "reason": "the loan record changed"})
    return new


def borrowing_base_facts(db: Session, borrower: Borrower, review: BorrowingBaseReview) -> dict[str, dict[str, Fact]]:
    """Facts for each line of a borrowing base review: recalculated, certificate and difference."""
    end = review.period_end
    out: dict[str, dict[str, Fact]] = {"computed": {}, "certificate": {}, "difference": {}}
    for line, value in review.computed.items():
        if value is None or review.calc_run_id is None:
            continue
        key = "bb.availability" if line == "availability" else f"bb.{line}"
        existing = current_fact(db, borrower.id, key, end, 0)
        if existing is None or existing.value != Decimal(str(value)) or existing.calc_run_id != review.calc_run_id:
            existing = add_fact(db, borrower_id=borrower.id, facility_id=review.facility_id, key=key, period_end=end,
                                months=0, value=Decimal(str(value)), kind="calculated",
                                calc_run_id=review.calc_run_id, actor=ACTOR)
        out["computed"][line] = existing
    for line, value in review.certificate.items():
        if value is None:
            continue
        existing = current_fact(db, borrower.id, f"bbc.{line}", end, 0)
        if existing is None and review.origin == "seeded":
            existing = add_fact(
                db, borrower_id=borrower.id, facility_id=review.facility_id, key=f"bbc.{line}", period_end=end,
                months=0, value=Decimal(str(value)), kind="seeded", actor=ACTOR,
                note=f"Borrowing base certificate line as loaded with review {review.id}; "
                     "from synthetic ground truth, not extracted")
        if existing is not None and existing.value == Decimal(str(value)):
            out["certificate"][line] = existing
    differences = {d["line"]: d for d in review.differences
                   if d.get("difference") is not None and d["line"] in out["computed"]
                   and d["line"] in out["certificate"]}
    if differences:
        wanted = {line: Decimal(str(d["difference"])) for line, d in differences.items()}
        have = {line: current_fact(db, borrower.id, f"bb.diff.{line}", end, 0) for line in wanted}
        if any(f is None or f.value != wanted[line] for line, f in have.items()):
            calc = CalcRun(
                borrower_id=borrower.id, formula_key="borrowing_base.reconcile", formula_version="borrowing-base-1",
                terms_version_id=review.terms_version_id, period_end=end, engine_version="borrowing-base-1",
                inputs=[{"name": f"{side}.{line}", "key": out[side][line].key, "period_end": end.isoformat(),
                         "fact_id": str(out[side][line].id), "value": str(out[side][line].value)}
                        for line in wanted for side in ("computed", "certificate")],
                outputs={line: str(v) for line, v in wanted.items()},
                trace={"review_id": str(review.id), "method": "recalculated less certificate, from the review"},
                created_by_type=ACTOR[0], created_by_id=ACTOR[1])
            db.add(calc)
            db.flush()
            have = {line: add_fact(db, borrower_id=borrower.id, facility_id=review.facility_id,
                                   key=f"bb.diff.{line}", period_end=end, months=0, value=v, kind="calculated",
                                   calc_run_id=calc.id, actor=ACTOR) for line, v in wanted.items()}
        out["difference"] = {line: f for line, f in have.items() if f is not None}
    return out


# one borrower ----------------------------------------------------------------------------------
def _cycle(db: Session, borrower: Borrower, period_end: date) -> Cycle:
    cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.period_end == period_end)
                       .order_by(Cycle.created_at.desc())).scalars().first()
    if cycle is None:
        raise ContentError(f"{borrower.name} has no monitoring cycle for {period_end.isoformat()}; "
                           "open the cycle or choose a period that has one")
    return cycle


def _loans(db: Session, reg: Registry, borrower: Borrower, end: date) -> list[dict[str, Any]]:
    loans = []
    for f in db.execute(select(Facility).where(Facility.borrower_id == borrower.id).order_by(Facility.code)).scalars():
        commitment = record_fact(db, borrower, "loan.commitment", f.commitment, "usd", end, record_ref=f.code,
                                 facility=f)
        key = "sys.revolver_outstanding" if f.facility_type == "revolver" else "sys.term_loan_outstanding"
        pricing: list[Any] = []
        rate = (f.profile or {}).get("interest_rate")
        if rate:
            m = _MARGIN.match(rate.strip())
            if m:
                margin = record_fact(db, borrower, "loan.margin", Decimal(m.group("pct")) / Decimal(100), "pct", end,
                                     record_ref=f.code, facility=f, quote=rate.strip())
                pricing = [m.group("base"), reg.add(margin, f"{f.name}, margin over the reference rate", "pct2")]
            else:
                pricing = reg.plain_text(rate, f"{f.name} pricing")
        loans.append({
            "id": str(f.id), "code": f.code, "name": f.name, "type": f.facility_type,
            "has_borrowing_base": f.has_borrowing_base,
            "maturity": f.maturity_date.isoformat() if f.maturity_date else None, "pricing": pricing,
            "commitment": reg.add(commitment, f"{f.name}, commitment"),
            "outstanding": reg.add(current_fact(db, borrower.id, key, end, 0), f"{f.name}, outstanding, {day(end)}"),
            "availability": reg.add(current_fact(db, borrower.id, "bb.availability", end, 0),
                                    f"{f.name}, availability, {day(end)}") if f.facility_type == "revolver" else None,
        })
    return loans


def _covenant_row(reg: Registry, db: Session, borrower: Borrower, test: CovenantTest) -> dict[str, Any]:
    name, end = test.covenant_name, test.period_end
    when = day(end)
    return {
        "covenant": name, "covenant_id": test.covenant_id, "period_end": end.isoformat(), "operator": test.operator,
        "unit": test.unit, "outcome": test.outcome, "error": None if test.outcome != "cannot_test" else "inputs missing",
        "calc_run_id": str(test.calc_run_id) if test.calc_run_id else None,
        "value": reg.add(db.get(Fact, test.value_fact_id) if test.value_fact_id else None, f"{name}, calculated, {when}"),
        "threshold": reg.add(current_fact(db, borrower.id, f"cov.{test.covenant_id}.threshold", end, 0),
                             f"{name}, required, {when}"),
        "headroom_pct": reg.add(current_fact(db, borrower.id, f"cov.{test.covenant_id}.headroom_pct", end, 0),
                                f"{name}, cushion, {when}"),
        "reported": reg.add(db.get(Fact, test.reported_fact_id) if test.reported_fact_id else None,
                            f"{name}, reported on the certificate, {when}"),
        "certificate_claims_compliance": test.reported_in_compliance,
    }


def _spread(db: Session, reg: Registry, borrower: Borrower, end: date) -> dict[str, Any]:
    """The current fact for every template line and period up to the review date."""
    cells: dict[str, dict[str, str]] = {}
    periods: dict[str, int] = {}
    facts = db.execute(select(Fact).where(
        Fact.borrower_id == borrower.id, Fact.key.in_(list(template.LINE_BY_KEY)), Fact.period_end <= end,
        Fact.status.in_(USABLE_STATUSES)).order_by(Fact.created_at, Fact.id)).scalars()
    for f in facts:
        line = template.LINE_BY_KEY[f.key]
        iso = f.period_end.isoformat()
        reg.add(f, f"{line.label}, {day(f.period_end)}")
        cells.setdefault(f.key, {})[iso] = str(f.id)  # later facts replace earlier ones
        if line.flow:
            periods[iso] = f.months
    return {"template": template.TEMPLATE_ID,
            "periods": [{"period_end": iso, "months": months} for iso, months in sorted(periods.items())],
            "cells": cells}


def build_borrower(db: Session, reg: Registry, borrower: Borrower, period_end: date) -> dict[str, Any]:
    cycle = _cycle(db, borrower, period_end)
    sheet, _, _ = review_service.build_sheet(db, cycle)  # the same facts the workspace shows
    end = period_end
    ends = quarter_ends(end, TREND_QUARTERS)
    rating = None
    if borrower.risk_rating is not None:
        rating = reg.add(record_fact(db, borrower, "borrower.risk_rating", Decimal(borrower.risk_rating), "count",
                                     end, record_ref=borrower.code), "Risk rating")
    profile = borrower.profile or {}

    # covenants: this period from the review sheet's tests, and every earlier test for the history
    tests = list(db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower.id, CovenantTest.superseded.is_(False), CovenantTest.covenant_id != "*",
        CovenantTest.period_end <= end).order_by(CovenantTest.period_end, CovenantTest.covenant_name)).scalars())
    sheet_calcs = {c["calc_run_id"] for c in sheet["covenants"]}
    history = [_covenant_row(reg, db, borrower, t) for t in tests]
    covenants = [row for row in history if row["period_end"] == end.isoformat()
                 and (row["calc_run_id"] in sheet_calcs or not sheet_calcs)]
    untested = [{"covenant": t.covenant_name, "error": t.error} for t in db.execute(select(CovenantTest).where(
        CovenantTest.cycle_id == cycle.id, CovenantTest.covenant_id == "*")).scalars()]

    # key metrics over the last eight quarters, stored as calculated facts by the metrics service
    by_end = {e: store_metrics(db, borrower, e) for e in ends}
    labels = review_service.METRIC_LABELS
    trend_rows = []
    for name in REVIEW_METRICS:
        cells = [reg.add(by_end[e].get(name), f"{labels[name]}, {day(e)}") for e in ends]
        if any(cells):
            unit = next(reg.facts[c["fig"]]["unit"] for c in cells if c)
            trend_rows.append({"metric": name, "label": labels[name], "unit": unit, "cells": cells})
    year_earlier = {m["metric"]: reg.add_id(m["year_earlier"], f"{m['label']}, a year earlier") for m in sheet["metrics"]}

    # signals: what fired, with the stored facts that sit behind it
    current_tests = {row["covenant_id"]: row for row in covenants}
    trend_by_metric = {row["metric"]: row for row in trend_rows}
    signals = []
    for s in db.execute(select(Signal).where(Signal.cycle_id == cycle.id)
                        .order_by(Signal.rank.nulls_last(), Signal.severity, Signal.rule_id, Signal.id)).scalars():
        subject = (s.basis or {}).get("subject")
        evidence: list[dict[str, Any]] = []
        metric = SIGNAL_METRIC.get(s.rule_id)
        if metric and metric in trend_by_metric:
            evidence.append({"label": "Now", "fig": trend_by_metric[metric]["cells"][-1]})
            evidence.append({"label": "A year earlier", "fig": year_earlier.get(metric)})
        elif s.rule_id.startswith("covenant_headroom") and subject in current_tests:
            evidence.append({"label": "Cushion", "fig": current_tests[subject]["headroom_pct"]})
            subject = current_tests[subject]["covenant"]
        elif s.rule_id == "line_usage_high":
            evidence.append({"label": "Outstanding", "fig": reg.add(
                current_fact(db, borrower.id, "sys.revolver_outstanding", end, 0), f"Line of credit outstanding, {day(end)}")})
            evidence.append({"label": "Commitment", "fig": reg.add(
                current_fact(db, borrower.id, "sys.commitment", end, 0), f"Line of credit commitment, {day(end)}")})
        elif s.rule_id == "availability_low":
            evidence.append({"label": "Availability", "fig": reg.add(
                current_fact(db, borrower.id, "bb.availability", end, 0), f"Availability, {day(end)}")})
        explanation = (s.explanation or {}).get("text")
        signals.append({
            "id": str(s.id), "rule": s.rule_id, "label": SIGNAL_LABELS.get(s.rule_id, s.rule_id.replace("_", " ")),
            "severity": s.severity, "status": s.status, "subject": subject,
            "evidence": [e for e in evidence if e["fig"]],
            "explanation": reg.narrative(explanation, "a signal explanation") if explanation else []})

    # borrowing base: recalculated beside the certificate
    review = db.execute(select(BorrowingBaseReview).where(BorrowingBaseReview.cycle_id == cycle.id)
                        .order_by(BorrowingBaseReview.period_end.desc(), BorrowingBaseReview.created_at.desc())).scalars().first()
    borrowing_base = None
    if review is not None:
        bb = borrowing_base_facts(db, borrower, review)
        status = {d["line"]: d.get("status") for d in review.differences}
        when = day(review.period_end)
        lines = []
        for line in LINE_NAMES:
            if line not in bb["computed"] and line not in bb["certificate"]:
                continue
            label = BB_LABELS[line]
            lines.append({
                "line": line, "label": label, "total": line in BB_TOTALS, "status": status.get(line),
                "computed": reg.add(bb["computed"].get(line), f"{label}, recalculated, {when}"),
                "certificate": reg.add(bb["certificate"].get(line), f"{label}, certificate, {when}"),
                "difference": reg.add(bb["difference"].get(line), f"{label}, recalculated less certificate, {when}")})
        borrowing_base = {"as_of": review.period_end.isoformat(), "outcome": review.outcome, "review_id": str(review.id),
                          "calc_run_id": str(review.calc_run_id) if review.calc_run_id else None, "lines": lines}

    # open work items and actions
    items = [{"id": str(w.id), "type": w.item_type, "severity": w.severity, "status": w.status, "decision": w.decision,
              "title": reg.plain_text(w.title, "a work item title"),
              "question": reg.plain_text(w.question, "a work item question")}
             for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id, WorkItem.status == "open")
                                 .order_by(WorkItem.created_at, WorkItem.id)).scalars()]
    actions = [{"id": str(a.id), "status": a.status, "owner": reg.user_name(a.owner_id),
                "due_date": a.due_date.isoformat() if a.due_date else None, "escalated": a.escalated,
                "title": reg.plain_text(a.title, "an action title"), "detail": reg.plain_text(a.detail, "an action")}
               for a in db.execute(select(Action).where(Action.borrower_id == borrower.id,
                                                        Action.status.in_(("open", "in_progress")))
                                   .order_by(Action.due_date.nulls_last(), Action.created_at, Action.id)).scalars()]

    # commentary: the current version of each section, draft or approved
    sheet_row = db.execute(select(ReviewSheet).where(ReviewSheet.cycle_id == cycle.id)).scalar_one_or_none()
    commentary = []
    if sheet_row is not None:
        rows: list[Commentary] = review_service.current_commentary(db, sheet_row)
        rows.sort(key=lambda c: (SECTION_ORDER.index(c.section) if c.section in SECTION_ORDER else 99, c.section))
        for c in rows:
            author = "Review Agent" if c.author_type == "agent" else (
                reg.user_name(uuid.UUID(c.author_id)) if len(c.author_id) == 36 else c.author_id)
            commentary.append({
                "id": str(c.id), "section": c.section, "version": c.version, "status": c.status,
                "written_by_agent": c.author_type == "agent", "author": author,
                "approved_by": reg.user_name(c.approved_by), "body": c.body,
                "segments": reg.narrative(c.body, f"the {c.section} commentary")})

    # changes since the prior period: both values are facts; the direction is a word, not a number
    prior_end = ends[-2] if len(ends) > 1 else None
    changes: dict[str, Any] = {"prior_period": prior_end.isoformat() if prior_end else None, "metrics": [],
                               "covenants": [], "new_signals": [], "cleared_signals": []}
    if prior_end is not None:
        for row in trend_rows:
            before, now = row["cells"][-2], row["cells"][-1]
            if before and now:
                a, b = Decimal(reg.facts[before["fig"]]["value"]), Decimal(reg.facts[now["fig"]]["value"])
                changes["metrics"].append({"label": row["label"], "unit": row["unit"], "prior": before, "current": now,
                                           "direction": "up" if b > a else "down" if b < a else "unchanged"})
        before_outcomes = {r["covenant_id"]: r["outcome"] for r in history if r["period_end"] == prior_end.isoformat()}
        for row in covenants:
            previous = before_outcomes.get(row["covenant_id"])
            if previous != row["outcome"]:
                changes["covenants"].append({"covenant": row["covenant"], "prior_outcome": previous,
                                             "outcome": row["outcome"]})
        def fired(when: date) -> set[tuple[str, str]]:
            return {(s.rule_id, (s.basis or {}).get("subject") or "") for s in db.execute(select(Signal).where(
                Signal.borrower_id == borrower.id, Signal.period_end == when)).scalars()}
        now_fired, before_fired = fired(end), fired(prior_end)
        def words(pairs: set[tuple[str, str]]) -> list[str]:
            return sorted(SIGNAL_LABELS.get(r, r.replace("_", " ")) + (f": {s.replace('_', ' ')}" if s else "")
                          for r, s in pairs)
        changes["new_signals"], changes["cleared_signals"] = words(now_fired - before_fired), words(before_fired - now_fired)

    return {
        "borrower": {"id": str(borrower.id), "code": borrower.code, "name": borrower.name, "industry": borrower.industry,
                     "location": ", ".join(x for x in (profile.get("city"), profile.get("state")) if x),
                     "relationship_manager": reg.user_name(borrower.relationship_manager_id),
                     "analyst": reg.user_name(borrower.analyst_id), "risk_rating": rating,
                     "fiscal_year_end_month": borrower.fiscal_year_end_month},
        "period_end": end.isoformat(), "months": cycle.months,
        "cycle": {"id": str(cycle.id), "stage": cycle.stage, "status": cycle.status},
        "loans": _loans(db, reg, borrower, end), "covenants": covenants, "covenants_untested": untested,
        "covenant_history": history,
        "trend": {"periods": [e.isoformat() for e in ends], "rows": trend_rows},
        "signals": signals, "borrowing_base": borrowing_base, "work_items": items, "actions": actions,
        "commentary": commentary, "review_sheet_status": sheet_row.status if sheet_row else None,
        "changes": changes, "spread": _spread(db, reg, borrower, end),
    }


# the whole package -----------------------------------------------------------------------------
def _worst(covenants: list[dict[str, Any]]) -> str | None:
    outcomes = [c["outcome"] for c in covenants]
    return max(outcomes, key=lambda o: OUTCOME_RANK.get(o, 0)) if outcomes else None


def _portfolio(reg: Registry, borrowers: list[dict[str, Any]]) -> dict[str, Any]:
    rows, watch, all_out, tests, breaches, signals, items = [], [], [], [], [], [], []
    for b in borrowers:
        name, code = b["borrower"]["name"], b["borrower"]["code"]
        out_ids = [loan["outstanding"]["fig"] for loan in b["loans"] if loan["outstanding"]]
        all_out.extend(out_ids)
        worst = _worst(b["covenants"])
        b_tests = [f"{name}: {c['covenant']}" for c in b["covenants"]]
        b_breach = [f"{name}: {c['covenant']}" for c in b["covenants"] if c["outcome"].startswith("breach")]
        b_signals = [f"{name}: {s['label']}" + (f" ({s['subject']})" if s["subject"] else "") for s in b["signals"]]
        b_items = [f"{name}: {w['type']} {w['id']}" for w in b["work_items"]]
        tests.extend(b_tests), breaches.extend(b_breach), signals.extend(b_signals), items.extend(b_items)
        rows.append({
            "borrower": name, "code": code, "risk_rating": b["borrower"]["risk_rating"], "worst_outcome": worst,
            "outstanding": reg.derive(f"{code}.outstanding", f"{name}, loans outstanding", "sum", out_ids, "usd")
            if out_ids else None,
            "signals": reg.derive(f"{code}.signals", f"{name}, signals this period", "count", b_signals, "count"),
            "work_items": reg.derive(f"{code}.work_items", f"{name}, open work items", "count", b_items, "count")})
        reasons = []
        if b_breach:
            reasons.append("Covenant breach: " + ", ".join(c["covenant"] for c in b["covenants"]
                                                           if c["outcome"].startswith("breach")))
        if b["borrowing_base"] and b["borrowing_base"]["outcome"] == "over_advance":
            reasons.append("Line of credit is over-advanced")
        if any(c["outcome"] == "cannot_test" for c in b["covenants"]) or b["covenants_untested"]:
            reasons.append("A covenant could not be tested")
        high = [s["label"] for s in b["signals"] if s["severity"] in ("high", "critical")]
        if high:
            reasons.append("High-severity signal: " + ", ".join(sorted(set(high))))
        if any(w["severity"] == "critical" for w in b["work_items"]):
            reasons.append("Critical work item open")
        if reasons:
            watch.append({"borrower": name, "code": code, "risk_rating": b["borrower"]["risk_rating"],
                          "worst_outcome": worst, "reasons": reasons})
    summary = [
        {"label": "Borrowers reviewed", "fig": reg.derive("borrowers", "Borrowers reviewed", "count",
                                                          [b["borrower"]["name"] for b in borrowers], "count")},
        {"label": "Loans outstanding", "fig": reg.derive("outstanding", "Loans outstanding, all borrowers", "sum",
                                                         all_out, "usd")},
        {"label": "Covenants tested", "fig": reg.derive("tests", "Covenants tested", "count", tests, "count")},
        {"label": "Covenant breaches", "fig": reg.derive("breaches", "Covenant breaches", "count", breaches, "count")},
        {"label": "Signals this period", "fig": reg.derive("signals", "Signals this period", "count", signals, "count")},
        {"label": "Open work items", "fig": reg.derive("work_items", "Open work items", "count", items, "count")},
    ]
    return {"summary": summary, "rows": rows, "watch_list": watch}


def build_content(db: Session, *, scope: str, period_end: date, borrower_id: uuid.UUID | None = None,
                  meeting_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Everything a package says. Returns the content with its frozen facts under `facts`."""
    reg = Registry(db)
    meeting = None
    if scope == "borrower":
        borrower = db.get(Borrower, borrower_id) if borrower_id else None
        if borrower is None:
            raise ContentError("a borrower package needs a borrower that exists")
        chosen = [borrower]
        title = f"{borrower.name}: credit review, {day(period_end)}"
    elif scope == "portfolio":
        ids = db.execute(select(Cycle.borrower_id).where(Cycle.period_end == period_end)).scalars().all()
        chosen = list(db.execute(select(Borrower).where(Borrower.id.in_(ids)).order_by(Borrower.name)).scalars())
        if not chosen:
            raise ContentError(f"no borrower has a monitoring cycle for {period_end.isoformat()}")
        title = f"Portfolio review, {day(period_end)}"
    elif scope == "meeting":
        meeting = db.get(ReviewMeeting, meeting_id) if meeting_id else None
        if meeting is None:
            raise ContentError("a meeting package needs a review meeting that exists")
        period_end = meeting.period_end
        ids = db.execute(select(ReviewSheet.borrower_id).where(ReviewSheet.meeting_id == meeting.id)).scalars().all()
        chosen = list(db.execute(select(Borrower).where(Borrower.id.in_(ids)).order_by(Borrower.name)).scalars())
        if not chosen:
            raise ContentError("no review sheet has been added to this meeting yet")
        title = f"{meeting.title}: review package, {day(period_end)}"
    else:
        raise ContentError(f"unknown package scope {scope!r}")
    borrowers = [build_borrower(db, reg, b, period_end) for b in chosen]
    portfolio = _portfolio(reg, borrowers)
    db.flush()
    return {
        "version": CONTENT_VERSION, "scope": scope, "title": title, "period_end": period_end.isoformat(),
        "meeting": {"id": str(meeting.id), "title": meeting.title, "meeting_date": meeting.meeting_date.isoformat()}
        if meeting else None,
        "borrowers": borrowers, "portfolio": portfolio, "warnings": reg.warnings,
        "facts": dict(sorted(reg.facts.items())), "derived": dict(sorted(reg.derived.items())),
    }


def has_draft_commentary(content: dict[str, Any]) -> list[str]:
    return [f"{b['borrower']['name']}: {c['section']}" for b in content["borrowers"] for c in b["commentary"]
            if c["status"] != "approved"]


class RefBook:
    """Numbers each source in the order a file first shows it."""

    def __init__(self, content: dict[str, Any]):
        self.sources = {**content["facts"], **content["derived"]}
        self.facts = content["facts"]
        self.numbers: dict[str, int] = {}

    def record(self, figure: dict[str, Any]) -> dict[str, Any]:
        return self.sources[figure["fig"]]

    def number(self, figure: dict[str, Any]) -> int:
        return self.numbers.setdefault(figure["fig"], len(self.numbers) + 1)

    def listing(self) -> list[tuple[int, dict[str, Any], dict[str, str]]]:
        return [(n, self.sources[sid], describe_source(self.sources[sid], self.facts))
                for sid, n in sorted(self.numbers.items(), key=lambda kv: kv[1])]

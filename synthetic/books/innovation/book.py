"""Assemble one innovation client (data only; nothing is rendered here), compute what the engine should reach, and
check that the scenario came out exactly as designed."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from synthetic.book import DocPlan
from synthetic.books.innovation import documents, model, reports
from synthetic.books.innovation.expected import (
    EXCEPTION_SEVERITY,
    FIRST_TEST,
    TOLERANCE,
    Series,
    build_plan,
    compute_signals,
    covenant_rows,
    plan_ratio,
    q,
)  # fmt: skip
from synthetic.books.innovation.model import LAST, MONTHS, Month, N, Period
from synthetic.books.innovation.roster import (
    AS_OF,
    CLIENTS,
    CURRENT_PERIOD,
    DEFAULT_SEED,
    SCENARIOS,
    ClientSpec,
)  # fmt: skip
from synthetic.books.innovation.terms import (
    DSCR_EFFECTIVE,
    DSCR_MIN,
    FERROGATE,
    SLUG,
    ClientTerms,
    build_terms,
)

D = Decimal
MARGIN = {"usd": D(50_000), "months": D("0.5"), "pct": D("0.03"), "ratio": D("0.25")}  # no test sits closer to its threshold than this
PENDING = "cash.statement_mismatch"  # raised by the statements-to-certificate reconciliation (Phase 3)
REQUIREMENTS = (("bank_statements", "bank_statement"), ("mrr_report", "mrr_report"),
                ("monthly_financials", "monthly_financials"), ("compliance_certificate", "compliance_certificate"))  # fmt: skip


@dataclass
class ClientBook:
    spec: ClientSpec
    opening: Month
    months: list[Month]
    periods: list[Period]  # all 22; `published` is what is printed
    comparative: Period
    series: Series
    plan: dict[date, int]
    terms: ClientTerms
    certificates: list[dict]
    documents: list[DocPlan]
    funding_events: list[dict]
    expected: dict
    scenario_details: dict

    @property
    def published(self) -> list[Period]:
        return self.periods[model.PUBLISHED_FROM :]


def _funding_events(spec: ClientSpec, docs: list[DocPlan]) -> list[dict]:
    events = []
    for event in spec.funding:
        evidence = [d.id for d in docs if d.type == "term_sheet"] if event.kind == "extension" or spec.id == "nimbusfield-security" \
            else [d.id for d in docs if d.type == "investor_update"]  # fmt: skip
        events.append({"kind": event.kind, "amount": event.amount, "expected_close": event.expected_close,
                       "status": event.status, "note": event.note, "evidence_document_ids": evidence})  # fmt: skip
    return events


def _reporting_items(docs: list[DocPlan]) -> list[dict]:
    items = []
    for requirement, doc_type in REQUIREMENTS:
        due = documents.package_due(doc_type)
        doc = next((d for d in docs if d.type == doc_type and d.period_end == CURRENT_PERIOD), None)
        reference = doc.received_date if doc else AS_OF
        items.append({"requirement": requirement, "document_type": doc_type, "due_date": due,
                      "received_date": doc.received_date if doc else None, "days_late": (reference - due).days})  # fmt: skip
    return items


def _version_in_force(versions: list[dict], end: date) -> dict:
    """The terms version governing a test at `end`: the latest whose effective_from is on or before it."""
    return [v for v in versions if date.fromisoformat(v["effective_from"]) <= end][-1]


def _dscr_rows(series: Series, version: dict, facility_id: str, certified: set[date]) -> list[dict]:
    """Ferrogate's trailing-twelve-month DSCR tests, one per month from the month its terms version takes effect."""
    covenant = next(c for c in version["terms"]["covenants"] if c["id"] == "dscr")
    threshold = D(covenant["test"]["threshold"])
    rows = []
    for i in range(N):
        if MONTHS[i] < DSCR_EFFECTIVE or series.dscr(i) is None:
            continue
        value = q(series.dscr(i), 2)
        reported = MONTHS[i] in certified
        rows.append({
            "period_end": MONTHS[i], "covenant_id": "dscr", "covenant_name": covenant["name"], "archetype": "coverage",
            "facility_id": facility_id, "terms_version_id": version["id"], "terms_version": version["version"],
            "unit": "ratio", "operator": ">=", "threshold": threshold, "value": value, "pass": value >= threshold,
            "headroom": q((value - threshold) / threshold, 4), "note": None,
            "reported_value": value if reported else None, "reported_threshold": threshold if reported else None,
            "reported_in_compliance": value >= threshold if reported else None,
            "outcome": "compliant" if value >= threshold else "breach",
        })  # fmt: skip
    return rows


def _expected(spec: ClientSpec, series: Series, plan: dict, terms: ClientTerms, docs: list[DocPlan],
              events: list[dict], details: dict, certificates: list[dict]) -> dict:
    rows = covenant_rows(spec, series, plan, terms.version["id"], terms.facility["id"])
    versions = terms.versions()
    if len(versions) > 1:  # a later version adds the DSCR test; every row cites the version in force at its period
        certified = {c["period_end"] for c in certificates}
        rows += _dscr_rows(series, versions[-1], terms.facility["id"], certified)
    for row in rows:
        version = _version_in_force(versions, row["period_end"])
        row["terms_version_id"], row["terms_version"] = version["id"], version["version"]
    halted = spec.scenario == "late_package"
    items = _reporting_items(docs)
    if halted:  # the October package has not arrived: October cannot be tested yet
        for row in rows:
            if row["period_end"] == CURRENT_PERIOD:
                row["after_repair"] = {"value": row["value"], "pass": row["pass"], "headroom": row["headroom"],
                                       "outcome": row["outcome"]}  # fmt: skip
                row.update(value=None, headroom=None, outcome="cannot_test", note=None, missing="package_not_received")
                row["pass"] = None
    visible = [r for r in rows if r["outcome"] != "cannot_test"]
    signals: list[dict] = []
    for i in range(FIRST_TEST + 3, N):
        if halted and i == LAST:
            continue  # financial signals are unmeasured while the spread is blocked
        late = [(it["requirement"], it["days_late"]) for it in items] if i == LAST else []
        signals += compute_signals(series, plan, visible, i, late)

    exceptions: list[dict] = []

    def raise_exception(kind: str, subject: str, summary: str) -> None:
        exceptions.append({"type": kind, "severity": EXCEPTION_SEVERITY[kind], "period_end": CURRENT_PERIOD,
                           "subject": subject, "summary": summary})  # fmt: skip

    for it in items:
        if it["received_date"] is None and it["days_late"] > 0:
            raise_exception("intake.missing_document", f"requirement:{it['requirement']}",
                            f"{it['document_type']} for {CURRENT_PERIOD.isoformat()} was due "
                            f"{it['due_date'].isoformat()} and has not been received.")
    chasing = any(e["type"] == "intake.missing_document" for e in exceptions)
    if spec.scenario == "stripple_package":
        raise_exception("intake.unclassified", f"document:{spec.id}.mrr-export",
                        "mrr_export.xlsx names no company and shows 2025, not October 2026: which client and month?")
        raise_exception("spread.value_unverified", f"document:{spec.id}.mf-{CURRENT_PERIOD.isoformat()}",
                        "'Contract liabilities' is not a template line, and the capitalised software figure may be "
                        "the balance rather than the month's spending.")
    if spec.scenario == "restricted_account":
        raise_exception(PENDING, f"cash:{CURRENT_PERIOD.isoformat()}",
                        "Bank statements show the escrow collateral account as restricted; the certificate counts it "
                        "as unrestricted cash.")
    for event in events:
        if event["status"] in ("expected", "signed") and event["expected_close"] < AS_OF:
            raise_exception("funding_slipped", f"funding_event:{event['kind']}:{event['expected_close'].isoformat()}",
                            f"The {event['kind'].replace('_', ' ')} expected to close on "
                            f"{event['expected_close'].isoformat()} has not closed.")
    for row in rows:
        if row["period_end"] != CURRENT_PERIOD:
            continue
        if row["outcome"] == "breach":
            raise_exception("covenant.breach", f"covenant:{row['covenant_id']}", f"{row['covenant_name']} fails its threshold.")
        elif row["outcome"] == "breach_reported_compliant":
            raise_exception("covenant.reported_mismatch", f"covenant:{row['covenant_id']}",
                            f"{row['covenant_name']} fails its threshold while the certificate claims compliance.")
    for signal in signals:
        if signal["period_end"] == CURRENT_PERIOD and signal["severity"] == "high":
            if signal["rule"] == "reporting_late" and chasing:
                continue  # one late filing is one question for a person
            raise_exception("signal.high", f"signal:{signal['rule']}", f"High-severity signal {signal['rule']}.")
    details["reporting"] = items
    return {"covenant_tests": rows, "borrowing_base": [], "signals": signals, "exceptions": exceptions}


def _details(spec: ClientSpec, series: Series, plan: dict, docs: list[DocPlan], events: list[dict]) -> dict:
    """Facts a grader needs that are not obvious from the rest of the file."""
    if spec.scenario == "pledged_cash":
        return {"covenant_id": "min_unrestricted_cash", "true_unrestricted_cash": series.cash(LAST),
                "pledged_cash_counted": spec.pledged, "certificate_cash": series.cash(LAST) + spec.pledged,
                "threshold": spec.min_cash, "definition_clause": {"_anchor": (SLUG, "def_unrestricted_cash")}}  # fmt: skip
    if spec.scenario == "late_package":
        return {"missing_requirements": ["bank_statements", "mrr_report"], "days_late": 12}
    if spec.scenario == "runway_falling":
        return {"rml_by_month": {MONTHS[i].isoformat(): q(series.rml(i), 2) for i in range(LAST - 3, LAST + 1)}}
    if spec.scenario == "plan_miss":
        return {"plan_ratio_by_month": {MONTHS[i].isoformat(): q(plan_ratio(series, plan, i), 4)
                                        for i in range(LAST - 3, LAST + 1)}}  # fmt: skip
    if spec.scenario == "funding_slipped":
        event = events[0]
        return {"event": {k: event[k] for k in ("kind", "amount", "expected_close")},
                "days_past_expected_close": (AS_OF - event["expected_close"]).days,
                "rml": q(series.rml(LAST), 2)}  # fmt: skip
    if spec.scenario == "restricted_account":
        return {"newly_restricted": spec.extra["newly_restricted"], "certificate_cash": series.cash(LAST) + spec.extra["newly_restricted"],
                "statement_unrestricted_cash": series.cash(LAST)}  # fmt: skip
    if spec.scenario == "cash_flow_positive":
        return {"avg_net_burn": q(series.avg_burn(LAST), 2)}
    if spec.scenario == "stripple_package":
        return {
            "new_line": {"printed_label": "Contract liabilities", "belongs_to": "bs.deferred_revenue_current",
                         "document_id": f"{spec.id}.mf-{CURRENT_PERIOD.isoformat()}"},
            "capitalised_software": {"balance_key": "bs.capitalised_software", "spend_key": "cf.capitalised_software_spend",
                                     "balance": series.months[LAST].balances["bs.capitalised_software"],
                                     "month_spend": series.months[LAST].flows["cf.capitalised_software_spend"],
                                     "misread_runway": q(reports.misread_runway(series, LAST), 2),
                                     "true_runway": q(series.rml(LAST), 2)},
            "held_file": {"document_id": f"{spec.id}.mrr-export", "reason": "no company name; rows are 2025, not 2026"},
        }  # fmt: skip
    return {}


def build_client(spec: ClientSpec, seed: int = DEFAULT_SEED) -> ClientBook:
    opening, months = model.simulate(spec, seed)
    periods = model.build_periods(months)
    problems = model.check_periods(opening, periods)
    if problems:
        raise AssertionError(f"{spec.id}: {problems[:3]}")
    comparative = model.comparative_fy2024(opening, periods[11])
    series = Series(months)
    plan = build_plan(spec, series)
    terms = build_terms(spec, plan)
    certificates = reports.build_certificates(spec, series, plan)
    rng = random.Random(f"{seed}:{spec.id}:documents")
    docs = documents.plan_documents(spec, opening, months, periods, comparative, series, certificates, terms, rng)
    docs += documents.notice_documents(spec, series, months, rng)
    if spec.scenario == "stripple_package":
        docs.append(documents.stripple_export(spec, months)[0])
    events = _funding_events(spec, docs)
    details = _details(spec, series, plan, docs, events)
    result = _expected(spec, series, plan, terms, docs, events, details, certificates)
    book = ClientBook(spec, opening, months, periods, comparative, series, plan, terms, certificates, docs, events,
                      result, details)
    verify(book)
    return book


def build_clients(seed: int = DEFAULT_SEED) -> list[ClientBook]:
    return [build_client(spec, seed) for spec in CLIENTS]


def scenario_record(book: ClientBook) -> dict:
    return {"code": book.spec.scenario, "description": SCENARIOS[book.spec.scenario], "details": book.scenario_details}


def verify(book: ClientBook) -> None:
    """Fail loudly if the client's figures are not the owner's, or its scenario is not what it is meant to produce."""
    spec, series, result = book.spec, book.series, book.expected
    rows = result["covenant_tests"]
    current = {r["covenant_id"]: r for r in rows if r["period_end"] == CURRENT_PERIOD}
    earlier = [r for r in rows if r["period_end"] != CURRENT_PERIOD]
    kinds = sorted(e["type"] for e in result["exceptions"])
    now_signals = [s for s in result["signals"] if s["period_end"] == CURRENT_PERIOD]

    def need(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(f"{spec.id} ({spec.scenario}): {message}")

    # the owner's October figures (spec 2.1), exactly
    need(series.cash(LAST) == spec.cash, "unrestricted cash at 31 October is not the owner's")
    need(series.net_burn3(LAST) == 3 * spec.burn, "three-month net burn is not three times the owner's average")
    if spec.rml is None:
        need(series.rml(LAST) is None, "runway should not be meaningful")
    else:
        need(q(series.rml(LAST), 1) == D(spec.rml), f"runway is {q(series.rml(LAST), 1)}, the owner's is {spec.rml}")
    need(book.months[LAST].balances["saas.mrr"] == spec.mrr, "MRR at 31 October is not the sized MRR")
    need(book.months[LAST].balances["saas.customers"] == spec.customers, "customers at 31 October")
    need(book.months[LAST].balances["bs.cash_restricted"] == spec.pledged, "pledged cash at 31 October")
    # no test sits on its threshold; every earlier test passes (Corvane's September is the designed exception)
    for r in rows:
        if r["value"] is not None:
            need(abs(r["value"] - r["threshold"]) >= MARGIN[r["unit"]], f"{r['covenant_id']} sits on its threshold")
    allowed = {("2026-09-30", "revenue_vs_plan")} if spec.scenario == "plan_miss" else set()
    for r in earlier:
        if r["outcome"] == "cannot_test":
            continue
        need(r["outcome"] == "compliant" or (r["period_end"].isoformat(), r["covenant_id"]) in allowed,
             f"{r['covenant_id']} {r['period_end']} is {r['outcome']}")
    if spec.id == FERROGATE:
        dscr = [r for r in rows if r["covenant_id"] == "dscr"]
        need([r["period_end"] for r in dscr] == list(MONTHS[MONTHS.index(DSCR_EFFECTIVE) :]), "DSCR tests May to October")
        need(all(r["outcome"] == "compliant" and r["threshold"] == D(DSCR_MIN) for r in dscr), "DSCR should be compliant")
    # a certificate figure is exact, or far outside every tolerance
    for r in rows:
        if r["reported_value"] is not None and r["value"] is not None:
            gap = abs(r["reported_value"] - r["value"])
            need(gap == 0 or gap >= 20 * TOLERANCE.get(r["unit"], D("0.01")), f"{r['covenant_id']} certificate is within tolerance")
    wanted = {
        "clean": [], "funding_expected": [], "runway_falling": [], "cash_flow_positive": [],
        "pledged_cash": ["covenant.reported_mismatch", "signal.high"],
        "late_package": ["intake.missing_document", "intake.missing_document"],
        "stripple_package": ["intake.unclassified", "spread.value_unverified"],
        "plan_miss": ["covenant.breach"],
        "funding_slipped": ["funding_slipped", "signal.high"],
        "restricted_account": [PENDING],
    }[spec.scenario]
    need(kinds == sorted(wanted), f"exceptions are {kinds}")
    if spec.scenario in ("clean", "funding_expected", "cash_flow_positive", "runway_falling"):
        loud = [s["rule"] for s in now_signals if s["severity"] != "low" and s["rule"] != "runway_falling"]
        need(not loud, f"has loud signals {loud}")
        need(all(r["outcome"] == "compliant" for r in current.values()), "covenants should all pass")
    if spec.scenario in ("clean", "funding_expected"):
        need(not any(s["rule"] == "runway_falling" for s in now_signals), "clean client trips runway_falling")
    if spec.scenario == "pledged_cash":
        cash = current["min_unrestricted_cash"]
        need(cash["outcome"] == "breach_reported_compliant" and cash["reported_value"] > spec.min_cash > cash["value"],
             "certificate should count pledged cash and claim compliance while true cash breaches")
        need(cash["reported_value"] - cash["value"] == spec.pledged, "the difference should be the pledged account")
    if spec.scenario == "late_package":
        need(sorted(e["subject"] for e in result["exceptions"])
             == ["requirement:bank_statements", "requirement:mrr_report"], "wrong requirements missing")
        need(max(i["days_late"] for i in book.scenario_details["reporting"]) == 12, "worst lateness should be 12 days")
        need(all(r["outcome"] == "cannot_test" for r in current.values()), "October should not be testable")
        need(not any(d.period_end == CURRENT_PERIOD for d in book.documents), "no October document should exist")
    if spec.scenario == "runway_falling":
        points = [series.rml(i) for i in range(LAST - 3, LAST + 1)]
        need(all(b < a for a, b in zip(points, points[1:], strict=False)), "runway should fall three months running")
        need(points[-1] >= 12, "runway should still be above the watch level")
        need(any(s["rule"] == "runway_falling" for s in now_signals), "runway_falling should fire")
        need(not any(s["rule"] == "burn_rising" for s in now_signals), "burn_rising should not fire")
    if spec.scenario == "plan_miss":
        ratio = {i: plan_ratio(series, book.plan, i) for i in (LAST - 2, LAST - 1, LAST)}
        need(ratio[LAST - 2] >= D("0.84"), "August should still be above 84 percent of plan")
        need(ratio[LAST - 1] <= D("0.77") and ratio[LAST] <= D("0.77"), "September and October should be under plan")
        need(current["revenue_vs_plan"]["outcome"] == "breach", "plan miss should be a breach")
        need(len(book.terms.version["terms"]["covenants"][2]["params"]["plan"]) == 18, "plan should have 18 months")
    if spec.scenario == "funding_slipped":
        need(book.funding_events[0]["expected_close"] < AS_OF, "the round should be past its date")
        need(series.rml(LAST) < 9, "runway should be under 9 months")
    if spec.scenario == "restricted_account":
        accounts = reports.bank_accounts(spec, book.months, LAST)
        held = sum(a["closing"] for a in accounts if a["restricted"])
        need(held == spec.pledged == spec.extra["newly_restricted"] + spec.extra["restricted_before"],
             "restricted balances should add to the pledged figure")
        need(all(r["outcome"] == "compliant_variance" for r in current.values() if r["covenant_id"] != "revenue_vs_plan"),
             "cash and runway should differ from the certificate but both pass")
    if spec.scenario == "cash_flow_positive":
        need(series.avg_burn(LAST) <= 0, "average net burn should be zero or negative")
        run = current["min_runway_months"]
        need(run["value"] is None and run["pass"] and run["note"] == "not_meaningful_cash_flow_positive",
             "runway should be not meaningful and compliant")
    if spec.scenario == "stripple_package":
        roll = reports.software_roll(book.months, LAST)
        need(roll["opening"] + roll["additions"] - roll["amortisation"] == roll["closing"], "software roll does not tie")
        need(roll["closing"] > 10 * roll["additions"], "balance should dwarf the month's spending")
        need(reports.misread_runway(series, LAST) < series.rml(LAST) * D("0.7"), "the misread should change runway a lot")
    for event in book.funding_events:
        need(event["kind"] in ("equity_round", "extension", "milestone_tranche", "venture_debt"), "funding kind")
    need(len(spec.id) <= 32, "borrower code is longer than 32 characters")

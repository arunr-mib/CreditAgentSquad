"""Assemble the ground truth for one borrower (data only, nothing is rendered here).

Order of work: simulate the financials, size the facilities, choose covenant
thresholds and write the agreement, build the borrower's certificates and
collateral reports, lay out the system-of-record history and the document
list, then compute the expected results and check that the scenario came out
exactly as designed.
"""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from synthetic import collateral, expected, model
from synthetic.certificates import COST_SAVINGS_LABEL, build_certificates
from synthetic.scenarios import (
    CURRENT_PERIOD,
    DEFAULT_SEED,
    ROSTER,
    SCENARIOS,
    TODAY,
    BorrowerSpec,
    build_params,
)
from synthetic.terms import TermsBuild, build_terms

D = Decimal
TEST_PERIODS = [model.period_end(y, q) for y in (2025, 2026) for q in (1, 2, 3, 4) if (y, q) <= (2026, 3)]
SPREAD_BLOCKERS = {
    "late_reporting": "package_not_received",
    "missing_page": "spread_incomplete: the balance sheet does not foot (page missing)",
    "image_only": "spread_incomplete: the income statement page has no text layer",
}


@dataclass
class DocPlan:
    id: str
    slug: str
    type: str
    title: str
    period_end: date | None
    document_date: date
    received_date: date
    payload: dict = field(default_factory=dict)
    pages: int = 0
    extra: dict = field(default_factory=dict)  # recorded in the truth file beside the spec's keys

    @property
    def filename(self) -> str:
        return f"{self.slug}.pdf"


@dataclass
class BorrowerBook:
    spec: BorrowerSpec
    opening: dict[str, Decimal]
    quarters: list[model.Quarter]
    all_periods: list[model.Period]  # from Q1 2023; only `periods` is published
    periods: list[model.Period]  # Q1 2024 to Q3 2026
    comparative: model.Period  # FY2023, printed as the comparative column of the FY2024 statements
    commitment: Decimal
    term_payment: Decimal
    terms: TermsBuild
    certificates: list[dict]
    borrowing_base: list[dict]
    system_of_record: list[dict]
    documents: list[DocPlan]
    expected: dict
    scenario_details: dict

    def period(self, end: date) -> model.Period:
        return next(p for p in self.all_periods if p.period_end == end)


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _size_commitment(peak: Decimal, usage_target: Decimal, step: Decimal | None = None) -> Decimal:
    raw = peak / usage_target
    if step is None:
        step = D(250_000) if raw < 10_000_000 else D(500_000) if raw < 25_000_000 else D(1_000_000)
    return (raw / step).to_integral_value(ROUND_CEILING) * step


def _system_of_record(spec: BorrowerSpec, book_periods: list[model.Period], commitment: Decimal, rng) -> list[dict]:
    by_end = {p.period_end: p for p in book_periods}
    records = []
    for year in (2024, 2025, 2026):
        for month in range(1, 13):
            if (year, month) > (2026, 10):
                break
            as_of = _month_end(year, month)
            quarter = (month - 1) // 3 + 1
            wobble = D(rng.randint(-15, 15)) / 1000
            if as_of in by_end:
                outstanding = by_end[as_of].values["bs.revolver"]
                term = by_end[as_of].values["bs.cpltd"] + by_end[as_of].values["bs.long_term_debt"]
            else:
                before_end = model.period_end(year, quarter - 1) if quarter > 1 else date(year - 1, 12, 31)
                after_end = model.period_end(year, quarter)
                before = by_end[before_end].values
                term = before["bs.cpltd"] + before["bs.long_term_debt"]
                if after_end in by_end:
                    after = by_end[after_end].values["bs.revolver"]
                    step = D((month - 1) % 3 + 1) / 3
                    raw = before["bs.revolver"] + (after - before["bs.revolver"]) * step
                else:
                    raw = before["bs.revolver"]
                raw = raw * (1 + wobble)
                outstanding = min(commitment, (raw / 1000).quantize(D(1), ROUND_HALF_UP) * 1000)
            past_due = 0
            if spec.scenario == "deteriorating_trend":
                past_due = {(2026, 8): 6, (2026, 9): 12, (2026, 10): 19}.get((year, month), 0)
            records.append(
                {
                    "date": as_of,
                    "revolver_outstanding": outstanding if spec.revolver else D(0),
                    "commitment": commitment if spec.revolver else D(0),
                    "past_due_days": past_due,
                    "term_loan_outstanding": term,
                }
            )
    return records


def _fiscal_label(p: model.Period) -> str:
    return f"FY{p.fiscal_year}" if p.months == 12 else f"Q{p.quarter} {p.fiscal_year}"


def _plan_documents(spec: BorrowerSpec, book: dict, rng) -> list[DocPlan]:
    bid = spec.id
    terms: TermsBuild = book["terms"]
    by_end = {p.period_end: p for p in book["all_periods"]}
    docs = [
        DocPlan(
            f"{bid}.credit-agreement", "credit-agreement", "credit_agreement",
            f"Credit Agreement between {spec.name} and Bank of Stoic", None, spec.closing_date,
            spec.closing_date, {"legal": terms.agreement},
        )
    ]  # fmt: skip
    for amendment in terms.amendments:
        docs.append(
            DocPlan(
                f"{bid}.{amendment.slug}", amendment.slug, "amendment",
                f"First Amendment to Credit Agreement, {spec.name}", None, amendment.doc_date,
                amendment.doc_date + timedelta(days=3), {"legal": amendment},
            )
        )  # fmt: skip
    for year in (2024, 2025):
        end = date(year, 12, 31)
        received = end + timedelta(days=rng.randint(76, 108))
        docs.append(
            DocPlan(
                f"{bid}.afs-{year}", f"afs-{year}", "annual_financial_statements",
                f"{spec.name} audited financial statements, fiscal year {year}", end, received - timedelta(days=9),
                received, {"current": by_end[end], "comparative": by_end[date(year - 1, 12, 31)], "audited": True},
            )
        )  # fmt: skip
    slack = spec.reporting_due_days - 3
    quarterly_received: dict[date, date] = {}
    for year in (2025, 2026):
        for quarter in (1, 2, 3):
            end = model.period_end(year, quarter)
            received = end + timedelta(days=rng.randint(slack - 16, slack))
            quarterly_received[end] = received
            if end == CURRENT_PERIOD and spec.scenario == "late_reporting":
                continue
            docs.append(
                DocPlan(
                    f"{bid}.ifs-{end.isoformat()}", f"ifs-{end.isoformat()}", "interim_financial_statements",
                    f"{spec.name} interim financial statements, {_fiscal_label(by_end[end])}", end,
                    received - timedelta(days=4), received,
                    {"current": by_end[end], "comparative": by_end[date(year - 1, end.month, end.day)], "audited": False},
                )
            )  # fmt: skip
    for certificate in book["certificates"]:
        end = certificate["period_end"]
        received = quarterly_received.get(end) or end + timedelta(days=rng.randint(slack - 12, slack))
        doc_id = f"{bid}.cc-{end.isoformat()}"
        certificate["document_id"] = doc_id
        docs.append(
            DocPlan(
                doc_id, f"cc-{end.isoformat()}", "compliance_certificate",
                f"{spec.name} compliance certificate, {_fiscal_label(by_end[end])}", end,
                received - timedelta(days=2), received, {"certificate": certificate},
            )
        )  # fmt: skip
    for entry in book["borrowing_base"]:
        end = entry["period_end"]
        received = end + timedelta(days=rng.randint(9, 17))
        doc_id = f"{bid}.bbc-{end.isoformat()}"
        entry["document_id"] = doc_id
        docs.append(
            DocPlan(
                doc_id, f"bbc-{end.isoformat()}", "borrowing_base_certificate",
                f"{spec.name} borrowing base certificate as of {end.isoformat()}", end,
                received - timedelta(days=2), received, {"borrowing_base": entry},
            )
        )  # fmt: skip
    return docs


def _days_late(spec: BorrowerSpec, end: date, docs: list[DocPlan]) -> tuple[int, list[dict]]:
    """Worst lateness, in days, of the package required for a quarter end (negative = early)."""
    annual = end.month == 12
    required = [
        ("annual_statements", "annual_financial_statements", 120)
        if annual
        else ("quarterly_statements", "interim_financial_statements", spec.reporting_due_days),
        ("compliance_certificate", "compliance_certificate", spec.reporting_due_days),
    ]
    worst, detail = -10_000, []
    for requirement, doc_type, due_days in required:
        due = end + timedelta(days=due_days)
        doc = next((d for d in docs if d.type == doc_type and d.period_end == end), None)
        late = ((doc.received_date if doc else TODAY) - due).days
        worst = max(worst, late)
        detail.append(
            {
                "requirement": requirement,
                "document_type": doc_type,
                "due_date": due,
                "received_date": doc.received_date if doc else None,
                "days_late": late,
            }
        )
    return worst, detail


def _expected(spec: BorrowerSpec, book: dict, docs: list[DocPlan], details: dict) -> dict:
    fin: expected.Financials = book["fin"]
    versions = book["terms"].versions
    certificates = {c["period_end"]: c for c in book["certificates"]}
    sor = {r["date"]: r for r in book["system_of_record"]}
    blocker = SPREAD_BLOCKERS.get(spec.scenario)

    tests_by_period: dict[date, list[dict]] = {}
    for end in TEST_PERIODS:
        version = expected.terms_version_in_force(versions, end)
        rows = []
        for covenant in version["terms"]["covenants"]:
            test = covenant["test"]
            value, lines = expected.covenant_value(
                covenant, version["terms"]["definitions"], fin, end, book["availability_at"](end)
            )
            threshold = expected.threshold_in_force(test, end)
            passed = expected.passes(value, test["operator"], threshold)
            room = expected.headroom(value, test["operator"], threshold)
            reported = certificates.get(end, {}).get("reported", {}).get(covenant["id"])
            row = {
                "period_end": end,
                "covenant_id": covenant["id"],
                "covenant_name": covenant["name"],
                "archetype": covenant["archetype"],
                "facility_id": version["facility_id"],
                "terms_version_id": version["id"],
                "terms_version": version["version"],
                "unit": test["unit"],
                "operator": test["operator"],
                "threshold": threshold,
                "value": value,
                "pass": passed,
                "headroom": room,
                "reported_value": reported["value"] if reported else None,
                "reported_threshold": reported["threshold"] if reported else None,
                "reported_in_compliance": reported["in_compliance"] if reported else None,
                "outcome": expected.classify(passed, reported, value, test["unit"]),
                "calculation": lines,
            }
            if end == CURRENT_PERIOD and blocker:
                # The figures needed cannot be read from what has been delivered. The values the
                # test will give once the gap is repaired are kept under `after_repair`.
                row["after_repair"] = {"value": value, "pass": passed, "headroom": room, "outcome": row["outcome"]}
                row.update(value=None, headroom=None, outcome="cannot_test", calculation=[], missing=blocker)
                row["pass"] = None
            rows.append(row)
        tests_by_period[end] = rows

    bb_results = []
    for entry in book["borrowing_base"]:
        calculated = entry["_calculated"]
        differences = expected.reconcile_borrowing_base(calculated, entry["certificate"])
        bb_results.append(
            {
                "period_end": entry["period_end"],
                "facility_id": versions[0]["facility_id"],
                "calculated": calculated,
                "differences": differences,
                "certificate_matches": not differences,
                "over_advance": calculated["availability"] < 0,
                "availability": calculated["availability"],
            }
        )

    # Financial signals need a completed spread; where the current spread is blocked they are unmeasured.
    usable = [p for p in book["periods"] if not (blocker and p.period_end == CURRENT_PERIOD)]
    signal_fin = expected.Financials(usable)
    signals: list[dict] = []
    lateness: dict[date, tuple[int, list[dict]]] = {}
    for end in TEST_PERIODS:
        record = sor[end]
        line = None
        if spec.revolver:
            line = {"outstanding": record["revolver_outstanding"], "commitment": record["commitment"]}
        bb_at_end = next((r["calculated"] for r in bb_results if r["period_end"] == end), None)
        lateness[end] = _days_late(spec, end, docs)
        signals += expected.compute_signals(
            end, signal_fin, tests_by_period, TEST_PERIODS, line, bb_at_end, lateness[end][0], record["past_due_days"]
        )

    exceptions: list[dict] = []

    def raise_exception(kind: str, subject: str, summary: str) -> None:
        exceptions.append(
            {
                "type": kind,
                "severity": expected.EXCEPTION_SEVERITY[kind],
                "period_end": CURRENT_PERIOD,
                "subject": subject,
                "summary": summary,
            }
        )

    if spec.scenario == "late_reporting":
        for item in lateness[CURRENT_PERIOD][1]:
            if item["received_date"] is None:
                raise_exception(
                    "intake.missing_document",
                    f"requirement:{item['requirement']}",
                    f"{item['document_type']} for {CURRENT_PERIOD.isoformat()} was due "
                    f"{item['due_date'].isoformat()} and has not been received.",
                )
        details["missing_requirements"] = [i["requirement"] for i in lateness[CURRENT_PERIOD][1]]
        details["days_late"] = lateness[CURRENT_PERIOD][0]
    current_fs = f"{spec.id}.ifs-{CURRENT_PERIOD.isoformat()}"
    if spec.scenario == "missing_page":
        raise_exception(
            "spread.does_not_foot",
            f"document:{current_fs}",
            "The liabilities and equity page of the balance sheet is missing, so total assets cannot be "
            "agreed to total liabilities and equity.",
        )
    if spec.scenario == "image_only":
        raise_exception(
            "spread.image_only", f"document:{current_fs}", "The income statement page is an image with no text layer."
        )
    if spec.scenario == "restated_comparative":
        raise_exception(
            "spread.restatement",
            f"document:{current_fs}",
            "The prior-year comparative column differs from the interim statements delivered a year ago.",
        )
    if spec.scenario == "unapproved_amendment":
        raise_exception(
            "terms.unapproved_amendment",
            f"document:{book['terms'].unapproved['document_id']}",
            "A signed amendment is on file but has not been approved into the governing terms.",
        )
    for row in tests_by_period[CURRENT_PERIOD]:
        if row["outcome"] == "breach":
            raise_exception(
                "covenant.breach", f"covenant:{row['covenant_id']}", f"{row['covenant_name']} fails its threshold."
            )
        elif row["outcome"] == "breach_reported_compliant":
            raise_exception(
                "covenant.reported_mismatch",
                f"covenant:{row['covenant_id']}",
                f"{row['covenant_name']} fails its threshold while the certificate claims compliance.",
            )
    for result in bb_results:
        if result["period_end"] != CURRENT_PERIOD:
            continue
        subject = f"borrowing_base:{CURRENT_PERIOD.isoformat()}"
        if result["over_advance"]:
            raise_exception("bb.over_advance", subject, "Line outstanding exceeds the borrowing base.")
        if not result["certificate_matches"]:
            raise_exception(
                "bb.certificate_mismatch", subject, "The certificate differs from the recalculated borrowing base."
            )
    for signal in signals:
        if signal["period_end"] == CURRENT_PERIOD and signal["severity"] == "high":
            raise_exception("signal.high", f"signal:{signal['rule']}", f"High-severity signal {signal['rule']}.")

    tests = [row for end in TEST_PERIODS for row in tests_by_period[end]]
    return {"covenant_tests": tests, "borrowing_base": bb_results, "signals": signals, "exceptions": exceptions}


def _verify_scenario(spec: BorrowerSpec, result: dict, details: dict) -> None:
    """Fail loudly if a borrower's results are not what its scenario is meant to produce."""
    tests = result["covenant_tests"]
    current = {t["covenant_id"]: t for t in tests if t["period_end"] == CURRENT_PERIOD}
    earlier = [t for t in tests if t["period_end"] != CURRENT_PERIOD]
    kinds = sorted(e["type"] for e in result["exceptions"])
    current_signals = [s for s in result["signals"] if s["period_end"] == CURRENT_PERIOD]

    def need(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(f"{spec.id} ({spec.scenario}): {message}")

    need(all(t["outcome"] == "compliant" for t in earlier), "an earlier period is not compliant")
    for t in tests:
        if t["unit"] == "ratio" and t["value"] is not None:
            need(abs(t["value"] - t["threshold"]) >= D("0.03"), f"{t['covenant_id']} sits on its threshold")
    outcomes = sorted(t["outcome"] for t in current.values())
    wanted_kinds: dict[str, list[str]] = {
        "clean": [],
        "hidden_breach": ["covenant.reported_mismatch"],
        "unapproved_amendment": ["covenant.reported_mismatch", "terms.unapproved_amendment"],
        "addback_over_cap": [],
        "late_reporting": ["intake.missing_document", "intake.missing_document", "signal.high"],
        "miscounted_ineligible": ["bb.certificate_mismatch"],
        "over_advance": ["bb.over_advance"],
        "scale_trap": [],
        "restated_comparative": ["spread.restatement"],
        "missing_page": ["spread.does_not_foot"],
        "image_only": ["spread.image_only"],
        "step_up": ["covenant.reported_mismatch"],
        "reported_breach": ["covenant.breach"],
    }
    if spec.scenario == "deteriorating_trend":
        need(set(kinds) == {"signal.high"}, f"unexpected exceptions {kinds}")
        rules = {s["rule"] for s in current_signals}
        wanted = {"revenue_ttm_decline", "ebitda_margin_decline", "dso_increase", "dpo_increase",
                  "leverage_increase", "covenant_headroom_low", "covenant_headroom_falling",
                  "line_usage_high", "payment_past_due"}  # fmt: skip
        need(wanted <= rules, f"missing signals {sorted(wanted - rules)}")
        need(outcomes == ["compliant"] * len(outcomes), "covenants should still pass")
    else:
        need(kinds == wanted_kinds[spec.scenario], f"exceptions are {kinds}")
    if spec.scenario in ("clean", "scale_trap", "restated_comparative", "miscounted_ineligible"):
        need(outcomes == ["compliant"] * len(outcomes), f"outcomes are {outcomes}")
    if spec.scenario == "clean":
        loud = [s["rule"] for s in current_signals if s["severity"] != "low"]
        need(not loud, f"clean borrower has signals {loud}")
    if spec.scenario == "addback_over_cap":
        need(outcomes == ["compliant_variance"] * len(outcomes), f"outcomes are {outcomes}")
    if spec.scenario in ("late_reporting", "missing_page", "image_only"):
        need(outcomes == ["cannot_test"] * len(outcomes), f"outcomes are {outcomes}")
        need(all(t["after_repair"]["pass"] for t in current.values()), "should pass after repair")
    if spec.scenario in ("hidden_breach", "step_up", "unapproved_amendment"):
        need(current["total_leverage"]["outcome"] == "breach_reported_compliant", "leverage should be a hidden breach")
        need(outcomes.count("breach_reported_compliant") == 1, f"outcomes are {outcomes}")
    if spec.scenario == "unapproved_amendment":
        need(details["under_amendment"]["pass"], "the test should pass under the amendment")
    if spec.scenario == "reported_breach":
        need(current["fccr"]["outcome"] == "breach", "fixed charge coverage should breach")
        need(outcomes.count("breach") == 1, f"outcomes are {outcomes}")
    if spec.borrowing_base:
        for r in result["borrowing_base"]:
            if r["period_end"] != CURRENT_PERIOD:
                need(r["certificate_matches"] and not r["over_advance"], "an earlier certificate is not clean")
            elif spec.scenario not in ("over_advance", "miscounted_ineligible"):
                need(r["availability"] >= r["calculated"]["commitment"] / 10, "availability is thin")
        if spec.scenario == "miscounted_ineligible":
            need(not result["borrowing_base"][-1]["over_advance"], "should not also be over-advanced")


def build_borrower(spec: BorrowerSpec, seed: int = DEFAULT_SEED) -> BorrowerBook:
    params = build_params(spec, seed)
    opening, quarters = model.simulate(params)
    all_periods = model.build_periods(opening, quarters, spec.scale)
    problems = model.check_periods(all_periods)
    if problems:
        raise AssertionError(f"{spec.id}: {problems[:3]}")
    periods = [p for p in all_periods if p.fiscal_year >= model.FIRST_TRUTH_YEAR]
    comparative = next(p for p in all_periods if p.period_end == date(2023, 12, 31))
    fin = expected.Financials(periods)
    rng = random.Random(f"{seed}:{spec.id}:records")

    commitment = D(0)
    if spec.revolver:
        step = spec.overrides.get("commitment_step")
        peak = max(p.values["bs.revolver"] for p in periods)
        commitment = _size_commitment(peak, D(spec.usage_target), D(step) if step else None)
    term_payment = quarters[0].flows["sup.scheduled_principal"]

    def availability_at(end: date) -> Decimal | None:
        if not spec.revolver:
            return None
        return commitment - fin.point("bs.revolver", end)

    sor = _system_of_record(spec, all_periods, commitment, rng)
    bb_terms = collateral.bb_terms_for(spec, commitment) if spec.borrowing_base else None
    terms = build_terms(spec, fin, TEST_PERIODS, opening, term_payment, commitment, bb_terms, availability_at)
    certificates = build_certificates(spec, terms.versions, fin, TEST_PERIODS, availability_at)

    borrowing_base: list[dict] = []
    if spec.borrowing_base:
        sor_by_date = {r["date"]: r for r in sor}
        june = next(p for p in periods if p.period_end == date(2026, 6, 30)).values
        september = next(p for p in periods if p.period_end == CURRENT_PERIOD).values
        receivables, inventory, outstanding = {}, {}, {}
        for i, as_of in enumerate(collateral.BB_DATES, start=1):
            for target, key in ((receivables, "bs.accounts_receivable"), (inventory, "bs.inventory")):
                value = june[key] + (september[key] - june[key]) * i / 3
                target[as_of] = (value / spec.scale).quantize(D(1), ROUND_HALF_UP) * spec.scale
            outstanding[as_of] = sor_by_date[as_of]["revolver_outstanding"]
        borrowing_base = collateral.build_borrowing_base(spec, seed, bb_terms, receivables, inventory, outstanding)

    work = {
        "terms": terms,
        "fin": fin,
        "periods": periods,
        "all_periods": all_periods,
        "certificates": certificates,
        "borrowing_base": borrowing_base,
        "system_of_record": sor,
        "availability_at": availability_at,
    }
    documents = _plan_documents(spec, work, rng)
    details = _scenario_details(spec, work, documents)
    result = _expected(spec, work, documents, details)
    _verify_scenario(spec, result, details)
    return BorrowerBook(
        spec, opening, quarters, all_periods, periods, comparative, commitment, term_payment, terms,
        certificates, borrowing_base, sor, documents, result, details,
    )  # fmt: skip


def _scenario_details(spec: BorrowerSpec, work: dict, documents: list[DocPlan]) -> dict:
    """Facts about the scenario that a grader needs and that are not obvious from the rest of the file."""
    details: dict = {}
    fin: expected.Financials = work["fin"]
    terms: TermsBuild = work["terms"]
    current_cert = next((c for c in work["certificates"] if c["period_end"] == CURRENT_PERIOD), None)
    current_fs = f"{spec.id}.ifs-{CURRENT_PERIOD.isoformat()}"
    if spec.scenario == "hidden_breach":
        line = next(
            x for x in current_cert["reported"]["total_leverage"]["calculation"] if x["label"] == COST_SAVINGS_LABEL
        )
        details = {"covenant_id": "total_leverage", "unpermitted_addback": line["label"], "amount": line["amount"]}
    elif spec.scenario == "unapproved_amendment":
        version = terms.versions[-1]
        covenant = next(c for c in version["terms"]["covenants"] if c["id"] == "total_leverage")
        amended_cap = {"type": "amount", "value": terms.unapproved["amended_cap"]}
        addback = {**version["terms"]["definitions"]["ebitda"]["addbacks"][0], "cap": amended_cap}
        amended = {"ebitda": {"base": "ebitda", "addbacks": [addback]}}
        value, _ = expected.covenant_value(covenant, amended, fin, CURRENT_PERIOD)
        threshold = expected.threshold_in_force(covenant["test"], CURRENT_PERIOD)
        details = {
            **terms.unapproved,
            "covenant_id": "total_leverage",
            "under_amendment": {
                "value": value,
                "threshold": threshold,
                "pass": expected.passes(value, covenant["test"]["operator"], threshold),
            },
        }
    elif spec.scenario == "addback_over_cap":
        taken = fin.ttm("is.nonrecurring_expense", CURRENT_PERIOD)
        details = {"addback": "restructuring", "cap": spec.addback_cap["value"], "taken_by_borrower": taken}
    elif spec.scenario == "step_up":
        details = dict(terms.step)
    elif spec.scenario == "scale_trap":
        details = {"statement_scale": spec.scale, "certificate_scale": current_cert["scale"]}
    elif spec.scenario == "restated_comparative":
        doc = next(d for d in documents if d.id == current_fs)
        original = doc.payload["comparative"]
        shift = (original.values["is.revenue"] * D("0.012") / spec.scale).quantize(D(1), ROUND_HALF_UP) * spec.scale
        restated = dict(original.values)
        restated["is.revenue"] -= shift
        restated["is.cogs"] -= shift
        doc.payload["comparative_values"] = restated
        details = {
            "document_id": current_fs,
            "comparative_period_end": original.period_end,
            "restated_lines": [
                {"key": key, "as_previously_reported": original.values[key], "as_restated": restated[key]}
                for key in ("is.revenue", "is.cogs")
            ],
        }
    elif spec.scenario == "missing_page":
        doc = next(d for d in documents if d.id == current_fs)
        doc.payload["omit_section"] = "balance_sheet_liabilities"
        details = {"document_id": current_fs, "omitted_section": "balance sheet: liabilities and equity"}
    elif spec.scenario == "image_only":
        doc = next(d for d in documents if d.id == current_fs)
        doc.payload["image_section"] = "income_statement"
        details = {"document_id": current_fs, "image_section": "income statement"}
    elif spec.scenario == "miscounted_ineligible":
        entry = work["borrowing_base"][-1]
        gap = entry["_calculated"]["ineligible_over_age"] - entry["certificate"]["ineligible_over_age"]
        details = {"document_id": entry["document_id"], "over_90_counted_as_eligible": gap}
    elif spec.scenario == "over_advance":
        entry = work["borrowing_base"][-1]
        details = {"document_id": entry["document_id"], "over_advance_amount": -entry["_calculated"]["availability"]}
    return details


def build_book(seed: int = DEFAULT_SEED) -> list[BorrowerBook]:
    return [build_borrower(spec, seed) for spec in ROSTER]


def scenario_record(book: BorrowerBook) -> dict:
    return {"code": book.spec.scenario, "description": SCENARIOS[book.spec.scenario], "details": book.scenario_details}

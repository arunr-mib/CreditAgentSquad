"""Cross-check against the synthetic loan book (spec sections 14 and 16).

The generator in `synthetic/` computes its `expected` block with its own arithmetic. This
module generates the book into a temporary directory (about five seconds), feeds every truth
file's period values and terms through `app.calc`, and requires exact agreement. It runs the
generator as a separate process and reads only its JSON output, never its code. It is skipped
when the generator is not in the checkout.

A disagreement is a finding to investigate, not a number to patch. The one place where the
two sides are known to differ in labelling (not arithmetic) is pinned in
KNOWN_SEVERITY_DIFFERENCES, so the suite fails the moment either side moves.
"""

import json
import subprocess
import sys
from collections import Counter
from datetime import date
from decimal import Decimal as D
from functools import cache
from pathlib import Path

import pytest
from app.calc import covenants as cov
from app.calc.borrowing_base import (
    ArRow,
    InventoryRow,
    compute_borrowing_base,
    reconcile,
    unused_availability,
)
from app.calc.periods import provider_from_facts
from app.calc.signals import (
    PeriodMetrics,
    ReportingItem,
    SystemRow,
    compute_signal_inputs,
    evaluate_signals,
    reporting_due_date,
)
from app.calc.template import LINE_BY_KEY, compute_statement
from app.calc.terms import TermsVersion, terms_in_force

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    not (REPO / "synthetic" / "generate.py").exists(), reason="the synthetic generator is not in this checkout")

# Agreement between the computed value and the certificate, by unit of the covenant.
TOLERANCE = {"ratio": D("0.01"), "usd": D("1")}

# Truth line name -> app.calc line name, where they differ.
BB_LINES = {
    "gross_ar": "ar_total", "ineligible_excluded": "ar_ineligible_excluded",
    "ineligible_over_age": "ar_ineligible_age", "ineligible_cross_aging": "ar_ineligible_cross_aging",
    "ineligible_contra": "ar_ineligible_contra", "ineligible_concentration": "ar_ineligible_concentration",
    "total_ineligible_ar": "ar_ineligible_total", "eligible_ar": "ar_eligible",
    "gross_inventory": "inventory_total", "ineligible_inventory": "inventory_ineligible",
    "eligible_inventory": "inventory_eligible", "lesser_of_base_and_commitment": "borrowing_limit",
}

# Labelling difference the spec does not settle (reported to the owner; not arithmetic).
KNOWN_SEVERITY_DIFFERENCES = {  # rule id -> (app.calc severity, truth severity)
}


class Book:
    """One truth file, wired to the engine the way the services will wire a borrower."""

    def __init__(self, path: Path) -> None:
        self.data = json.loads(path.read_text())
        self.borrower = self.data["borrower"]["id"]
        self.fye_month = self.data["borrower"]["fiscal_year_end_month"]
        self.versions = [TermsVersion.model_validate(v) for v in self.data["terms_versions"]]
        self.periods = self.data["periods"] + self.data["comparative_periods"]
        self.system_rows = [
            SystemRow(date.fromisoformat(r["date"]), D(r["revolver_outstanding"]), D(r["commitment"]), r["past_due_days"])
            for r in self.data["system_of_record"]
        ]
        self.spread_problems: list[str] = []
        facts: dict = {}
        for period in self.periods:
            period_end, months = date.fromisoformat(period["period_end"]), period["months"]
            stated = {k: D(v) for k, v in period["values"].items()}
            inputs = {k: v for k, v in stated.items() if not LINE_BY_KEY[k].computed}
            spread = compute_statement(inputs)
            self.spread_problems += [f"{period['period_end']} {e.code} {e.key}" for e in spread.errors]
            self.spread_problems += [
                f"{period['period_end']} {key}: computed {value}, truth {stated.get(key)}"
                for key, value in spread.computed.items() if stated.get(key) != value
            ]
            for key, value in spread.values.items():
                facts[(key, period_end, months)] = value

        # Availability: the recalculated borrowing base where there is one, else the unused commitment.
        self.borrowing_bases = {}
        for entry in self.data["borrowing_base"]:
            period_end = date.fromisoformat(entry["period_end"])
            terms = terms_in_force(self.versions, period_end).version.terms
            rows = [
                ArRow(r["customer"], D(r["buckets"]["0_30"]), D("0"), D(r["buckets"]["31_60"]), D(r["buckets"]["61_90"]),
                      D(r["buckets"]["over_90"]), frozenset() if r["category"] == "trade" else frozenset([r["category"]]),
                      D(r["contra"]))
                for r in entry["ar_aging"]
            ]
            inventory = [InventoryRow(i["category"], D(i["amount"])) for i in entry["inventory"]]
            self.borrowing_bases[period_end] = compute_borrowing_base(
                rows, inventory, terms.borrowing_base, D(entry["outstanding"]), D(entry["letters_of_credit"]))
        self.availability: dict[date, D] = {k: v.availability for k, v in self.borrowing_bases.items()}
        rows_by_date = {r.date: r for r in self.system_rows}
        for period in self.data["periods"]:
            period_end, months = date.fromisoformat(period["period_end"]), period["months"]
            in_force = terms_in_force(self.versions, period_end).version
            if in_force is not None and in_force.terms.borrowing_base is None and period_end in rows_by_date:
                row = rows_by_date[period_end]
                facts[("bb.availability", period_end, months)] = unused_availability(row.commitment, row.revolver_outstanding)
            elif period_end in self.availability:
                facts[("bb.availability", period_end, months)] = self.availability[period_end]
        self.provider = provider_from_facts(facts)
        self.tested_periods = sorted({date.fromisoformat(e["period_end"]) for e in self.data["expected"]["covenant_tests"]})

    @cache  # noqa: B019 - the books live for the whole test session
    def test(self, covenant_id: str, period_end: date):
        version = terms_in_force(self.versions, period_end).version
        covenant = version.terms.covenant(covenant_id)
        return version, cov.test_covenant(covenant, period_end, self.provider, version.terms.definitions,
                                          fye_month=self.fye_month)


@pytest.fixture(scope="session")
def books(tmp_path_factory) -> list[Book]:
    """Generate the book into a temporary directory and load every truth file."""
    out = tmp_path_factory.mktemp("synthetic-book")
    command = [sys.executable, "-m", "synthetic.generate", "--out", str(out / "out"), "--oracle", str(out / "oracle.csv")]
    run = subprocess.run(command, cwd=REPO, capture_output=True, text=True, timeout=300, check=False)
    assert run.returncode == 0, f"synthetic.generate failed:\n{run.stdout}\n{run.stderr}"
    files = sorted((out / "out" / "truth").glob("*.json"))
    assert len(files) >= 15, f"expected the whole book, found {len(files)} truth files"
    return [Book(path) for path in files]


def text(value) -> str | None:
    return None if value is None else str(value)


def test_template_subtotals_reproduce_every_computed_line(books):
    assert [f"{book.borrower} {p}" for book in books for p in book.spread_problems] == []


def test_covenant_values_pass_flags_headroom_and_outcomes(books):
    """Every expected covenant test: terms version, threshold in force, value, pass, headroom, outcome.

    Where the truth expects `cannot_test` because a document is defective (missing page, no
    text layer, package not received), the truth values are still complete, so the engine is
    held to the `after_repair` result instead.
    """
    problems, compared = [], 0
    for book in books:
        compared += len(book.data["expected"]["covenant_tests"])
        problems += covenant_problems(book)
    assert compared >= 300
    assert problems == []


def covenant_problems(book: Book) -> list[str]:
    problems = []
    for expected in book.data["expected"]["covenant_tests"]:
        period_end = date.fromisoformat(expected["period_end"])
        version, result = book.test(expected["covenant_id"], period_end)
        reported = (expected["reported_value"], expected["reported_threshold"], expected["reported_in_compliance"])
        entry = None
        if any(item is not None for item in reported):
            entry = cov.CertificateEntry(
                None if reported[0] is None else D(reported[0]), None if reported[1] is None else D(reported[1]), reported[2])
        outcome = cov.determine_outcome(result, entry, TOLERANCE[expected["unit"]])
        target = expected.get("after_repair", expected)
        mine = {
            "terms_version_id": version.id, "threshold": text(result.threshold), "operator": result.operator,
            "value": text(result.value), "pass": result.passed, "headroom": text(result.headroom_pct),
            "outcome": outcome.outcome,
        }
        theirs = {
            "terms_version_id": expected["terms_version_id"], "threshold": expected["threshold"],
            "operator": expected["operator"], "value": target["value"], "pass": target["pass"],
            "headroom": target["headroom"], "outcome": target["outcome"],
        }
        for item in mine:
            if mine[item] != theirs[item]:
                problems.append(f"{book.borrower} {expected['period_end']} {expected['covenant_id']} {item}: "
                                f"app.calc {mine[item]!r}, truth {theirs[item]!r}")
    return problems


def test_borrowing_base_figures_and_reconciliation(books):
    problems, compared = [], 0
    for book in books:
        compared += len(book.data["expected"]["borrowing_base"])
        problems += borrowing_base_problems(book)
    assert compared >= 20
    assert problems == []


def borrowing_base_problems(book: Book) -> list[str]:
    problems = []
    expected_by_date = {e["period_end"]: e for e in book.data["expected"]["borrowing_base"]}
    assert len(expected_by_date) == len(book.data["borrowing_base"])
    for entry in book.data["borrowing_base"]:
        where = f"{book.borrower} {entry['period_end']}"
        expected = expected_by_date[entry["period_end"]]
        result = book.borrowing_bases[date.fromisoformat(entry["period_end"])]
        problems += [f"{where} {e.code} {e.message}" for e in result.errors]
        for name, value in expected["calculated"].items():
            mine = result.lines[BB_LINES.get(name, name)]
            if text(mine) != value:
                problems.append(f"{where} {name}: app.calc {mine}, truth {value}")
        if text(result.availability) != expected["availability"]:
            problems.append(f"{where} availability: app.calc {result.availability}, truth {expected['availability']}")
        if result.is_over_advance != expected["over_advance"]:
            problems.append(f"{where} over_advance: app.calc {result.is_over_advance}, truth {expected['over_advance']}")

        certificate = {BB_LINES.get(k, k): D(v) for k, v in entry["certificate"].items()}
        to_truth = {v: k for k, v in BB_LINES.items()}
        mine = [(to_truth.get(r.line, r.line), text(r.computed), text(r.certificate))
                for r in reconcile(result, certificate, D("0")) if r.status != "match"]
        theirs = [(d["line"], d["calculated"], d["certificate"]) for d in expected["differences"]]
        if mine != theirs:
            problems.append(f"{where} differences: app.calc {mine}, truth {theirs}")
        if (not mine) != expected["certificate_matches"]:
            problems.append(f"{where} certificate_matches: app.calc {not mine}, truth {expected['certificate_matches']}")
    return problems


def reporting_items(book: Book, period_end: date) -> list[ReportingItem]:
    """Quarterly and annual requirements falling on `period_end`, with the receipt date if delivered."""
    received = {(d["type"], d["period_end"]): date.fromisoformat(d["received_date"]) for d in book.data["documents"]}
    at_year_end = period_end.month == book.fye_month
    items = []
    for requirement in terms_in_force(book.versions, period_end).version.terms.reporting_requirements:
        if requirement.frequency == "monthly":
            continue  # monthly borrowing base certificates are outside this quarterly check
        if requirement.frequency == "annual" and not at_year_end:
            continue
        if requirement.document_type == "interim_financial_statements" and at_year_end:
            continue  # interim statements cover the first three quarters only
        items.append(ReportingItem(
            requirement.id, period_end, reporting_due_date(period_end, requirement.due_days_after_period_end),
            received.get((requirement.document_type, period_end.isoformat()))))
    return items


def comparable(signal) -> tuple:
    """An app.calc signal in the truth's shape: (rule, period_end, covenant_id, value, trigger, detail)."""
    basis, rule = signal.basis, signal.rule_id
    detail: tuple = ()
    if signal.rule_id == "covenant_headroom_low":
        value, trigger = basis["current"]["value"], basis["threshold"]
    elif signal.rule_id == "covenant_headroom_falling":
        value, trigger = basis["values"][-1]["value"], None
        detail = (text(basis["values"][0]["value"]), text(basis["values"][1]["value"]))
    elif signal.rule_id == "line_usage_high":
        value, trigger = basis["usage"], basis["threshold"]
    elif signal.rule_id == "availability_low":
        value, trigger = basis["ratio"], basis["threshold"]
    elif signal.rule_id in ("revenue_ttm_decline", "ebitda_margin_decline", "cash_decline"):
        value, trigger = basis["change"], -basis["threshold"]
    elif signal.rule_id in ("dso_increase", "dpo_increase", "leverage_increase"):
        value, trigger = basis["change"], basis["threshold"]
    elif signal.rule_id == "reporting_late":
        value, trigger = basis["days_late"], basis["threshold"]
    elif signal.rule_id == "payment_past_due":
        value, trigger = basis["past_due_days"], basis["threshold"]
    else:
        value, trigger = basis.get("current", {}).get("value"), basis.get("threshold")
    covenant_id = basis.get("covenant_id")
    return (rule, signal.period_end.isoformat(), covenant_id, text(value), None if trigger is None else D(str(trigger)), detail)


def test_signals_match_exactly(books):
    """Rule, period, covenant, value, trigger and (for falling headroom) the two earlier values.

    Wiring, as the monitoring cycle will do it: one series entry per statement period with the
    unrounded signal inputs; covenant headroom for the periods the book tests; availability
    only where a borrowing base governs; the system-of-record rows; and the reporting items
    due for the period, judged as of the book's `as_of` date.
    """
    problems, compared = [], 0
    for book in books:
        compared += len(book.data["expected"]["signals"])
        problems += signal_problems(book)
    assert compared >= 50
    assert problems == []


def signal_problems(book: Book) -> list[str]:
    as_of = date.fromisoformat(book.data["as_of"])
    series = []
    for period in book.periods:
        period_end = date.fromisoformat(period["period_end"])
        metrics = dict(compute_signal_inputs(period_end, book.provider, fye_month=book.fye_month).values)
        metrics["availability"] = book.availability.get(period_end)
        headroom = {}
        if period_end in book.tested_periods:
            for covenant in terms_in_force(book.versions, period_end).version.terms.covenants:
                headroom[covenant.id] = book.test(covenant.id, period_end)[1].headroom_pct
        series.append(PeriodMetrics(period_end, period["months"], metrics, headroom))

    mine: Counter = Counter()
    severities = {}
    for period_end in book.tested_periods:
        evaluation = evaluate_signals(period_end, series, system_rows=book.system_rows,
                                      reporting=reporting_items(book, period_end), as_of=as_of)
        late = [s for s in evaluation.signals if s.rule_id == "reporting_late"]
        # The truth carries one reporting signal per period; app.calc raises one per late
        # requirement. Compare the most overdue one (a reported finding, not arithmetic).
        keep = [s for s in evaluation.signals if s.rule_id != "reporting_late"]
        keep += sorted(late, key=lambda s: s.basis["days_late"])[-1:]
        for signal in keep:
            key = comparable(signal)
            mine[key] += 1
            severities[key] = signal.severity

    theirs: Counter = Counter()
    problems = []
    for expected in book.data["expected"]["signals"]:
        detail = expected["detail"]
        falling = (detail["two_periods_ago"], detail["prior_period"]) if "prior_period" in detail else ()
        trigger = None if expected["trigger"] is None else D(expected["trigger"])
        key = (expected["rule"], expected["period_end"], detail.get("covenant_id"), expected["value"], trigger, falling)
        theirs[key] += 1
        if key in severities:
            pair = (severities[key], expected["severity"])
            wanted = KNOWN_SEVERITY_DIFFERENCES.get(expected["rule"])
            if (pair != wanted) if wanted else (pair[0] != pair[1]):
                problems.append(f"{book.borrower} {key[:3]} severity: app.calc {pair[0]}, truth {pair[1]}")
    problems += [f"{book.borrower} only app.calc fires {key}" for key in sorted(mine - theirs, key=str)]
    problems += [f"{book.borrower} only truth expects {key}" for key in sorted(theirs - mine, key=str)]
    return problems

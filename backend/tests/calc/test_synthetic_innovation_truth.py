"""Cross-check against the innovation book (design spec section 11).

The generator in `synthetic/books/innovation/` computes its `expected` block with its own arithmetic. This module
generates the book into a temporary directory, feeds every venture client's period values and terms through `app.calc`
(template `vc-1`), and requires exact agreement on the statements, every covenant test and its outcome, and the
current period's signals. It reads only the generator's JSON output, never its code. The four kept C&I borrowers
are the v1 book, cross-checked by `test_synthetic_truth.py`; here they are required to be byte-identical to v1.

A disagreement is a finding to investigate, never a number to patch.
"""

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.calc import covenants as cov
from app.calc.periods import provider_from_facts
from app.calc.signals import PeriodMetrics, ReportingItem, compute_signal_inputs, evaluate_signals
from app.calc.template import compute_statement, template_lines
from app.calc.terms import TermsVersion, terms_in_force

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    not (REPO / "synthetic" / "books" / "innovation" / "generate.py").exists(),
    reason="the innovation generator is not in this checkout")
KEPT = ("kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain")
# the engine's own tolerances (covenant_service.DEFAULT_TOLERANCE); a unit it does not list is exact
TOLERANCE = {"ratio": D("0.005"), "usd": D("1"), "pct": D("0.0005"), "days": D("0.5")}
# Raised by the live cycle (the cash reconciliation and the Intake and Spreading Agents), never by the covenant
# calculation these tests check. Both are now raised and graded end to end by the stand-in suite; this pins the
# answer key's rows so the calculation checks fail if the key moves.
RAISED_BY_THE_CYCLE = {"brackmere-medical": ["cash.statement_mismatch"],
                       "cindrel-tech": ["intake.unclassified", "spread.value_unverified"]}  # fmt: skip
VC_LINES = {line.key: line for line in template_lines("vc-1")}
VC_KEYS = set(VC_LINES)
OPTIONAL_KEYS = {key for key, line in VC_LINES.items() if line.optional}  # unmeasured when not printed, never zero
# Ferrogate Cloud: terms v2 (a TTM `dscr` covenant) governs from 2026-05-31, so six extra tests (May to October 2026)
TESTS = 16 * 3 * 15 + 6


class Client:
    """One truth file, wired to the engine the way the services wire a borrower."""

    def __init__(self, path: Path) -> None:
        self.data = json.loads(path.read_text())
        self.id = self.data["borrower"]["id"]
        self.versions = [TermsVersion.model_validate(v) for v in self.data["terms_versions"]]
        self.current = date.fromisoformat(self.data["current_period"])
        self.version = terms_in_force(self.versions, self.current).version  # the version governing the current period
        self.terms = self.version.terms
        self.problems: list[str] = []
        facts = {}
        for period in self.data["periods"] + self.data["comparative_periods"]:
            end, months = date.fromisoformat(period["period_end"]), period["months"]
            stated = {k: D(str(v)) for k, v in period["values"].items()}
            unknown, missing = set(stated) - VC_KEYS, VC_KEYS - set(stated) - OPTIONAL_KEYS
            if unknown or missing:
                self.problems.append(f"{end}: keys differ from the template: unknown {sorted(unknown)}, "
                                     f"missing {sorted(missing)}")
            inputs = {k: v for k, v in stated.items() if k in VC_LINES and not VC_LINES[k].computed}
            spread = compute_statement(inputs, template_id="vc-1")
            self.problems += [f"{end} {e.code} {e.key}" for e in spread.errors]
            self.problems += [f"{end} {k}: computed {v}, truth {stated.get(k)}" for k, v in spread.computed.items()
                              if stated.get(k) != v]
            for key, value in stated.items():
                facts[(key, end, months)] = value
        self.provider = provider_from_facts(facts)
        plan = next(c for c in self.terms.covenants if c.archetype == "revenue_vs_plan").typed_params.plan
        self.plan = {p.period_end: p.amount for p in plan}
        self.results = {}
        for row in self.data["expected"]["covenant_tests"]:
            end = date.fromisoformat(row["period_end"])
            in_force = terms_in_force(self.versions, end)  # the version in force that period, not the latest
            governing = in_force.version
            if governing is None or governing.id != row["terms_version_id"]:
                self.problems.append(f"{end} {row['covenant_id']}: truth uses {row['terms_version_id']}, "
                                     f"engine finds {governing and governing.id}")
                continue
            covenant = governing.terms.covenant(row["covenant_id"])
            self.results[(end, row["covenant_id"])] = cov.test_covenant(
                covenant, end, self.provider, self.terms.definitions, fye_month=12, template_id="vc-1")


def text(value) -> str | None:
    return None if value is None else str(value)


def covenant_problems(client: Client) -> list[str]:
    problems = []
    for row in client.data["expected"]["covenant_tests"]:
        end = date.fromisoformat(row["period_end"])
        result = client.results.get((end, row["covenant_id"]))
        if result is None:
            continue  # already reported as a terms-version disagreement
        target = row.get("after_repair", row)
        reported = (row["reported_value"], row["reported_threshold"], row["reported_in_compliance"])
        entry = None
        if any(item is not None for item in reported):
            entry = cov.CertificateEntry(None if reported[0] is None else D(reported[0]),
                                         None if reported[1] is None else D(reported[1]), reported[2])
        outcome = cov.determine_outcome(result, entry, TOLERANCE.get(row["unit"], D("0")))
        mine = {"value": result.value, "pass": result.passed, "headroom": result.headroom_pct, "note": result.note,
                "threshold": result.threshold, "outcome": outcome.outcome}
        theirs = {"value": None if target["value"] is None else D(target["value"]), "pass": target["pass"],
                  "headroom": None if target["headroom"] is None else D(target["headroom"]),
                  "note": row.get("note"), "threshold": D(row["threshold"]), "outcome": target["outcome"]}
        for name in mine:
            if mine[name] != theirs[name]:
                problems.append(f"{client.id} {row['period_end']} {row['covenant_id']} {name}: "
                                f"app.calc {mine[name]!r}, truth {theirs[name]!r}")
    return problems


def signal_problems(client: Client) -> list[str]:
    """The current period's signals, with the engine's own covenant headroom and the approved plan from the terms."""
    if client.data["scenario"]["code"] == "late_package":
        return []  # the October spread is blocked, so financial signals are unmeasured (checked by the seed test)
    plan = {k: D(v) for k, v in client.plan.items()}
    inputs = compute_signal_inputs(client.current, client.provider, fye_month=12, template_id="vc-1",
                                   history_months=13, plan=plan)
    series = []
    for end in sorted({date.fromisoformat(r["period_end"]) for r in client.data["expected"]["covenant_tests"]})[-14:]:
        entry = inputs if end == client.current else inputs.history.get(end)
        headroom = {cid: res.headroom_pct for (e, cid), res in client.results.items()
                    if e == end and res.headroom_pct is not None}
        series.append(PeriodMetrics(end, end.month, dict(entry.values), headroom))
    items = [ReportingItem(i["requirement"], client.current, date.fromisoformat(i["due_date"]),
                           None if i["received_date"] is None else date.fromisoformat(i["received_date"]))
             for i in client.data["scenario"]["details"]["reporting"]]
    evaluation = evaluate_signals(client.current, series, reporting=items,
                                  as_of=date.fromisoformat(client.data["as_of"]), template_id="vc-1")
    mine = sorted((s.rule_id, s.severity, s.basis.get("covenant_id") or "") for s in evaluation.signals)
    theirs = sorted((s["rule"], s["severity"], (s.get("detail") or {}).get("covenant_id") or "")
                    for s in client.data["expected"]["signals"] if s["period_end"] == client.data["current_period"])
    return [] if mine == theirs else [f"{client.id}: app.calc {mine}; truth {theirs}"]


@pytest.fixture(scope="session")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("innovation-book")
    run = subprocess.run([sys.executable, "-m", "synthetic.books.innovation.generate", "--out", str(out / "out"),
                          "--oracle", str(out / "oracle.csv")], cwd=REPO, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, f"generate failed:\n{run.stdout}\n{run.stderr}"
    return out


@pytest.fixture(scope="session")
def clients(book) -> list[Client]:
    files = sorted(p for p in (book / "out" / "truth").glob("*.json") if p.stem not in KEPT)
    assert len(files) == 16
    return [Client(p) for p in files]


def test_statements_reproduce_every_subtotal(clients):
    assert [p for c in clients for p in c.problems] == []


def test_covenant_values_pass_flags_headroom_and_outcomes(clients):
    problems = [p for c in clients for p in covenant_problems(c)]
    assert sum(len(c.data["expected"]["covenant_tests"]) for c in clients) == TESTS
    assert problems == []


def test_current_period_signals_match(clients):
    assert [p for c in clients for p in signal_problems(c)] == []


def test_the_runway_of_a_cash_flow_positive_client_is_not_meaningful(clients):
    ferrogate = next(c for c in clients if c.id == "ferrogate-cloud")
    result = ferrogate.results[(ferrogate.current, "min_runway_months")]
    assert (result.value, result.passed, result.note) == (None, True, cov.NOT_MEANINGFUL_CASH_FLOW_POSITIVE)


def test_a_plan_that_stops_short_of_the_test_month_cannot_be_tested_and_names_the_month(clients):
    """The approved plan runs to October 2026. November cannot be tested against a partial plan."""
    client = clients[0]
    covenant = client.terms.covenant("revenue_vs_plan")
    result = cov.test_covenant(covenant, date(2026, 11, 30), client.provider, client.terms.definitions, fye_month=12,
                               template_id="vc-1")
    assert result.passed is None and result.value is None
    assert any("2026-11-30" in error.message for error in result.errors)


def test_only_agent_raised_exceptions_are_outside_the_calculation_checks(clients):
    pending = {c.id: sorted(x["type"] for x in c.data["expected"]["exceptions"] if x["type"] in
                            {t for kinds in RAISED_BY_THE_CYCLE.values() for t in kinds})
               for c in clients}
    assert {k: v for k, v in pending.items() if v} == RAISED_BY_THE_CYCLE


def test_kept_borrowers_are_the_v1_book_byte_for_byte(book, tmp_path):
    legacy_out = tmp_path / "legacy"
    run = subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(legacy_out), "--oracle",
                          str(tmp_path / "legacy-oracle.csv")], cwd=REPO, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr
    for borrower in KEPT:
        assert (book / "out" / "truth" / f"{borrower}.json").read_bytes() == \
            (legacy_out / "truth" / f"{borrower}.json").read_bytes(), borrower
    mine = {d["id"]: d["text_sha256"] for d in json.loads((book / "out" / "manifest.json").read_text())["documents"]
            if d["borrower_id"] in KEPT}
    theirs = {d["id"]: d["text_sha256"] for d in json.loads((legacy_out / "manifest.json").read_text())["documents"]
              if d["borrower_id"] in KEPT}
    assert mine == theirs and len(mine) == 73


def test_oracle_keeps_the_kept_rows_signed_and_leaves_the_new_rows_for_the_owner(book):
    import csv

    rows = list(csv.DictReader((book / "oracle.csv").open(newline="")))
    kept = [r for r in rows if r["borrower_id"] in KEPT]
    new = [r for r in rows if r["borrower_id"] not in KEPT]
    assert kept and all(r["owner_signed_off"] == "yes" for r in kept)
    assert new and all(r["owner_signed_off"] == "no" for r in new)

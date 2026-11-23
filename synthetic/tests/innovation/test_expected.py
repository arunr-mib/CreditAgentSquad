"""The expected arithmetic: plan, covenant rows, outcomes against the certificate, and the startup signals."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

from synthetic.books.innovation import model
from synthetic.books.innovation.expected import (
    FIRST_TEST,
    build_plan,
    classify,
    compute_signals,
    covenant_rows,
    plan_ratio,
    q,
)  # fmt: skip

LAST = model.LAST
CURRENT = date(2026, 10, 31)


def rows_for(sim):
    plan = build_plan(sim.spec, sim.series)
    return plan, covenant_rows(sim.spec, sim.series, plan, "tv", "f")


def test_fifteen_tested_months_three_covenants_each_from_august_2025(sims):
    plan, rows = rows_for(sims["datamarrow"])
    assert len(rows) == 15 * 3 == 3 * (model.N - FIRST_TEST)
    assert rows[0]["period_end"] == date(2025, 8, 31) and rows[-1]["period_end"] == CURRENT
    assert [r["covenant_id"] for r in rows[:3]] == [
        "min_unrestricted_cash",
        "min_runway_months",
        "revenue_vs_plan",
    ]
    assert len(plan) == 18 and all(
        v % 1000 == 0 for v in plan.values()
    )  # May 2025 to October 2026, to the thousand


def test_clean_clients_beat_plan_by_about_five_percent(sims):
    for client_id in ("mosswell-robotics", "tarnavi-ai", "pellucid-sensors"):
        sim = sims[client_id]
        plan = build_plan(sim.spec, sim.series)
        assert all(
            D("1.04") < plan_ratio(sim.series, plan, i) < D("1.06") for i in range(FIRST_TEST, model.N)
        )


def test_meridew_falls_under_the_floor_in_september_and_october_only(sims):
    sim = sims["meridew-analytics"]
    plan = build_plan(sim.spec, sim.series)
    ratio = {i: plan_ratio(sim.series, plan, i) for i in (LAST - 3, LAST - 2, LAST - 1, LAST)}
    assert ratio[LAST - 3] > D("0.95") and ratio[LAST - 2] >= D("0.84")
    assert ratio[LAST - 1] <= D("0.77") and ratio[LAST] <= D("0.77")


def test_a_cash_flow_positive_runway_is_not_meaningful_and_never_divides(sims):
    sim = sims["ferrogate-cloud"]
    plan, rows = rows_for(sim)
    row = next(r for r in rows if r["covenant_id"] == "min_runway_months" and r["period_end"] == CURRENT)
    assert (row["value"], row["pass"], row["headroom"], row["note"]) == (
        None,
        True,
        None,
        "not_meaningful_cash_flow_positive",
    )
    assert (row["reported_value"], row["reported_in_compliance"], row["outcome"]) == (None, True, "compliant")


def test_outcome_table():
    unit = "usd"
    assert classify(False, D(1), True, D(2), True, unit) == "breach_reported_compliant"
    assert classify(False, D(1), True, D(1), False, unit) == "breach"
    assert classify(False, D(1), False, None, None, unit) == "breach"
    assert classify(True, D(5000), True, D(5000), True, unit) == "compliant"
    assert classify(True, D(5000), True, D(9000), True, unit) == "compliant_variance"
    assert classify(True, D(5000), False, None, None, unit) == "compliant"
    assert (
        classify(True, None, True, None, False, "months") == "compliant_variance"
    )  # n/m, certificate says no


def test_datamarrows_certificate_counts_pledged_cash_and_the_covenant_breaches(sims):
    _, rows = rows_for(sims["datamarrow"])
    cash = next(r for r in rows if r["covenant_id"] == "min_unrestricted_cash" and r["period_end"] == CURRENT)
    assert (cash["value"], cash["reported_value"], cash["outcome"]) == (
        D(4_600_000),
        D(6_100_000),
        "breach_reported_compliant",
    )
    runway = next(r for r in rows if r["covenant_id"] == "min_runway_months" and r["period_end"] == CURRENT)
    assert (runway["value"], runway["reported_value"], runway["outcome"]) == (
        D("7.1"),
        D("9.4"),
        "compliant_variance",
    )
    assert all(r["outcome"] == "compliant" for r in rows if r["period_end"] != CURRENT)


def test_signals_follow_spec_7(sims):
    def current(client_id):
        sim = sims[client_id]
        plan, rows = rows_for(sim)
        return {(s["rule"], s["severity"]) for s in compute_signals(sim.series, plan, rows, LAST, [])}

    assert ("runway_below_watch", "high") in current("datamarrow")  # 7.1 months is under 9
    assert ("runway_below_watch", "medium") in current("calvere-health")  # 9.5 is under 12 and not under 9
    assert ("runway_falling", "medium") in current("brightvane-energy")
    assert not any(
        rule.startswith("runway") or rule == "burn_rising" for rule, _ in current("mosswell-robotics")
    )
    assert ("revenue_below_plan", "medium") in current("meridew-analytics")
    assert q(sims["nimbusfield-security"].series.rml(LAST), 2) < 9


def test_reporting_lateness_over_fifteen_days_is_a_high_signal(sims):
    sim = sims["calvere-health"]
    plan, rows = rows_for(sim)
    quiet = compute_signals(sim.series, plan, rows, LAST, [("bank_statements", 12)])
    loud = compute_signals(sim.series, plan, rows, LAST, [("bank_statements", 16)])
    assert not [s for s in quiet if s["rule"] == "reporting_late"]
    assert [s["severity"] for s in loud if s["rule"] == "reporting_late"] == ["high"]


def test_ferrogate_dscr_is_comfortably_above_its_covenant_from_may_2026(sims):
    """Ferrogate's DSCR covenant (TTM, minimum 1.25x) takes effect 2026-05-31; its truth must clear it comfortably."""
    series = sims["ferrogate-cloud"].series
    first = model.MONTHS.index(date(2026, 5, 31))
    values = [series.dscr(i) for i in range(first, LAST + 1)]
    assert len(values) == 6 and all(v is not None and v > D("2.0") for v in values)


def test_dscr_is_ebitda_over_interest_plus_scheduled_principal_and_never_divides_by_zero(sims):
    series = sims["ferrogate-cloud"].series
    i = LAST
    window = range(i - 11, i + 1)
    ebitda = sum(
        series.months[j].flows["is.vc_operating_loss"]
        + series.months[j].flows["is.vc_depreciation_amortization"]
        for j in window
    )
    service = sum(
        series.months[j].flows["is.vc_interest"] + series.months[j].flows["sup.scheduled_principal"]
        for j in window
    )
    assert series.dscr(i) == D(ebitda) / D(service)
    assert series.dscr(5) is None  # fewer than twelve months of history

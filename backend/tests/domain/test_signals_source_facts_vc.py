"""A venture signal's basis links every figure it shows to a stored fact; the grader flags any that is not."""
from datetime import date
from decimal import Decimal

import pytest
from app.domain.facts import Fact
from app.domain.monitoring import Signal
from app.guardrails.numbers import same_number
from sqlalchemy import select

VENTURE_RULES = ("runway_below_watch", "runway_falling", "burn_rising", "revenue_below_plan",
                 "covenant_headroom_falling", "covenant_headroom_low")


def _points(basis):
    """Every figure in a basis: a dict carrying a value and a fact_id slot."""
    found = []
    if isinstance(basis, dict):
        if "value" in basis and "fact_id" in basis:
            found.append(basis)
        for v in basis.values():
            found.extend(_points(v))
    elif isinstance(basis, list):
        for v in basis:
            found.extend(_points(v))
    return found


@pytest.mark.parametrize("code", ["brightvane-energy", "nimbusfield-security", "meridew-analytics", "datamarrow"])
def test_every_venture_signal_basis_links_each_figure_to_a_stored_fact(innovation_cycle, code):
    db, borrower, cycle = innovation_cycle(code, through="signals")
    signals = db.execute(select(Signal).where(Signal.borrower_id == borrower.id)).scalars().all()
    checked = 0
    for s in signals:
        if s.rule_id not in VENTURE_RULES:
            continue
        basis = s.basis or {}
        points = _points(basis)
        assert points, f"{code} {s.rule_id}: no figures in the basis"
        for p in points:
            assert p["fact_id"], f"{code} {s.rule_id}: figure {p['value']} has no source fact"
            fact = db.get(Fact, p["fact_id"])
            assert fact is not None and fact.borrower_id == borrower.id
            assert same_number(fact.value, Decimal(str(p["value"]))), f"{code} {s.rule_id}: fact disagrees with figure"
        if not s.rule_id.startswith("covenant_"):
            assert basis.get("metric_fact_ids"), f"{code} {s.rule_id}: no metric_fact_ids"
        checked += 1
    print(code, "venture signals checked:", checked)


def _fired(db, borrower, rule_id):
    rows = db.execute(select(Signal).where(Signal.borrower_id == borrower.id, Signal.rule_id == rule_id)
                      .order_by(Signal.period_end.desc())).scalars().all()
    assert rows, f"no {rule_id} signal"
    return rows[0]


def test_burn_rising_links_both_months_whatever_the_size_of_the_burn(innovation_cycle):
    from app.calc import signals as sig
    from app.domain.signals_service import _venture_source_facts

    db, borrower, _ = innovation_cycle("brightvane-energy", through="signals")
    row = _fired(db, borrower, "burn_rising")
    raw = {k: ({**v, "fact_id": None, "period_end": date.fromisoformat(v["period_end"])}
               if isinstance(v, dict) and "value" in v else v) for k, v in row.basis.items()}
    fired = sig.Signal("burn_rising", row.severity, row.period_end, None, raw)
    out = _venture_source_facts(db, borrower, row.period_end, fired)
    for name in ("current", "prior"):
        assert out[name]["fact_id"], name
        fact = db.get(Fact, out[name]["fact_id"])
        assert same_number(fact.value, Decimal(str(raw[name]["value"])))
    assert set(out["metric_fact_ids"]) == {"current", "prior"}


def test_a_small_burn_is_linked_too():
    """Whole-dollar storage broke the link below about $333,000 a month; two places keep it."""
    from app.domain.metrics_service import _PRECISE

    assert _PRECISE["avg_net_burn"] == 2
    burn = Decimal("120345.6666666667")  # a small borrower's unrounded monthly burn
    assert same_number(burn.quantize(Decimal("0.01")), burn)
    assert not same_number(burn.quantize(Decimal("1")), burn)


def test_revenue_below_plan_links_its_ratio_to_a_fact_that_records_the_plan(innovation_cycle):
    from app.domain.facts import CalcRun

    db, borrower, _ = innovation_cycle("meridew-analytics", through="signals")
    row = _fired(db, borrower, "revenue_below_plan")
    point = row.basis["current"]
    fact = db.get(Fact, point["fact_id"])
    assert fact.key == "metric.plan_ratio" and same_number(fact.value, Decimal(str(point["value"])))
    calc = db.get(CalcRun, fact.calc_run_id)
    assert calc.terms_version_id is not None
    assert len(calc.outputs["plan_months"]) == 3
    assert Decimal(calc.outputs["plan_total"]) == sum(Decimal(v) for v in calc.outputs["plan_months"].values())
    assert any(i.get("terms_version_id") == str(calc.terms_version_id) for i in calc.inputs)


def test_an_amended_plan_recomputes_the_ratio_and_the_same_terms_reuse_it(innovation_cycle):
    from app.domain.facts import CalcRun
    from app.domain.metrics_service import store_plan_ratio
    from app.domain.signals_service import approved_plan_with_terms
    from app.domain.terms import TermsVersion

    db, borrower, _ = innovation_cycle("meridew-analytics", through="signals")
    row = _fired(db, borrower, "revenue_below_plan")
    end = row.period_end
    plan, version_id = approved_plan_with_terms(db, borrower, end)
    from app.domain.signals_service import monthly_ends
    three = {m: plan[m] for m in monthly_ends(end, 3)}
    first = store_plan_ratio(db, borrower, end, three, version_id)
    assert store_plan_ratio(db, borrower, end, three, version_id).id == first.id  # same terms: reused
    old = db.get(TermsVersion, version_id)
    amended = TermsVersion(facility_id=old.facility_id, version=old.version + 50, status="superseded",
                           effective_from=old.effective_from, approved_by=old.approved_by,
                           approved_at=old.approved_at, terms=old.terms)
    db.add(amended)
    db.flush()
    bigger = {m: amount * 2 for m, amount in three.items()}
    second = store_plan_ratio(db, borrower, end, bigger, amended.id)
    assert second.id != first.id and second.value != first.value
    assert db.get(CalcRun, second.calc_run_id).terms_version_id == amended.id
    assert store_plan_ratio(db, borrower, end, bigger, amended.id).id == second.id

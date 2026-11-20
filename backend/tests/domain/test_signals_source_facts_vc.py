"""A venture signal's basis links every figure it shows to a stored fact; the grader flags any that is not."""
import pytest
from app.domain.facts import Fact
from app.domain.monitoring import Signal
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


@pytest.mark.parametrize("code", ["brightvane-energy", "nimbusfield-security", "corvane-analytics", "dataflake"])
def test_every_venture_signal_basis_links_each_figure_to_a_stored_fact(innovation_cycle, code):
    db, borrower, cycle = innovation_cycle(code, through="signals")
    signals = db.execute(select(Signal).where(Signal.cycle_id == cycle.id)).scalars().all()
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
        if not s.rule_id.startswith("covenant_"):
            assert basis.get("metric_fact_ids"), f"{code} {s.rule_id}: no metric_fact_ids"
        checked += 1
    print(code, "venture signals checked:", checked)

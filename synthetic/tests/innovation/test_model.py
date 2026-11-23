"""The monthly truth model and its expected arithmetic: the owner's October figures exactly, and every statement balances and ties."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.expected import Series, q
from synthetic.books.innovation.roster import BY_ID

# spec 2.1, as the owner wrote it: unrestricted cash, average monthly net burn over the last three months, RML
OWNER = {
    "datamarrow": (4_600_000, 650_000, "7.1"), "calvere-health": (4_000_000, 420_000, "9.5"),
    "brightvane-energy": (5_500_000, 450_000, "12.2"), "mosswell-robotics": (7_800_000, 600_000, "13.0"),
    "tavernel-grid": (2_600_000, 200_000, "13.0"), "tarnavi-ai": (12_000_000, 800_000, "15.0"),
    "kelvra-bio": (9_200_000, 500_000, "18.4"), "orbitline-systems": (3_900_000, 210_000, "18.6"),
    "cindrel-tech": (6_600_000, 300_000, "22.0"), "veridia-payments": (14_000_000, 550_000, "25.5"),
    "vantrell-labs": (11_000_000, 400_000, "27.5"), "pellucid-sensors": (6_300_000, 220_000, "28.6"),
}  # fmt: skip


@pytest.mark.parametrize("client_id", sorted(OWNER))
def test_the_owners_october_figures_exactly(sims, client_id):
    cash, burn, rml = OWNER[client_id]
    series = sims[client_id].series
    assert series.cash(model.LAST) == cash
    assert series.avg_burn(model.LAST) == burn  # the mean of August, September and October, to the dollar
    assert q(series.rml(model.LAST), 1) == D(rml)


def test_every_statement_balances_foots_and_ties(sims):
    for book in sims.values():
        assert model.check_periods(book.opening, book.periods) == [], book.spec.id


def test_eighteen_months_are_published_from_may_2025(sims):
    book = sims["datamarrow"]
    published = book.periods[model.PUBLISHED_FROM :]
    assert published[0].period_end == date(2025, 5, 31) and published[-1].period_end == date(2026, 10, 31)
    assert len(published) == 18 and len(book.periods) == 22


def test_the_vc1_lines_are_the_template_lines(sims):
    assert "saas.mrr" in model.ALL_KEYS and "cf.capitalised_software_spend" in model.ALL_KEYS
    assert len(model.ALL_KEYS) == len(set(model.ALL_KEYS))
    p = sims["tarnavi-ai"].periods[-1]
    assert set(p.values) == set(model.ALL_KEYS)
    assert p.values["saas.arr"] == 12 * p.values["saas.mrr"]


def test_financing_inflows_are_not_burn(sims):
    """Kelvra raised 10 million in January 2026 and Veridia drew 5 million of venture debt in April: cash jumps
    that month, net burn does not move."""
    kelvra, veridia = sims["kelvra-bio"], sims["veridia-payments"]
    jan = model.MONTHS.index(date(2026, 1, 31))
    assert kelvra.months[jan].flows["cf.equity_raised"] == 10_000_000
    change = kelvra.months[jan].flows["cf.vc_net_change_in_cash"]
    assert change > 9_000_000
    assert abs(kelvra.series.avg_burn(jan) - 500_000) < 150_000
    apr = model.MONTHS.index(date(2026, 4, 30))
    assert veridia.months[apr].flows["cf.debt_raised"] == 5_000_000
    assert (
        veridia.months[apr].balances["bs.venture_debt_current"]
        + veridia.months[apr].balances["bs.venture_debt_noncurrent"]
        == 8_000_000
    )


def test_net_burn_is_capex_plus_capitalised_software_less_operating_cash_flow(sims):
    month = sims["cindrel-tech"].months[model.LAST]
    f = month.flows
    burn = f["cf.vc_capex"] + f["cf.capitalised_software_spend"] - f["cf.vc_operating_cash_flow"]
    assert f["cf.vc_net_change_in_cash"] == -burn  # no financing that month


def test_trailing_three_months_across_a_fiscal_year_end(sims):
    """Review focus: January's trailing three months use November and December of the prior year, not zeros."""
    book = sims["mosswell-robotics"]
    jan = model.MONTHS.index(date(2026, 1, 31))
    key = "cf.vc_operating_cash_flow"
    direct = book.series.flow3(key, jan)
    nov, dec = book.months[jan - 2].flows[key], book.months[jan - 1].flows[key]
    assert direct == nov + dec + book.months[jan].flows[key] and nov != 0 and dec != 0
    # the identity the engine relies on: YTD(Jan) + FY2025 - YTD(October 2025)
    ytd = {p.period_end: p.values[key] for p in book.periods}
    assert ytd[date(2026, 1, 31)] + ytd[date(2025, 12, 31)] - ytd[date(2025, 10, 31)] == direct


def test_ferrogate_generates_cash_and_runway_is_not_meaningful(sims):
    series = sims["ferrogate-cloud"].series
    assert series.avg_burn(model.LAST) == -250_000 and series.rml(model.LAST) is None


def test_only_brightvane_trips_runway_falling(sims):
    def falling(series: Series) -> bool:
        points = [series.rml(i) for i in range(model.LAST - 3, model.LAST + 1)]
        return None not in points and all(a - b > 1 for a, b in zip(points, points[1:], strict=False))

    for client_id in (
        "mosswell-robotics",
        "tarnavi-ai",
        "orbitline-systems",
        "veridia-payments",
        "vantrell-labs",
        "pellucid-sensors",
        "tavernel-grid",
        "kelvra-bio",
        "cindrel-tech",
        "meridew-analytics",
    ):
        assert not falling(sims[client_id].series), client_id
    for client_id in ("datamarrow", "calvere-health", "nimbusfield-security", "brackmere-medical", "ferrogate-cloud"):
        assert not falling(sims[client_id].series), client_id
    assert falling(sims["brightvane-energy"].series)


def test_same_seed_same_truth_and_a_new_seed_keeps_the_owners_figures():
    spec = BY_ID["datamarrow"]
    a, b = model.simulate(spec, 1), model.simulate(spec, 1)
    assert [m.flows for m in a[1]] == [m.flows for m in b[1]]
    other = model.simulate(spec, 2)
    assert [m.flows for m in other[1]] != [m.flows for m in a[1]]
    assert (
        Series(other[1]).cash(model.LAST) == spec.cash
        and Series(other[1]).net_burn3(model.LAST) == 3 * spec.burn
    )

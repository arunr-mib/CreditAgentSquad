"""The financial model: every period of every borrower balances, ties and accumulates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from synthetic import expected, model
from synthetic.book import TEST_PERIODS
from synthetic.scenarios import ROSTER

D = Decimal


def test_roster_shape():
    assert 19 <= len(ROSTER) <= 22
    assert len({s.id for s in ROSTER}) == len(ROSTER) == len({s.name for s in ROSTER})
    assert sum(s.borrowing_base for s in ROSTER) == 8
    assert sum(s.scenario == "clean" for s in ROSTER) >= 8
    scenarios = {s.scenario for s in ROSTER}
    assert len(scenarios) == 14  # thirteen exception scenarios plus clean
    for spec in ROSTER:
        assert 1 <= spec.risk_rating <= 9
        assert 2 <= len(spec.covenants) <= 4
        assert spec.revolver or spec.term_loan
        assert 15 <= D(spec.revenue_2023) <= 250
        assert spec.relationship_manager != spec.analyst


def test_every_period_balances_and_ties(books):
    for book in books:
        assert model.check_periods(book.all_periods) == [], book.spec.id
        assert len(book.periods) == 11
        by_end = {p.period_end: p for p in book.all_periods}
        for p in book.periods:
            v = p.values
            assert all(isinstance(x, Decimal) for x in v.values())
            assert v["bs.total_assets"] == v["bs.total_liabilities_and_equity"]
            assert v["cf.net_income"] == v["is.net_income"]
            assert v["cf.depreciation_amortization"] == v["is.depreciation_amortization"]
            prior_year_end = by_end[date(p.fiscal_year - 1, 12, 31)].values
            assert v["cf.net_change_in_cash"] == v["bs.cash"] - prior_year_end["bs.cash"]
            assert all(x % p.scale == 0 for x in v.values())
            assert p.months == p.quarter * 3
            assert set(v) == set(model.LINES)


def test_computed_lines_follow_the_template_formulas(books):
    for book in books:
        for p in book.periods:
            v = p.values
            assert v["is.gross_profit"] == v["is.revenue"] - v["is.cogs"]
            assert v["is.operating_income"] == (
                v["is.gross_profit"] - v["is.sga"] - v["is.depreciation_amortization"]
                - v["is.other_operating_expense"] - v["is.nonrecurring_expense"]
            )  # fmt: skip
            assert v["is.pretax_income"] == v["is.operating_income"] - v["is.interest_expense"] + v["is.other_income_net"]
            assert v["is.net_income"] == v["is.pretax_income"] - v["is.income_tax_expense"]
            assert v["cf.cfi"] == -v["cf.capex"] + v["cf.other_investing"]
            assert v["cf.cff"] == (
                v["cf.revolver_net"] + v["cf.term_debt_proceeds"] - v["cf.term_debt_repayments"]
                - v["cf.distributions"] + v["cf.other_financing"]
            )  # fmt: skip
            assert v["cf.net_change_in_cash"] == v["cf.cfo"] + v["cf.cfi"] + v["cf.cff"]


def test_year_to_date_accumulates_discrete_quarters(books):
    for book in books:
        quarters = {(q.year, q.quarter): q for q in book.quarters}
        for p in book.periods:
            for key in model.FLOW_KEYS:
                if model.LINES[key].computed:
                    continue
                total = sum((quarters[(p.fiscal_year, n)].flows[key] for n in range(1, p.quarter + 1)), D(0))
                assert p.values[key] == total, (book.spec.id, p.period_end, key)


def test_trailing_twelve_months_identity(books):
    """YTD(current) + FY(prior) - YTD(same period, prior year) equals the last four discrete quarters."""
    for book in books:
        fin = expected.Financials(book.periods)
        ordered = sorted(book.quarters, key=lambda q: (q.year, q.quarter))
        for end in TEST_PERIODS:
            index = next(i for i, q in enumerate(ordered) if model.period_end(q.year, q.quarter) == end)
            last_four = ordered[index - 3 : index + 1]
            for key in ("is.revenue", "is.interest_expense", "cf.capex", "cf.distributions", "sup.scheduled_principal"):
                assert fin.ttm(key, end) == sum((q.flows[key] for q in last_four), D(0)), (book.spec.id, end, key)
            net_income = sum(
                (
                    q.flows["is.revenue"] - q.flows["is.cogs"] - q.flows["is.sga"]
                    - q.flows["is.depreciation_amortization"] - q.flows["is.other_operating_expense"]
                    - q.flows["is.nonrecurring_expense"] - q.flows["is.interest_expense"]
                    + q.flows["is.other_income_net"] - q.flows["is.income_tax_expense"]
                    for q in last_four
                ),
                D(0),
            )  # fmt: skip
            assert fin.ttm("is.net_income", end) == net_income
        december = date(2025, 12, 31)
        assert fin.ttm("is.revenue", december) == fin.ytd("is.revenue", december)


def test_retained_earnings_and_debt_roll_forward(books):
    for book in books:
        by_end = {p.period_end: p for p in book.all_periods}
        for p in book.periods:
            prior = by_end[date(p.fiscal_year - 1, 12, 31)]
            v, pv = p.values, prior.values
            rolled = prior.memo["equity.retained_earnings"] + v["is.net_income"] - v["cf.distributions"]
            assert p.memo["equity.retained_earnings"] == rolled
            assert v["bs.revolver"] == pv["bs.revolver"] + v["cf.revolver_net"]
            term, prior_term = v["bs.cpltd"] + v["bs.long_term_debt"], pv["bs.cpltd"] + pv["bs.long_term_debt"]
            assert term == prior_term + v["cf.term_debt_proceeds"] - v["cf.term_debt_repayments"]
            assert v["sup.scheduled_principal"] <= v["cf.term_debt_repayments"]
        if book.spec.term_loan:
            # The term loan pays the same contractual installment every quarter.
            for q in book.quarters:
                if q.flows["sup.financed_capex"] == 0 and q.year == 2024:
                    assert q.flows["sup.scheduled_principal"] >= book.term_payment


def test_missing_input_is_an_error_not_zero(books):
    fin = expected.Financials(books[0].periods)
    try:
        fin.ttm("is.revenue", date(2024, 3, 31))  # needs fiscal 2023, which is not a published period
    except expected.MissingInput:
        return
    raise AssertionError("a missing period must raise")

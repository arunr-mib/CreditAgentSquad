"""Worked example: one small borrower, two years of quarterly statements, three covenants.

Every expected figure below is computed by hand in the comments, not by the engine.

Meridian Fastener Co. (invented), calendar fiscal year, whole dollars. Statements are fiscal
year to date, as an interim package presents them.

Income statement and supplemental lines, year to date:

                      2024 Q1    2024 H1    2024 9M    FY 2024    2025 Q1    2025 H1    2025 9M    FY 2025
revenue             1,000,000  2,000,000  3,000,000  4,000,000  1,000,000  1,900,000  2,900,000  3,900,000
cogs                  600,000  1,200,000  1,800,000  2,400,000    600,000  1,160,000  1,760,000  2,360,000
sga                   200,000    400,000    600,000    800,000    200,000    400,000    600,000    800,000
dep. and amort.        40,000     80,000    120,000    160,000     40,000     80,000    120,000    160,000
other opex             10,000     20,000     30,000     40,000     10,000     20,000     30,000     40,000
non-recurring               0          0          0          0     80,000    200,000    200,000    200,000
interest expense       30,000     60,000     90,000    120,000     30,000     60,000     90,000    120,000
other income                0          0          0          0          0          0          0          0
income tax             30,000     60,000     90,000    120,000     10,000     10,000     40,000     70,000
=> net income          90,000    180,000    270,000    360,000     30,000    -30,000     60,000    150,000
capex                  50,000    100,000    150,000    200,000     50,000    100,000    150,000    200,000
financed capex              0          0          0     40,000          0     20,000     20,000     20,000
cash taxes paid        25,000     50,000     75,000    100,000     20,000     25,000     45,000     65,000
cash interest paid     28,000     56,000     84,000    112,000     30,000     60,000     90,000    120,000
scheduled principal    25,000     50,000     75,000    100,000     25,000     50,000     75,000    100,000

Net income check, 2025 H1: 1,900,000 - 1,160,000 = 740,000 gross profit; less 400,000, 80,000,
20,000 and 200,000 = 40,000 operating income; less 60,000 interest = -20,000; less 10,000 tax = -30,000.
"""

from datetime import date
from decimal import Decimal as D

from app.calc import covenants as cov
from app.calc import errors as E
from app.calc.covenants import determine_outcome
from app.calc.decimal_utils import round_half_up
from app.calc.periods import FactValue, provider_from_facts
from app.calc.signals import PeriodMetrics, compute_signal_inputs, evaluate_signals
from app.calc.template import check_statement, compute_statement
from app.calc.terms import TermsVersion, compare_terms, terms_in_force

PERIODS = [(date(2024, 3, 31), 3), (date(2024, 6, 30), 6), (date(2024, 9, 30), 9), (date(2024, 12, 31), 12),
           (date(2025, 3, 31), 3), (date(2025, 6, 30), 6), (date(2025, 9, 30), 9), (date(2025, 12, 31), 12)]
FYE24, H1_25, FYE25 = date(2024, 12, 31), date(2025, 6, 30), date(2025, 12, 31)

FLOWS = {
    "is.revenue": "1000000 2000000 3000000 4000000 1000000 1900000 2900000 3900000",
    "is.cogs": "600000 1200000 1800000 2400000 600000 1160000 1760000 2360000",
    "is.sga": "200000 400000 600000 800000 200000 400000 600000 800000",
    "is.depreciation_amortization": "40000 80000 120000 160000 40000 80000 120000 160000",
    "is.other_operating_expense": "10000 20000 30000 40000 10000 20000 30000 40000",
    "is.nonrecurring_expense": "0 0 0 0 80000 200000 200000 200000",
    "is.interest_expense": "30000 60000 90000 120000 30000 60000 90000 120000",
    "is.other_income_net": "0 0 0 0 0 0 0 0",
    "is.income_tax_expense": "30000 60000 90000 120000 10000 10000 40000 70000",
    "cf.capex": "50000 100000 150000 200000 50000 100000 150000 200000",
    "sup.financed_capex": "0 0 0 40000 0 20000 20000 20000",
    "sup.cash_taxes_paid": "25000 50000 75000 100000 20000 25000 45000 65000",
    "sup.cash_interest_paid": "28000 56000 84000 112000 30000 60000 90000 120000",
    "sup.scheduled_principal": "25000 50000 75000 100000 25000 50000 75000 100000",
}
NET_INCOME = "90000 180000 270000 360000 30000 -30000 60000 150000"  # by hand, see the module docstring

BALANCE_SHEETS = {
    #                               FY 2024    2025 H1    FY 2025
    "bs.cash":                     "300000     200000     150000",
    "bs.accounts_receivable":      "650000     700000     650000",
    "bs.inventory":                "450000     500000     520000",
    "bs.other_current_assets":     "100000     100000      80000",
    "bs.net_ppe":                 "1150000    1200000    1250000",
    "bs.intangibles":              "300000     300000     300000",
    "bs.other_noncurrent_assets":       "0          0          0",
    "bs.accounts_payable":         "280000     300000     320000",
    "bs.accrued_liabilities":      "100000     100000     100000",
    "bs.revolver":                 "400000     600000     650000",
    "bs.cpltd":                    "100000     100000     100000",
    "bs.other_current_liabilities":     "0          0          0",
    "bs.long_term_debt":          "1000000     900000     850000",
    "bs.subordinated_debt":        "200000     200000     200000",
    "bs.other_noncurrent_liabilities":  "0          0          0",
    "bs.total_equity":             "870000     800000     730000",
}
BS_DATES = [(FYE24, 12), (H1_25, 6), (FYE25, 12)]
# By hand:         total current assets, total assets, total current liabilities, total liabilities
BS_TOTALS = {
    FYE24: ("1500000", "2950000", "880000", "2080000"),   # 2,080,000 + 870,000 = 2,950,000
    H1_25: ("1500000", "3000000", "1100000", "2200000"),  # 2,200,000 + 800,000 = 3,000,000
    FYE25: ("1400000", "2950000", "1170000", "2220000"),  # 2,220,000 + 730,000 = 2,950,000
}


def build_facts():
    """Spread each period through the template and store inputs and computed lines as facts."""
    facts = {}
    for index, (period_end, months) in enumerate(PERIODS):
        inputs = {key: D(row.split()[index]) for key, row in FLOWS.items()}
        income = compute_statement({k: v for k, v in inputs.items() if k.startswith("is.")}, statements=["is"])
        assert income.errors == []
        assert income.computed["is.net_income"] == D(NET_INCOME.split()[index])
        for key, value in {**inputs, **income.computed}.items():
            facts[(key, period_end, months)] = FactValue(value, f"{key}@{period_end.isoformat()}/{months}")
    for index, (period_end, months) in enumerate(BS_DATES):
        inputs = {key: D(row.split()[index]) for key, row in BALANCE_SHEETS.items()}
        tca, ta, tcl, tl = (D(x) for x in BS_TOTALS[period_end])
        stated = {"stated.bs.total_current_assets": tca, "stated.bs.total_assets": ta,
                  "stated.bs.total_current_liabilities": tcl, "stated.bs.total_liabilities": tl,
                  "stated.bs.total_liabilities_and_equity": ta}
        sheet = check_statement({**inputs, **stated}, scale=1, prior_fye_cash=None, statements=["bs"])
        assert sheet.errors == [], sheet.errors
        assert [c.status for c in sheet.checks] == ["pass"] * 6  # five footings and the balance check
        for key, value in sheet.values.items():
            facts[(key, period_end, months)] = FactValue(value, f"{key}@{period_end.isoformat()}/{months}")
    return facts


PROVIDER = provider_from_facts(build_facts())


def terms(fccr_threshold, leverage_steps, cap):
    return {
        "definitions": {"ebitda": {"base": "ebitda", "addbacks": [
            {"name": "restructuring", "source_key": "is.nonrecurring_expense", "cap": cap}]}},
        "covenants": [
            {"id": "fccr", "name": "Fixed Charge Coverage Ratio", "archetype": "coverage",
             "params": {"numerator_base": "adjusted_ebitda", "deductions": ["unfinanced_capex", "cash_taxes"],
                        "denominator": ["cash_interest", "scheduled_principal"]},
             "test": {"operator": ">=", "threshold": fccr_threshold, "steps": [], "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": []},
            {"id": "leverage", "name": "Total Leverage Ratio", "archetype": "leverage",
             "params": {"debt": "total_debt", "ebitda": "adjusted_ebitda"},
             "test": {"operator": "<=", "threshold": "3.50", "steps": leverage_steps, "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": []},
            {"id": "current_ratio", "name": "Current Ratio", "archetype": "current_ratio", "params": {},
             "test": {"operator": ">=", "threshold": "1.25", "steps": [], "unit": "ratio"},
             "measurement": {"basis": "point", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": []},
        ],
        "reporting_requirements": [],
        "borrowing_base": None,
    }


CAP_10_PCT = {"type": "pct_of", "value": "0.10", "of": "ebitda"}
STEP_DOWN = [{"from": "2025-12-31", "value": "3.00"}]
VERSIONS = [
    # Original agreement.
    {"version": 1, "status": "superseded", "effective_from": "2023-01-01", "effective_to": "2025-06-30",
     "prepared_by": "analyst-1", "approved_by": "officer-1", "terms": terms("1.50", [], CAP_10_PCT)},
    # First amendment, approved: coverage minimum raised, leverage maximum steps down at year end.
    {"version": 2, "status": "approved", "effective_from": "2025-07-01", "effective_to": None,
     "prepared_by": "analyst-1", "approved_by": "officer-1", "terms": terms("1.75", STEP_DOWN, CAP_10_PCT)},
    # Second amendment, on file but not approved: it would remove the add-back cap.
    {"version": 3, "status": "proposed", "effective_from": "2025-10-01", "effective_to": None,
     "prepared_by": "analyst-1", "terms": terms("1.75", STEP_DOWN, None)},
]
TOLERANCE = D("0.01")


def run_tests_at(period_end, certificate):
    governing = terms_in_force(VERSIONS, period_end)
    assert governing.error is None
    out = {}
    for covenant in governing.version.terms.covenants:
        result = cov.test_covenant(covenant, period_end, PROVIDER, governing.version.terms.definitions)
        out[covenant.id] = (result, determine_outcome(result, certificate.get(covenant.id), TOLERANCE))
    return governing.version, out



def summary(result):
    return (str(result.value), str(result.threshold), result.passed, str(result.headroom), str(result.headroom_pct))


def test_fiscal_year_end_2024_under_the_original_terms():
    version, out = run_tests_at(FYE24, {})
    assert version.version == 1
    # EBITDA = 360,000 + 120,000 + 120,000 + 160,000 = 760,000; no non-recurring charges, so nothing is added back.
    # FCCR = (760,000 - (200,000 - 40,000) - 100,000) / (112,000 + 100,000) = 500,000 / 212,000 = 2.35849
    assert summary(out["fccr"][0]) == ("2.36", "1.50", True, "0.86", "0.5733")  # 0.86 / 1.50
    ab = out["fccr"][0].trace.addbacks[0]
    assert (ab.raw, ab.cap_limit, ab.applied, ab.capped) == (D("0"), D("76000"), D("0"), False)
    # Leverage = (400,000 + 100,000 + 1,000,000 + 200,000) / 760,000 = 1,700,000 / 760,000 = 2.23684
    assert summary(out["leverage"][0]) == ("2.24", "3.50", True, "1.26", "0.3600")  # 1.26 / 3.50
    # Current ratio = 1,500,000 / 880,000 = 1.70455
    assert summary(out["current_ratio"][0]) == ("1.70", "1.25", True, "0.45", "0.3600")  # 0.45 / 1.25
    assert [o.outcome for _, o in out.values()] == ["compliant"] * 3


def test_interim_june_2025_uses_trailing_twelve_months_and_the_capped_addback():
    certificate = {
        "fccr": {"value": "2.25", "threshold": "1.50", "in_compliance": True},  # borrower ignored the cap
        "leverage": {"value": "3.27", "threshold": "3.50", "in_compliance": True},
        "current_ratio": {"value": "1.36", "threshold": "1.25", "in_compliance": True},
    }
    version, out = run_tests_at(H1_25, certificate)
    assert version.version == 1  # last day of the original terms

    fccr, fccr_outcome = out["fccr"]
    # TTM = YTD June 2025 + FY 2024 - YTD June 2024:
    #   net income  -30,000 + 360,000 - 180,000 = 150,000     interest  60,000 + 120,000 - 60,000 = 120,000
    #   tax          10,000 + 120,000 -  60,000 =  70,000     D&A       80,000 + 160,000 - 80,000 = 160,000
    #   EBITDA = 500,000
    #   non-recurring 200,000 + 0 - 0 = 200,000; cap 10% x 500,000 = 50,000; adjusted EBITDA = 550,000
    #   capex 100,000 + 200,000 - 100,000 = 200,000; financed 20,000 + 40,000 - 0 = 60,000; unfinanced 140,000
    #   cash taxes 25,000 + 100,000 - 50,000 = 75,000
    #   cash interest 60,000 + 112,000 - 56,000 = 116,000; principal 50,000 + 100,000 - 50,000 = 100,000
    #   FCCR = (550,000 - 140,000 - 75,000) / (116,000 + 100,000) = 335,000 / 216,000 = 1.55093
    assert summary(fccr) == ("1.55", "1.50", True, "0.05", "0.0333")  # 0.05 / 1.50
    assert abs(fccr.raw_value - D("335000") / D("216000")) < D("1e-20")
    (ab,) = fccr.trace.addbacks
    assert (ab.name, ab.raw, ab.cap_type, ab.cap_value, ab.cap_limit, ab.applied, ab.capped) == (
        "restructuring", D("200000"), "pct_of", D("0.10"), D("50000"), D("50000"), True)
    # Uncapped it would be (700,000 - 215,000) / 216,000 = 2.24537, which is what the certificate reports.
    assert fccr_outcome.outcome == "compliant_variance"
    assert [(v.field, str(v.computed), str(v.reported)) for v in fccr_outcome.variances] == [("value", "1.55", "2.25")]

    # The trace names all 30 facts: ten lines, each as YTD current, prior fiscal year and prior-year YTD.
    keys = []
    for item in fccr.trace.inputs:
        if item.key not in keys:
            keys.append(item.key)
    assert keys == [
        "is.net_income", "is.interest_expense", "is.income_tax_expense", "is.depreciation_amortization",
        "is.nonrecurring_expense", "cf.capex", "sup.financed_capex", "sup.cash_taxes_paid",
        "sup.cash_interest_paid", "sup.scheduled_principal",
    ]
    assert len(fccr.trace.inputs) == 30
    assert [(i.period_end, i.months, i.sign, str(i.value), i.fact_id) for i in fccr.trace.inputs[:3]] == [
        (H1_25, 6, 1, "-30000", "is.net_income@2025-06-30/6"),
        (FYE24, 12, 1, "360000", "is.net_income@2024-12-31/12"),
        (date(2024, 6, 30), 6, -1, "180000", "is.net_income@2024-06-30/6"),
    ]

    # Leverage = (600,000 + 100,000 + 900,000 + 200,000) / 550,000 = 1,800,000 / 550,000 = 3.27273
    assert summary(out["leverage"][0]) == ("3.27", "3.50", True, "0.23", "0.0657")  # 0.23 / 3.50
    assert out["leverage"][1].outcome == "compliant"
    # Current ratio = 1,500,000 / 1,100,000 = 1.36364
    assert summary(out["current_ratio"][0]) == ("1.36", "1.25", True, "0.11", "0.0880")  # 0.11 / 1.25
    assert out["current_ratio"][1].outcome == "compliant"


def test_fiscal_year_end_2025_under_the_amended_terms():
    certificate = {
        "fccr": {"value": "2.07", "threshold": "1.75", "in_compliance": True},
        "leverage": {"value": "3.27", "threshold": "3.00", "in_compliance": False},
    }
    version, out = run_tests_at(FYE25, certificate)
    assert version.version == 2  # the proposed version 3 also covers the date and does not govern

    # EBITDA = 150,000 + 120,000 + 70,000 + 160,000 = 500,000; add-back 200,000 capped at 50,000 -> 550,000
    # FCCR = (550,000 - (200,000 - 20,000) - 65,000) / (120,000 + 100,000) = 305,000 / 220,000 = 1.38636
    assert summary(out["fccr"][0]) == ("1.39", "1.75", False, "-0.36", "-0.2057")  # -0.36 / 1.75
    assert out["fccr"][1].outcome == "breach_reported_compliant"
    # Leverage = 1,800,000 / 550,000 = 3.27273 against 3.00, which stepped down on this very date.
    assert summary(out["leverage"][0]) == ("3.27", "3.00", False, "-0.27", "-0.0900")
    assert out["leverage"][1].outcome == "breach"
    # Current ratio = 1,400,000 / 1,170,000 = 1.19658
    assert summary(out["current_ratio"][0]) == ("1.20", "1.25", False, "-0.05", "-0.0400")
    assert out["current_ratio"][1].outcome == "breach" and out["current_ratio"][1].certificate_compared is False


def test_the_unapproved_amendment_explains_the_certificate_but_is_terms_drift():
    approved = terms_in_force(VERSIONS, FYE25).version
    proposed = TermsVersion.model_validate(VERSIONS[2])
    used = cov.test_covenant(proposed.terms.covenant("fccr"), FYE25, PROVIDER, proposed.terms.definitions)
    # Uncapped: (700,000 - 180,000 - 65,000) / 220,000 = 455,000 / 220,000 = 2.06818
    assert str(used.value) == "2.07" and used.passed is True
    differences = compare_terms(proposed.terms, approved.terms)
    assert [(d.path, d.kind, d.used) for d in differences] == [
        ("definitions[ebitda].addbacks[restructuring].cap", "changed", None)]


def test_first_quarter_2024_cannot_be_tested_and_names_what_is_missing():
    _, out = run_tests_at(date(2024, 3, 31), {})
    fccr, outcome = out["fccr"]
    assert outcome.outcome == "cannot_test" and fccr.value is None and fccr.passed is None
    missing = {(e.key, e.period_end, e.months) for e in outcome.errors if e.code == E.MISSING_INPUT}
    assert ("is.net_income", date(2023, 12, 31), 12) in missing
    assert ("is.net_income", date(2023, 3, 31), 3) in missing
    assert {e.code for e in outcome.errors} == {E.MISSING_INPUT}
    ratio, outcome = out["current_ratio"]
    assert outcome.outcome == "cannot_test"
    assert [(e.key, e.period_end, e.months) for e in outcome.errors] == [
        ("bs.total_current_assets", date(2024, 3, 31), 3), ("bs.total_current_liabilities", date(2024, 3, 31), 3)]


def test_no_terms_in_force_before_the_agreement():
    governing = terms_in_force(VERSIONS, date(2022, 12, 31))
    assert governing.version is None
    outcome = determine_outcome(cov.untested("fccr", date(2022, 12, 31), [governing.error]), None, TOLERANCE)
    assert outcome.outcome == "cannot_test" and outcome.errors[0].code == E.NO_TERMS_IN_FORCE


def test_signals_from_the_june_2025_results():
    series = []
    for period_end, months in ((FYE24, 12), (H1_25, 6)):
        _, out = run_tests_at(period_end, {})
        inputs = compute_signal_inputs(period_end, PROVIDER)
        series.append(PeriodMetrics(period_end, months, inputs.values,
                                    {cid: result.headroom_pct for cid, (result, _) in out.items()}))
    # June 2025 by hand: revenue TTM 1,900,000 + 4,000,000 - 2,000,000 = 3,900,000; net income TTM 150,000;
    # EBITDA margin 500,000 / 3,900,000 = 0.1282; DSO 700,000 x 365 / 3,900,000 = 65.5;
    # DPO 300,000 x 365 / (1,160,000 + 2,400,000 - 1,200,000) = 109,500,000 / 2,360,000 = 46.4;
    # leverage (plain EBITDA) 1,800,000 / 500,000 = 3.60.
    places = {"revenue_ttm": 0, "net_income_ttm": 0, "cash": 0, "ebitda_margin": 4, "dso": 1, "dpo": 1, "leverage": 2}
    assert {k: str(round_half_up(v, places[k])) for k, v in series[1].metrics.items()} == {
        "revenue_ttm": "3900000", "net_income_ttm": "150000", "cash": "200000",
        "ebitda_margin": "0.1282", "dso": "65.5", "dpo": "46.4", "leverage": "3.60"}
    evaluation = evaluate_signals(H1_25, series)
    # Headroom of 3.33%, 6.57% and 8.80% is below 10% on all three covenants; nothing else can fire.
    assert [(s.rule_id, s.subject, str(s.basis["current"]["value"])) for s in evaluation.signals] == [
        ("covenant_headroom_low", "fccr", "0.0333"),
        ("covenant_headroom_low", "leverage", "0.0657"),
        ("covenant_headroom_low", "current_ratio", "0.0880"),
    ]
    assert all(s.severity == "medium" and s.period_end == H1_25 for s in evaluation.signals)

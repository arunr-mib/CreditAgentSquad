"""The borrower roster and the scenario assigned to each borrower.

Every borrower carries exactly one scenario code. Scenario effects on the
financial model are expressed as per-quarter adjustments (`QuarterAdj`);
effects on documents, certificates and terms are applied by the modules that
build those things, keyed on the scenario code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from synthetic.model import ModelParams, QuarterAdj

D = Decimal
LENDER = "Bank of Stoic"
TODAY = date(2026, 11, 17)
CURRENT_PERIOD = date(2026, 9, 30)
DEFAULT_SEED = 20261117

SCENARIOS: dict[str, str] = {
    "clean": "Clean performer: every covenant passes with room, documents are complete and on time.",
    "hidden_breach": (
        "Breach behind a compliant certificate: the leverage covenant fails for the current quarter, "
        "but the borrower's certificate adds pro forma cost savings that the agreement does not permit "
        "and claims compliance."
    ),
    "unapproved_amendment": (
        "Amendment on file but not approved into terms: a signed amendment raises the cap on the "
        "restructuring add-back. The test passes under the amendment and fails under the approved terms."
    ),
    "addback_over_cap": (
        "Add-back over its cap: the certificate adds back all restructuring charges although the "
        "agreement caps the add-back. Both calculations pass, so the difference is a logged variance."
    ),
    "deteriorating_trend": (
        "Deteriorating trend: revenue, margin, collections and leverage worsen over five quarters. "
        "Covenants still pass, but early-warning signals fire and the line is nearly fully drawn."
    ),
    "late_reporting": (
        "Late reporting: the package for the current quarter has not been received and is more than "
        "15 days past its due date."
    ),
    "miscounted_ineligible": (
        "Miscounted ineligible receivable: the borrowing base certificate counts one customer's "
        "invoices aged over 90 days as eligible."
    ),
    "over_advance": (
        "Over-advance: a large customer has cross-aged out of the borrowing base, and the line "
        "outstanding now exceeds the borrowing base."
    ),
    "scale_trap": (
        "Scale trap: the financial statements are presented in thousands while the compliance "
        "certificate is presented in whole dollars. The figures agree once scale is applied."
    ),
    "restated_comparative": (
        "Restated prior period: the comparative column of the current interim statements differs "
        "from the prior-year interim statements as originally delivered."
    ),
    "missing_page": (
        "Missing page: the liabilities and equity page of the current interim balance sheet was "
        "omitted from the delivered file, so the balance sheet cannot foot."
    ),
    "image_only": (
        "Image-only page: the income statement page of the current interim statements is a scanned "
        "image with no text layer."
    ),
    "step_up": (
        "Step-up threshold: the leverage covenant tightened on 2026-01-01. The current quarter passes "
        "the old threshold and fails the new one; the certificate tests against the old threshold."
    ),
    "reported_breach": (
        "True breach, correctly reported: the fixed charge coverage covenant fails for the current "
        "quarter and the borrower's certificate reports the breach."
    ),
}

PROFILES: dict[str, dict] = {
    "manufacturing": dict(
        gm="0.285", sga="0.165", opex="0.004", dso=47, dio=62, dpo=41, ppe="0.30", capex="0.034",
        intang="0.06", seas=("0.96", "1.02", "1.03", "0.99"), term="0.30", line="0.055",
    ),
    "distribution": dict(
        gm="0.215", sga="0.150", opex="0.003", dso=41, dio=52, dpo=37, ppe="0.07", capex="0.010",
        intang="0.04", seas=("0.94", "1.03", "1.05", "0.98"), term="0.10", line="0.075",
    ),
    "services": dict(
        gm="0.330", sga="0.225", opex="0.004", dso=56, dio=0, dpo=28, ppe="0.12", capex="0.022",
        intang="0.07", seas=("0.97", "1.01", "1.02", "1.00"), term="0.21", line="0.045",
    ),
    "healthcare services": dict(
        gm="0.385", sga="0.270", opex="0.005", dso=49, dio=5, dpo=30, ppe="0.16", capex="0.026",
        intang="0.12", seas=("1.00", "1.00", "0.98", "1.02"), term="0.25", line="0.040",
    ),
    "food processing": dict(
        gm="0.245", sga="0.135", opex="0.003", dso=33, dio=44, dpo=34, ppe="0.34", capex="0.034",
        intang="0.05", seas=("0.95", "0.99", "1.02", "1.04"), term="0.24", line="0.050",
    ),
    "logistics": dict(
        gm="0.235", sga="0.115", opex="0.004", dso=44, dio=2, dpo=29, ppe="0.42", capex="0.040",
        intang="0.07", seas=("0.96", "1.00", "1.01", "1.03"), term="0.23", line="0.045",
    ),
}


@dataclass(frozen=True)
class CovenantSpec:
    id: str
    name: str
    archetype: str
    params: dict
    operator: str
    unit: str
    mode: str = "pass"  # pass | fail_current | step | amendment_gap
    cushion: Decimal = D("0.25")


def fccr(base: str = "ebitda", distributions: bool = False, **kw) -> CovenantSpec:
    deductions = ["unfinanced_capex", "cash_taxes"] + (["distributions"] if distributions else [])
    params = {
        "numerator_base": base,
        "deductions": deductions,
        "denominator": ["cash_interest", "scheduled_principal"],
    }
    return CovenantSpec("fccr", "Fixed Charge Coverage Ratio", "coverage", params, ">=", "ratio", **kw)


def dscr(**kw) -> CovenantSpec:
    params = {
        "numerator_base": "ebitda",
        "deductions": ["cash_taxes"],
        "denominator": ["interest_expense", "scheduled_principal"],
    }
    return CovenantSpec("dscr", "Debt Service Coverage Ratio", "coverage", params, ">=", "ratio", **kw)


def interest_coverage(base: str = "ebitda", **kw) -> CovenantSpec:
    params = {"numerator_base": base, "deductions": [], "denominator": ["interest_expense"]}
    return CovenantSpec(
        "interest_coverage", "Interest Coverage Ratio", "coverage", params, ">=", "ratio", **kw
    )


def leverage(base: str = "ebitda", debt: str = "total_debt", **kw) -> CovenantSpec:
    cid, name = ("total_leverage", "Total Leverage Ratio")
    if debt == "senior_debt":
        cid, name = ("senior_leverage", "Senior Leverage Ratio")
    return CovenantSpec(cid, name, "leverage", {"debt": debt, "ebitda": base}, "<=", "ratio", **kw)


def current_ratio(**kw) -> CovenantSpec:
    return CovenantSpec("current_ratio", "Current Ratio", "current_ratio", {}, ">=", "ratio", **kw)


def min_tnw(**kw) -> CovenantSpec:
    params = {"step_up_pct_of_net_income": None}
    return CovenantSpec(
        "min_tnw", "Minimum Tangible Net Worth", "min_tangible_net_worth", params, ">=", "usd", **kw
    )


def min_liquidity(include_availability: bool, **kw) -> CovenantSpec:
    params = {"include_availability": include_availability}
    return CovenantSpec("min_liquidity", "Minimum Liquidity", "min_liquidity", params, ">=", "usd", **kw)


def max_capex(**kw) -> CovenantSpec:
    return CovenantSpec("max_capex", "Maximum Capital Expenditures", "max_capex", {}, "<=", "usd", **kw)


def debt_to_tnw(**kw) -> CovenantSpec:
    return CovenantSpec(
        "debt_to_tnw", "Total Liabilities to Tangible Net Worth Ratio", "debt_to_tnw", {}, "<=", "ratio", **kw
    )


@dataclass(frozen=True)
class BorrowerSpec:
    id: str
    name: str
    legal_form: str  # corporation | llc
    industry: str
    city: str
    state: str
    revenue_2023: str  # millions of dollars
    scale: int
    risk_rating: int
    relationship_manager: str
    analyst: str
    cfo: str
    auditor: str
    closing_date: date
    scenario: str
    covenants: tuple[CovenantSpec, ...]
    revolver: bool = True
    term_loan: bool = True
    borrowing_base: bool = False
    sub_debt: str = "0"
    addback_cap: dict | None = None  # {"type": "amount"|"pct_of"|"none", "value": ...}
    reporting_due_days: int = 45
    usage_target: str = "0.72"  # peak line usage that sizes the commitment
    overrides: dict = field(default_factory=dict)
    letters_of_credit: str = "0"
    concentrated_customer: bool = False  # one customer above the concentration limit


STATE_NAMES = {
    "CA": "California", "ID": "Idaho", "IL": "Illinois", "KS": "Kansas", "NC": "North Carolina",
    "NV": "Nevada", "OH": "Ohio", "OK": "Oklahoma", "PA": "Pennsylvania", "TN": "Tennessee",
    "WA": "Washington", "WI": "Wisconsin",
}  # fmt: skip
RMS = ("Dana Whitcombe", "Marcus Oyelaran", "Priya Venkataraman", "Colin Abernathy")
ANALYSTS = ("Jules Hartmann", "Naomi Castellano", "Theo Lindqvist")
CREDIT_OFFICERS = ("Ruth Okafor-Bell", "Graham Sedgwick")
AUDITORS = ("Wexley Arnault LLP", "Greaves & Tolland, P.C.", "Morrow Castellan LLP", "Hobart Lindgren & Co. LLP")

_TIGHT = D("0.045")

ROSTER: tuple[BorrowerSpec, ...] = (
    BorrowerSpec(
        "harrowgate-precision", "Harrowgate Precision Components, Inc.", "corporation", "manufacturing",
        "Rockford", "IL", "86", 1000, 4, RMS[0], ANALYSTS[0], "Elise Trommler", AUDITORS[0],
        date(2022, 3, 18), "clean", (fccr(), leverage(), min_tnw()), borrowing_base=True,
    ),
    BorrowerSpec(
        "tallwater-foodservice", "Tallwater Foodservice Supply, LLC", "llc", "distribution",
        "Fresno", "CA", "212", 1000, 5, RMS[1], ANALYSTS[1], "Raymond Okeke", AUDITORS[1],
        date(2021, 9, 30), "clean", (fccr(), leverage(debt="senior_debt")), borrowing_base=True,
        sub_debt="0.025", letters_of_credit="400000", concentrated_customer=True,
    ),
    BorrowerSpec(
        "brindlewood-home-health", "Brindlewood Home Health Partners, LLC", "llc", "healthcare services",
        "Chattanooga", "TN", "41", 1000, 4, RMS[2], ANALYSTS[2], "Marisol Ybarra", AUDITORS[2],
        date(2022, 11, 4), "clean", (dscr(), leverage(), min_liquidity(True)),
    ),
    BorrowerSpec(
        "marlowe-ridge-logistics", "Marlowe Ridge Cold Storage & Logistics, Inc.", "corporation", "logistics",
        "Allentown", "PA", "128", 1000, 5, RMS[3], ANALYSTS[0], "Desmond Achterberg", AUDITORS[3],
        date(2021, 6, 25), "clean", (fccr(), leverage(), max_capex()),
        overrides={"financed": {(2025, 2): "3200000"}},
    ),
    BorrowerSpec(
        "ostrander-valley-foods", "Ostrander Valley Foods, Inc.", "corporation", "food processing",
        "Yakima", "WA", "157", 1000, 4, RMS[0], ANALYSTS[1], "Noreen Vandersteen", AUDITORS[0],
        date(2022, 8, 12), "clean",
        (fccr(base="adjusted_ebitda"), leverage(base="adjusted_ebitda"), min_tnw()),
        borrowing_base=True, addback_cap={"type": "none"}, overrides={"nonrecurring": {(2025, 2): "640000"}},
    ),
    BorrowerSpec(
        "dunmore-industrial-supply", "Dunmore Industrial Supply Co.", "corporation", "distribution",
        "Toledo", "OH", "64", 1, 3, RMS[1], ANALYSTS[2], "Curtis Hallgren", AUDITORS[1],
        date(2023, 2, 10), "clean", (interest_coverage(), current_ratio(), debt_to_tnw()),
        term_loan=False, borrowing_base=True,
    ),
    BorrowerSpec(
        "sablewood-dental", "Sablewood Dental Management, LLC", "llc", "healthcare services",
        "Boise", "ID", "28", 1, 4, RMS[2], ANALYSTS[0], "Annika Prewitt", AUDITORS[2],
        date(2023, 5, 19), "clean", (dscr(), leverage()), revolver=False,
    ),
    BorrowerSpec(
        "larkspur-environmental", "Larkspur Environmental Services, Inc.", "corporation", "services",
        "Durham", "NC", "53", 1000, 3, RMS[3], ANALYSTS[1], "Tobias Wennerstrom", AUDITORS[3],
        date(2022, 1, 28), "clean",
        (fccr(base="adjusted_ebitda", distributions=True), leverage(base="adjusted_ebitda"), max_capex()),
        addback_cap={"type": "pct_of", "value": "0.10"},
        overrides={"nonrecurring": {(2025, 4): "310000"}, "dist_cap": "0.40"},
    ),
    BorrowerSpec(
        "kestrel-bay-packaging", "Kestrel Bay Packaging Corp.", "corporation", "manufacturing",
        "Green Bay", "WI", "118", 1000, 6, RMS[0], ANALYSTS[2], "Lorraine Destefano", AUDITORS[0],
        date(2022, 5, 6), "hidden_breach", (leverage(mode="fail_current"), current_ratio(cushion=D("0.05"))),
        overrides={"shock": "-0.080"},
    ),
    BorrowerSpec(
        "vantry-freight", "Vantry Freight Systems, LLC", "llc", "logistics",
        "Memphis", "TN", "94", 1000, 6, RMS[1], ANALYSTS[0], "Garrett Molyneux", AUDITORS[1],
        date(2022, 10, 14), "unapproved_amendment",
        (leverage(base="adjusted_ebitda", mode="amendment_gap"), interest_coverage(base="adjusted_ebitda")),
        addback_cap={"type": "amount", "value": "500000"},
        overrides={"nonrecurring": {(2026, 2): "1400000", (2026, 3): "1900000"}},
    ),
    BorrowerSpec(
        "quillfeather-bakery", "Quillfeather Bakery Brands, Inc.", "corporation", "food processing",
        "Lancaster", "PA", "72", 1000, 5, RMS[2], ANALYSTS[1], "Imogen Barraclough", AUDITORS[2],
        date(2021, 12, 3), "addback_over_cap",
        (leverage(base="adjusted_ebitda"), fccr(base="adjusted_ebitda")),
        addback_cap={"type": "amount", "value": "500000"},
        overrides={"nonrecurring": {(2026, 2): "620000", (2026, 3): "480000"}},
    ),
    BorrowerSpec(
        "thornbury-metal", "Thornbury Metal Fabricators, Inc.", "corporation", "manufacturing",
        "Chattanooga", "TN", "47", 1000, 7, RMS[3], ANALYSTS[2], "Winston Praeger", AUDITORS[3],
        date(2021, 4, 16), "deteriorating_trend",
        (leverage(cushion=_TIGHT), interest_coverage(cushion=_TIGHT), current_ratio(cushion=D("0.05"))),
        usage_target="0.93", overrides={"commitment_step": "50000"},
    ),
    BorrowerSpec(
        "eastmere-building", "Eastmere Building Products, LLC", "llc", "distribution",
        "Spokane", "WA", "135", 1000, 5, RMS[0], ANALYSTS[0], "Felicity Okonjo", AUDITORS[0],
        date(2022, 7, 22), "late_reporting", (fccr(), leverage()), reporting_due_days=30,
    ),
    BorrowerSpec(
        "northgale-electrical", "Northgale Electrical Wholesale, Inc.", "corporation", "distribution",
        "Tulsa", "OK", "88", 1000, 5, RMS[1], ANALYSTS[1], "Bertrand Skaggs", AUDITORS[1],
        date(2022, 12, 9), "miscounted_ineligible", (interest_coverage(), debt_to_tnw()),
        term_loan=False, borrowing_base=True,
    ),
    BorrowerSpec(
        "briarstone-beverage", "Briarstone Beverage Company", "corporation", "food processing",
        "Asheville", "NC", "39", 1, 6, RMS[2], ANALYSTS[2], "Hadley Quarmby", AUDITORS[2],
        date(2023, 3, 31), "over_advance", (fccr(), leverage()), borrowing_base=True, usage_target="0.90",
        overrides={"revolver_pct": "0.100", "term_pct": "0.20"},
    ),
    BorrowerSpec(
        "wrenfield-diagnostics", "Wrenfield Diagnostic Laboratories, Inc.", "corporation",
        "healthcare services", "Madison", "WI", "61", 1000, 4, RMS[3], ANALYSTS[0], "Cordelia Naismith",
        AUDITORS[3], date(2022, 4, 29), "scale_trap", (leverage(), min_tnw(), max_capex(), min_liquidity(False)),
    ),
    BorrowerSpec(
        "halvorsen-plastics", "Halvorsen Plastics & Molding, Inc.", "corporation", "manufacturing",
        "Erie", "PA", "76", 1000, 5, RMS[0], ANALYSTS[1], "Stellan Brodeur", AUDITORS[0],
        date(2021, 11, 19), "restated_comparative", (fccr(), leverage()), borrowing_base=True,
    ),
    BorrowerSpec(
        "ashgrove-fleet", "Ashgrove Fleet Maintenance, LLC", "llc", "services",
        "Wichita", "KS", "22", 1, 5, RMS[1], ANALYSTS[2], "Rosalind Eckhart", AUDITORS[1],
        date(2023, 6, 30), "missing_page", (fccr(), leverage(), current_ratio()),
    ),
    BorrowerSpec(
        "stanmoor-mechanical", "Stanmoor Mechanical Contractors, Inc.", "corporation", "services",
        "Reno", "NV", "33", 1, 5, RMS[2], ANALYSTS[0], "Ignatius Fairweather", AUDITORS[2],
        date(2022, 9, 16), "image_only", (dscr(), current_ratio(), min_tnw()),
    ),
    BorrowerSpec(
        "calder-finch-staffing", "Calder & Finch Staffing Group, LLC", "llc", "services",
        "Columbus", "OH", "16.5", 1, 6, RMS[3], ANALYSTS[1], "Philippa Trask", AUDITORS[3],
        date(2023, 1, 20), "step_up", (leverage(mode="step"), fccr()), overrides={"shock": "-0.065"},
    ),
    BorrowerSpec(
        "pellham-grain", "Pellham Grain & Milling Co.", "corporation", "food processing",
        "Salina", "KS", "215", 1000, 7, RMS[0], ANALYSTS[2], "Augustin Lindqvist-Hale", AUDITORS[0],
        date(2021, 8, 27), "reported_breach",
        (fccr(mode="fail_current"), leverage(cushion=D("0.10")), min_tnw()), borrowing_base=True,
    ),
)

# Only one amendment is ever approved into terms in this book: Marlowe Ridge's first amendment.
APPROVED_AMENDMENT_BORROWER = "marlowe-ridge-logistics"
APPROVED_AMENDMENT_EFFECTIVE = date(2025, 7, 1)
UNAPPROVED_AMENDMENT_CAP = "3500000"


def _scenario_adjustments(spec: BorrowerSpec) -> dict[tuple[int, int], QuarterAdj]:
    adj: dict[tuple[int, int], QuarterAdj] = {}

    def at(year: int, quarter: int) -> QuarterAdj:
        return adj.setdefault((year, quarter), QuarterAdj())

    for (year, quarter), amount in spec.overrides.get("nonrecurring", {}).items():
        at(year, quarter).nonrecurring = D(amount)
    for (year, quarter), amount in spec.overrides.get("financed", {}).items():
        at(year, quarter).financed_capex = D(amount)
    if spec.scenario in ("hidden_breach", "reported_breach", "step_up"):
        at(2026, 3).margin = D(spec.overrides.get("shock", "-0.050"))
    if spec.scenario == "deteriorating_trend":
        ramp = [(2025, 3), (2025, 4), (2026, 1), (2026, 2), (2026, 3)]
        growth = ["-0.08", "-0.12", "-0.16", "-0.18", "-0.19"]
        margin = ["-0.012", "-0.026", "-0.040", "-0.050", "-0.056"]
        dso = ["3", "7", "11", "16", "22"]
        dpo = ["5", "10", "16", "22", "28"]
        for i, (year, quarter) in enumerate(ramp):
            a = at(year, quarter)
            a.growth, a.margin, a.dso, a.dpo = D(growth[i]), D(margin[i]), D(dso[i]), D(dpo[i])
        # An unplanned equipment replacement in the current quarter is drawn on the line.
        at(2026, 3).extra_capex = D(spec.revenue_2023) * 1_000_000 * D("0.016")
    return adj


def build_params(spec: BorrowerSpec, seed: int) -> ModelParams:
    prof = PROFILES[spec.industry]
    o = spec.overrides
    llc = spec.legal_form == "llc"
    line_default = prof["line"] if spec.term_loan else "0.105"  # a line with no term loan carries more
    revolver_pct = D(o.get("revolver_pct", line_default)) if spec.revolver else D(0)
    term_pct = D(o.get("term_pct", prof["term"])) if spec.term_loan else D(0)
    return ModelParams(
        borrower_id=spec.id,
        seed=seed,
        scale=spec.scale,
        revenue_2023=D(spec.revenue_2023) * 1_000_000,
        seasonality=tuple(D(s) for s in prof["seas"]),
        growth=D(o.get("growth", "0.045")),
        gross_margin=D(o.get("gm", prof["gm"])),
        sga_pct=D(o.get("sga", prof["sga"])),
        other_opex_pct=D(prof["opex"]),
        other_income_pct=D(o.get("other_income", "0.0006")),
        tax_rate=D("0.02") if llc else D("0.25"),
        dist_floor=D("0.30") if llc else D("0.10"),
        dist_cap=D(o.get("dist_cap", "0.85" if llc else "0.75")),
        dso=D(prof["dso"]),
        dio=D(prof["dio"]),
        dpo=D(prof["dpo"]),
        oca_pct=D("0.012"),
        accrued_pct=D("0.11"),
        ocl_pct=D("0.014"),
        ppe_pct=D(prof["ppe"]),
        capex_pct=D(prof["capex"]),
        intangibles_pct=D(prof["intang"]),
        onca_pct=D("0.010"),
        oncl_pct=D("0.015"),
        cash_pct=D(o.get("cash_pct", "0.030")),
        has_revolver=spec.revolver,
        revolver_pct=revolver_pct,
        term_pct=term_pct,
        term_amort_years=int(o.get("amort_years", 10)),
        sub_debt_pct=D(spec.sub_debt),
        onca_drift=D(o.get("onca_drift", "0")),
        adjustments=_scenario_adjustments(spec),
    )

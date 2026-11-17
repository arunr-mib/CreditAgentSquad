"""Credit agreement content and terms versions.

For each borrower this module chooses covenant thresholds (from the simulated
figures, so that each scenario produces exactly the intended outcome), writes
the text of the credit agreement and any amendment, and builds the terms
versions in the spec's JSON shape. Every citation quotes one sentence exactly
as printed; its page number is filled in after the agreement is rendered.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from synthetic import expected
from synthetic.scenarios import (
    APPROVED_AMENDMENT_BORROWER,
    APPROVED_AMENDMENT_EFFECTIVE,
    CREDIT_OFFICERS,
    CURRENT_PERIOD,
    LENDER,
    STATE_NAMES,
    UNAPPROVED_AMENDMENT_CAP,
    BorrowerSpec,
    CovenantSpec,
)

D = Decimal
MARGIN = D("0.03")  # no ratio test may sit closer than this to its threshold
ADDBACK_NAME = "restructuring"
ADDBACK_SOURCE = "is.nonrecurring_expense"


# --------------------------------------------------------------------------- document structure


@dataclass
class Para:
    text: str
    anchors: tuple[str, ...] = ()
    style: str = "body"  # body | indent | center | small


@dataclass
class Section:
    number: str
    title: str
    paras: list[Para]


@dataclass
class Article:
    number: str
    title: str
    sections: list[Section]


@dataclass
class LegalDoc:
    slug: str
    doc_type: str  # credit_agreement | amendment
    title: str
    subtitle: str
    doc_date: date
    borrower_name: str
    preamble: list[Para]
    articles: list[Article]
    signature_blocks: list[tuple[str, str, str]]  # (party, signer, title)
    exhibits: list[tuple[str, list[Para], list[list[str]] | None]] = field(default_factory=list)
    cites: dict[str, dict] = field(default_factory=dict)  # anchor -> {"section", "quote"}
    toc: bool = True

    def cite(self, anchor: str, section: str, sentence: str) -> str:
        self.cites[anchor] = {"section": section, "quote": sentence}
        return sentence


def money(amount: Decimal | str) -> str:
    return f"${int(D(amount)):,}"


def ratio_words(value: Decimal | str) -> str:
    return f"{D(value):.2f} to 1.00"


def pct_words(value: Decimal | str) -> str:
    pct = D(value) * 100
    return f"{pct.normalize():f}%"


def long_date(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# --------------------------------------------------------------------------- thresholds


def _ceil(x: Decimal, grid: Decimal) -> Decimal:
    return (x / grid).to_integral_value(ROUND_CEILING) * grid


def _floor(x: Decimal, grid: Decimal) -> Decimal:
    return (x / grid).to_integral_value(ROUND_FLOOR) * grid


def _nice(x: Decimal, up: bool) -> Decimal:
    """Round a dollar amount to two significant digits."""
    grid = D(10) ** (x.adjusted() - 1)
    return _ceil(x, grid) if up else _floor(x, grid)


def _between(lo: Decimal, hi: Decimal) -> Decimal:
    """A threshold on the coarsest usual grid that fits strictly inside [lo, hi]."""
    for grid in (D("0.25"), D("0.05")):
        candidates = []
        t = _ceil(lo, grid)
        while t <= hi:
            candidates.append(t)
            t += grid
        if candidates:
            mid = (lo + hi) / 2
            return min(candidates, key=lambda c: (abs(c - mid), c))
    raise ValueError(f"no threshold fits between {lo} and {hi}")


_RATIO_CAPS = {"fccr": "1.25", "dscr": "1.25", "interest_coverage": "3.00", "current_ratio": "1.25"}


def choose_test(
    cov: CovenantSpec, series: dict[date, Decimal], amended: dict[date, Decimal] | None = None
) -> dict:
    """Pick the threshold (and any step) that gives the covenant its intended history."""
    current = series[CURRENT_PERIOD]
    prior = [v for end, v in series.items() if end != CURRENT_PERIOD]
    upper = cov.operator == "<="
    steps: list[dict] = []
    if cov.mode == "pass":
        worst = max(series.values()) if upper else min(series.values())
        if cov.unit == "usd":
            threshold = _nice(worst * (1 + cov.cushion) if upper else worst / (1 + cov.cushion), up=upper)
        elif upper:
            threshold = _ceil(worst * (1 + cov.cushion), D("0.25") if cov.cushion >= D("0.2") else D("0.05"))
            if cov.archetype == "leverage" and cov.cushion >= D("0.2"):
                threshold = max(threshold, D("2.50"))
        else:
            threshold = _floor(worst / (1 + cov.cushion), D("0.05"))
            if cov.cushion >= D("0.2") and cov.id in _RATIO_CAPS:
                threshold = min(threshold, D(_RATIO_CAPS[cov.id]))
                if threshold < 1 and worst / D("1.10") >= 1:
                    threshold = D("1.00")  # a coverage or liquidity ratio is not set below one
    elif cov.mode == "fail_current":
        if upper:
            threshold = _between(max(prior) + MARGIN, current - MARGIN)
        else:
            threshold = _between(current + MARGIN, min(prior) - MARGIN)
    elif cov.mode == "amendment_gap":
        assert upper and amended is not None
        threshold = _between(max(max(prior), amended[CURRENT_PERIOD]) + MARGIN, current - MARGIN)
    elif cov.mode == "step":
        assert upper
        this_year = [v for end, v in series.items() if end.year == CURRENT_PERIOD.year and end != CURRENT_PERIOD]
        last_year = [v for end, v in series.items() if end.year < CURRENT_PERIOD.year]
        stepped = _between(max(this_year) + MARGIN, current - MARGIN)
        threshold = _ceil(max(max(last_year), current) + MARGIN, D("0.25"))  # the level before the step
        threshold = max(threshold, _ceil(stepped + D("0.25"), D("0.25")))
        steps = [{"from": f"{CURRENT_PERIOD.year}-01-01", "value": f"{stepped:.2f}"}]
    else:
        raise ValueError(cov.mode)
    text = f"{threshold:.2f}" if cov.unit == "ratio" else f"{threshold:f}"
    return {"operator": cov.operator, "threshold": text, "steps": steps, "unit": cov.unit}


# --------------------------------------------------------------------------- clause text


def addback_cap_json(cap: dict | None) -> dict | None:
    if cap is None or cap["type"] == "none":
        return None
    if cap["type"] == "amount":
        return {"type": "amount", "value": cap["value"]}
    return {"type": "pct_of", "value": cap["value"], "of": {"op": "named", "name": "ebitda"}}


def adjusted_ebitda_sentence(cap: dict | None) -> str:
    base = (
        '"Adjusted EBITDA" means, for any period, EBITDA for such period plus restructuring and other '
        "non-recurring charges deducted in determining net income for such period"
    )
    if cap is None:
        return base + "."
    if cap["type"] == "amount":
        return (
            f"{base}, provided that the aggregate amount added back pursuant to this definition shall not "
            f"exceed {money(cap['value'])} in any period of four consecutive fiscal quarters."
        )
    return (
        f"{base}, provided that the aggregate amount added back pursuant to this definition shall not "
        f"exceed {pct_words(cap['value'])} of EBITDA for such period, calculated before giving effect to "
        "such add-back."
    )


_EARNINGS_WORDS = {"ebitda": "EBITDA", "adjusted_ebitda": "Adjusted EBITDA"}
_DEDUCTION_WORDS = {
    "unfinanced_capex": "Unfinanced Capital Expenditures",
    "cash_taxes": "cash paid for income taxes",
    "distributions": "distributions to owners",
}
_DENOMINATOR_WORDS = {
    "cash_interest": "cash paid for interest",
    "interest_expense": "interest expense",
    "scheduled_principal": "scheduled principal payments on term debt",
}


def _join(words: list[str]) -> str:
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + " and " + words[-1]


def covenant_definition_sentence(cov: CovenantSpec) -> str:
    p = cov.params
    if cov.archetype == "coverage":
        numerator = f"{_EARNINGS_WORDS[p['numerator_base']]} for such period"
        if p["deductions"]:
            numerator += " minus " + _join([_DEDUCTION_WORDS[d] for d in p["deductions"]]) + " for such period"
        denominator = _join([_DENOMINATOR_WORDS[d] for d in p["denominator"]])
        if len(p["denominator"]) > 1:
            denominator = "the sum of " + denominator
        return (
            f'"{cov.name}" means, for any period of four consecutive fiscal quarters, the ratio of (a) '
            f"{numerator} to (b) {denominator} for such period."
        )
    if cov.archetype == "leverage":
        debt = "Senior Debt" if p["debt"] == "senior_debt" else "Total Debt"
        return (
            f'"{cov.name}" means, as of any date, the ratio of (a) {debt} as of such date to (b) '
            f"{_EARNINGS_WORDS[p['ebitda']]} for the period of four consecutive fiscal quarters then ended."
        )
    if cov.archetype == "current_ratio":
        return (
            '"Current Ratio" means, as of any date, the ratio of (a) total current assets to (b) total '
            "current liabilities of the Borrower as of such date."
        )
    if cov.archetype == "min_tangible_net_worth":
        return (
            '"Tangible Net Worth" means, as of any date, total equity of the Borrower minus goodwill and '
            "intangibles as of such date."
        )
    if cov.archetype == "min_liquidity":
        extra = " plus unused availability under the Revolving Commitment" if p["include_availability"] else ""
        return f'"Liquidity" means, as of any date, unrestricted cash and equivalents of the Borrower{extra} as of such date.'
    if cov.archetype == "max_capex":
        return (
            '"Capital Expenditures" means, for any period, purchases of property and equipment by the '
            "Borrower during such period."
        )
    if cov.archetype == "debt_to_tnw":
        return (
            f'"{cov.name}" means, as of any date, the ratio of (a) total liabilities of the Borrower to (b) '
            "Tangible Net Worth as of such date."
        )
    raise ValueError(cov.archetype)


def covenant_threshold_sentence(cov: CovenantSpec, threshold: str) -> str:
    quarter = "measured as of the last day of each fiscal quarter"
    if cov.archetype == "coverage":
        return (
            f"The Borrower shall not permit the {cov.name}, {quarter} for the period of four consecutive "
            f"fiscal quarters then ended, to be less than {ratio_words(threshold)}."
        )
    if cov.archetype in ("leverage", "debt_to_tnw"):
        return f"The Borrower shall not permit the {cov.name}, {quarter}, to exceed {ratio_words(threshold)}."
    if cov.archetype == "current_ratio":
        return f"The Borrower shall not permit the Current Ratio, {quarter}, to be less than {ratio_words(threshold)}."
    if cov.archetype == "min_tangible_net_worth":
        return f"The Borrower shall maintain Tangible Net Worth, {quarter}, of not less than {money(threshold)}."
    if cov.archetype == "min_liquidity":
        return f"The Borrower shall maintain Liquidity, {quarter}, of not less than {money(threshold)}."
    if cov.archetype == "max_capex":
        return (
            f"The Borrower shall not make Capital Expenditures in an aggregate amount exceeding "
            f"{money(threshold)} in any period of four consecutive fiscal quarters, {quarter}."
        )
    raise ValueError(cov.archetype)


def covenant_step_sentence(cov: CovenantSpec, step: dict) -> str:
    start = long_date(date.fromisoformat(step["from"]))
    return (
        f"Notwithstanding the foregoing, as of the last day of each fiscal quarter ending on or after "
        f"{start}, the {cov.name} shall not exceed {ratio_words(step['value'])}."
    )


def _measurement_basis(cov: CovenantSpec) -> str:
    return "ttm" if cov.archetype in ("coverage", "leverage", "max_capex") else "point"


# --------------------------------------------------------------------------- the agreement


@dataclass
class TermsBuild:
    agreement: LegalDoc
    amendments: list[LegalDoc]
    versions: list[dict]  # citations still carry "_anchor": (slug, anchor)
    clause_index: list[dict]
    unapproved: dict | None  # details of the amendment that must stay out of approved terms
    facilities: list[dict]
    step: dict | None  # the dated threshold step, where a covenant has one


def _quarter_ends_between(start: date, finish: date) -> int:
    count, year = 0, start.year
    while year <= finish.year:
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            if start < date(year, month, day) <= finish:
                count += 1
        year += 1
    return count


def build_terms(
    spec: BorrowerSpec,
    fin: expected.Financials,
    test_periods: list[date],
    opening: dict[str, Decimal],
    term_payment: Decimal,
    commitment: Decimal,
    bb_terms: dict | None,
    availability_at,
) -> TermsBuild:
    """Thresholds, agreement text, amendments and terms versions for one borrower."""
    bid = spec.id
    cap = None if spec.addback_cap is None or spec.addback_cap["type"] == "none" else spec.addback_cap
    uses_adjusted = spec.addback_cap is not None
    addbacks = []
    if uses_adjusted:
        addbacks.append(
            {
                "name": ADDBACK_NAME,
                "source_key": ADDBACK_SOURCE,
                "cap": addback_cap_json(cap),
                "citation": {"field": "definitions.ebitda.addbacks.restructuring", "_anchor": ("credit-agreement", "def.adjusted_ebitda")},
            }
        )
    definitions = {"ebitda": {"base": "ebitda", "addbacks": addbacks}}
    amended_definitions = None
    if spec.scenario == "unapproved_amendment":
        amended_cap = {"type": "amount", "value": UNAPPROVED_AMENDMENT_CAP}
        amended_definitions = {
            "ebitda": {"base": "ebitda", "addbacks": [{**addbacks[0], "cap": addback_cap_json(amended_cap)}]}
        }

    doc = LegalDoc(
        slug="credit-agreement",
        doc_type="credit_agreement",
        title="CREDIT AGREEMENT",
        subtitle=f"dated as of {long_date(spec.closing_date)}",
        doc_date=spec.closing_date,
        borrower_name=spec.name,
        preamble=[],
        articles=[],
        signature_blocks=[
            (spec.name, spec.cfo, "Chief Financial Officer"),
            (LENDER, spec.relationship_manager, "Senior Vice President"),
        ],
    )

    # ---- covenants and thresholds
    covenants_json: list[dict] = []
    covenant_sections: list[Section] = []
    definition_paras: dict[str, Para] = {}
    step_details = None
    tightened_leverage = None
    for index, cov in enumerate(spec.covenants, start=1):
        shell = {"archetype": cov.archetype, "params": cov.params, "rounding": _rounding(cov)}
        series = {
            end: expected.covenant_value(shell, definitions, fin, end, availability_at(end))[0]
            for end in test_periods
        }
        amended = None
        if cov.mode == "amendment_gap":
            amended = {
                end: expected.covenant_value(shell, amended_definitions, fin, end, availability_at(end))[0]
                for end in test_periods
            }
        test = choose_test(cov, series, amended)
        if bid == APPROVED_AMENDMENT_BORROWER and cov.id == "total_leverage":
            # The agreement as signed was looser; the approved first amendment tightens it.
            tightened_leverage = test["threshold"]
            test = {**test, "threshold": f"{D(tightened_leverage) + D('0.50'):.2f}"}
        section = f"6.{index}"
        def_anchor, thr_anchor = f"cov.{cov.id}.definition", f"cov.{cov.id}.threshold"
        sentence = doc.cite(def_anchor, "1.1", covenant_definition_sentence(cov))
        definition_paras[cov.id] = Para(sentence, (def_anchor,))
        text = doc.cite(thr_anchor, section, covenant_threshold_sentence(cov, test["threshold"]))
        anchors = [thr_anchor]
        citations = [
            {"field": "test.threshold", "_anchor": ("credit-agreement", thr_anchor)},
            {"field": "definition", "_anchor": ("credit-agreement", def_anchor)},
        ]
        for i, step in enumerate(test["steps"]):
            step_anchor = f"cov.{cov.id}.step{i}"
            text += " " + doc.cite(step_anchor, section, covenant_step_sentence(cov, step))
            anchors.append(step_anchor)
            citations.append({"field": f"test.steps[{i}]", "_anchor": ("credit-agreement", step_anchor)})
            step_details = {"covenant_id": cov.id, "old_threshold": test["threshold"], **step}
        covenant_sections.append(Section(section, cov.name, [Para(text, tuple(anchors))]))
        covenants_json.append(
            {
                "id": cov.id,
                "name": cov.name,
                "archetype": cov.archetype,
                "params": cov.params,
                "test": test,
                "measurement": {"basis": _measurement_basis(cov), "frequency": "quarterly"},
                "rounding": _rounding(cov),
                "citations": citations,
            }
        )

    # ---- facilities
    facilities: list[dict] = []
    term_original = D(0)
    revolver_maturity = spec.closing_date.replace(year=spec.closing_date.year + 6)
    term_maturity = spec.closing_date.replace(year=spec.closing_date.year + 7)
    if spec.revolver:
        facilities.append(
            {
                "id": f"{bid}-rlc",
                "borrower_id": bid,
                "type": "revolver",
                "name": "Revolving Line of Credit",
                "commitment": f"{commitment:f}",
                "original_amount": f"{commitment:f}",
                "closing_date": spec.closing_date.isoformat(),
                "maturity_date": revolver_maturity.isoformat(),
                "interest_rate": "Term SOFR + 2.75%",
                "borrowing_base": spec.borrowing_base,
            }
        )
    if spec.term_loan:
        opening_term = opening["bs.cpltd"] + opening["bs.long_term_debt"]
        term_original = opening_term + term_payment * _quarter_ends_between(spec.closing_date, date(2022, 12, 31))
        facilities.append(
            {
                "id": f"{bid}-tl",
                "borrower_id": bid,
                "type": "term_loan",
                "name": "Term Loan",
                "commitment": f"{term_original:f}",
                "original_amount": f"{term_original:f}",
                "closing_date": spec.closing_date.isoformat(),
                "maturity_date": term_maturity.isoformat(),
                "interest_rate": "Term SOFR + 3.00%",
                "borrowing_base": False,
                "quarterly_installment": f"{term_payment:f}",
            }
        )

    # ---- Article 1: definitions
    defs: list[Para] = [
        Para(
            'As used in this Agreement, the following terms have the meanings set forth below. Terms defined '
            "in the singular include the plural and vice versa."
        ),
    ]
    named: dict[str, Para] = {}
    named["Affiliate"] = Para(
        '"Affiliate" means, with respect to any person, any other person that directly or indirectly '
        "controls, is controlled by, or is under common control with such person."
    )
    named["Business Day"] = Para(
        '"Business Day" means any day other than a Saturday, a Sunday or a day on which commercial banks '
        f"in the State of {STATE_NAMES[spec.state]} are authorized or required by law to close."
    )
    named["Closing Date"] = Para(f'"Closing Date" means {long_date(spec.closing_date)}.')
    named["Compliance Certificate"] = Para(
        '"Compliance Certificate" means a certificate substantially in the form of Exhibit A, signed by '
        "the chief financial officer of the Borrower, setting forth the calculations required to "
        "establish compliance with Article 6."
    )
    named["EBITDA"] = Para(
        doc.cite(
            "def.ebitda",
            "1.1",
            '"EBITDA" means, for any period, net income of the Borrower for such period plus, to the extent '
            "deducted in determining net income for such period, interest expense, income tax expense, and "
            "depreciation and amortization, all determined in accordance with GAAP.",
        ),
        ("def.ebitda",),
    )
    if uses_adjusted:
        named["Adjusted EBITDA"] = Para(
            doc.cite("def.adjusted_ebitda", "1.1", adjusted_ebitda_sentence(cap)), ("def.adjusted_ebitda",)
        )
    named["GAAP"] = Para(
        '"GAAP" means generally accepted accounting principles in the United States of America, applied '
        "on a basis consistent with the financial statements delivered to the Lender before the Closing Date."
    )
    named["Loan Documents"] = Para(
        '"Loan Documents" means this Agreement, each note, each security agreement, each Compliance '
        "Certificate and every other document delivered to the Lender in connection with this Agreement."
    )
    named["Obligations"] = Para(
        '"Obligations" means all loans, advances, debts, liabilities and obligations of the Borrower to '
        "the Lender arising under any Loan Document, whether now existing or hereafter arising."
    )
    named["Subordinated Debt"] = Para(
        '"Subordinated Debt" means indebtedness of the Borrower that is subordinated to the Obligations '
        "on terms and pursuant to documentation satisfactory to the Lender."
    )
    named["Total Debt"] = Para(
        doc.cite(
            "def.total_debt",
            "1.1",
            '"Total Debt" means, as of any date, the sum of the outstanding principal amount of the line of '
            "credit, the current portion of long-term debt, long-term debt net of current portion, and "
            "Subordinated Debt of the Borrower as of such date.",
        ),
        ("def.total_debt",),
    )
    if any(c.params.get("debt") == "senior_debt" for c in spec.covenants):
        named["Senior Debt"] = Para('"Senior Debt" means, as of any date, Total Debt minus Subordinated Debt as of such date.')
    if any("unfinanced_capex" in c.params.get("deductions", []) for c in spec.covenants):
        named["Unfinanced Capital Expenditures"] = Para(
            '"Unfinanced Capital Expenditures" means, for any period, purchases of property and equipment '
            "by the Borrower during such period minus capital expenditures financed with purchase-money "
            "debt during such period."
        )
    needs_tnw = any(c.archetype in ("min_tangible_net_worth", "debt_to_tnw") for c in spec.covenants)
    for cov in spec.covenants:
        key = cov.name
        if cov.archetype == "min_tangible_net_worth":
            key = "Tangible Net Worth"
        elif cov.archetype == "min_liquidity":
            key = "Liquidity"
        elif cov.archetype == "max_capex":
            key = "Capital Expenditures"
        named[key] = definition_paras[cov.id]
    if needs_tnw and "Tangible Net Worth" not in named:
        named["Tangible Net Worth"] = Para(
            '"Tangible Net Worth" means, as of any date, total equity of the Borrower minus goodwill and '
            "intangibles as of such date."
        )
    if spec.revolver:
        named["Revolving Commitment"] = Para(
            '"Revolving Commitment" means the commitment of the Lender to make Revolving Loans in the '
            "amount set forth in Section 2.1, as reduced or increased from time to time in accordance with "
            "this Agreement."
        )
        named["Revolving Maturity Date"] = Para(f'"Revolving Maturity Date" means {long_date(revolver_maturity)}.')
    if spec.term_loan:
        named["Term Maturity Date"] = Para(f'"Term Maturity Date" means {long_date(term_maturity)}.')

    clause_index_anchors: list[tuple[str, str]] = [
        ("definitions.ebitda", "def.ebitda"),
        ("definitions.total_debt", "def.total_debt"),
    ]
    bb_json = None
    if bb_terms is not None:
        ar = next(c for c in bb_terms["components"] if c["collateral"] == "accounts_receivable")
        inv = next(c for c in bb_terms["components"] if c["collateral"] == "inventory")
        rules = ar["eligibility"]
        named["Borrowing Base"] = Para(
            doc.cite(
                "bb.base",
                "1.1",
                f'"Borrowing Base" means, as of any date, the sum of (a) {pct_words(ar["advance_rate"])} of '
                f'Eligible Accounts, plus (b) the lesser of {pct_words(inv["advance_rate"])} of Eligible '
                f'Inventory and {money(inv["sublimit"])}, minus (c) Reserves.',
            ),
            ("bb.base",),
        )
        named["Borrowing Base Certificate"] = Para(
            '"Borrowing Base Certificate" means a certificate substantially in the form of Exhibit B, '
            "signed by the chief financial officer of the Borrower, setting forth the calculation of the "
            "Borrowing Base."
        )
        named["Eligible Accounts"] = Para(
            doc.cite(
                "bb.ar_eligibility",
                "1.1",
                '"Eligible Accounts" means accounts receivable of the Borrower arising in the ordinary '
                f'course of business, excluding (a) any account that remains unpaid more than '
                f'{rules["max_age_days"]} days after its invoice date, (b) all accounts owing by an account '
                f'debtor if more than {pct_words(rules["cross_aging_pct"])} of the aggregate balance owing by '
                f'such account debtor remains unpaid more than {rules["max_age_days"]} days after invoice '
                "date, (c) accounts owing by an Affiliate of the Borrower, by an account debtor located "
                "outside the United States, or by a governmental authority, (d) accounts to the extent "
                "subject to offset by amounts owed by the Borrower to the account debtor, and (e) accounts "
                "owing by any single account debtor to the extent that such accounts exceed "
                f'{pct_words(rules["concentration_limit_pct"])} of the aggregate amount of all accounts that '
                "are Eligible Accounts before giving effect to this clause (e).",
            ),
            ("bb.ar_eligibility",),
        )
        named["Eligible Inventory"] = Para(
            doc.cite(
                "bb.inventory_eligibility",
                "1.1",
                '"Eligible Inventory" means inventory of the Borrower valued at the lower of cost and '
                "market, excluding work in process and inventory held on consignment.",
            ),
            ("bb.inventory_eligibility",),
        )
        reserve_words = _join([f'a {r["name"].lower()} in the amount of {money(r["amount"])}' for r in bb_terms["reserves"]])
        named["Reserves"] = Para(
            doc.cite("bb.reserves", "1.1", f'"Reserves" means {reserve_words}.'), ("bb.reserves",)
        )
        bb_json = {**bb_terms, "citation": {"field": "borrowing_base", "_anchor": ("credit-agreement", "bb.base")}}
        clause_index_anchors += [
            ("borrowing_base.components[accounts_receivable].eligibility", "bb.ar_eligibility"),
            ("borrowing_base.components[inventory].eligibility", "bb.inventory_eligibility"),
            ("borrowing_base.reserves", "bb.reserves"),
        ]
    defs += [named[k] for k in sorted(named, key=str.lower)]
    article1 = Article(
        "1",
        "DEFINITIONS",
        [
            Section("1.1", "Defined Terms", defs),
            Section(
                "1.2",
                "Accounting Terms",
                [
                    Para(
                        "All accounting terms not specifically defined in this Agreement shall be construed in "
                        "accordance with GAAP, and all financial computations required under this Agreement "
                        "shall be made in accordance with GAAP. All ratios shall be calculated to two decimal "
                        "places, rounding the result up if the third decimal place is five or more."
                    )
                ],
            ),
        ],
    )

    # ---- Article 2: facilities
    sections2: list[Section] = []
    n = 1
    if spec.revolver:
        sentence = doc.cite(
            "fac.revolver",
            f"2.{n}",
            "Subject to the terms and conditions of this Agreement, the Lender agrees to make revolving "
            "loans to the Borrower from time to time until the Revolving Maturity Date in an aggregate "
            f"principal amount at any time outstanding not to exceed {money(commitment)}.",
        )
        extra = (
            " The Borrower may borrow, repay and reborrow Revolving Loans, and all Revolving Loans shall be "
            "due and payable in full on the Revolving Maturity Date."
        )
        sections2.append(Section(f"2.{n}", "Revolving Loans", [Para(sentence + extra, ("fac.revolver",))]))
        clause_index_anchors.append(("facilities.revolver.commitment", "fac.revolver"))
        n += 1
    if spec.term_loan:
        sentence = doc.cite(
            "fac.term",
            f"2.{n}",
            f"The Lender has made a term loan to the Borrower on the Closing Date in the original principal "
            f"amount of {money(term_original)}.",
        )
        repay = doc.cite(
            "fac.term_repayment",
            f"2.{n}",
            f"The Borrower shall repay the Term Loan in consecutive quarterly installments of "
            f"{money(term_payment)} each, payable on the last day of each fiscal quarter, with the "
            "remaining unpaid balance due and payable on the Term Maturity Date.",
        )
        sections2.append(
            Section(f"2.{n}", "Term Loan", [Para(sentence + " " + repay, ("fac.term", "fac.term_repayment"))])
        )
        clause_index_anchors += [
            ("facilities.term_loan.original_amount", "fac.term"),
            ("facilities.term_loan.quarterly_installment", "fac.term_repayment"),
        ]
        n += 1
    sections2.append(
        Section(
            f"2.{n}",
            "Interest",
            [
                Para(
                    "Each Revolving Loan shall bear interest at a rate per annum equal to Term SOFR plus 2.75%, "
                    "and the Term Loan shall bear interest at a rate per annum equal to Term SOFR plus 3.00%. "
                    "Interest shall be payable in arrears on the last Business Day of each calendar month and "
                    "shall be computed on the basis of the actual number of days elapsed in a year of 360 days."
                ),
                Para(
                    "Upon the occurrence and during the continuance of an Event of Default, all Obligations "
                    "shall bear interest at a rate per annum that is two percentage points above the rate "
                    "otherwise applicable."
                ),
            ],
        )
    )
    n += 1
    sections2.append(
        Section(
            f"2.{n}",
            "Fees",
            [
                Para(
                    "The Borrower shall pay to the Lender an unused line fee on the average daily unused "
                    "portion of any revolving commitment, payable quarterly in arrears, and such other fees as "
                    "are set forth in the fee letter delivered on the Closing Date."
                )
            ],
        )
    )
    n += 1
    if bb_terms is not None:
        sections2.append(
            Section(
                f"2.{n}",
                "Borrowing Base",
                [
                    Para(
                        "The aggregate outstanding principal amount of the Revolving Loans plus the undrawn "
                        "amount of all outstanding letters of credit shall not at any time exceed the lesser "
                        "of the Revolving Commitment and the Borrowing Base."
                    ),
                    Para(
                        "If at any time such aggregate amount exceeds the lesser of the Revolving Commitment "
                        "and the Borrowing Base, the Borrower shall immediately, and without notice or demand, "
                        "prepay the Revolving Loans in an amount sufficient to eliminate such excess."
                    ),
                    Para(
                        "The Lender may conduct field examinations of the collateral and may establish or "
                        "adjust Reserves in its reasonable credit judgment upon notice to the Borrower."
                    ),
                ],
            )
        )
        n += 1
    sections2.append(
        Section(
            f"2.{n}",
            "Payments and Prepayments",
            [
                Para(
                    "All payments by the Borrower shall be made to the Lender in immediately available funds "
                    "without setoff or counterclaim. The Borrower may prepay the Obligations in whole or in "
                    "part at any time without premium or penalty, and prepayments of the Term Loan shall be "
                    "applied to installments in the inverse order of maturity."
                )
            ],
        )
    )
    article2 = Article("2", "THE CREDIT FACILITIES", sections2)

    article3 = Article(
        "3",
        "CONDITIONS PRECEDENT",
        [
            Section(
                "3.1",
                "Conditions to Closing",
                [
                    Para(
                        "The obligation of the Lender to make the initial extension of credit is subject to "
                        "the receipt by the Lender of each of the following, in form and substance "
                        "satisfactory to the Lender: executed counterparts of each Loan Document; resolutions "
                        "and incumbency certificates of the Borrower; evidence of insurance; lien searches; "
                        "and an opinion of counsel to the Borrower."
                    )
                ],
            ),
            Section(
                "3.2",
                "Conditions to Each Extension of Credit",
                [
                    Para(
                        "The obligation of the Lender to make any extension of credit is subject to the "
                        "conditions that the representations and warranties in Article 4 are true and correct "
                        "in all material respects on the date of such extension of credit and that no Default "
                        "or Event of Default has occurred and is continuing or would result from it."
                    )
                ],
            ),
        ],
    )
    article4 = Article(
        "4",
        "REPRESENTATIONS AND WARRANTIES",
        [
            Section(
                "4.1",
                "Organization and Authority",
                [
                    Para(
                        "The Borrower is duly organized, validly existing and in good standing under the laws "
                        "of its jurisdiction of organization, has all requisite power and authority to carry "
                        "on its business, and has duly authorized the execution, delivery and performance of "
                        "each Loan Document."
                    )
                ],
            ),
            Section(
                "4.2",
                "Financial Statements",
                [
                    Para(
                        "The financial statements of the Borrower delivered to the Lender fairly present, in "
                        "all material respects, the financial condition and results of operations of the "
                        "Borrower as of the dates and for the periods indicated, in accordance with GAAP. "
                        "Since the date of the most recent audited financial statements there has been no "
                        "material adverse change in the business, assets or financial condition of the Borrower."
                    )
                ],
            ),
            Section(
                "4.3",
                "Litigation and Compliance",
                [
                    Para(
                        "There is no action, suit or proceeding pending or, to the knowledge of the Borrower, "
                        "threatened against the Borrower that could reasonably be expected to have a material "
                        "adverse effect. The Borrower is in compliance in all material respects with all laws "
                        "and regulations applicable to it."
                    )
                ],
            ),
            Section(
                "4.4",
                "Collateral",
                [
                    Para(
                        "The Borrower has good title to its assets, free of all liens other than liens "
                        "permitted by this Agreement, and the security documents create in favor of the Lender "
                        "a valid, perfected, first-priority security interest in the collateral described in them."
                    )
                ],
            ),
        ],
    )

    # ---- Article 5: reporting
    due = spec.reporting_due_days
    reporting_paras = [
        Para(
            "(a) "
            + doc.cite(
                "rep.annual_statements",
                "5.1(a)",
                "As soon as available, and in any event within 120 days after the end of each fiscal year, "
                "the Borrower shall deliver to the Lender audited financial statements of the Borrower for "
                "such fiscal year, accompanied by an unqualified opinion of independent certified public "
                "accountants acceptable to the Lender.",
            ),
            ("rep.annual_statements",),
            "indent",
        ),
        Para(
            "(b) "
            + doc.cite(
                "rep.quarterly_statements",
                "5.1(b)",
                f"As soon as available, and in any event within {due} days after the end of each of the "
                "first three fiscal quarters of each fiscal year, the Borrower shall deliver to the Lender "
                "internally prepared financial statements of the Borrower for the fiscal year to date.",
            ),
            ("rep.quarterly_statements",),
            "indent",
        ),
        Para(
            "(c) "
            + doc.cite(
                "rep.compliance_certificate",
                "5.1(c)",
                f"Within {due} days after the end of each fiscal quarter, the Borrower shall deliver to the "
                "Lender a Compliance Certificate signed by its chief financial officer.",
            ),
            ("rep.compliance_certificate",),
            "indent",
        ),
    ]
    reporting_json = [
        _requirement("annual_statements", "annual_financial_statements", "annual", 120, "audited"),
        _requirement("quarterly_statements", "interim_financial_statements", "quarterly", due, "internal"),
        _requirement("compliance_certificate", "compliance_certificate", "quarterly", due, None),
    ]
    if bb_terms is not None:
        reporting_paras.append(
            Para(
                "(d) "
                + doc.cite(
                    "rep.borrowing_base_certificate",
                    "5.1(d)",
                    "Within 20 days after the end of each calendar month, the Borrower shall deliver to the "
                    "Lender a Borrowing Base Certificate as of the last day of such month, together with an "
                    "accounts receivable aging and an inventory report.",
                ),
                ("rep.borrowing_base_certificate",),
                "indent",
            )
        )
        reporting_json.append(
            _requirement("borrowing_base_certificate", "borrowing_base_certificate", "monthly", 20, None)
        )
    article5 = Article(
        "5",
        "AFFIRMATIVE COVENANTS",
        [
            Section("5.1", "Financial Reporting", reporting_paras),
            Section(
                "5.2",
                "Notices",
                [
                    Para(
                        "The Borrower shall promptly notify the Lender in writing of the occurrence of any "
                        "Default or Event of Default, any litigation that could reasonably be expected to have "
                        "a material adverse effect, and any change in its name, jurisdiction of organization "
                        "or chief executive office."
                    )
                ],
            ),
            Section(
                "5.3",
                "Maintenance of Existence, Properties and Insurance",
                [
                    Para(
                        "The Borrower shall preserve and maintain its legal existence and all rights and "
                        "franchises material to its business, keep its properties in good working order, and "
                        "maintain insurance with financially sound insurers in such amounts and against such "
                        "risks as are customary for companies engaged in similar businesses."
                    )
                ],
            ),
            Section(
                "5.4",
                "Books, Records and Inspections",
                [
                    Para(
                        "The Borrower shall keep proper books of record and account in accordance with GAAP "
                        "and shall permit representatives of the Lender, upon reasonable notice and during "
                        "normal business hours, to visit and inspect its properties and to examine its books "
                        "and records."
                    )
                ],
            ),
            Section(
                "5.5",
                "Depository Relationship",
                [
                    Para(
                        "The Borrower shall maintain its primary operating and depository accounts with the "
                        "Lender for so long as any Obligations remain outstanding."
                    )
                ],
            ),
        ],
    )
    article6 = Article("6", "FINANCIAL COVENANTS", covenant_sections)
    article7 = Article(
        "7",
        "NEGATIVE COVENANTS",
        [
            Section(
                "7.1",
                "Indebtedness",
                [
                    Para(
                        "The Borrower shall not create, incur or permit to exist any indebtedness other than "
                        "the Obligations, purchase-money indebtedness incurred to finance the acquisition of "
                        "equipment, Subordinated Debt, and trade payables incurred in the ordinary course of "
                        "business."
                    )
                ],
            ),
            Section(
                "7.2",
                "Liens",
                [
                    Para(
                        "The Borrower shall not create or permit to exist any lien on any of its assets other "
                        "than liens in favor of the Lender, purchase-money liens on equipment securing "
                        "indebtedness permitted by Section 7.1, and liens for taxes not yet due."
                    )
                ],
            ),
            Section(
                "7.3",
                "Distributions",
                [
                    Para(
                        "The Borrower shall not declare or pay any dividend or distribution to its owners if a "
                        "Default or Event of Default has occurred and is continuing or would result from such "
                        "payment, other than distributions to owners in amounts necessary to pay income taxes "
                        "attributable to the income of the Borrower."
                    )
                ],
            ),
            Section(
                "7.4",
                "Fundamental Changes and Dispositions",
                [
                    Para(
                        "The Borrower shall not merge or consolidate with any other person, sell all or "
                        "substantially all of its assets, or change the nature of its business, and shall not "
                        "sell or otherwise dispose of assets outside the ordinary course of business."
                    )
                ],
            ),
        ],
    )
    article8 = Article(
        "8",
        "EVENTS OF DEFAULT",
        [
            Section(
                "8.1",
                "Events of Default",
                [
                    Para(
                        "Each of the following shall constitute an Event of Default: (a) the Borrower fails to "
                        "pay any principal when due, or any interest or fee within three Business Days after "
                        "it is due; (b) the Borrower fails to observe any covenant contained in Article 6 or "
                        "Article 7; (c) the Borrower fails to observe any other covenant in any Loan Document "
                        "and such failure continues for 30 days after notice from the Lender; (d) any "
                        "representation or warranty proves to have been incorrect in any material respect when "
                        "made; or (e) the Borrower becomes insolvent or becomes the subject of any bankruptcy "
                        "or insolvency proceeding."
                    )
                ],
            ),
            Section(
                "8.2",
                "Remedies",
                [
                    Para(
                        "Upon the occurrence and during the continuance of an Event of Default, the Lender may "
                        "terminate its commitments, declare all Obligations immediately due and payable, and "
                        "exercise all rights and remedies available to it under the Loan Documents and "
                        "applicable law."
                    )
                ],
            ),
        ],
    )
    article9 = Article(
        "9",
        "MISCELLANEOUS",
        [
            Section(
                "9.1",
                "Amendments and Waivers",
                [
                    Para(
                        "No amendment or waiver of any provision of this Agreement shall be effective unless "
                        "it is in writing and signed by the Lender and the Borrower, and then such amendment "
                        "or waiver shall be effective only in the specific instance and for the specific "
                        "purpose for which it is given."
                    )
                ],
            ),
            Section(
                "9.2",
                "Notices",
                [
                    Para(
                        "All notices under this Agreement shall be in writing and shall be delivered by hand, "
                        "by nationally recognized overnight courier or by electronic mail to the addresses set "
                        "forth on the signature pages."
                    )
                ],
            ),
            Section(
                "9.3",
                "Expenses and Indemnity",
                [
                    Para(
                        "The Borrower shall pay all reasonable out-of-pocket expenses of the Lender incurred "
                        "in connection with the preparation, administration and enforcement of the Loan "
                        "Documents, and shall indemnify the Lender against all losses arising out of the Loan "
                        "Documents, except to the extent resulting from the gross negligence or willful "
                        "misconduct of the Lender."
                    )
                ],
            ),
            Section(
                "9.4",
                "Governing Law and Jury Waiver",
                [
                    Para(
                        f"This Agreement shall be governed by the laws of the State of {STATE_NAMES[spec.state]}. Each party "
                        "irrevocably waives, to the fullest extent permitted by law, any right to trial by "
                        "jury in any proceeding arising out of or relating to any Loan Document."
                    )
                ],
            ),
            Section(
                "9.5",
                "Counterparts and Entire Agreement",
                [
                    Para(
                        "This Agreement may be executed in counterparts, each of which shall be an original. "
                        "The Loan Documents constitute the entire agreement of the parties with respect to "
                        "their subject matter and supersede all prior agreements and understandings."
                    )
                ],
            ),
        ],
    )
    doc.preamble = [
        Para(
            f"This CREDIT AGREEMENT is entered into as of {long_date(spec.closing_date)} between "
            f"{spec.name}, a {STATE_NAMES[spec.state]} {_form_words(spec)} (the \"Borrower\"), and {LENDER} (the \"Lender\")."
        ),
        Para(
            "The Borrower has requested that the Lender extend credit to the Borrower, and the Lender is "
            "willing to do so on the terms and subject to the conditions set forth in this Agreement. "
            "Accordingly, the parties agree as follows."
        ),
    ]
    doc.articles = [article1, article2, article3, article4, article5, article6, article7, article8, article9]
    doc.exhibits = _exhibits(spec, covenants_json, facilities, term_payment, bb_terms is not None)

    for requirement in reporting_json:
        requirement["citation"] = {
            "field": f"reporting_requirements.{requirement['id']}",
            "_anchor": ("credit-agreement", f"rep.{requirement['id']}"),
        }
    terms_v1 = {
        "definitions": definitions,
        "covenants": covenants_json,
        "reporting_requirements": reporting_json,
        "borrowing_base": bb_json,
    }
    facility_id = facilities[0]["id"]
    approved_at = spec.closing_date + timedelta(days=6)
    version1 = {
        "id": f"tv-{bid}-1",
        "facility_id": facility_id,
        "version": 1,
        "status": "approved",
        "effective_from": spec.closing_date.isoformat(),
        "effective_to": None,
        "prepared_by": spec.analyst,
        "approved_by": CREDIT_OFFICERS[len(bid) % 2],
        "approved_at": approved_at.isoformat(),
        "warnings": [],
        "source_documents": [f"{bid}.credit-agreement"],
        "terms": terms_v1,
    }
    versions = [version1]
    amendments: list[LegalDoc] = []
    unapproved = None
    clause_index = [{"field": f, "_anchor": ("credit-agreement", a)} for f, a in clause_index_anchors]

    if bid == APPROVED_AMENDMENT_BORROWER:
        amendment, version2 = _approved_amendment(spec, version1, tightened_leverage)
        amendments.append(amendment)
        versions.append(version2)
    if spec.scenario == "unapproved_amendment":
        amendment, unapproved = _unapproved_amendment(spec, cap)
        amendments.append(amendment)
    return TermsBuild(doc, amendments, versions, clause_index, unapproved, facilities, step_details)


def _rounding(cov: CovenantSpec) -> dict:
    return {"dp": 2 if cov.unit == "ratio" else 0, "mode": "half_up"}


def _requirement(rid: str, document_type: str, frequency: str, due_days: int, quality: str | None) -> dict:
    return {
        "id": rid,
        "document_type": document_type,
        "frequency": frequency,
        "due_days_after_period_end": due_days,
        "quality": quality,
    }


def _form_words(spec: BorrowerSpec) -> str:
    return "limited liability company" if spec.legal_form == "llc" else "corporation"


def _exhibits(spec, covenants_json, facilities, term_payment, has_bb) -> list:
    rows = [["Covenant", "Section", "Required", "Actual", "In compliance"]]
    for i, cov in enumerate(covenants_json, start=1):
        rows.append([cov["name"], f"6.{i}", "________", "________", "Yes / No"])
    exhibits = [
        (
            "EXHIBIT A - FORM OF COMPLIANCE CERTIFICATE",
            [
                Para(
                    f"The undersigned, the chief financial officer of {spec.name} (the \"Borrower\"), certifies "
                    f"to {LENDER} (the \"Lender\") pursuant to Section 5.1(c) of the Credit Agreement that the "
                    "financial statements delivered with this certificate fairly present the financial "
                    "condition of the Borrower, that no Default or Event of Default has occurred and is "
                    "continuing except as described in an attachment to this certificate, and that the "
                    "calculations set forth below are true and correct."
                ),
                Para(
                    "Attach the detailed calculation of each financial covenant, showing each component and "
                    "the source of each figure in the financial statements."
                ),
            ],
            rows,
        )
    ]
    if has_bb:
        exhibits.append(
            (
                "EXHIBIT B - FORM OF BORROWING BASE CERTIFICATE",
                [
                    Para(
                        "The Borrowing Base Certificate shall set forth, as of the last day of the month: "
                        "gross accounts receivable; each category of ineligible accounts; Eligible Accounts; "
                        "gross inventory; ineligible inventory; Eligible Inventory; Reserves; the Borrowing "
                        "Base; the Revolving Commitment; the outstanding Revolving Loans and letters of "
                        "credit; and the resulting availability. An accounts receivable aging by account "
                        "debtor and an inventory report by category shall be attached."
                    )
                ],
                None,
            )
        )
    schedule = [["Facility", "Amount", "Maturity"]]
    for facility in facilities:
        schedule.append([facility["name"], money(facility["commitment"]), long_date(date.fromisoformat(facility["maturity_date"]))])
    notes = [Para("The commitments and original principal amounts of the credit facilities are as follows.")]
    if term_payment > 0:
        notes.append(
            Para(
                f"The Term Loan is repayable in quarterly installments of {money(term_payment)} on the last "
                "day of March, June, September and December of each year."
            )
        )
    exhibits.append(("SCHEDULE 1 - CREDIT FACILITIES", notes, schedule))
    return exhibits


def _amendment_shell(spec: BorrowerSpec, number: str, doc_date: date, slug: str) -> LegalDoc:
    doc = LegalDoc(
        slug=slug,
        doc_type="amendment",
        title=f"{number} AMENDMENT TO CREDIT AGREEMENT",
        subtitle=f"dated as of {long_date(doc_date)}",
        doc_date=doc_date,
        borrower_name=spec.name,
        preamble=[
            Para(
                f"This {number} AMENDMENT TO CREDIT AGREEMENT (this \"Amendment\") is entered into as of "
                f"{long_date(doc_date)} between {spec.name} (the \"Borrower\") and {LENDER} (the \"Lender\")."
            ),
            Para(
                f"The Borrower and the Lender are parties to a Credit Agreement dated as of "
                f"{long_date(spec.closing_date)} (the \"Credit Agreement\"). The Borrower has requested that "
                "the Lender amend the Credit Agreement in certain respects, and the Lender is willing to do "
                "so on the terms set forth in this Amendment. Capitalized terms used and not defined in this "
                "Amendment have the meanings given to them in the Credit Agreement."
            ),
        ],
        articles=[],
        signature_blocks=[
            (spec.name, spec.cfo, "Chief Financial Officer"),
            (LENDER, spec.relationship_manager, "Senior Vice President"),
        ],
        toc=False,
    )
    return doc


def _amendment_boilerplate(first: int) -> list[Section]:
    return [
        Section(
            str(first),
            "Conditions to Effectiveness",
            [
                Para(
                    "This Amendment shall become effective upon receipt by the Lender of counterparts of this "
                    "Amendment executed by the Borrower and the Lender and payment by the Borrower of the "
                    "amendment fee and the reasonable expenses of the Lender."
                )
            ],
        ),
        Section(
            str(first + 1),
            "Representations and Warranties",
            [
                Para(
                    "The Borrower represents and warrants that, after giving effect to this Amendment, the "
                    "representations and warranties in the Credit Agreement are true and correct in all "
                    "material respects and no Default or Event of Default has occurred and is continuing."
                )
            ],
        ),
        Section(
            str(first + 2),
            "Reaffirmation and No Other Changes",
            [
                Para(
                    "Except as expressly amended by this Amendment, the Credit Agreement and the other Loan "
                    "Documents remain in full force and effect and are ratified and confirmed. This Amendment "
                    "is a Loan Document. This Amendment shall be governed by the law that governs the Credit "
                    "Agreement and may be executed in counterparts."
                )
            ],
        ),
    ]


def _approved_amendment(spec: BorrowerSpec, version1: dict, tightened: str) -> tuple[LegalDoc, dict]:
    """Marlowe Ridge: the leverage threshold tightened from 2025-07-01, properly approved."""
    doc_date = APPROVED_AMENDMENT_EFFECTIVE - timedelta(days=5)
    doc = _amendment_shell(spec, "FIRST", doc_date, "amendment-1")
    terms2 = copy.deepcopy(version1["terms"])
    cov = next(c for c in terms2["covenants"] if c["id"] == "total_leverage")
    index = terms2["covenants"].index(cov) + 1
    spec_cov = next(c for c in spec.covenants if c.id == "total_leverage")
    cov["test"] = {**cov["test"], "threshold": tightened}
    new_sentence = covenant_threshold_sentence(spec_cov, tightened)
    quote = doc.cite("cov.total_leverage.threshold", "1", new_sentence)
    effective = doc.cite(
        "effective",
        "2",
        f"The amendment set forth in Section 1 shall be effective as of "
        f"{long_date(APPROVED_AMENDMENT_EFFECTIVE)} and shall apply to each fiscal quarter ending on or "
        "after that date.",
    )
    doc.articles = [
        Article(
            "",
            "",
            [
                Section(
                    "1",
                    f"Amendment to Section 6.{index}",
                    [
                        Para(
                            f"Section 6.{index} of the Credit Agreement is hereby amended and restated in its "
                            "entirety to read as follows:"
                        ),
                        Para(quote, ("cov.total_leverage.threshold",), "indent"),
                    ],
                ),
                Section("2", "Effective Date", [Para(effective, ("effective",))]),
                *_amendment_boilerplate(3),
            ],
        )
    ]
    cov["citations"] = [
        {"field": "test.threshold", "_anchor": ("amendment-1", "cov.total_leverage.threshold")},
        cov["citations"][1],
    ]
    day_before = APPROVED_AMENDMENT_EFFECTIVE - timedelta(days=1)
    version1["status"] = "superseded"
    version1["effective_to"] = day_before.isoformat()
    version2 = {
        **version1,
        "id": f"tv-{spec.id}-2",
        "version": 2,
        "status": "approved",
        "effective_from": APPROVED_AMENDMENT_EFFECTIVE.isoformat(),
        "effective_to": None,
        "approved_at": (doc_date + timedelta(days=3)).isoformat(),
        "source_documents": [f"{spec.id}.credit-agreement", f"{spec.id}.amendment-1"],
        "terms": terms2,
    }
    return doc, version2


def _unapproved_amendment(spec: BorrowerSpec, cap: dict) -> tuple[LegalDoc, dict]:
    """A signed amendment that raises the add-back cap. It is on file and is never approved into terms."""
    doc_date = date(2026, 8, 21)
    effective_date = date(2026, 7, 1)
    doc = _amendment_shell(spec, "FIRST", doc_date, "amendment-1")
    new_cap = {"type": "amount", "value": UNAPPROVED_AMENDMENT_CAP}
    quote = doc.cite("def.adjusted_ebitda", "1", adjusted_ebitda_sentence(new_cap))
    effective = doc.cite(
        "effective",
        "2",
        f"The amendment set forth in Section 1 shall be effective as of {long_date(effective_date)} and "
        "shall apply to the fiscal quarter ending September 30, 2026 and each fiscal quarter thereafter.",
    )
    doc.articles = [
        Article(
            "",
            "",
            [
                Section(
                    "1",
                    "Amendment to Section 1.1",
                    [
                        Para(
                            'Section 1.1 of the Credit Agreement is hereby amended by deleting the definition '
                            'of "Adjusted EBITDA" in its entirety and replacing it with the following:'
                        ),
                        Para(quote, ("def.adjusted_ebitda",), "indent"),
                    ],
                ),
                Section("2", "Effective Date", [Para(effective, ("effective",))]),
                *_amendment_boilerplate(3),
            ],
        )
    ]
    details = {
        "document_id": f"{spec.id}.amendment-1",
        "document_date": doc_date.isoformat(),
        "effective_from": effective_date.isoformat(),
        "field": "definitions.ebitda.addbacks.restructuring.cap",
        "approved_cap": cap["value"],
        "amended_cap": UNAPPROVED_AMENDMENT_CAP,
        "_anchor": ("amendment-1", "def.adjusted_ebitda"),
    }
    return doc, details

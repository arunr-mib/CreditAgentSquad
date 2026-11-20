"""Terms for an innovation client: the venture loan agreement (as a LegalDoc), the terms version with citation
placeholders, and the facility. The approved plan figures are terms data entered by a person (spec 5), so the
`revenue_vs_plan` covenant carries them in its parameters and the agreement only names the 80 percent floor."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from synthetic.books.innovation.expected import DUE_DAYS
from synthetic.books.innovation.model import MONTHS
from synthetic.books.innovation.roster import LENDER, ClientSpec
from synthetic.scenarios import CREDIT_OFFICERS
from synthetic.terms import Article, LegalDoc, Para, Section, long_date, money

D = Decimal
SLUG = "credit-agreement"
FERROGATE = "ferrogate-cloud"
PLAN_MONTHS = MONTHS[4:]
DSCR_EFFECTIVE = date(2026, 5, 31)  # Ferrogate adds a trailing-twelve-month DSCR covenant from this month end
DSCR_MIN = "1.25"


@dataclass
class ClientTerms:
    agreement: LegalDoc
    version: dict  # citations still carry "_anchor": (slug, anchor)
    facility: dict
    clause_index: list[dict]
    later_versions: tuple[dict, ...] = ()

    def versions(self) -> list[dict]:
        """Every terms version in order. When a later version exists the first is superseded the day before it."""
        if not self.later_versions:
            return [self.version]
        first = {**deepcopy(self.version), "status": "superseded",
                 "effective_to": (date.fromisoformat(self.later_versions[0]["effective_from"]) - timedelta(days=1)).isoformat()}  # fmt: skip
        return [first, *deepcopy(self.later_versions)]


def build_agreement(spec: ClientSpec) -> LegalDoc:
    """The agreement text. Every cited sentence is kept whole on one page, and the page is recorded at render time."""
    doc = LegalDoc(
        slug=SLUG, doc_type="credit_agreement", title="VENTURE LOAN AND SECURITY AGREEMENT",
        subtitle=f"Dated as of {long_date(spec.closing_date)}", doc_date=spec.closing_date,
        borrower_name=spec.name, preamble=[], articles=[], signature_blocks=[], toc=True,
    )  # fmt: skip
    cite = doc.cite
    doc.preamble = [
        Para(
            f"This Venture Loan and Security Agreement is entered into as of {long_date(spec.closing_date)} between "
            f"{spec.name}, a Delaware corporation (the Borrower), and {LENDER} (the Lender)."
        )
    ]
    doc.articles = [
        Article(
            "1",
            "DEFINITIONS",
            [
                Section(
                    "1.1",
                    "Defined Terms",
                    [
                        Para(
                            cite(
                                "def_unrestricted_cash",
                                "1.1",
                                '"Unrestricted Cash" means cash held in deposit accounts of the Borrower with the Lender, '
                                "excluding any cash that is pledged, escrowed or otherwise restricted.",
                            ),
                            ("def_unrestricted_cash",),
                        ),
                        Para(
                            cite(
                                "def_net_burn",
                                "1.1",
                                '"Net Burn" means, for any month, capital expenditures plus capitalized software development '
                                "spend, less net cash from operating activities, and excludes the proceeds of equity and debt "
                                "financing.",
                            ),
                            ("def_net_burn",),
                        ),
                        Para(
                            cite(
                                "def_runway",
                                "1.1",
                                '"Runway" means Unrestricted Cash divided by the average monthly Net Burn for the three months '
                                "then ended; if that average is zero or negative, Runway is not meaningful and the covenant is "
                                "satisfied.",
                            ),
                            ("def_runway",),
                        ),
                        *(
                            [
                                Para(
                                    cite(
                                        "def_dscr",
                                        "1.1",
                                        '"Debt Service Coverage Ratio" means, for any period of twelve consecutive months, the ratio '
                                        "of (a) earnings before interest, taxes, depreciation and amortization for such period to "
                                        "(b) the sum of interest expense and scheduled principal payments for such period.",
                                    ),
                                    ("def_dscr",),
                                )
                            ]
                            if spec.id == FERROGATE
                            else []
                        ),
                        Para(
                            '"Approved Plan" means the monthly revenue plan approved by the Lender and recorded in the Lender\'s '
                            "credit file, as updated by written agreement of the Lender and the Borrower."
                        ),
                    ],
                )
            ],
        ),  # fmt: skip
        Article(
            "2",
            "THE LOAN",
            [
                Section(
                    "2.1",
                    "Venture Term Loan",
                    [
                        Para(
                            cite(
                                "facility",
                                "2.1",
                                f"The Lender has made a venture term loan to the Borrower in the aggregate principal amount of "
                                f"{money(spec.venture_debt)}, bearing interest at the rate of Prime plus 3.50 percent.",
                            ),
                            ("facility",),
                        )
                    ],
                )
            ],
        ),  # fmt: skip
        Article(
            "5",
            "REPORTING",
            [
                Section(
                    "5.1",
                    "Financial Statements and Certificates",
                    [
                        Para(
                            cite(
                                "rep_annual",
                                "5.1(a)",
                                "Within 180 days after the end of each fiscal year, the Borrower shall deliver audited financial "
                                "statements with an unqualified opinion.",
                            ),
                            ("rep_annual",),
                        ),
                        Para(
                            cite(
                                "rep_monthly",
                                "5.1(b)",
                                "Within 30 days after the end of each month, the Borrower shall deliver management financial "
                                "statements for that month and the year to date.",
                            ),
                            ("rep_monthly",),
                        ),
                        Para(
                            cite(
                                "rep_certificate",
                                "5.1(c)",
                                "Within 30 days after the end of each month, the Borrower shall deliver a compliance certificate "
                                "signed by its chief financial officer.",
                            ),
                            ("rep_certificate",),
                        ),
                        Para(
                            cite(
                                "rep_mrr",
                                "5.1(d)",
                                "Within 15 days after the end of each month, the Borrower shall deliver a monthly recurring "
                                "revenue report.",
                            ),
                            ("rep_mrr",),
                        ),
                        Para(
                            cite(
                                "rep_bank",
                                "5.1(e)",
                                "Within 7 days after the end of each month, the Borrower shall deliver its bank account "
                                "statements for that month.",
                            ),
                            ("rep_bank",),
                        ),
                    ],
                )
            ],
        ),  # fmt: skip
        Article(
            "6",
            "FINANCIAL COVENANTS",
            [
                Section(
                    "6.1",
                    "Minimum Unrestricted Cash",
                    [
                        Para(
                            cite(
                                "cov_cash",
                                "6.1",
                                f"Unrestricted Cash shall not be less than {money(spec.min_cash)} at any month end.",
                            ),
                            ("cov_cash",),
                        )
                    ],
                ),
                Section(
                    "6.2",
                    "Minimum Runway",
                    [
                        Para(
                            cite(
                                "cov_runway",
                                "6.2",
                                f"Runway shall not be less than {spec.min_rml} months at any month end.",
                            ),
                            ("cov_runway",),
                        )
                    ],
                ),
                Section(
                    "6.3",
                    "Revenue to Plan",
                    [
                        Para(
                            cite(
                                "cov_plan",
                                "6.3",
                                "Revenue for any three-month period shall not be less than 80% of the Approved Plan for the same "
                                "three months.",
                            ),
                            ("cov_plan",),
                        )
                    ],
                ),
            ],
        ),  # fmt: skip
    ]
    if spec.id == FERROGATE:
        doc.articles[-1].sections.append(
            Section(
                "6.4",
                "Debt Service Coverage",
                [
                    Para(
                        cite(
                            "cov_dscr",
                            "6.4",
                            f"From and after {long_date(DSCR_EFFECTIVE)}, the Borrower shall not permit the Debt Service Coverage "
                            "Ratio, measured as of the last day of each month for the period of twelve consecutive months then ended, "
                            f"to be less than {DSCR_MIN} to 1.00.",
                        ),
                        ("cov_dscr",),
                    )
                ],
            )
        )
    doc.signature_blocks = [(spec.name, spec.cfo, "Chief Financial Officer"),
                            (LENDER, CREDIT_OFFICERS[len(spec.id) % 2], "Credit Officer")]  # fmt: skip
    return doc


def _requirement(
    rid: str, document_type: str, frequency: str, due_days: int, quality: str | None, anchor: str
) -> dict:
    return {
        "id": rid, "document_type": document_type, "frequency": frequency, "due_days_after_period_end": due_days,
        "quality": quality, "citation": {"field": f"reporting_requirements.{rid}", "_anchor": (SLUG, anchor)},
    }  # fmt: skip


def covenants_json(spec: ClientSpec, plan: dict[date, int]) -> list[dict]:
    def covenant(cid, name, params, operator_threshold, unit, basis, dp, anchors) -> dict:
        return {
            "id": cid, "name": name, "archetype": cid, "params": params,
            "test": {"operator": ">=", "threshold": operator_threshold, "steps": [], "unit": unit},
            "measurement": {"basis": basis, "frequency": "monthly"}, "rounding": {"dp": dp, "mode": "half_up"},
            "citations": [{"field": field, "_anchor": (SLUG, anchor)} for field, anchor in anchors],
        }  # fmt: skip

    return [
        covenant("min_unrestricted_cash", "Minimum Unrestricted Cash", {}, str(spec.min_cash), "usd", "point", 0,
                 (("test.threshold", "cov_cash"), ("definition", "def_unrestricted_cash"))),
        covenant("min_runway_months", "Minimum Runway", {}, spec.min_rml, "months", "t3m", 1,
                 (("test.threshold", "cov_runway"), ("definition", "def_runway"), ("definition", "def_net_burn"))),
        covenant("revenue_vs_plan", "Revenue to Plan",
                 {"metric": "revenue", "plan": [{"period_end": m.isoformat(), "amount": str(plan[m])} for m in PLAN_MONTHS]},
                 spec.plan_floor, "pct", "t3m", 4, (("test.threshold", "cov_plan"),)),
    ]  # fmt: skip


def dscr_covenant() -> dict:
    """The legacy book's coverage shape (params and ttm basis); on a venture template the engine measures vc_ebitda."""
    return {
        "id": "dscr", "name": "Debt Service Coverage Ratio", "archetype": "coverage",
        "params": {"numerator_base": "ebitda", "deductions": [], "denominator": ["interest_expense", "scheduled_principal"]},
        "test": {"operator": ">=", "threshold": DSCR_MIN, "steps": [], "unit": "ratio"},
        "measurement": {"basis": "ttm", "frequency": "monthly"}, "rounding": {"dp": 2, "mode": "half_up"},
        "citations": [{"field": "test.threshold", "_anchor": (SLUG, "cov_dscr")},
                      {"field": "definition", "_anchor": (SLUG, "def_dscr")}],
    }  # fmt: skip


def build_terms(spec: ClientSpec, plan: dict[date, int]) -> ClientTerms:
    agreement = build_agreement(spec)
    facility_id = f"{spec.id}-vl"
    facility = {
        "id": facility_id, "borrower_id": spec.id, "type": "term_loan", "name": "Venture Term Loan",
        "commitment": str(spec.venture_debt), "original_amount": str(spec.venture_debt),
        "closing_date": spec.closing_date.isoformat(),
        "maturity_date": (spec.closing_date + timedelta(days=4 * 365)).isoformat(),
        "interest_rate": "Prime + 3.50%", "borrowing_base": False,
    }  # fmt: skip
    terms = {
        "definitions": {},
        "covenants": covenants_json(spec, plan),
        "reporting_requirements": [
            _requirement("monthly_financials", "monthly_financials", "monthly", DUE_DAYS["monthly_financials"],
                         "internal", "rep_monthly"),
            _requirement("compliance_certificate", "compliance_certificate", "monthly",
                         DUE_DAYS["compliance_certificate"], None, "rep_certificate"),
            _requirement("mrr_report", "mrr_report", "monthly", DUE_DAYS["mrr_report"], None, "rep_mrr"),
            _requirement("bank_statements", "bank_statement", "monthly", DUE_DAYS["bank_statement"], None, "rep_bank"),
            _requirement("annual_statements", "annual_financial_statements", "annual", 180, "audited", "rep_annual"),
        ],
        "borrowing_base": None,
    }  # fmt: skip
    version = {
        "id": f"tv-{spec.id}-1", "facility_id": facility_id, "version": 1, "status": "approved",
        "effective_from": spec.closing_date.isoformat(), "effective_to": None, "prepared_by": spec.analyst,
        "approved_by": CREDIT_OFFICERS[len(spec.id) % 2],
        "approved_at": (spec.closing_date + timedelta(days=6)).isoformat(), "warnings": [],
        "source_documents": [f"{spec.id}.{SLUG}"], "terms": terms,
    }  # fmt: skip
    clause_index = [{"field": "facilities.venture_term_loan.commitment", "_anchor": (SLUG, "facility")}]
    later: tuple[dict, ...] = ()
    if spec.id == FERROGATE:
        version2 = {
            **version, "id": f"tv-{spec.id}-2", "version": 2, "effective_from": DSCR_EFFECTIVE.isoformat(),
            "approved_at": (DSCR_EFFECTIVE - timedelta(days=20)).isoformat(),
            "terms": {**deepcopy(terms), "covenants": [*deepcopy(terms["covenants"]), dscr_covenant()]},
        }  # fmt: skip
        later = (version2,)
    return ClientTerms(agreement, version, facility, clause_index, later)

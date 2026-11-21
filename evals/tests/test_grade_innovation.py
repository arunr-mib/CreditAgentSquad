from evals.book import BOOKS, load_book
from evals.grade import STAGE_OF_ITEM, Truth

PACKS = {"annual_financial_statements", "interim_financial_statements", "monthly_financials"}


def test_statements_are_the_periods_financial_pack_never_a_bank_statement():
    for borrower in load_book(BOOKS["innovation"]):
        truth = Truth(borrower)
        if truth.statements is not None:
            assert truth.statements["type"] in PACKS, borrower.code


def test_every_innovation_client_with_a_current_pack_has_it_selected():
    book = load_book(BOOKS["innovation"], ["tidewell-medical", "stripple-tech"])
    tide = Truth(book.get("tidewell-medical"))
    assert tide.statements["type"] == "monthly_financials"
    assert tide.statements["period_end"] == "2026-10-31"


def test_a_not_meaningful_runway_has_no_expected_numeric_certificate_value():
    ferrogate = Truth(load_book(BOOKS["innovation"], ["ferrogate-cloud"]).get("ferrogate-cloud"))
    expected = ferrogate.expected_facts()  # must not raise on Decimal(None)
    assert "cert.min_runway_months.value" not in expected
    assert "cert.min_runway_months.threshold" in expected
    assert "cert.min_unrestricted_cash.value" in expected


def test_funding_and_cash_exceptions_map_to_stages():
    assert STAGE_OF_ITEM["funding_slipped"] == "signals"
    assert STAGE_OF_ITEM["cash"] == "covenant_testing"



def test_expected_facts_include_mrr_and_bank_figures_for_a_monthly_client():
    book = load_book(BOOKS["innovation"], ["tidewell-medical"])
    expected = Truth(book.get("tidewell-medical")).expected_facts()
    assert expected["saas.mrr"][2] == "mrr-2026-10-31.pdf"
    assert expected["bank.cash_unrestricted"][0] == 4300000 and expected["bank.cash_restricted"][0] == 1100000


def test_figures_the_book_says_are_held_for_a_person_are_not_expected_as_stored_facts():
    """Stripple's pack prints a line the template does not know and a capitalised-software figure that may be
    the wrong measure; the key expects both held, so they are not expected extractions, and the documents
    after spreading (the certificate) are not read while the cycle rests there. MRR and bank still are."""
    stripple = Truth(load_book(BOOKS["innovation"], ["stripple-tech"]).get("stripple-tech"))
    expected = stripple.expected_facts()
    assert stripple.held == {"bs.deferred_revenue_current", "bs.capitalised_software", "cf.capitalised_software_spend"}
    assert stripple.held.isdisjoint(expected)
    assert "bs.cash_unrestricted" in expected and "saas.mrr" in expected
    assert not [k for k in expected if k.startswith("cert.")]
    tide = Truth(load_book(BOOKS["innovation"], ["tidewell-medical"]).get("tidewell-medical"))
    assert tide.held == set() and any(k.startswith("cert.") for k in tide.expected_facts())

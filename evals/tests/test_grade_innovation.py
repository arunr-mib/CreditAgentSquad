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


def test_a_certificate_figure_stored_for_a_held_figure_borrower_is_graded_not_ungraded():
    """Stripple's cycle rests at spreading, so the certificate is not expected; a certificate or held figure that
    is stored anyway still has a true value, so a wrong one is an invented-number and never 'ungraded'."""
    stripple = Truth(load_book(BOOKS["innovation"], ["stripple-tech"]).get("stripple-tech"))
    end = stripple.end.isoformat()
    cert_key = next(iter(k for k in stripple.expected_facts(every_figure=True) if k.startswith("cert.")))
    assert cert_key not in stripple.expected_facts()
    fact = {"key": cert_key, "period_end": end}
    assert stripple.value_for(fact) == stripple.expected_facts(every_figure=True)[cert_key][0]
    held = next(iter(stripple.held))
    assert stripple.value_for({"key": held, "period_end": end}) is not None


def test_a_stored_runway_metric_for_a_not_meaningful_period_is_an_invented_number(engine, file_store):
    """Ferrogate is cash-flow positive: runway has no figure, so a metric.rml (or a signal runway fact) stored
    for the period is invented, however it got there."""
    import copy

    from evals.grade import grade_borrower
    from evals.run import run_pass
    from evals.standin import StandInReader

    book = load_book(BOOKS["innovation"], ["ferrogate-cloud"])
    recording = run_pass(engine, book, StandInReader(book), decide=True)["ferrogate-cloud"]
    assert grade_borrower(book.get("ferrogate-cloud"), recording)["failures"] == []
    end = book.get("ferrogate-cloud").current_period.isoformat()
    template = recording["facts"][0]
    for key in ("metric.rml", "signal.runway_below_watch.rml"):
        tampered = copy.deepcopy(recording)
        tampered["facts"].append({**template, "key": key, "period_end": end, "value": "-3.5", "status": "verified"})
        graded = grade_borrower(book.get("ferrogate-cloud"), tampered)
        assert [f["name"] for f in graded["failures"]] == ["invented-number"], key
    # a runway fact for another period is not this period's figure
    other = copy.deepcopy(recording)
    other["facts"].append({**template, "key": "metric.rml", "period_end": "2025-01-31", "value": "9", "status": "verified"})
    assert grade_borrower(book.get("ferrogate-cloud"), other)["failures"] == []

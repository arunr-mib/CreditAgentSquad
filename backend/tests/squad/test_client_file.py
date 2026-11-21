from datetime import date
from decimal import Decimal

from app.domain.facts_service import add_fact
from app.domain.workflow import open_cycle
from app.squad.client_file import measure_series

from .conftest import sign_in

ENDS = [date(2026, 8, 31), date(2026, 9, 30), date(2026, 10, 31)]


def _periods(db, borrower):
    for end in ENDS:
        open_cycle(db, borrower_id=borrower.id, period_end=end, months=1, cycle_type="monthly")


def _facility(db, borrower):
    from app.domain.credit import Facility
    f = Facility(borrower_id=borrower.id, code=f"{borrower.code}-TL", name="Term loan", facility_type="term_loan",
                 commitment=Decimal("1000000"))
    db.add(f)
    db.flush()
    return f


def _test(db, borrower, facility, covenant, end, *, value_fact=None, note=None, superseded=False):
    from app.domain.monitoring import CovenantTest
    t = CovenantTest(borrower_id=borrower.id, facility_id=facility.id, covenant_id=covenant, covenant_name=covenant,
                     period_end=end, value_fact_id=value_fact.id if value_fact else None,
                     value=value_fact.value if value_fact else None, outcome="pass" if value_fact else "not_meaningful",
                     note=note, superseded=superseded)
    db.add(t)
    db.flush()
    return t


def test_runway_comes_from_the_stored_covenant_test_even_without_metric_rml(db, world):
    b = world["borrower"]  # vc-1
    _periods(db, b)
    fac = _facility(db, b)
    fact = add_fact(db, borrower_id=b.id, key="cov.min_runway_months.value", period_end=ENDS[0], months=0,
                    value=Decimal("13.0"), kind="seeded", unit="months", status="verified")
    _test(db, b, fac, "min_runway_months", ENDS[0], value_fact=fact)
    _test(db, b, fac, "min_runway_months", ENDS[1], note="not_meaningful_cash_flow_positive")
    series = measure_series(db, b)
    assert series["kind"] == "rml" and series["label"] == "Runway (months)"
    assert [p["period_end"] for p in series["points"]] == [e.isoformat() for e in ENDS]
    assert series["points"][0]["fact"]["id"] == str(fact.id) and series["points"][0]["note"] is None
    assert series["points"][1]["fact"] is None and series["points"][1]["note"] == "Not meaningful: cash-flow positive"
    assert series["points"][2]["fact"] is None and series["points"][2]["note"] == "Not measured"  # no test at all


def test_only_the_runway_covenant_counts_for_runway(db, world):
    b = world["borrower"]
    _periods(db, b)
    fac = _facility(db, b)
    other = add_fact(db, borrower_id=b.id, key="cov.revenue_vs_plan.value", period_end=ENDS[2], months=0,
                     value=Decimal("1.05"), kind="seeded", unit="pct", status="verified")
    _test(db, b, fac, "revenue_vs_plan", ENDS[2], value_fact=other)
    _test(db, b, fac, "min_runway_months", ENDS[2], note="not_meaningful_cash_flow_positive")
    point = measure_series(db, b)["points"][2]
    assert point["fact"] is None and point["note"] == "Not meaningful: cash-flow positive"


def test_a_superseded_runway_test_is_not_read(db, world):
    b = world["borrower"]
    _periods(db, b)
    fac = _facility(db, b)
    old = add_fact(db, borrower_id=b.id, key="cov.min_runway_months.value", period_end=ENDS[2], months=0,
                   value=Decimal("9.0"), kind="seeded", unit="months", status="verified")
    _test(db, b, fac, "min_runway_months", ENDS[2], value_fact=old, superseded=True)
    assert measure_series(db, b)["points"][2]["fact"] is None


def test_headroom_picks_the_tightest_headroom_of_live_tests(db, world):
    b = world["other"]
    b.template_id = "ci-1"
    _periods(db, b)
    fac = _facility(db, b)
    loose = add_fact(db, borrower_id=b.id, key="cov.leverage.headroom_pct", period_end=ENDS[2], months=0,
                     value=Decimal("0.31"), kind="seeded", unit="pct", status="verified")
    tight = add_fact(db, borrower_id=b.id, key="cov.fccr.headroom_pct", period_end=ENDS[2], months=0,
                     value=Decimal("-0.08"), kind="seeded", unit="pct", status="verified")
    dropped = add_fact(db, borrower_id=b.id, key="cov.capex.headroom_pct", period_end=ENDS[2], months=0,
                       value=Decimal("-0.5"), kind="seeded", unit="pct", status="verified")
    _test(db, b, fac, "leverage", ENDS[2])
    _test(db, b, fac, "fccr", ENDS[2])
    _test(db, b, fac, "capex", ENDS[2], superseded=True)  # an amendment dropped it: its old headroom must not win
    series = measure_series(db, b)
    assert series["kind"] == "headroom" and series["points"][2]["fact"]["id"] == str(tight.id)
    assert str(loose.id) != str(tight.id) != str(dropped.id)
    assert series["points"][0]["note"] == "Not measured"


def test_the_browser_is_served_the_one_document_words_table(db, client, world):
    from app.squad.words import DOCUMENT_TYPE_WORDS, document_type_words
    db.commit()
    sign_in(client, "priya.raman")
    served = client.get("/api/v1/words/document-types").json()
    assert served["types"] == DOCUMENT_TYPE_WORDS and served["unclassified"] == document_type_words(None)
    assert all(document_type_words(k) == v for k, v in served["types"].items())
    from app.squad.words import NOTE_WORDS
    assert served["notes"] == NOTE_WORDS
    assert NOTE_WORDS["not_meaningful_cash_flow_positive"] == "Not meaningful: cash-flow positive"


def test_measure_endpoint(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/borrowers/{world['other'].id}/measure").json()["points"] == []
    assert client.get("/api/v1/borrowers/00000000-0000-0000-0000-000000000000/measure").status_code == 404

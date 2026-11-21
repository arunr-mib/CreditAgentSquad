from datetime import date
from decimal import Decimal

from app.domain.facts_service import add_fact
from app.domain.workflow import open_cycle
from app.squad import client_file
from app.squad.client_file import measure_series

from .conftest import sign_in

ENDS = [date(2026, 8, 31), date(2026, 9, 30), date(2026, 10, 31)]


def _periods(db, borrower):
    for end in ENDS:
        open_cycle(db, borrower_id=borrower.id, period_end=end, months=1, cycle_type="monthly")


def test_runway_points_carry_stored_facts_and_never_a_zero(db, world, monkeypatch):
    b = world["borrower"]  # vc-1
    _periods(db, b)
    # `seeded`: a `calculated` fact must name its calculation run (check constraint `calculated_has_calc`)
    fact = add_fact(db, borrower_id=b.id, key="metric.rml", period_end=ENDS[0], months=0, value=Decimal("14.2"),
                    kind="seeded", unit="count", status="verified")
    asked: list = []
    monkeypatch.setattr(client_file, "runway_not_meaningful",
                        lambda db, borrower, period_end: asked.append(period_end) or period_end == ENDS[2])
    series = measure_series(db, b)
    assert series["kind"] == "rml" and series["label"] == "Runway (months)"
    assert [p["period_end"] for p in series["points"]] == [e.isoformat() for e in ENDS]
    assert series["points"][0]["fact"]["id"] == str(fact.id) and series["points"][0]["note"] is None
    assert series["points"][1]["fact"] is None and series["points"][1]["note"] == "Not measured"
    assert series["points"][2]["fact"] is None and series["points"][2]["note"] == "Not meaningful: cash-flow positive"
    assert asked == [ENDS[2]]  # the full runway computation runs for the latest point only


def test_a_proposed_runway_is_not_shown_as_measured(db, world, monkeypatch):
    b = world["borrower"]
    _periods(db, b)
    add_fact(db, borrower_id=b.id, key="metric.rml", period_end=ENDS[2], months=0, value=Decimal("9.0"),
             kind="seeded", unit="count", status="proposed")
    monkeypatch.setattr(client_file, "runway_not_meaningful", lambda *a: False)
    assert measure_series(db, b)["points"][2]["fact"] is None


def test_headroom_picks_the_tightest_stored_headroom_per_period(db, world):
    b = world["other"]
    b.template_id = "ci-1"
    _periods(db, b)
    loose = add_fact(db, borrower_id=b.id, key="cov.leverage.headroom_pct", period_end=ENDS[2], months=0,
                     value=Decimal("0.31"), kind="seeded", unit="pct", status="verified")
    tight = add_fact(db, borrower_id=b.id, key="cov.fccr.headroom_pct", period_end=ENDS[2], months=0,
                     value=Decimal("0.04"), kind="seeded", unit="pct", status="verified")
    series = measure_series(db, b)
    assert series["kind"] == "headroom" and series["points"][2]["fact"]["id"] == str(tight.id) != str(loose.id)
    assert series["points"][0]["note"] == "Not measured"


def test_a_breached_headroom_is_the_tightest_not_missing(db, world):
    b = world["other"]
    b.template_id = "ci-1"
    _periods(db, b)
    add_fact(db, borrower_id=b.id, key="cov.leverage.headroom_pct", period_end=ENDS[2], months=0,
             value=Decimal("0.31"), kind="seeded", unit="pct", status="verified")
    breach = add_fact(db, borrower_id=b.id, key="cov.fccr.headroom_pct", period_end=ENDS[2], months=0,
                      value=Decimal("-0.08"), kind="seeded", unit="pct", status="verified")
    assert measure_series(db, b)["points"][2]["fact"]["id"] == str(breach.id)


def test_the_browser_is_served_the_one_document_words_table(db, client, world):
    from app.squad.words import DOCUMENT_TYPE_WORDS, document_type_words
    db.commit()
    sign_in(client, "priya.raman")
    served = client.get("/api/v1/words/document-types").json()
    assert served["types"] == DOCUMENT_TYPE_WORDS and served["unclassified"] == document_type_words(None)
    assert all(document_type_words(k) == v for k, v in served["types"].items())


def test_measure_endpoint(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/borrowers/{world['other'].id}/measure").json()["points"] == []
    assert client.get("/api/v1/borrowers/00000000-0000-0000-0000-000000000000/measure").status_code == 404

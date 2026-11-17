"""API behaviour an independent review found missing: each case here failed before its fix."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.api import routes_credit
from app.core.config import get_settings
from app.domain import workflow
from app.domain.credit import Borrower, Facility
from app.domain.facts_service import add_fact
from app.domain.monitoring import WorkItem
from app.domain.terms import TermsVersion
from app.seed_users import seed_users
from fastapi import HTTPException
from sqlalchemy import select

API = "/api/v1"
PERIOD = date(2026, 9, 30)


@pytest.fixture()
def world(db, client, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_users(db, password="pw")
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.", risk_rating=5)
    db.add(borrower)
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="HTD-TL", name="Term loan", facility_type="term_loan",
                        commitment=D("10000000"), origination_date=date(2024, 1, 15))
    db.add(facility)
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    db.flush()
    yield borrower, facility, cycle
    get_settings.cache_clear()


def sign_in(client, who, password="pw"):
    r = client.post(f"{API}/auth/login", json={"email": f"{who}@bankofstoic.example", "password": password})
    assert r.status_code == 200, r.text


def terms():
    return {
        "definitions": {"ebitda": {"base": "ebitda", "addbacks": []}},
        "covenants": [
            {"id": "leverage", "name": "Total Leverage Ratio", "archetype": "leverage",
             "params": {"debt": "total_debt", "ebitda": "ebitda"},
             "test": {"operator": "<=", "threshold": "3.50", "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"},
             "citations": [{"document_id": "agreement", "section": "7.12", "page": 7, "quote": "..."}]},
        ],
        "reporting_requirements": [], "borrowing_base": None,
    }


def test_terms_boarded_by_hand_are_proposed_and_need_a_second_person(client, db, world):
    _, facility, _ = world
    url = f"{API}/facilities/{facility.id}/terms"
    body = {"terms": terms(), "effective_from": "2024-01-15"}
    sign_in(client, "ruth.calloway")  # credit review prepares nothing
    assert client.post(url, json=body).status_code == 403
    sign_in(client, "li.zhang")
    assert client.post(url, json={"terms": {"covenants": "none"}, "effective_from": "2024-01-15"}).status_code == 422
    made = client.post(url, json=body)
    assert made.status_code == 201 and made.json()["status"] == "proposed"
    version = db.get(TermsVersion, made.json()["id"])
    assert version.prepared_by_type == "user" and version.status == "proposed"
    item = db.get(WorkItem, made.json()["approval_item_id"])
    assert item.item_type == "terms.approval_needed" and item.requires_second_person
    decide = f"{API}/work-items/{item.id}/decide"
    reason = {"decision": "approve", "reason": "Checked against the signed agreement."}
    assert client.post(decide, json=reason).status_code == 409  # the person who boarded them cannot approve
    sign_in(client, "omar.haddad")
    assert client.post(decide, json=reason).status_code == 200
    assert db.execute(select(TermsVersion.status).where(TermsVersion.id == version.id)).scalar_one() == "approved"


# ---- numbers typed into a request -------------------------------------------------------------

NOT_FIGURES = ["NaN", "nan", "sNaN", "Infinity", "-Infinity", "inf", "1e400", "1e-400", "0.1234567", "", "abc"]


@pytest.mark.parametrize("value", NOT_FIGURES)
def test_fact_routes_refuse_values_that_are_not_storable_figures(client, db, world, value):
    borrower, _, _ = world
    fact = add_fact(db, borrower_id=borrower.id, key="bs.cash", period_end=PERIOD, months=0, value=D("2150000"),
                    kind="seeded")
    sign_in(client, "priya.raman")
    corrected = client.post(f"{API}/facts/{fact.id}/correct", json={"value": value, "reason": "Typed."})
    assert corrected.status_code == 422, corrected.text
    entered = client.post(f"{API}/borrowers/{borrower.id}/facts", json={
        "key": "bs.inventory", "period_end": "2026-09-30", "months": 0, "value": value, "reason": "Typed."})
    assert entered.status_code == 422, entered.text
    db.expire_all()
    assert fact.status == "verified"  # nothing was superseded by a refused value


@pytest.mark.parametrize("value", NOT_FIGURES)
def test_the_route_parser_itself_refuses_them_before_any_service_is_called(value):
    """The service layer refuses NaN and Infinity too; the route must not depend on that."""
    with pytest.raises(HTTPException) as refused:
        routes_credit._decimal(value)
    assert refused.value.status_code == 422


def test_fact_routes_still_accept_ordinary_figures(client, db, world):
    borrower, _, _ = world
    sign_in(client, "priya.raman")
    for typed, stored in (("1,400,000", "1400000"), ("-0", "0"), (" 12.5 ", "12.5"), ("2e3", "2000")):
        made = client.post(f"{API}/borrowers/{borrower.id}/facts", json={
            "key": "bs.inventory", "period_end": "2026-09-30", "months": 0, "value": typed, "reason": "Keyed."})
        assert made.status_code == 201 and D(made.json()["value"]) == D(stored), made.text


def test_other_numbers_in_requests_are_refused_or_clamped_never_a_server_error(client, db, world):
    borrower, _, _ = world
    sign_in(client, "admin")
    for path in ("/ledger?limit=-5", "/ledger?limit=0", "/ledger?limit=99999999999999999999", "/agent-runs?limit=-1",
                 f"/ui/borrowers/{borrower.id}/timeline?limit=-1", "/evals/runs?limit=-1", "/ledger?before_seq=3"):
        assert client.get(API + path).status_code == 200, path
    for query in ("limit=abc", "limit=NaN", "before_seq=-1", "before_seq=0", "before_seq=99999999999999999999999"):
        assert client.get(f"{API}/ledger?{query}").status_code == 422, query
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.get(f"{API}/documents/{missing}/pages/1").status_code == 404
    for page in ("-1", "0", "99999999999999999999", "NaN"):
        assert client.get(f"{API}/documents/{missing}/pages/{page}").status_code == 422, page
        assert client.get(f"{API}/ui/documents/{missing}/pages/{page}/figures").status_code == 422, page
        assert client.get(f"{API}/ui/documents/{missing}/pages/{page}/locate?quote=x").status_code == 422, page
    schedule = {"title": "Quarterly pack", "scope": "portfolio", "cadence": "quarterly"}
    for days in (-1, 100000, 10**30):
        refused = client.post(f"{API}/package-schedules", json={**schedule, "days_after_period_end": days})
        assert refused.status_code == 422, days

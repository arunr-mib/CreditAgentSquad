"""The workspace API over a small seeded world."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.core import clock
from app.core.config import get_settings
from app.domain import workflow
from app.domain.credit import Borrower, Facility
from app.domain.facts_service import add_fact, correct_fact
from app.domain.org import User
from app.domain.work_items import raise_item
from app.seed_users import seed_users
from support.statement_pdf import build_pdf

PERIOD = date(2026, 9, 30)


@pytest.fixture()
def world(db, client, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_users(db, password="pw")
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.", risk_rating=5)
    db.add(borrower)
    db.flush()
    db.add(Facility(borrower_id=borrower.id, code="HTD-RLOC", name="Revolver", facility_type="revolver",
                    commitment=D("5000000"), has_borrowing_base=True))
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    db.flush()
    yield borrower, cycle
    get_settings.cache_clear()


def sign_in(client, who):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def test_everything_requires_sign_in(client, world):
    for path in ("/borrowers", "/work-items", "/cycles", "/calendar", "/ledger", "/agent-runs", "/signals"):
        assert client.get("/api/v1" + path).status_code == 401


def test_borrower_list_and_detail(client, db, world):
    borrower, cycle = world
    sign_in(client, "priya.raman")
    listed = client.get("/api/v1/borrowers").json()
    assert listed[0]["name"] == borrower.name and listed[0]["total_commitment"] == "5000000"
    assert listed[0]["latest_cycle"]["stage"] == "awaiting_package"
    detail = client.get(f"/api/v1/borrowers/{borrower.id}").json()
    assert detail["facilities"][0]["has_borrowing_base"] is True
    assert client.get("/api/v1/borrowers/00000000-0000-4000-8000-000000000000").status_code == 404


def test_upload_page_citations_and_file(client, db, world):
    borrower, _ = world
    sign_in(client, "ruth.calloway")  # credit review is read-only
    refused = client.post(f"/api/v1/borrowers/{borrower.id}/documents", files={"file": ("q3.pdf", build_pdf())})
    assert refused.status_code == 403
    sign_in(client, "priya.raman")
    bad = client.post(f"/api/v1/borrowers/{borrower.id}/documents", files={"file": ("x.txt", b"hello")})
    assert bad.status_code == 422
    up = client.post(f"/api/v1/borrowers/{borrower.id}/documents", files={"file": ("q3.pdf", build_pdf())})
    assert up.status_code == 201 and up.json()["page_count"] == 3 and "storage_path" not in up.json()
    doc_id = up.json()["id"]
    page = client.get(f"/api/v1/documents/{doc_id}/pages/1").json()
    assert page["has_text"] and "Net revenue" in page["text"] and page["citations"] == []
    file = client.get(f"/api/v1/documents/{doc_id}/file")
    assert file.headers["content-type"] == "application/pdf" and file.content.startswith(b"%PDF")


def test_fact_lineage_and_spread_grid(client, db, world):
    borrower, _ = world
    analyst = db.query(User).filter(User.email == "priya.raman@bankofstoic.example").one()
    seeded = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=PERIOD, months=9,
                      value=D("48250000"), kind="seeded")
    corrected = correct_fact(db, seeded, value=D("48300000"), user_id=analyst.id, reason="Credit memo reclass.")
    sign_in(client, "priya.raman")
    fact = client.get(f"/api/v1/facts/{corrected.id}").json()
    assert fact["value"] == "48300000" and fact["kind"] == "manual" and fact["reason"] == "Credit memo reclass."
    assert [h["value"] for h in fact["history"]] == ["48250000"] and fact["history"][0]["status"] == "superseded"
    grid = client.get(f"/api/v1/borrowers/{borrower.id}/spread").json()
    revenue = next(line for line in grid["lines"] if line["key"] == "is.revenue")
    assert revenue["cells"]["2026-09-30"]["value"] == "48300000" and grid["periods"] == [{"period_end": "2026-09-30", "months": 9}]


def test_work_queue_and_decision_rules(client, db, world):
    borrower, cycle = world
    preparer = db.query(User).filter(User.email == "li.zhang@bankofstoic.example").one()
    low = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="intake", item_type="intake.unclassified",
                     severity="low", title="Unfiled document", question="What is this document?",
                     allowed_decisions=["classified_by_hand"], required_permission="upload_document")
    crit = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing",
                      item_type="test.second_person", severity="critical", title="Approve commentary",
                      question="Approve the commentary for release?", allowed_decisions=["approve", "reject"],
                      required_permission="approve_terms", requires_second_person=True, prepared_by_id=str(preparer.id))
    sign_in(client, "priya.raman")
    queue = client.get("/api/v1/work-items").json()
    assert [w["id"] for w in queue] == [str(crit.id), str(low.id)] and queue[0]["borrower_name"] == borrower.name
    assert client.post(f"/api/v1/work-items/{crit.id}/decide", json={"decision": "approve"}).status_code == 403
    sign_in(client, "li.zhang")  # has the permission but prepared the terms
    assert client.post(f"/api/v1/work-items/{crit.id}/decide", json={"decision": "approve"}).status_code == 409
    sign_in(client, "helen.strand")
    assert client.post(f"/api/v1/work-items/{crit.id}/decide", json={"decision": "postpone"}).status_code == 422
    done = client.post(f"/api/v1/work-items/{crit.id}/decide", json={"decision": "approve", "reason": "Checked against the amendment."})
    assert done.status_code == 200 and done.json()["status"] == "decided"
    assert len(client.get("/api/v1/work-items").json()) == 1
    detail = client.get(f"/api/v1/cycles/{cycle.id}").json()
    assert len(detail["stages"]) == 10 and next(s for s in detail["stages"] if s["stage"] == "intake")["open_work_items"] == 1


def test_ledger_clock_and_verify(client, db, world):
    sign_in(client, "priya.raman")
    assert client.post("/api/v1/clock", json={"today": "2026-11-17"}).status_code == 403
    sign_in(client, "admin")
    assert client.post("/api/v1/clock", json={"today": "2026-11-17"}).json()["today"] == "2026-11-17"
    assert clock.today(db) == date(2026, 11, 17)
    assert client.get("/api/v1/calendar").json()["as_of"] == "2026-11-17"
    events = client.get("/api/v1/ledger", params={"action": "clock."}).json()
    assert events[0]["action"] == "clock.set" and events[0]["payload"]["to"] == "2026-11-17"
    assert client.get("/api/v1/ledger/verify").json()["ok"] is True

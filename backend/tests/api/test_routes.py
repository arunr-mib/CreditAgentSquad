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


def test_fact_confirm_correct_reject_and_manual_entry(client, db, world):
    borrower, _ = world
    proposed = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=PERIOD, months=9,
                        value=D("48250000"), kind="seeded", status="proposed")
    sign_in(client, "ruth.calloway")  # credit review cannot change figures
    assert client.post(f"/api/v1/facts/{proposed.id}/confirm").status_code == 403
    sign_in(client, "priya.raman")
    assert client.post(f"/api/v1/facts/{proposed.id}/confirm").json()["status"] == "confirmed"
    assert client.post(f"/api/v1/facts/{proposed.id}/correct", json={"value": "abc", "reason": "x"}).status_code == 422
    assert client.post(f"/api/v1/facts/{proposed.id}/correct", json={"value": "48,300,000", "reason": ""}).status_code == 422
    fixed = client.post(f"/api/v1/facts/{proposed.id}/correct", json={"value": "48,300,000", "reason": "Reclass."}).json()
    assert fixed["value"] == "48300000" and fixed["kind"] == "manual"
    assert client.get(f"/api/v1/facts/{proposed.id}").json()["status"] == "superseded"
    assert client.post(f"/api/v1/facts/{fixed['id']}/reject", json={"reason": ""}).status_code == 422
    base = f"/api/v1/borrowers/{borrower.id}/facts"
    entry = {"key": "bs.total_assets", "period_end": "2026-09-30", "months": 0, "value": "1", "reason": "x"}
    assert client.post(base, json=entry).status_code == 422  # totals are calculated, never entered
    entry.update(key="cf.capex", months=9, value="1,400,000", reason="Keyed from page 3.")
    made = client.post(base, json=entry)
    assert made.status_code == 201 and made.json()["value"] == "1400000" and made.json()["reason"] == "Keyed from page 3."


def test_assign_a_work_item_and_acknowledge_a_signal(client, db, world):
    from app.domain.monitoring import Signal

    borrower, cycle = world
    item = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="intake", item_type="intake.unclassified",
                      title="Unfiled document", question="What is this document?",
                      allowed_decisions=["classified_by_hand"], required_permission="upload_document")
    signal = Signal(borrower_id=borrower.id, period_end=PERIOD, rule_id="net_loss", rule_version="signals-1",
                    severity="high", basis={})
    db.add(signal)
    db.flush()
    owner = db.query(User).filter(User.email == "tomas.keller@bankofstoic.example").one()
    sign_in(client, "priya.raman")
    done = client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": str(owner.id), "due_date": "2026-11-20"})
    assert done.status_code == 200 and done.json()["due_date"] == "2026-11-20" and done.json()["assigned_to"] == str(owner.id)
    ack = client.post(f"/api/v1/signals/{signal.id}/acknowledge", json={"note": "Discussed with the lender."})
    assert ack.status_code == 200 and ack.json()["status"] == "acknowledged"
    assert client.post(f"/api/v1/signals/{signal.id}/acknowledge", json={}).status_code == 422


def test_a_held_figure_says_which_line_its_label_names_and_its_value_there(client, db, world):
    """Read-only: the work item says which line a held row's printed label names, with the value
    the printed figure has under that line. Nothing is stored and the item's evidence is unchanged."""
    from app.domain.facts import Fact

    borrower, cycle = world

    def held(key, label, value, months=0):
        return add_fact(db, borrower_id=borrower.id, key=key, period_end=PERIOD, months=months, value=D(value),
                        kind="seeded", status="proposed", label_text=label)

    payable = held("bs.accrued_liabilities", "Accounts payable", "8067000")
    accrued = held("bs.accounts_payable", "Accrued liabilities", "1966000")
    # an outflow printed as (1,200) and filed under a line stored as printed: the line its label
    # names stores outflows as positive amounts, so the value there has the other sign
    capex = held("cf.other_investing", "Purchases of property and equipment", "-1200000", months=9)
    unfamiliar = held("bs.revolver", "Notes payable to bank", "500000")
    cells = [
        {"key": "bs.accrued_liabilities", "row_label": "Accounts payable", "reason": "mapping_doubt", "fact_id": str(payable.id)},
        {"key": "bs.accounts_payable", "row_label": "Accrued liabilities", "reason": "mapping_doubt", "fact_id": str(accrued.id)},
        {"key": "cf.other_investing", "row_label": "Purchases of property and equipment", "reason": "mapping_doubt",
         "fact_id": str(capex.id)},
        {"key": "bs.revolver", "row_label": "Notes payable to bank", "reason": "mapping_doubt", "fact_id": str(unfamiliar.id)},
        {"key": "bs.inventory", "row_label": "", "reason": "label_mismatch", "fact_id": None},
    ]
    item = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="spreading",
                      item_type="spread.value_unverified", title="Held", question="Is each figure right?",
                      allowed_decisions=["values_confirmed", "values_corrected"], required_permission="confirm_spread",
                      evidence={"document_id": None, "cells": cells})
    facts_before = db.query(Fact).count()
    sign_in(client, "priya.raman")
    got = client.get(f"/api/v1/work-items/{item.id}").json()["evidence"]["cells"]
    assert [c["reads_as"] for c in got] == [
        {"key": "bs.accounts_payable", "value": "8067000"},
        {"key": "bs.accrued_liabilities", "value": "1966000"},
        {"key": "cf.capex", "value": "1200000"},
        None,   # an unfamiliar label names no line
        None,   # nothing was stored
    ]
    assert [{k: v for k, v in c.items() if k != "reads_as"} for c in got] == cells
    db.refresh(item)
    assert item.evidence["cells"] == cells and db.query(Fact).count() == facts_before
    # the same item type raised at another stage (terms, certificate) is passed through as stored
    other = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing",
                       item_type="spread.value_unverified", title="Held", question="?", allowed_decisions=["retry"],
                       evidence={"cells": cells[:1]})
    assert client.get(f"/api/v1/work-items/{other.id}").json()["evidence"] == {"cells": cells[:1]}

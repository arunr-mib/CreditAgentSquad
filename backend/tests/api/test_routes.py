"""The workspace API over a small seeded world."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.core import clock
from app.core.config import get_settings
from app.domain import workflow
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts_service import add_fact, correct_fact
from app.domain.monitoring import CovenantTest
from app.domain.org import User
from app.domain.work_items import raise_item
from app.seed_users import seed_users
from sqlalchemy import select
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


def test_borrower_list_carries_the_tightest_stored_headroom(client, db, world):
    borrower, cycle = world
    facility = db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalar_one()
    sign_in(client, "priya.raman")
    # no covenant has been tested: nothing is shown, and nothing is read as zero
    assert client.get("/api/v1/borrowers").json()[0]["tightest_headroom"] is None

    def tested(covenant, period, headroom, outcome="compliant", **fields):
        fact = None
        if headroom is not None:
            fact = add_fact(db, borrower_id=borrower.id, key=f"cov.{covenant}.headroom_pct", period_end=period,
                            months=0, value=D(headroom), kind="seeded", unit="pct")
        db.add(CovenantTest(borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id, covenant_id=covenant,
                            covenant_name=covenant.replace("_", " ").title(), period_end=period, outcome=outcome,
                            **fields))
        db.flush()
        return fact

    tested("fixed_charge", PERIOD, "0.2")
    tight = tested("total_leverage", PERIOD, "0.05")
    tested("current_ratio", PERIOD, None, outcome="cannot_test")       # no stored headroom: left out
    tested("total_leverage", date(2026, 6, 30), "-0.5")                # an earlier period does not count
    tested("senior_leverage", PERIOD, "-0.9", superseded=True)         # nor does a test that was replaced
    row = client.get("/api/v1/borrowers").json()[0]
    assert row["tightest_headroom"]["id"] == str(tight.id)
    assert row["tightest_headroom"]["value"] == "0.05" and row["tightest_headroom"]["unit"] == "pct"
    assert row["tightest_headroom"]["key"] == "cov.total_leverage.headroom_pct"
    assert row["tightest_headroom"]["label"] == "Total Leverage, headroom"

    # a corrected headroom is a new fact; the list shows that one, not the fact it replaced
    analyst = db.query(User).filter(User.email == "priya.raman@bankofstoic.example").one()
    corrected = correct_fact(db, tight, value=D("0.3"), user_id=analyst.id, reason="Threshold misread.")
    row = client.get("/api/v1/borrowers").json()[0]
    assert corrected.id != tight.id and row["tightest_headroom"]["value"] == "0.2"
    assert row["tightest_headroom"]["key"] == "cov.fixed_charge.headroom_pct"


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
    # freshness: the newest document received on or before the working date, never one dated after it
    assert client.get("/api/v1/clock").json() == {
        "today": "2026-11-17", "latest_document_received": None, "days_since_latest_document": None}
    borrower_id = db.execute(select(Borrower.id)).scalars().first()
    for name, received in (("on-time.pdf", date(2026, 10, 30)), ("from-the-future.pdf", date(2026, 12, 1))):
        db.add(Document(borrower_id=borrower_id, title=name, file_name=name, storage_path=name, sha256=name.ljust(64, "0"),
                        received_date=received))
    db.flush()
    assert client.get("/api/v1/clock").json() == {
        "today": "2026-11-17", "latest_document_received": "2026-10-30", "days_since_latest_document": 18}
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


def test_a_person_runs_the_next_stage_only_with_the_permission_and_a_model(client, db, world, monkeypatch, tmp_path):
    from app.domain import stages
    from app.domain.monitoring import STAGES

    _, cycle = world
    url = f"/api/v1/cycles/{cycle.id}/run"
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {s: (lambda db, cycle, st: "done") for s in STAGES})
    sign_in(client, "helen.strand")  # a credit officer decides; she does not run agents
    assert client.post(url).status_code == 403

    sign_in(client, "priya.raman")
    # no model: recorded mode with nothing recorded. Nothing runs and no stage is failed by it.
    monkeypatch.setenv("SQUAD_LLM_MODE", "recorded")
    monkeypatch.setenv("SQUAD_RECORDINGS_DIR", str(tmp_path / "none"))
    get_settings.cache_clear()
    assert client.get("/api/v1/agents/status").json()["model_connected"] is False
    refused = client.post(url)
    assert refused.status_code == 409 and "Nothing was run" in refused.json()["detail"]
    assert {s.status for s in workflow.stages(db, cycle)} == {"pending"}
    # live mode needs a key
    monkeypatch.setenv("SQUAD_LLM_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.delenv("SQUAD_ANTHROPIC_API_KEY", raising=False)  # read first; a cloud session sets it
    get_settings.cache_clear()
    assert client.post(url).status_code == 409
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    get_settings.cache_clear()
    status = client.get("/api/v1/agents/status").json()
    assert status["model_connected"] is True and status["mode"] == "live" and "key" not in str(status).lower()

    ran = client.post(url).json()
    assert ran["ran"] == [{"stage": STAGES[0], "result": "done", "error": None}] and ran["stage"] == STAGES[1]
    asked = client.get("/api/v1/ledger", params={"action": "cycle.run_requested"}).json()
    assert len(asked) == 1 and asked[0]["actor_type"] == "user"
    assert client.post("/api/v1/cycles/00000000-0000-4000-8000-000000000000/run").status_code == 404
    assert stages.LLM_FACTORY is not None


def test_a_breach_decision_needs_a_reason_on_the_server(client, db, world):
    borrower, cycle = world
    breach = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing",
                        item_type="covenant.breach", severity="critical", title="Leverage breach",
                        question="How should the breach be handled?",
                        allowed_decisions=["reservation_of_rights", "not_a_breach"],
                        required_permission="decide_breach")
    sign_in(client, "helen.strand")
    for reason in ("", "   "):
        refused = client.post(f"/api/v1/work-items/{breach.id}/decide", json={"decision": "not_a_breach", "reason": reason})
        assert refused.status_code == 422 and "reason" in refused.json()["detail"]
    db.refresh(breach)
    assert breach.status == "open"
    done = client.post(f"/api/v1/work-items/{breach.id}/decide",
                       json={"decision": "reservation_of_rights", "reason": "  Letter sent while the waiver is worked.  "})
    assert done.status_code == 200 and done.json()["decision_reason"] == "Letter sent while the waiver is worked."


def test_an_item_is_routed_only_to_someone_who_may_decide_it_and_keeps_its_due_date(client, db, world):
    from app.core.ledger import LedgerEvent

    borrower, cycle = world
    breach = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing",
                        item_type="covenant.breach", severity="critical", title="Leverage breach",
                        question="How should the breach be handled?", allowed_decisions=["reservation_of_rights"],
                        required_permission="decide_breach")
    breach.due_date = date(2026, 11, 20)
    db.flush()
    analyst = db.query(User).filter(User.email == "priya.raman@bankofstoic.example").one()
    officer = db.query(User).filter(User.email == "helen.strand@bankofstoic.example").one()
    sign_in(client, "priya.raman")
    refused = client.post(f"/api/v1/work-items/{breach.id}/assign", json={"assigned_to": str(analyst.id)})
    assert refused.status_code == 422 and "cannot decide" in refused.json()["detail"]
    routed = client.post(f"/api/v1/work-items/{breach.id}/assign", json={"assigned_to": str(officer.id)})
    assert routed.status_code == 200 and routed.json()["assigned_to"] == str(officer.id)
    assert routed.json()["due_date"] == "2026-11-20", "routing without a due date keeps the one set"
    moved = client.post(f"/api/v1/work-items/{breach.id}/assign",
                        json={"assigned_to": str(officer.id), "due_date": "2026-11-27"})
    assert moved.json()["due_date"] == "2026-11-27"
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.assigned")
                       .order_by(LedgerEvent.seq.desc()).limit(1)).scalar_one()
    assert event.payload["previous_due_date"] == "2026-11-20" and event.payload["due_date"] == "2026-11-27"


def test_a_breach_lists_the_open_questions_that_may_change_it(client, db, world):
    borrower, cycle = world
    breach = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing",
                        item_type="covenant.breach", severity="critical", title="Leverage breach",
                        question="How should the breach be handled?", allowed_decisions=["reservation_of_rights"],
                        required_permission="decide_breach")
    amendment = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="compliance_tracking",
                           item_type="terms.unapproved_amendment", severity="high", title="First amendment on file",
                           question="Should the terms be updated before covenants are tested?",
                           allowed_decisions=["amendment_not_applicable"], required_permission="approve_terms")
    raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="intake", item_type="intake.unclassified",
               title="Unfiled document", question="What is this document?", allowed_decisions=["classified_by_hand"],
               required_permission="upload_document")
    sign_in(client, "helen.strand")
    related = client.get(f"/api/v1/work-items/{breach.id}").json()["related_items"]
    assert [r["id"] for r in related] == [str(amendment.id)] and "amendment" in related[0]["relation"]
    assert client.get(f"/api/v1/work-items/{amendment.id}").json()["related_items"] == []


def test_a_spreadsheet_is_served_as_an_attachment_with_its_own_media_type(client, world, tmp_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    borrower, _ = world
    sign_in(client, "priya.raman")
    up = client.post(f"/api/v1/borrowers/{borrower.id}/documents", files={"file": ("m.csv", b"Month,MRR\n2025-01,100\n")})
    assert up.status_code == 201
    file = client.get(f"/api/v1/documents/{up.json()['id']}/file")
    assert file.headers["content-type"].startswith("text/csv")
    assert file.headers["content-disposition"].startswith("attachment")
    get_settings.cache_clear()


def test_a_file_name_outside_latin_1_or_with_a_quote_cannot_break_the_download_header(client, world, tmp_path, monkeypatch):
    from urllib.parse import unquote

    from app.api.disposition import content_disposition
    from app.core.config import get_settings

    name = 'Bilan — 月次 "Q3".csv'
    header = content_disposition("attachment", name)
    header.encode("latin-1")  # a header value must be Latin-1 clean
    assert header.startswith('attachment; filename="') and header.count('"') == 2 and "filename*=UTF-8''" in header
    assert unquote(header.split("filename*=UTF-8''")[1]) == name
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    borrower, _ = world
    sign_in(client, "priya.raman")
    up = client.post(f"/api/v1/borrowers/{borrower.id}/documents", files={"file": (name, b"Month,MRR\n2025-01,100\n")})
    assert up.status_code == 201
    file = client.get(f"/api/v1/documents/{up.json()['id']}/file")
    assert file.status_code == 200 and "filename*=UTF-8''" in file.headers["content-disposition"]
    get_settings.cache_clear()


def test_a_commentary_approval_in_the_list_names_its_review_sheet(db, client, world):
    borrower, cycle = world
    item = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="review_prep", item_type="review.commentary_approval",
                      severity="medium", title="Commentary awaiting approval", question="Approve?",
                      allowed_decisions=["approve", "return_for_rework"], required_permission="approve_commentary",
                      evidence={"review_sheet_id": "11111111-1111-1111-1111-111111111111"})
    other = raise_item(db, borrower_id=borrower.id, cycle_id=cycle.id, stage="intake", item_type="intake.unclassified",
                       severity="low", title="Unfiled", question="?", allowed_decisions=["classified_by_hand"],
                       required_permission="upload_document")
    sign_in(client, "priya.raman")
    rows = {w["id"]: w for w in client.get("/api/v1/work-items").json()}
    assert rows[str(item.id)]["review_sheet_id"] == "11111111-1111-1111-1111-111111111111"
    assert "review_sheet_id" not in rows[str(other.id)]

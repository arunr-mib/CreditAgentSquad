"""The read-only workspace views, over two borrowers from the synthetic book loaded through the
real services: one with a breach behind a compliant certificate, one with an over-advance."""
import subprocess
import sys
import uuid
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.api.routes_ui import expression_text
from app.core.config import get_settings
from app.core.ledger import LedgerEvent
from app.domain import hooks  # noqa: F401
from app.domain.credit import Borrower
from app.domain.facts import Fact
from app.domain.facts_service import correct_fact
from app.domain.org import User
from app.seed_book import seed_book
from app.seed_users import seed_users
from sqlalchemy import func, select

REPO = Path(__file__).resolve().parents[3]
BREACH, OVER_ADVANCE = "kestrel-bay-packaging", "briarstone-beverage"
API = "/api/v1"
PERIOD, PRIOR = date(2026, 9, 30), date(2025, 9, 30)


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    existing = REPO / "synthetic" / "out"
    if (existing / "truth" / f"{BREACH}.json").exists():
        return existing
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    return out


@pytest.fixture()
def world(db, client, book, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_users(db, password="pw")
    seed_book(db, root=book, only=[BREACH, OVER_ADVANCE], password="pw")
    db.flush()
    borrowers = {b.code: b for b in db.execute(select(Borrower)).scalars()}
    yield borrowers
    get_settings.cache_clear()


def sign_in(client, who="priya.raman"):
    r = client.post(f"{API}/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def test_views_require_sign_in(client, world):
    borrower = world[BREACH]
    for path in ("/ui/portfolio", "/ui/facts?ids=x", "/ui/users", f"/ui/borrowers/{borrower.id}/overview",
                 f"/ui/borrowers/{borrower.id}/covenants", f"/ui/borrowers/{borrower.id}/terms",
                 f"/ui/borrowers/{borrower.id}/borrowing-base", f"/ui/borrowers/{borrower.id}/timeline"):
        assert client.get(API + path).status_code == 401, path


def test_views_write_nothing(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    before = db.execute(select(func.count()).select_from(LedgerEvent)).scalar()
    for path in ("/ui/portfolio", f"/ui/borrowers/{borrower.id}/overview", f"/ui/borrowers/{borrower.id}/covenants",
                 f"/ui/borrowers/{borrower.id}/terms", f"/ui/borrowers/{borrower.id}/timeline"):
        assert client.get(API + path).status_code == 200, path
    assert db.execute(select(func.count()).select_from(LedgerEvent)).scalar() == before


def test_portfolio_summary_counts_and_totals(client, db, world):
    sign_in(client)
    body = client.get(f"{API}/ui/portfolio").json()
    assert body["borrowers"] == 2 and body["as_of"] == "2026-11-17" and body["period_end"] == "2026-09-30"
    listed = client.get(f"{API}/borrowers").json()
    assert D(body["exposure"]["commitment"]) == sum(D(b["total_commitment"]) for b in listed)
    assert body["cycles"]["open"] == 2 and sum(s["count"] for s in body["cycles"]["by_stage"]) == 2
    outcomes = {o["outcome"]: o["count"] for o in body["covenants"]["by_outcome"]}
    assert outcomes.get("breach_reported_compliant") == 1 and sum(outcomes.values()) == body["covenants"]["tests"]
    types = {t["item_type"]: t["count"] for t in body["work_items"]["by_type"]}
    assert types["covenant.reported_mismatch"] == 1 and types["bb.over_advance"] == 1
    assert sum(types.values()) == body["work_items"]["open"] == len(client.get(f"{API}/work-items").json())
    # each balance is a fact the workspace can open, and the total is their exact sum
    exposure = body["borrower_exposure"]
    revolvers = [e["revolver_outstanding"] for e in exposure.values()]
    assert all(f["kind"] == "system" and f["label"] == "Line of credit, outstanding" for f in revolvers)
    assert D(body["exposure"]["revolver_outstanding"]) == sum(D(f["value"]) for f in revolvers)
    assert D(body["exposure"]["outstanding"]) == D(body["exposure"]["revolver_outstanding"]) + D(
        body["exposure"]["term_loan_outstanding"])


def test_borrower_list_headroom_is_the_lowest_stored_fact_of_the_latest_period(client, db, world):
    sign_in(client)
    listed = {b["code"]: b for b in client.get(f"{API}/borrowers").json()}
    for code in (BREACH, OVER_ADVANCE):
        borrower = world[code]
        covenants = client.get(f"{API}/ui/borrowers/{borrower.id}/covenants").json()
        current = [t for t in covenants["tests"] if t["period_end"] == "2026-09-30" and t["headroom_fact_id"]]
        lowest = min(current, key=lambda t: D(covenants["facts"][t["headroom_fact_id"]]["value"]))
        shown = listed[code]["tightest_headroom"]
        # the list shows a stored fact as it stands: same id, same value, calculated by code
        assert shown == covenants["facts"][lowest["headroom_fact_id"]], code
        stored = db.get(Fact, uuid.UUID(shown["id"]))
        assert D(shown["value"]) == stored.value and shown["kind"] == "calculated" and shown["calc_run_id"]
    breach = listed[BREACH]["tightest_headroom"]
    assert breach["label"] == "Total Leverage Ratio, headroom" and D(breach["value"]) < 0


def test_facts_in_bulk_with_labels(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    facts = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.period_end == PERIOD,
                                          Fact.key.in_(("is.revenue", "cov.total_leverage.value",
                                                        "cov.total_leverage.threshold", "cert.total_leverage.value",
                                                        "sys.revolver_outstanding")))).scalars().all()
    ids = ",".join(str(f.id) for f in facts) + ",not-a-uuid,00000000-0000-4000-8000-000000000000"
    body = client.get(f"{API}/ui/facts", params={"ids": ids}).json()
    assert len(body) == len(facts) == 5
    labels = {f["key"]: f["label"] for f in body.values()}
    assert labels["is.revenue"] == "Net revenue"
    assert labels["cov.total_leverage.value"] == "Total Leverage Ratio"
    assert labels["cov.total_leverage.threshold"] == "Total Leverage Ratio, threshold in force"
    assert labels["cert.total_leverage.value"] == "Total Leverage Ratio, reported on the certificate"
    assert client.get(f"{API}/ui/facts").json() == {}


def test_covenants_carry_fact_ids_clause_and_work_item(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    body = client.get(f"{API}/ui/borrowers/{borrower.id}/covenants").json()
    current = [t for t in body["tests"] if t["period_end"] == "2026-09-30"]
    leverage = next(t for t in current if t["covenant_id"] == "total_leverage")
    assert leverage["outcome"] == "breach_reported_compliant"
    for key in ("value_fact_id", "threshold_fact_id", "headroom_fact_id", "reported_fact_id"):
        assert leverage[key] in body["facts"], key
    assert body["facts"][leverage["threshold_fact_id"]]["value"] == leverage["threshold"]
    assert leverage["work_item"]["item_type"] == "covenant.reported_mismatch" and leverage["work_item"]["status"] == "open"
    assert leverage["terms_version"]["status"] == "approved" and leverage["loan_name"]
    assert leverage["citation"]["document_id"] and leverage["citation"]["page"] >= 1
    assert all(t["work_item"] is None for t in current if t["outcome"] == "compliant")
    assert client.get(f"{API}/ui/borrowers/00000000-0000-4000-8000-000000000000/covenants").status_code == 404


def test_source_of_a_calculated_figure_reaches_its_inputs(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    tests = client.get(f"{API}/ui/borrowers/{borrower.id}/covenants").json()["tests"]
    leverage = next(t for t in tests if t["covenant_id"] == "total_leverage" and t["period_end"] == "2026-09-30")
    source = client.get(f"{API}/ui/facts/{leverage['value_fact_id']}/source").json()
    assert source["fact"]["kind"] == "calculated" and source["page"] is None
    calc = source["calculation"]
    assert calc["expression"] == "Total debt ÷ EBITDA" and calc["terms_version"]["status"] == "approved"
    assert calc["outputs"]["value"] == "2.60" and calc["steps"][-1]["final"] and calc["steps"][-1]["unit"] == "ratio"
    # every input is a stored fact with a label, and the trailing-twelve-month lines list their three parts
    assert calc["inputs"] and all(i["fact_id"] in calc["facts"] for i in calc["inputs"])
    net_income = next(s for s in calc["steps"] if s["key"] == "is.net_income")
    assert net_income["basis"] == "trailing twelve months" and [i["sign"] for i in net_income["inputs"]] == [1, 1, -1]
    assert any(s["op"] == "named" and s["name"] == "EBITDA" for s in calc["steps"])
    same = client.get(f"{API}/ui/calculations/{calc['id']}").json()
    assert {p["key"] for p in same["produced"]} >= {"cov.total_leverage.value", "cov.total_leverage.threshold"}
    assert client.get(f"{API}/ui/calculations/00000000-0000-4000-8000-000000000000").status_code == 404


def test_source_of_a_statement_figure_is_located_on_its_page(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    for key, months, expected_page, row in (("is.revenue", 9, 3, "Net sales"), ("bs.long_term_debt", 0, 2, "Long-term debt"),
                                            ("cf.capex", 9, 4, "Purchases of property")):
        fact = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key == key, Fact.months == months,
                                             Fact.period_end == PERIOD)).scalar_one()
        source = client.get(f"{API}/ui/facts/{fact.id}/source").json()
        page = source["page"]
        assert page is not None, key
        assert page["method"] == "located" and page["page"] == expected_page and page["doc_type"] == "interim_statements"
        assert page["label_text"].startswith(row), page["label_text"]
        # the figure as printed is the stored value at the statement's scale
        printed = D(page["quote"].strip("()").replace(",", "")) * page["scale"]
        assert printed == abs(fact.value)
        (x0, y0, x1, y1), = page["boxes"]
        assert 0 < x0 < x1 < page["width"] and 0 < y0 < y1 < page["height"]
        # the box really is where the page says that figure is
        words = client.get(f"{API}/documents/{page['document_id']}/pages/{page['page']}").json()
        assert page["quote"] in words["text"]
    # the current-period figure sits in the first column, not the comparative one
    revenue = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key == "is.revenue",
                                            Fact.period_end == PERIOD)).scalar_one()
    prior = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key == "is.revenue",
                                          Fact.period_end == PRIOR)).scalar_one()
    now_page = client.get(f"{API}/ui/facts/{revenue.id}/source").json()["page"]
    assert now_page["comparative_column"] is False
    prior_page = client.get(f"{API}/ui/facts/{prior.id}/source").json()["page"]
    assert prior_page["document_id"] != now_page["document_id"] and prior_page["comparative_column"] is False


def test_source_of_a_certificate_figure_and_a_threshold_clause(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    tests = client.get(f"{API}/ui/borrowers/{borrower.id}/covenants").json()["tests"]
    leverage = next(t for t in tests if t["covenant_id"] == "total_leverage" and t["period_end"] == "2026-09-30")
    reported = client.get(f"{API}/ui/facts/{leverage['reported_fact_id']}/source").json()
    assert reported["page"]["doc_type"] == "compliance_certificate" and reported["page"]["quote"] == "2.41x"
    assert "Total Leverage Ratio" in reported["page"]["label_text"]
    threshold = client.get(f"{API}/ui/facts/{leverage['threshold_fact_id']}/source").json()
    assert threshold["fact"]["provenance"] == "term" and threshold["calculation"] is None
    assert threshold["term"]["threshold_in_force"] == leverage["threshold"] and threshold["term"]["operator"] == "<="
    clause = threshold["clause"]
    assert clause["doc_type"] == "credit_agreement" and clause["section"] and "Total Leverage Ratio" in clause["quote"]
    assert clause["boxes"], "the quoted clause is outlined on its page"
    assert all(0 < b[0] < b[2] <= clause["width"] and 0 < b[1] < b[3] <= clause["height"] for b in clause["boxes"])
    system = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key == "sys.revolver_outstanding")
                        .order_by(Fact.period_end.desc()).limit(1)).scalar_one()
    record = client.get(f"{API}/ui/facts/{system.id}/source").json()
    assert record["page"] is None and record["calculation"] is None and record["fact"]["connector"] == "core_loan_accounting"
    assert client.get(f"{API}/ui/facts/00000000-0000-4000-8000-000000000000/source").status_code == 404


def test_page_figures_and_quote_location(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    docs = client.get(f"{API}/borrowers/{borrower.id}/documents").json()
    interim = next(d for d in docs if d["doc_type"] == "interim_statements" and d["period_end"] == "2026-09-30")
    body = client.get(f"{API}/ui/documents/{interim['id']}/pages/3/figures").json()
    keys = [f["fact"]["key"] for f in body["figures"]]
    assert "is.revenue" in keys and "is.net_income" in keys and all(k.startswith("is.") for k in keys)
    assert all(f["method"] == "located" and f["boxes"] for f in body["figures"])
    tops = [f["boxes"][0][1] for f in body["figures"]]
    assert tops == sorted(tops), "figures come in reading order"
    balance = client.get(f"{API}/ui/documents/{interim['id']}/pages/2/figures").json()
    assert {f["fact"]["key"].split(".")[0] for f in balance["figures"]} == {"bs"}
    assert client.get(f"{API}/ui/documents/{interim['id']}/pages/99/figures").status_code == 404
    agreement = next(d for d in docs if d["doc_type"] == "credit_agreement")
    loans = client.get(f"{API}/ui/borrowers/{borrower.id}/terms").json()
    citation = next(c for loan in loans for v in loan["terms_versions"] for c in v["covenants"]
                    if c["id"] == "total_leverage")["citations"][0]
    assert citation["document_id"] == agreement["id"]
    found = client.get(f"{API}/ui/documents/{agreement['id']}/pages/{citation['page']}/locate",
                       params={"quote": citation["quote"]}).json()
    assert found["found"] and len(found["boxes"]) >= 1
    missing = client.get(f"{API}/ui/documents/{agreement['id']}/pages/{citation['page']}/locate",
                         params={"quote": "This sentence is not in the agreement."}).json()
    assert missing == {**missing, "found": False, "boxes": []}


def test_history_runs_in_both_directions(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    analyst = db.execute(select(User).where(User.email == "priya.raman@bankofstoic.example")).scalar_one()
    old = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key == "bs.cash",
                                        Fact.period_end == PERIOD)).scalar_one()
    new = correct_fact(db, old, value=old.value + D("1000"), user_id=analyst.id, reason="Bank statement shows more.")
    db.flush()
    from_old = client.get(f"{API}/ui/facts/{old.id}/source").json()["history"]
    assert [(h["relation"], h["status"]) for h in from_old] == [("later", "confirmed"), ("this", "superseded")]
    from_new = client.get(f"{API}/ui/facts/{new.id}/source").json()
    assert [h["relation"] for h in from_new["history"]] == ["this", "earlier"]
    assert from_new["fact"]["entered_by"] == "Priya Raman" and from_new["fact"]["reason"] == "Bank statement shows more."
    assert from_new["history"][0]["entered_by"] == "Priya Raman"


def test_terms_versions_and_overview(client, db, world):
    borrower = world[BREACH]
    sign_in(client)
    loans = client.get(f"{API}/ui/borrowers/{borrower.id}/terms").json()
    assert {loan["facility_type"] for loan in loans} == {"revolver", "term_loan"}
    versions = [v for loan in loans for v in loan["terms_versions"]]
    assert versions and sum(1 for v in versions if v["in_force"]) == 1
    governing = next(v for v in versions if v["in_force"])
    assert governing["status"] == "approved" and governing["approved_by_name"] and "terms" not in governing
    assert governing["source_documents"][0]["id"], "source documents resolve to stored documents"
    covenant = next(c for c in governing["covenants"] if c["id"] == "total_leverage")
    assert covenant["operator"] == "<=" and covenant["threshold"] == "2.50" and covenant["citations"][0]["document_id"]
    assert governing["reporting_requirements"] and governing["reporting_requirements"][0]["citation"]["page"]
    overview = client.get(f"{API}/ui/borrowers/{borrower.id}/overview").json()
    assert overview["cycle"]["period_end"] == "2026-09-30" and len(overview["cycle"]["stages"]) == 10
    waiting = [s for s in overview["cycle"]["stages"] if s["status"] == "needs_person"]
    assert [s["stage"] for s in waiting] == ["covenant_testing"] and waiting[0]["open_work_items"] == 1
    assert overview["exposure"]["revolver_outstanding"]["kind"] == "system" and overview["open_work_items"] == 1


def test_borrowing_base_reviews_line_by_line(client, db, world):
    borrower = world[OVER_ADVANCE]
    sign_in(client)
    reviews = client.get(f"{API}/ui/borrowers/{borrower.id}/borrowing-base").json()
    assert reviews and reviews[0]["period_end"] == "2026-09-30" and reviews[0]["outcome"] == "over_advance"
    latest = reviews[0]
    lines = {line["line"]: line for line in latest["lines"]}
    assert D(lines["availability"]["computed"]) < 0 and D(latest["over_advance"]) == -D(lines["availability"]["computed"])
    assert lines["borrowing_base"]["certificate"] is not None and lines["ar_eligible"]["status"] in ("match", "mismatch")
    assert [line["line"] for line in latest["lines"]][0] == "ar_total", "lines come in certificate order"
    assert latest["work_item"]["item_type"] == "bb.over_advance" and latest["certificate_document"]["id"]
    assert latest["availability_fact"]["key"] == "bb.availability" and latest["customers"]
    assert client.get(f"{API}/ui/borrowers/{world[BREACH].id}/borrowing-base").json() == []


def test_timeline_follows_the_ledger_for_one_borrower(client, db, world):
    borrower, other = world[BREACH], world[OVER_ADVANCE]
    sign_in(client, "helen.strand")
    item = next(w for w in client.get(f"{API}/work-items").json() if w["borrower_id"] == str(borrower.id))
    decided = client.post(f"{API}/work-items/{item['id']}/decide",
                          json={"decision": "reservation_of_rights", "reason": "Certificate overstates EBITDA."})
    assert decided.status_code == 200, decided.text
    events = client.get(f"{API}/ui/borrowers/{borrower.id}/timeline").json()
    assert events[0]["action"] == "work_item.decided" and events[0]["actor_name"] == "Helen Strand"
    assert events[0]["payload"]["reason"] == "Certificate overstates EBITDA."
    actions = {e["action"] for e in events}
    assert {"document.received", "covenant.tested", "work_item.raised", "cycle.opened"} <= actions
    assert "fact.recorded" not in actions and [e["seq"] for e in events] == sorted((e["seq"] for e in events), reverse=True)
    assert all("prev_hash" not in e for e in events)
    routine = client.get(f"{API}/ui/borrowers/{borrower.id}/timeline", params={"include_routine": True, "limit": 1000}).json()
    assert any(e["action"] == "obligation.received" for e in routine)
    assert not any(e["action"] == "obligation.received" for e in events), "routine events are left out by default"
    theirs = {e["entity_id"] for e in client.get(f"{API}/ui/borrowers/{other.id}/timeline").json()}
    assert item["id"] not in theirs
    users = client.get(f"{API}/ui/users").json()
    assert {"id", "name", "title", "role"} == set(users[0]) and any(u["name"] == "Helen Strand" for u in users)


def test_expression_text_reads_like_a_formula():
    tree = {"op": "div", "num": {"op": "sub", "args": [{"op": "named", "name": "ebitda"},
                                                       {"op": "line", "key": "sup.cash_taxes_paid", "period": "ttm"}]},
            "den": {"op": "add", "args": [{"op": "line", "key": "sup.cash_interest_paid", "period": "ttm"},
                                          {"op": "line", "key": "sup.scheduled_principal", "period": "ttm"}]}}
    assert expression_text(tree) == ("(EBITDA − Cash paid for income taxes) ÷ "
                                     "(Cash paid for interest + Scheduled principal payments on term debt)")
    assert expression_text({"op": "line", "key": "bs.cash"}) == "Cash and equivalents"


STEPPED = "calder-finch-staffing"


@pytest.fixture()
def stepped(db, client, book, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_users(db, password="pw")
    seed_book(db, root=book, only=[STEPPED], password="pw")
    db.flush()
    yield db.execute(select(Borrower).where(Borrower.code == STEPPED)).scalar_one()
    get_settings.cache_clear()


def test_a_stepped_threshold_cites_the_step_in_force_and_headroom_shows_its_own_formula(client, db, stepped):
    sign_in(client)
    body = client.get(f"{API}/ui/borrowers/{stepped.id}/covenants").json()
    leverage = [t for t in body["tests"] if t["covenant_id"] == "total_leverage"]
    current = next(t for t in leverage if t["period_end"] == "2026-09-30")
    before = next(t for t in leverage if t["period_end"] == "2025-09-30")
    assert D(current["threshold"]) == D("1.75") and D(before["threshold"]) == D("2.00")
    # the covenant row's clause is the step's for the stepped period, the base clause before it
    assert "1.75" in current["citation"]["quote"] and "2.00" not in current["citation"]["quote"]
    assert "2.00" in before["citation"]["quote"]

    threshold = client.get(f"{API}/ui/facts/{current['threshold_fact_id']}/source").json()
    term = threshold["term"]
    assert threshold["fact"]["provenance"] == "term" and threshold["calculation"] is None
    assert D(term["threshold_in_force"]) == D("1.75") and D(term["base_threshold"]) == D("2.00")
    assert not term["base_in_force"] and [s["in_force"] for s in term["steps"]] == [True]
    assert "1.75" in threshold["clause"]["quote"] and threshold["clause"]["boxes"]
    assert threshold["ratio_calculation_id"]

    headroom = client.get(f"{API}/ui/facts/{current['headroom_fact_id']}/source").json()
    derivation = headroom["headroom"]
    assert headroom["fact"]["provenance"] == "headroom" and headroom["calculation"] is None
    assert derivation["formula"] == "(threshold − value) ÷ |threshold|"
    assert derivation["value_fact_id"] == current["value_fact_id"]
    assert derivation["threshold_fact_id"] == current["threshold_fact_id"]
    value, limit = D(derivation["value"]), D(derivation["threshold"])
    assert D(derivation["headroom"]) == limit - value
    assert D(derivation["headroom_pct"]) == ((limit - value) / abs(limit)).quantize(D(derivation["headroom_pct"]))

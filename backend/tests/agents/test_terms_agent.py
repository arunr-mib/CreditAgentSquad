"""The Terms Agent with a scripted model that reads the synthetic book perfectly, and with
answers altered one way at a time: what code verifies, proposes, leaves out and refuses."""
import copy
import json
import os
import subprocess
import sys
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.schema import strict_schema
from app.agents.terms_agent import TermsReading, extract_terms
from app.calc.terms import compare_terms
from app.core.config import get_settings
from app.domain import hooks  # noqa: F401
from app.domain.covenant_service import governing_terms, run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.terms import TermsVersion
from app.domain.terms_service import TermsRefused, approve_terms, unapproved_amendments
from app.seed_book import doc_type, normalise_terms, seed_book
from sqlalchemy import select
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[3]
BORROWERS = ["briarstone-beverage", "marlowe-ridge-logistics", "vantry-freight", "calder-finch-staffing",
             "larkspur-environmental", "ostrander-valley-foods", "brindlewood-home-health"]


# ---- the book, seeded once for the module; each test's writes are rolled back


@pytest.fixture(scope="module")
def book_db(engine, tmp_path_factory):
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    conn = engine.connect()
    outer = conn.begin()
    db = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    seed_book(db, root=out, current="seeded", only=BORROWERS)
    db.flush()
    truths = {code: json.loads((out / "truth" / f"{code}.json").read_text()) for code in BORROWERS}
    yield db, truths
    db.close()
    outer.rollback()
    conn.close()
    os.environ.pop("FILE_STORE_DIR", None)
    get_settings.cache_clear()


@pytest.fixture()
def book(book_db):
    db, truths = book_db
    savepoint = db.begin_nested()
    try:
        yield db, truths
    finally:
        if savepoint.is_active:
            savepoint.rollback()
        db.expire_all()


# ---- a perfect reader: the answer a model would give if it copied the book's clauses exactly


def money(value) -> str:
    return f"${int(D(value)):,}"


def pct(value) -> str:
    return f"{(D(value) * 100).normalize():f}%"


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"


def where(citation: dict, prefix: str = "") -> dict:
    return {f"{prefix}document_id": citation["document_id"], f"{prefix}page": citation["page"],
            f"{prefix}section": citation["section"], f"{prefix}quote": citation["quote"]}


def covenant_rows(terms: dict) -> tuple[list[dict], list[dict]]:
    covenants, steps = [], []
    for c in terms["covenants"]:
        cites = {x["field"]: x for x in c["citations"]}
        params, test = c["params"], c["test"]
        printed = (lambda v, unit=test["unit"]: f"{v} to 1.00" if unit == "ratio" else money(v))
        availability = params.get("include_availability")
        covenants.append({
            "covenant_id": c["id"], "name": c["name"], "archetype": c["archetype"], "operator": test["operator"],
            "unit": test["unit"], "basis": c["measurement"]["basis"], "frequency": c["measurement"]["frequency"],
            "earnings": params.get("numerator_base") or params.get("ebitda") or "not_applicable",
            "debt": params.get("debt", "not_applicable"), "deductions": params.get("deductions", []),
            "denominator": params.get("denominator", []),
            "include_availability": "not_applicable" if availability is None else ("yes" if availability else "no"),
            "threshold_printed": printed(test["threshold"]), "net_income_step_up_printed": "",
            **where(cites["test.threshold"]), **where(cites["definition"], "definition_")})
        for i, step in enumerate(test["steps"]):
            steps.append({"covenant_id": c["id"], "from_date_printed": long_date(step["from"]),
                          "threshold_printed": printed(step["value"]), **where(cites[f"test.steps[{i}]"])})
    return covenants, steps


def addback_rows(terms: dict) -> list[dict]:
    rows = []
    for a in terms["definitions"]["ebitda"]["addbacks"]:
        cap = a["cap"]
        rows.append({"name": a["name"], "source": a["source_key"],
                     "cap_type": "none" if cap is None else ("amount" if cap["type"] == "amount" else "pct_of_ebitda"),
                     "cap_printed": "" if cap is None else (money(cap["value"]) if cap["type"] == "amount" else pct(cap["value"])),
                     **where(a["citation"])})
    return rows


def borrowing_base_rows(terms: dict, clause_index: list[dict]) -> tuple[list[dict], list[dict], str]:
    bb = terms["borrowing_base"]
    if bb is None:
        return [], [], "none"
    clauses = {c["field"]: c for c in clause_index}
    values, exclusions = [], []

    def value(item, collateral, printed, clause, name=""):
        values.append({"item": item, "collateral": collateral, "name": name, "printed": printed, **where(clause)})

    value("commitment", "not_applicable", money(bb["commitment"]), clauses["facilities.revolver.commitment"])
    for component in bb["components"]:
        kind, rules = component["collateral"], component["eligibility"]
        clause = clauses[f"borrowing_base.components[{kind}].eligibility"]
        value("advance_rate", kind, pct(component["advance_rate"]), bb["citation"])
        if component.get("sublimit") is not None:
            value("sublimit", kind, money(component["sublimit"]), bb["citation"])
        if rules.get("max_age_days") is not None:
            value("max_age_days", kind, f"{rules['max_age_days']} days", clause)
        for name in ("cross_aging_pct", "concentration_limit_pct"):
            if rules.get(name) is not None:
                value(name, kind, pct(rules[name]), clause)
        exclusions.append({"collateral": kind, "excluded": rules["exclude"], **where(clause)})
    for reserve in bb["reserves"]:
        value("reserve", "not_applicable", money(reserve["amount"]), clauses["borrowing_base.reserves"],
              name=reserve["name"].lower())
    return values, exclusions, bb["frequency"]


def perfect(truth: dict, *, versions=(0,)) -> dict:
    """The agreement's terms in full, then only what each later version restates from an amendment."""
    agreement = next(d for d in truth["documents"] if d["type"] == "credit_agreement")
    out = {"documents": [{"document_id": agreement["id"], "page": 1,
                          "quote": f"dated as of {long_date(agreement['document_date'])}",
                          "printed_date": long_date(agreement["document_date"])}],
           "covenants": [], "steps": [], "addbacks": [], "reporting": [], "borrowing_base_values": [],
           "borrowing_base_exclusions": [], "borrowing_base_frequency": "none", "notes": []}
    for n, index in enumerate(versions):
        tv = truth["terms_versions"][index]
        terms = tv["terms"]
        covenants, steps = covenant_rows(terms)
        values, exclusions, frequency = borrowing_base_rows(terms, tv.get("clause_index") or [])
        reporting = [{"document_type": doc_type(r["document_type"]), "frequency": r["frequency"],
                      "quality": r["quality"] or "not_stated", "due_days_printed": f"{r['due_days_after_period_end']} days",
                      **where(r["citation"])} for r in terms["reporting_requirements"]]
        groups = {"covenants": covenants, "steps": steps, "addbacks": addback_rows(terms), "reporting": reporting,
                  "borrowing_base_values": values, "borrowing_base_exclusions": exclusions}
        for name, rows in groups.items():
            out[name] += [r for r in rows if n == 0 or r["document_id"] != agreement["id"]]
        if n == 0:
            out["borrowing_base_frequency"] = frequency
        else:
            amendment = next(ref for ref in tv["source_documents"] if ref != agreement["id"])
            out["documents"].append(effective_row(amendment, tv["effective_from"]))
    return out


def effective_row(amendment_id: str, effective_from: str) -> dict:
    return {"document_id": amendment_id, "page": 1, "printed_date": long_date(effective_from),
            "quote": f"shall be effective as of {long_date(effective_from)}"}


def with_vantry_amendment(truth: dict) -> dict:
    """Vantry's signed amendment is not in any terms version of the book; the book describes it."""
    details = truth["scenario"]["details"]
    answer = perfect(truth)
    answer["addbacks"].append({
        "name": "restructuring", "source": "is.nonrecurring_expense", "cap_type": "amount",
        "cap_printed": money(details["amended_cap"]), "document_id": details["document_id"],
        "page": details["page"], "section": details["section"], "quote": details["quote"]})
    answer["documents"].append(effective_row(details["document_id"], details["effective_from"]))
    return answer


# ---- running the agent


def facility_of(db, truth) -> Facility:
    return db.execute(select(Facility).where(Facility.code == truth["terms_versions"][0]["facility_id"])).scalar_one()


def documents_of(db, facility, *, amendments=True) -> list[Document]:
    wanted = ("credit_agreement", "amendment") if amendments else ("credit_agreement",)
    return list(db.execute(select(Document).where(
        Document.borrower_id == facility.borrower_id, Document.doc_type.in_(wanted))).scalars())


def run(db, truth, answer, *, amendments=True, answers=None):
    facility = facility_of(db, truth)
    replies = [LLMResponse(content=[{"type": "text", "text": json.dumps(a)}], stop_reason="end_turn")
               for a in (answers or [answer])]
    llm = ScriptedClient(replies)
    result = extract_terms(db, facility=facility, documents=documents_of(db, facility, amendments=amendments), llm=llm)
    return result, facility, llm


def assert_equals_book(result, tv):
    expected = normalise_terms(tv["terms"], tv.get("clause_index"))
    differences = compare_terms(result.version.terms, expected, include_citations=True)
    assert differences == [], differences
    ours, book = result.version.terms["borrowing_base"], expected["borrowing_base"]
    if book is not None:
        clause = lambda c: (c["document_id"], c["section"], c["page"], c["quote"])  # noqa: E731
        assert [clause(c) for c in ours["citations"]] == [clause(c) for c in book["citations"]]
    assert result.version.warnings == [] and result.unverified == []


def officer(db) -> User:
    return db.execute(select(User).where(User.role == "credit_officer")).scalars().first()


def open_items(db, facility, item_type):
    return list(db.execute(select(WorkItem).where(
        WorkItem.borrower_id == facility.borrower_id, WorkItem.item_type == item_type,
        WorkItem.status == "open", WorkItem.agent_run_id.is_not(None))).scalars())


# ---- the perfect reader reproduces the book


@pytest.mark.parametrize("code", [c for c in BORROWERS if c != "marlowe-ridge-logistics"])
def test_agreement_alone_reproduces_the_books_terms_with_clean_citations(book, code):
    db, truths = book
    truth = truths[code]
    result, facility, llm = run(db, truth, perfect(truth), amendments=False)
    tv = truth["terms_versions"][0]
    assert result.status == "proposed"
    assert_equals_book(result, tv)
    assert result.version.effective_from == date.fromisoformat(tv["effective_from"])
    assert result.version.source_document_ids == tv["source_documents"]
    assert (result.version.status, result.version.prepared_by_type, result.version.prepared_by_id) == (
        "proposed", "agent", "terms@1")
    assert result.version.agent_run_id == result.run_id
    # one call, with each document attached as a PDF and named by id
    assert len(llm.requests) == 1
    blocks = llm.requests[0].messages[0]["content"]
    assert [b["type"] for b in blocks] == ["text", "document", "text"]
    assert tv["source_documents"][0] in blocks[0]["text"] and tv["source_documents"][0] in blocks[-1]["text"]


def test_marlowe_agreement_alone_is_version_one_and_with_the_amendment_is_version_two(book):
    db, truths = book
    truth = truths["marlowe-ridge-logistics"]
    v1, v2 = truth["terms_versions"]

    first, facility, _ = run(db, truth, perfect(truth), amendments=False)
    assert_equals_book(first, v1)
    assert first.version.effective_from == date(2021, 6, 25) and first.version.source_document_ids == v1["source_documents"]

    second, _, llm = run(db, truth, perfect(truth, versions=(0, 1)))
    assert_equals_book(second, v2)
    assert second.version.effective_from == date.fromisoformat(v2["effective_from"]) == date(2025, 7, 1)
    assert second.version.source_document_ids == v2["source_documents"]
    # only the restated threshold cites the amendment; the definition still cites the agreement
    leverage = next(c for c in second.version.terms["covenants"] if c["id"] == "total_leverage")
    assert [c["document_id"].rsplit(".", 1)[1] for c in leverage["citations"]] == ["amendment-1", "credit-agreement"]
    others = [c for c in second.version.terms["covenants"] if c["id"] != "total_leverage"]
    assert all(x["document_id"].endswith("credit-agreement") for c in others for x in c["citations"])
    # the agreement comes first, then the amendment, whatever order they were passed in
    blocks = llm.requests[0].messages[0]["content"]
    assert "credit agreement" in blocks[0]["text"] and "amendment" in blocks[2]["text"]


def test_calder_finch_step_up_is_read_with_its_date_and_cites_its_own_sentence(book):
    db, truths = book
    truth = truths["calder-finch-staffing"]
    result, _, _ = run(db, truth, perfect(truth))
    leverage = next(c for c in result.version.terms["covenants"] if c["id"] == "total_leverage")
    assert leverage["test"]["threshold"] == "2.00" and leverage["test"]["steps"] == [{"from": "2026-01-01", "value": "1.75"}]
    assert [c["field"] for c in leverage["citations"]] == ["test.threshold", "definition", "test.steps[0]"]


def test_vantry_amendment_raises_the_cap_and_governs_only_after_a_second_person_approves(book):
    db, truths = book
    truth = truths["vantry-freight"]
    details = truth["scenario"]["details"]
    period = date(2026, 9, 30)
    result, facility, _ = run(db, truth, with_vantry_amendment(truth))
    borrower = db.get(Borrower, facility.borrower_id)
    assert result.status == "proposed" and result.unverified == [] and result.version.warnings == []
    assert result.version.effective_from == date(2026, 7, 1)
    assert result.version.source_document_ids == ["vantry-freight.credit-agreement", "vantry-freight.amendment-1"]

    addback = result.version.terms["definitions"]["ebitda"]["addbacks"][0]
    assert addback["cap"] == {"type": "amount", "value": "3500000"} == {"type": "amount", "value": details["amended_cap"]}
    assert addback["citation"]["document_id"] == "vantry-freight.amendment-1" and addback["citation"]["page"] == 1
    assert addback["name"] == "restructuring"
    # everything the amendment does not restate is the agreement's, unchanged
    v1 = normalise_terms(truth["terms_versions"][0]["terms"], truth["terms_versions"][0]["clause_index"])
    changed = compare_terms(result.version.terms, v1, include_citations=True)
    assert {d.path.split(".cap")[0].split(".citation")[0] for d in changed} == {"definitions[ebitda].addbacks[restructuring]"}

    # proposed terms do not govern: the approved version still does, and the amendment is still outstanding
    row, _ = governing_terms(db, facility, period)
    assert row.version == 1 and row.id != result.version.id
    assert [d.meta["external_id"] for d in unapproved_amendments(db, facility)] == ["vantry-freight.amendment-1"]
    item = result.work_item
    assert item.item_type == "terms.approval_needed" and item.requires_second_person and item.status == "open"
    assert item.evidence["terms_version_id"] == str(result.version.id) and item.evidence["unverified"] == []
    analyst = db.get(User, borrower.analyst_id)
    with pytest.raises(PermissionError):
        approve_terms(db, result.version, analyst)

    approve_terms(db, result.version, officer(db))
    assert unapproved_amendments(db, facility) == []
    row, _ = governing_terms(db, facility, period)
    assert row.id == result.version.id
    tests = run_covenant_tests(db, borrower=borrower, facility=facility, period_end=period, raise_items=False)
    leverage = next(t for t in tests if t.covenant_id == details["covenant_id"])
    expected = details["under_amendment"]
    assert (leverage.value, leverage.threshold, leverage.passed) == (D(expected["value"]), D(expected["threshold"]), True)
    assert leverage.value == D("1.62")


# ---- what code refuses


def covenant(answer, cid):
    return next(c for c in answer["covenants"] if c["covenant_id"] == cid)


def assert_left_out_with_a_warning(db, result, path, reason):
    """The term is not in the proposed terms, is listed, and approval now needs a written reason."""
    assert result.status == "proposed"
    assert [(u["item"], u["reason"]) for u in result.unverified] == [(path, reason)]
    assert f"unverified_left_out:{path}" in result.version.warnings
    assert result.work_item.severity == "high" and result.work_item.evidence["unverified"] == result.unverified
    with pytest.raises(TermsRefused, match="written reason"):
        approve_terms(db, result.version, officer(db))


def test_a_quote_that_is_not_on_the_cited_page_keeps_the_covenant_out(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = perfect(truth)
    covenant(answer, "total_leverage")["page"] = 6  # the sentence is on page 7
    result, _, _ = run(db, truth, answer, amendments=False)
    assert_left_out_with_a_warning(db, result, "covenants.total_leverage", "quote_not_on_page")
    assert [c["id"] for c in result.version.terms["covenants"]] == ["interest_coverage"]


def test_a_quote_with_no_figure_is_refused(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = perfect(truth)
    row = covenant(answer, "total_leverage")
    row.update(page=row["definition_page"], section=row["definition_section"], quote=row["definition_quote"])
    result, _, _ = run(db, truth, answer, amendments=False)
    assert_left_out_with_a_warning(db, result, "covenants.total_leverage", "no_figure_in_quote")


def test_a_quote_with_two_candidate_figures_is_refused(book):
    db, truths = book
    truth = truths["calder-finch-staffing"]
    answer = perfect(truth)
    row = covenant(answer, "total_leverage")
    step = answer["steps"].pop()
    row["quote"] = f"{row['quote']} {step['quote']}"  # one quote that states both the level and its step-down
    result, _, _ = run(db, truth, answer)
    assert_left_out_with_a_warning(db, result, "covenants.total_leverage", "ambiguous_figure")
    assert "total_leverage" not in [c["id"] for c in result.version.terms["covenants"]]

    # and printed text that holds two figures chooses neither
    again = perfect(truth)
    covenant(again, "total_leverage")["threshold_printed"] = "2.00 to 1.00 and 1.75 to 1.00"
    result, _, _ = run(db, truth, again)
    assert ("covenants.total_leverage", "ambiguous_figure") in [(u["item"], u["reason"]) for u in result.unverified]


def test_a_threshold_whose_printed_text_disagrees_with_its_quote_is_refused(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = perfect(truth)
    covenant(answer, "total_leverage")["threshold_printed"] = "2.25 to 1.00"  # the sentence says 2.00 to 1.00
    result, _, _ = run(db, truth, answer, amendments=False)
    assert_left_out_with_a_warning(db, result, "covenants.total_leverage", "printed_disagrees_with_quote")
    assert "2.25" not in json.dumps(result.version.terms)


def test_a_number_typed_as_a_decimal_instead_of_as_printed_is_refused(book):
    db, truths = book
    truth = truths["larkspur-environmental"]
    answer = perfect(truth)
    answer["addbacks"][0]["cap_printed"] = "0.10"  # the page prints 10%
    result, _, _ = run(db, truth, answer)
    assert result.unverified[0]["item"] == "definitions.ebitda.addbacks.restructuring"
    # a capped add-back whose cap is unverified is left out whole; it never becomes an uncapped add-back
    assert result.version.terms["definitions"]["ebitda"]["addbacks"] == []


def test_an_unknown_archetype_never_reaches_the_terms(book):
    db, truths = book
    truth = truths["vantry-freight"]
    # outside the enumerated choices: the answer is refused whole, twice, and a person boards the terms
    bad = perfect(truth)
    covenant(bad, "total_leverage")["archetype"] = "ebitda_margin"
    result, facility, llm = run(db, truth, None, answers=[bad, bad], amendments=False)
    assert result.status == "failed" and result.version is None and len(llm.requests) == 2
    item = result.work_item
    assert (item.item_type, item.stage, item.severity) == ("spread.value_unverified", "covenant_testing", "high")
    assert "board" in item.question.lower() and item.evidence["reasons"]
    assert open_items(db, facility, "terms.approval_needed") == []

    # a covenant the agent says fits no archetype is left for a person
    other = perfect(truth)
    covenant(other, "total_leverage")["archetype"] = "other"
    result, _, _ = run(db, truth, other, amendments=False)
    assert_left_out_with_a_warning(db, result, "covenants.total_leverage", "not_supported")


def test_an_unknown_borrowing_base_component_or_exclusion_is_left_out_with_a_warning(book):
    db, truths = book
    truth = truths["briarstone-beverage"]
    answer = perfect(truth)
    rate = next(v for v in answer["borrowing_base_values"] if v["item"] == "advance_rate" and v["collateral"] == "inventory")
    answer["borrowing_base_values"].append({**rate, "collateral": "other"})
    answer["borrowing_base_exclusions"][0]["excluded"].append("other")
    result, _, _ = run(db, truth, answer)
    assert result.status == "proposed"
    assert {(u["item"], u["reason"]) for u in result.unverified} == {
        ("borrowing_base.components[other].advance_rate", "not_supported"),
        ("borrowing_base.components[accounts_receivable].eligibility.exclude", "not_supported")}
    assert [c["collateral"] for c in result.version.terms["borrowing_base"]["components"]] == ["accounts_receivable", "inventory"]
    assert len([w for w in result.version.warnings if w.startswith("unverified_left_out:borrowing_base")]) == 2


def test_a_borrowing_base_number_no_row_accounts_for_stops_the_proposal(book):
    db, truths = book
    truth = truths["briarstone-beverage"]
    answer = perfect(truth)
    answer["borrowing_base_values"] = [v for v in answer["borrowing_base_values"]
                                       if not (v["item"] == "advance_rate" and v["collateral"] == "inventory")]
    result, facility, _ = run(db, truth, answer)
    # the sentence states two advance rates and only one was reported: code will not choose
    assert result.status == "needs_person" and result.version is None
    assert ("borrowing_base.components[accounts_receivable].advance_rate", "ambiguous_figure") in [
        (u["item"], u["reason"]) for u in result.unverified]
    assert result.work_item.item_type == "spread.value_unverified" and result.work_item.stage == "covenant_testing"
    assert any("advance rate" in r for r in result.work_item.evidence["reasons"])
    assert open_items(db, facility, "terms.approval_needed") == []


def test_an_amendment_cited_for_something_it_does_not_state_is_not_applied(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = with_vantry_amendment(truth)
    # the agent cites the amendment for a looser leverage level that the amendment does not contain
    row = copy.deepcopy(covenant(answer, "total_leverage"))
    row.update(document_id="vantry-freight.amendment-1", page=1, section="1",
               quote=row["quote"].replace("2.00", "3.00"), threshold_printed="3.00 to 1.00")
    answer["covenants"].append(row)
    result, facility, _ = run(db, truth, answer)

    assert result.status == "proposed"
    reasons = {(u["item"], u["reason"]) for u in result.unverified}
    assert reasons == {("covenants.total_leverage", "quote_not_on_page"),
                       ("documents.vantry-freight.amendment-1", "amendment_not_applied")}
    # nothing from the amendment is applied, not even the part that does verify
    terms = result.version.terms
    assert next(c for c in terms["covenants"] if c["id"] == "total_leverage")["test"]["threshold"] == "2.00"
    assert terms["definitions"]["ebitda"]["addbacks"][0]["cap"]["value"] == "500000"
    assert "amendment-1" not in json.dumps(terms)
    assert result.version.source_document_ids == ["vantry-freight.credit-agreement"]
    assert result.version.effective_from == date(2022, 10, 14)
    assert "amendment_not_applied:vantry-freight.amendment-1" in result.version.warnings
    # so the amendment is still reported as missing from the terms, whatever is approved
    with pytest.raises(TermsRefused):
        approve_terms(db, result.version, officer(db), reason="reviewed against the agreement")
    assert [d.meta["external_id"] for d in unapproved_amendments(db, facility)] == ["vantry-freight.amendment-1"]


def test_an_amendment_whose_effective_date_cannot_be_verified_is_not_applied(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = with_vantry_amendment(truth)
    answer["documents"][1]["printed_date"] = "September 30, 2026"  # in the sentence, but not its effective date
    answer["documents"][1]["quote"] = ("shall be effective as of July 1, 2026 and shall apply to the fiscal "
                                       "quarter ending September 30, 2026")
    result, _, _ = run(db, truth, answer)
    assert result.version.effective_from == date(2022, 10, 14)
    assert result.version.terms["definitions"]["ebitda"]["addbacks"][0]["cap"]["value"] == "500000"
    assert "amendment_not_applied:vantry-freight.amendment-1" in result.version.warnings


def test_an_unverifiable_agreement_date_or_no_answer_proposes_nothing(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = perfect(truth)
    answer["documents"][0]["page"] = 2
    result, facility, _ = run(db, truth, answer, amendments=False)
    assert result.status == "needs_person" and result.version is None
    assert result.work_item.item_type == "spread.value_unverified"

    before = db.execute(select(TermsVersion).where(TermsVersion.facility_id == facility.id)).scalars().all()
    failed = extract_terms(db, facility=facility, documents=documents_of(db, facility), llm=ScriptedClient([]))
    assert failed.status == "failed" and failed.version is None and failed.work_item.id == result.work_item.id
    after = db.execute(select(TermsVersion).where(TermsVersion.facility_id == facility.id)).scalars().all()
    assert len(after) == len(before)


def test_a_definition_clause_that_is_not_on_its_page_is_kept_and_warned_about_by_the_citation_check(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = perfect(truth)
    covenant(answer, "interest_coverage")["definition_page"] = 9
    result, _, _ = run(db, truth, answer, amendments=False)
    assert [c["id"] for c in result.version.terms["covenants"]] == ["total_leverage", "interest_coverage"]
    assert result.version.warnings == ["quote_not_on_page:covenants.interest_coverage"]
    assert result.work_item.severity == "high"


def test_a_note_with_a_typed_figure_is_removed_and_the_model_has_no_field_for_a_number(book):
    db, truths = book
    truth = truths["vantry-freight"]
    answer = perfect(truth)
    answer["notes"] = ["The leverage covenant is 2.00 to 1.00.", "Page three is a table of contents."]
    result, _, _ = run(db, truth, answer, amendments=False)
    assert [n["detail"] for n in result.notes if n["action"] == "shown"] == ["Page three is a table of contents."]

    schema = json.dumps(strict_schema(TermsReading))
    assert '"number"' not in schema
    rows = strict_schema(TermsReading)["$defs"]
    integers = {name for row in rows.values() for name, prop in row["properties"].items() if prop.get("type") == "integer"}
    assert integers == {"page", "definition_page"}

"""The Covenant Agent with a scripted model, on borrowers from the synthetic book: what the tools
refuse, what code verifies after the answer, and what is written to the work item."""
import re
import uuid
from decimal import Decimal as D

import pytest
from app.agents import covenant
from app.agents.covenant import ABSTAIN_NO_ANSWER, ABSTAIN_UNVERIFIED, investigate
from app.agents.covenant_tools import COVENANT_TOOLS, run_calcs
from app.core.ledger import LedgerEvent, verify_chain
from app.domain.agents import AgentStep, Lesson
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import CalcRun
from app.domain.monitoring import CovenantTest, WorkItem
from app.domain.org import User
from app.domain.terms import TermsVersion
from app.domain.terms_service import unapproved_amendments
from sqlalchemy import func, select
from support.agent_book import FlowClient, answer, tool_call, tool_results

SCOPE_FIELDS = {"borrower_id", "borrower", "facility_id", "facility", "period_end", "period", "months",
                "cycle_id", "covenant_id"}
NO_FIGURE_QUOTE = "The Borrower has requested that the Lender amend the Credit Agreement in certain respects"
TWO_FIGURE_QUOTE = ("in any event within 120 days after the end of each fiscal year, the Borrower shall deliver to the "
                    "Lender audited financial statements of the Borrower for such fiscal year, accompanied by an "
                    "unqualified opinion of independent certified public accountants acceptable to the Lender. (b) As "
                    "soon as available, and in any event within 45 days")
UNRELATED_AMENDMENT_QUOTE = ("Except as expressly amended by this Amendment, the Credit Agreement and the other "
                             "Loan Documents remain in full force and effect")


def ref(fact_id: str) -> str:
    return "{{fact:" + fact_id + "}}"


def borrower(db, code) -> Borrower:
    return db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()


def item_for(db, code, item_type) -> WorkItem:
    return db.execute(select(WorkItem).where(
        WorkItem.borrower_id == borrower(db, code).id, WorkItem.item_type == item_type)).scalar_one()


def document(db, code, doc_type) -> Document:
    return db.execute(select(Document).where(
        Document.borrower_id == borrower(db, code).id, Document.doc_type == doc_type)).scalar_one()


def tool_steps(db, run_id) -> list[AgentStep]:
    return list(db.execute(select(AgentStep).where(AgentStep.run_id == run_id, AgentStep.kind == "tool")
                           .order_by(AgentStep.n)).scalars())


def checks(result) -> list[str]:
    return [n["check"] for n in result.notes]


# ---- vantry-freight: a signed amendment is on file but not in the approved terms --------------


@pytest.fixture()
def vantry(book):
    db, truths = book
    details = truths["vantry-freight"]["scenario"]["details"]
    return db, item_for(db, "vantry-freight", "covenant.reported_mismatch"), \
        document(db, "vantry-freight", "amendment"), details


def what_if_call(amendment, details, **over) -> dict:
    return {"change": "addback_cap", "addback_name": "restructuring", "document_id": str(amendment.id),
            "page": details["page"], "quote": details["quote"], **over}


def amendment_claim(amendment, details, **over) -> dict:
    return {"text": "The first amendment replaces the Adjusted EBITDA definition and raises the cap on the add-back.",
            "document_id": str(amendment.id), "page": details["page"], "quote": details["quote"], **over}


def resolve_answer(results, amendment, details, **over) -> dict:
    exception, what_if = results[0], results[-1]
    body = {
        "recommendation": "resolve",
        "explanation": (
            f"The leverage test fails under the approved terms at {ref(exception['test']['fact_ids']['value'])} "
            f"against a limit of {ref(exception['test']['fact_ids']['threshold'])}. A signed first amendment on "
            "file raises the cap on the restructuring add-back and is not yet in the approved terms. Recalculated "
            f"with that cap the ratio is {ref(what_if['fact_ids']['value'])}, which passes and agrees with the "
            f"certificate's {ref(exception['certificate']['reported_value_fact_id'])}."),
        "claims": [amendment_claim(amendment, details)],
        "calc_ids": [what_if["calc_id"]], "missing_evidence": [], "suggested_tag": "amendment_addback"}
    return {**body, **over}


def vantry_flow(amendment, details, final) -> FlowClient:
    return FlowClient([
        tool_call("get_exception"),
        tool_call("list_unapproved_amendments"),
        tool_call("read_page", {"document_id": str(amendment.id), "page": details["page"]}),
        tool_call("recalculate_with_cited_change", what_if_call(amendment, details)),
        lambda request: answer(final(tool_results(request))),
    ])


def test_cited_what_if_that_passes_ends_as_resolve_with_the_terms_note(vantry):
    db, item, amendment, details = vantry
    facility = db.get(Facility, item.facility_id)
    tests_before = db.execute(select(func.count()).select_from(CovenantTest)).scalar()
    test = db.get(CovenantTest, uuid.UUID(item.evidence["covenant_test_id"]))
    test_before = (test.value, test.threshold, test.passed, test.outcome, test.superseded, test.calc_run_id)
    terms_before = [(v.id, v.status, v.effective_to, v.terms) for v in db.execute(select(TermsVersion)).scalars()]

    llm = vantry_flow(amendment, details, lambda results: resolve_answer(results, amendment, details))
    result = investigate(db, item, llm)

    assert result.recommendation == result.model_recommendation == "resolve"
    assert "terms_differ_from_approved" in checks(result)
    assert all(n["action"] == "flagged" for n in result.notes)  # nothing was forced
    assert item.recommendation["recommendation"] == "resolve" and item.guardrail_notes == result.notes
    assert item.recommendation["agent_run_id"] == str(result.run_id)
    assert item.recommendation["suggested_tag"] == "amendment_addback"
    assert [c["document_type"] for c in item.recommendation["claims"]] == ["amendment"]

    # the what-if: the book's independent value under the amendment, logged as a what-if
    logged = run_calcs(db, result.run_id)
    assert len(logged) == 1 and str(logged[0].id) == result.governing_calc_id
    what_if = logged[0]
    assert D(what_if.outputs["value"]) == D(details["under_amendment"]["value"])
    assert D(what_if.outputs["threshold"]) == D(details["under_amendment"]["threshold"])
    assert what_if.outputs["passed"] is True and what_if.formula_key == "covenant.total_leverage.what_if"
    assert what_if.trace["agent"]["what_if"] is True
    assert what_if.trace["agent"]["change"]["to"] == {"type": "amount", "value": details["amended_cap"]}
    assert what_if.trace["agent"]["change"]["from"]["value"] == details["approved_cap"]
    assert what_if.trace["agent"]["citation"]["page"] == details["page"]
    # every calculation in evidence names the facts it read
    assert what_if.inputs and all(i["fact_id"] for i in what_if.inputs)
    origin = db.get(CalcRun, test.calc_run_id)
    assert origin.inputs and all(i["fact_id"] for i in origin.inputs)

    # the figures in the text were rendered by code from facts
    rendered = item.recommendation["explanation_rendered"]
    assert "2.09x" in rendered and "2.00x" in rendered and rendered.count("1.62x") == 2
    assert "{{fact:" in item.recommendation["explanation"] and "{{" not in rendered
    assert not re.search(r"\d", re.sub(r"\{\{fact:[^}]*\}\}", "", item.recommendation["explanation"]))

    # a what-if is not a test and does not touch terms; the person still decides
    assert db.execute(select(func.count()).select_from(CovenantTest)).scalar() == tests_before
    assert (test.value, test.threshold, test.passed, test.outcome, test.superseded, test.calc_run_id) == test_before
    assert [(v.id, v.status, v.effective_to, v.terms) for v in db.execute(select(TermsVersion)).scalars()] == terms_before
    assert [d.id for d in unapproved_amendments(db, facility)] == [amendment.id]
    assert item.status == "open" and item.decision is None and item.decided_by is None and item.decided_at is None

    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "covenant.recommendation_recorded")).scalar_one()
    assert event.entity_id == str(item.id) and event.payload["recommendation"] == "resolve"
    assert verify_chain(db)[0]


def test_a_typed_figure_in_the_explanation_forces_abstain(vantry):
    db, item, amendment, details = vantry

    def final(results):
        body = resolve_answer(results, amendment, details)
        return {**body, "explanation": body["explanation"] + " In short the ratio is 1.62x after the amendment."}

    result = investigate(db, item, vantry_flow(amendment, details, final))
    assert result.model_recommendation == "resolve" and result.recommendation == "abstain"
    assert ("figure_untraceable", "abstain") in [(n["check"], n["action"]) for n in result.notes]
    assert item.recommendation["explanation"] == item.recommendation["explanation_rendered"] == ABSTAIN_UNVERIFIED
    assert not re.search(r"\d", ABSTAIN_UNVERIFIED) and item.recommendation["suggested_tag"] is None
    assert item.status == "open" and item.decision is None


def test_figures_from_a_verified_quote_and_known_thresholds_may_be_typed(vantry):
    db, item, amendment, details = vantry

    def final(results):
        body = resolve_answer(results, amendment, details)
        return {**body, "explanation": body["explanation"] + " The amendment sets the cap at $3,500,000 and the "
                                                             "limit of 2.00 to 1.00 is unchanged."}

    result = investigate(db, item, vantry_flow(amendment, details, final))
    assert result.recommendation == "resolve" and "figure_untraceable" not in checks(result)


def test_a_fabricated_quote_drops_the_claim_and_a_resolve_does_not_survive(vantry):
    db, item, amendment, details = vantry
    invented = "The cap on restructuring charges is removed for the fiscal quarter ending September 30, 2026."

    def only_fabricated(results):
        return resolve_answer(results, amendment, details, claims=[amendment_claim(amendment, details, quote=invented)])

    result = investigate(db, item, vantry_flow(amendment, details, only_fabricated))
    assert result.model_recommendation == "resolve" and result.recommendation == "abstain"
    assert result.claims == [] and item.recommendation["claims"] == []
    assert {"quote_not_on_page", "no_claim_survived"} <= set(checks(result))

    def one_of_two(results):
        return resolve_answer(results, amendment, details, claims=[
            amendment_claim(amendment, details), amendment_claim(amendment, details, quote=invented)])

    again = investigate(db, item, vantry_flow(amendment, details, one_of_two))
    assert again.recommendation == "resolve" and len(again.claims) == 1
    assert ("quote_not_on_page", "claim_dropped") in [(n["check"], n["action"]) for n in again.notes]


def test_a_real_quote_cited_on_the_wrong_page_is_refused(vantry):
    db, item, amendment, details = vantry
    llm = FlowClient([
        tool_call("recalculate_with_cited_change", what_if_call(amendment, details, page=details["page"] + 1)),
        lambda request: answer({"recommendation": "escalate", "explanation": "The explanation could not be verified.",
                                "claims": [], "calc_ids": [], "missing_evidence": [], "suggested_tag": "other"})])
    result = investigate(db, item, llm)
    step = tool_steps(db, result.run_id)[0]
    assert step.refused and f"not on page {details['page'] + 1}" in step.detail["output"]["error"]
    assert run_calcs(db, result.run_id) == [] and result.recommendation == "escalate"
    # the refusal went back to the model as evidence
    assert llm.requests[1].messages[-1]["content"][0]["is_error"] is True

    # and a claim citing the right quote on the wrong page is dropped by the same rule
    def final(results):
        return resolve_answer(results, amendment, details,
                              claims=[amendment_claim(amendment, details, page=details["page"] + 1)])

    assert investigate(db, item, vantry_flow(amendment, details, final)).recommendation == "abstain"


def test_a_cited_change_needs_exactly_one_figure_in_the_quote(vantry, book):
    db, item, amendment, details = vantry
    threshold = book[1]["vantry-freight"]["terms_versions"][0]["terms"]["covenants"][0]["citations"][0]
    cited = {"document_id": threshold["document_id"], "page": threshold["page"], "quote": threshold["quote"]}
    llm = FlowClient([
        tool_call("recalculate_with_cited_change", what_if_call(amendment, details, quote=NO_FIGURE_QUOTE)),
        tool_call("recalculate_with_cited_change", {"change": "threshold", "addback_name": None, **cited,
                                                    "quote": TWO_FIGURE_QUOTE}),
        # a bare figure lifted from the page is not a clause
        tool_call("recalculate_with_cited_change", what_if_call(amendment, details, quote="exceed $3,500,000")),
        # the leverage clause states one ratio, but it is not a clause about the add-back
        tool_call("recalculate_with_cited_change", {"change": "addback_cap", "addback_name": "restructuring", **cited}),
        # the same clause read as this covenant's threshold
        tool_call("recalculate_with_cited_change", {"change": "threshold", "addback_name": None, **cited}),
        lambda request: answer({"recommendation": "escalate", "explanation": "No explanation was found.",
                                "claims": [], "calc_ids": [], "missing_evidence": [], "suggested_tag": "other"})])
    result = investigate(db, item, llm)
    steps = tool_steps(db, result.run_id)
    assert [s.refused for s in steps] == [True, True, True, True, False]
    assert "exactly one figure; it states 0" in steps[0].detail["output"]["error"]
    assert "exactly one figure; it states 2" in steps[1].detail["output"]["error"]
    assert "whole clause" in steps[2].detail["output"]["error"]
    assert "does not mention the restructuring add-back" in steps[3].detail["output"]["error"]
    assert D(steps[4].detail["output"]["threshold"]) == D("2.00") and steps[4].detail["output"]["passed"] is False
    # only the call that was not refused logged a calculation, and it left the breach standing
    assert len(run_calcs(db, result.run_id)) == 1 and result.recommendation == "escalate"
    assert "terms_differ_from_approved" not in checks(result)  # the cited threshold is the approved one


def test_a_threshold_cannot_be_taken_from_another_covenants_clause(vantry, book):
    db, item, amendment, details = vantry
    coverage = book[1]["vantry-freight"]["terms_versions"][0]["terms"]["covenants"][1]["citations"][0]
    assert "3.00 to 1.00" in coverage["quote"]  # a limit under which the leverage test would pass
    llm = FlowClient([
        tool_call("recalculate_with_cited_change", {"change": "threshold", "addback_name": None,
                                                    "document_id": coverage["document_id"], "page": coverage["page"],
                                                    "quote": coverage["quote"]}),
        tool_call("recalculate_with_cited_change", what_if_call(amendment, details, quote=UNRELATED_AMENDMENT_QUOTE.replace(
            "remain in full force and effect", "remain in full force and effect and are ratified and confirmed"))),
        lambda request: answer({"recommendation": "escalate", "explanation": "No explanation was found.",
                                "claims": [], "calc_ids": [], "missing_evidence": [], "suggested_tag": "other"})])
    result = investigate(db, item, llm)
    steps = tool_steps(db, result.run_id)
    assert steps[0].refused and "does not name the Total Leverage Ratio" in steps[0].detail["output"]["error"]
    assert steps[1].refused and run_calcs(db, result.run_id) == []


def test_tool_inputs_carrying_a_borrower_or_period_are_refused(vantry, book):
    db, item, amendment, details = vantry
    other = borrower(db, "kestrel-bay-packaging")
    llm = FlowClient([
        tool_call("get_exception", {"period_end": "2025-12-31"}),
        tool_call("recalculate_under_version", {"version": 1, "borrower_id": str(other.id)}),
        tool_call("recalculate_with_cited_change", what_if_call(amendment, details, facility_id=str(item.facility_id))),
        tool_call("list_terms_versions", {"borrower": other.code}),
        tool_call("read_page", {"document_id": str(document(db, other.code, "credit_agreement").id), "page": 1}),
        lambda request: answer({"recommendation": "abstain", "explanation": "The tools refused every call.",
                                "claims": [], "calc_ids": [], "missing_evidence": [], "suggested_tag": "other"})])
    result = investigate(db, item, llm)
    steps = tool_steps(db, result.run_id)
    assert all(s.refused for s in steps)
    assert all("Extra inputs" in s.detail["output"]["error"] for s in steps[:4])
    assert "no such document for this borrower" in steps[4].detail["output"]["error"]  # another borrower's file
    assert run_calcs(db, result.run_id) == []
    # the model's own abstain, with a clean explanation, is kept as written
    assert result.recommendation == "abstain" and result.explanation == "The tools refused every call."
    for definition in covenant.GATEWAY.definitions(covenant.SPEC.tools):
        assert not SCOPE_FIELDS & set(definition["input_schema"]["properties"]), definition["name"]
    assert len(COVENANT_TOOLS) == 9


def test_a_prohibited_phrase_escalates(vantry):
    db, item, amendment, details = vantry

    def final(results):
        body = resolve_answer(results, amendment, details)
        return {**body, "explanation": body["explanation"] + " Otherwise the bank should grant a waiver."}

    result = investigate(db, item, vantry_flow(amendment, details, final))
    assert result.model_recommendation == "resolve" and result.recommendation == "escalate"
    assert ("policy", "prohibited_phrase", "escalate") in [(n["layer"], n["check"], n["action"]) for n in result.notes]


def test_reaching_the_step_cap_abstains(vantry):
    db, item, _, _ = vantry
    llm = FlowClient([tool_call("list_documents") for _ in range(covenant.SPEC.max_steps)])
    result = investigate(db, item, llm)
    assert result.recommendation == "abstain" and result.model_recommendation is None
    assert ("runtime", "step_cap", "abstain") in [(n["layer"], n["check"], n["action"]) for n in result.notes]
    assert item.recommendation["explanation"] == ABSTAIN_NO_ANSWER and not re.search(r"\d", ABSTAIN_NO_ANSWER)
    assert item.recommendation["claims"] == [] and item.status == "open" and item.decision is None


def test_a_failed_or_refused_run_writes_an_abstain_produced_by_code(vantry):
    db, item, _, _ = vantry
    failed = investigate(db, item, FlowClient([]))  # the model call raises
    assert failed.recommendation == "abstain" and item.recommendation["explanation_rendered"] == ABSTAIN_NO_ANSWER
    from app.agents.llm import LLMResponse
    refused = investigate(db, item, FlowClient([LLMResponse(content=[], stop_reason="refusal")]))
    assert refused.recommendation == "abstain" and checks(refused) == ["refusal"]
    assert item.recommendation["agent_run_id"] == str(refused.run_id) and item.status == "open"


def test_a_passing_what_if_without_a_quote_for_the_difference_becomes_escalate(vantry, book):
    db, item, amendment, details = vantry
    threshold = book[1]["vantry-freight"]["terms_versions"][0]["terms"]["covenants"][0]["citations"][0]

    def agreement_only(results):
        return resolve_answer(results, amendment, details, claims=[{
            "text": "The agreement sets the leverage limit.", "document_id": threshold["document_id"],
            "page": threshold["page"], "quote": threshold["quote"]}])

    result = investigate(db, item, vantry_flow(amendment, details, agreement_only))
    assert result.model_recommendation == "resolve" and result.recommendation == "escalate"
    assert ("terms_drift", "difference_unbacked", "escalate") in [(n["layer"], n["check"], n["action"]) for n in result.notes]
    assert "terms_differ_from_approved" not in checks(result)

    def other_sentence(results):  # the amendment is quoted, but not the clause that states the new cap
        return resolve_answer(results, amendment, details,
                              claims=[amendment_claim(amendment, details, quote=UNRELATED_AMENDMENT_QUOTE)])

    again = investigate(db, item, vantry_flow(amendment, details, other_sentence))
    assert again.recommendation == "escalate" and "difference_unbacked" in checks(again)


def test_an_unknown_calculation_id_is_flagged(vantry):
    db, item, amendment, details = vantry

    def final(results):
        body = resolve_answer(results, amendment, details)
        return {**body, "calc_ids": [*body["calc_ids"], str(uuid.uuid4())]}

    result = investigate(db, item, vantry_flow(amendment, details, final))
    assert ("evidence", "unknown_calc_id", "flagged") in [(n["layer"], n["check"], n["action"]) for n in result.notes]
    assert result.calc_ids == [result.governing_calc_id] and result.recommendation == "resolve"


def test_an_overlong_explanation_is_sent_back_once_then_abstains(vantry):
    db, item, amendment, details = vantry
    long_text = " ".join(["word"] * 151)
    body = {"recommendation": "escalate", "explanation": long_text, "claims": [], "calc_ids": [],
            "missing_evidence": [], "suggested_tag": "other"}
    result = investigate(db, item, FlowClient([answer(body), answer(body)]))
    assert result.recommendation == "abstain" and checks(result) == ["schema"]


def test_lessons_come_from_people_and_are_returned_for_the_topic(vantry):
    db, item, _, _ = vantry
    author = db.execute(select(User)).scalars().first()
    db.add_all([
        Lesson(topic="covenant.reported_mismatch", tag="amendment_addback", written_by=author.id,
               text="Check for a signed amendment before treating a leverage failure as a breach."),
        Lesson(topic="bb.over_advance", tag=None, written_by=author.id, text="Not about covenants.")])
    db.flush()
    llm = FlowClient([tool_call("search_lessons", {"tag": None}),
                      lambda request: answer({"recommendation": "escalate", "explanation": "Nothing was verified.",
                                              "claims": [], "calc_ids": [], "missing_evidence": [],
                                              "suggested_tag": "other"})])
    result = investigate(db, item, llm)
    lessons = tool_steps(db, result.run_id)[0].detail["output"]["lessons"]
    assert [x["text"] for x in lessons] == ["Check for a signed amendment before treating a leverage failure as a breach."]


# ---- kestrel-bay-packaging: a true breach behind a compliant certificate ---------------------


def kestrel_flow(final) -> FlowClient:
    return FlowClient([
        tool_call("get_exception"),
        tool_call("list_unapproved_amendments"),
        tool_call("search_documents", {"query": "pro forma cost savings", "document_type": None}),
        tool_call("recalculate_under_version", {"version": 1}),
        lambda request: answer(final(tool_results(request))),
    ])


def kestrel_answer(results, citation, **over) -> dict:
    exception, rerun = results[0], results[-1]
    return {
        "recommendation": "escalate",
        "explanation": (
            f"The leverage test fails at {ref(rerun['fact_ids']['value'])} against a limit of "
            f"{ref(rerun['fact_ids']['threshold'])}. The certificate reports "
            f"{ref(exception['certificate']['reported_value_fact_id'])} by adding pro forma cost savings. The "
            "agreement's definition permits no such add-back and no amendment is on file, so the breach stands."),
        "claims": [{"text": "The agreement sets the leverage limit tested here.", "document_id": citation["document_id"],
                    "page": citation["page"], "quote": citation["quote"]}],
        "calc_ids": [rerun["calc_id"]], "missing_evidence": [], "suggested_tag": "true_breach", **over}


def test_a_true_breach_hidden_behind_a_compliant_certificate_ends_as_escalate(book):
    db, truths = book
    item = item_for(db, "kestrel-bay-packaging", "covenant.reported_mismatch")
    citation = truths["kestrel-bay-packaging"]["terms_versions"][0]["terms"]["covenants"][0]["citations"][0]
    expected = next(t for t in truths["kestrel-bay-packaging"]["expected"]["covenant_tests"]
                    if t["covenant_id"] == "total_leverage" and t["period_end"] == truths["kestrel-bay-packaging"]["current_period"])

    result = investigate(db, item, kestrel_flow(lambda results: kestrel_answer(results, citation)))
    assert result.recommendation == result.model_recommendation == "escalate" and result.notes == []
    rerun = run_calcs(db, result.run_id)[0]
    assert rerun.trace["agent"]["what_if"] is False and rerun.formula_key == "covenant.total_leverage"
    assert D(rerun.outputs["value"]) == D(expected["value"]) and rerun.outputs["passed"] is False
    assert all(i["fact_id"] for i in rerun.inputs)
    rendered = item.recommendation["explanation_rendered"]
    assert f"{expected['value']}x" in rendered and f"{expected['reported_value']}x" in rendered
    assert unapproved_amendments(db, db.get(Facility, item.facility_id)) == []
    assert item.status == "open" and item.decision is None

    # a resolve argued on a failing calculation does not survive policy
    wishful = investigate(db, item, kestrel_flow(
        lambda results: kestrel_answer(results, citation, recommendation="resolve", suggested_tag="borrower_calc_error")))
    assert wishful.model_recommendation == "resolve" and wishful.recommendation == "escalate"
    assert ("policy", "resolve_requires_evidence", "escalate") in [(n["layer"], n["check"], n["action"]) for n in wishful.notes]


# ---- pellham-grain: a breach the borrower reported correctly ---------------------------------


def test_a_reported_breach_can_end_as_a_request_and_typed_figures_in_the_list_are_removed(book):
    db, truths = book
    item = item_for(db, "pellham-grain", "covenant.breach")
    citation = next(c for c in truths["pellham-grain"]["terms_versions"][0]["terms"]["covenants"]
                    if c["id"] == "fccr")["citations"][0]

    def final(results):
        exception = results[0]
        return {"recommendation": "request",
                "explanation": (f"Fixed charge coverage is {ref(exception['test']['fact_ids']['value'])} against a "
                                f"minimum of {ref(exception['test']['fact_ids']['threshold'])}, and the certificate "
                                "reports the same failure. No waiver letter is on file."),
                "claims": [{"text": "The agreement sets the minimum coverage.", "document_id": citation["document_id"],
                            "page": citation["page"], "quote": citation["quote"]}],
                "calc_ids": [exception["test"]["calc_id"]],
                "missing_evidence": ["A waiver letter covering the quarter, if one was issued.",
                                     "Support for the 1.28x the borrower reports."],
                "suggested_tag": "missing_waiver"}

    result = investigate(db, item, FlowClient([tool_call("get_exception"),
                                               lambda request: answer(final(tool_results(request)))]))
    assert result.recommendation == "request" and result.suggested_tag == "missing_waiver"
    assert result.missing_evidence == ["A waiver letter covering the quarter, if one was issued."]
    assert ("figure_untraceable", "dropped") in [(n["check"], n["action"]) for n in result.notes]
    # no calculation was run, so the originating test governs
    test = db.get(CovenantTest, uuid.UUID(item.evidence["covenant_test_id"]))
    assert result.governing_calc_id == str(test.calc_run_id) == result.calc_ids[0]
    assert "1.28x" in item.recommendation["explanation_rendered"]


def test_only_open_covenant_exceptions_are_investigated(book):
    db, _ = book
    with pytest.raises(ValueError, match="does not investigate"):
        investigate(db, item_for(db, "thornbury-metal", "signal.high"), FlowClient([]))
    item = item_for(db, "pellham-grain", "covenant.breach")
    item.status = "decided"
    with pytest.raises(ValueError, match="open"):
        investigate(db, item, FlowClient([]))

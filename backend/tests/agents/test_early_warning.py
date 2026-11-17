"""The Early Warning Agent with a scripted model: explanations are checked and stored, the
ranking covers exactly the signals code fired, and nothing the model says adds or removes one."""
import json
import re
import uuid
from datetime import date

from app.agents.early_warning import explain_signals
from app.core.ledger import LedgerEvent, verify_chain
from app.domain.credit import Borrower
from app.domain.facts import CalcRun, Fact
from app.domain.monitoring import Signal
from sqlalchemy import select
from support.agent_book import FlowClient, answer

PERIOD = date(2026, 9, 30)


def setup(book):
    db, _ = book
    borrower = db.execute(select(Borrower).where(Borrower.code == "thornbury-metal")).scalar_one()
    return db, borrower


def signals(db, borrower) -> dict[str, Signal]:
    return {str(s.id): s for s in db.execute(select(Signal).where(
        Signal.borrower_id == borrower.id, Signal.period_end == PERIOD)).scalars()}


def snapshot(db, borrower):
    return sorted((str(s.id), s.rule_id, s.severity, json.dumps(s.basis, sort_keys=True), s.status)
                  for s in signals(db, borrower).values())


def listing(request) -> list[dict]:
    return json.loads(request.messages[0]["content"][1]["text"])["signals"]


def ref(entry, n=0) -> str:
    return "{{fact:" + entry["facts"][n]["fact_id"] + "}}"


def by_rule(entries, rule_id) -> dict:
    return next(e for e in entries if e["rule_id"] == rule_id)


def test_explanations_are_stored_rendered_and_ranked(book):
    db, borrower = setup(book)
    before = snapshot(db, borrower)
    assert len(before) == 13

    def respond(request):
        entries = listing(request)
        assert all(e["facts"] for e in entries)  # code found a fact behind every signal
        revenue, usage = by_rule(entries, "revenue_ttm_decline"), by_rule(entries, "line_usage_high")
        past_due = by_rule(entries, "payment_past_due")
        ranking = [past_due["signal_id"], usage["signal_id"], revenue["signal_id"]]
        return answer({
            "explanations": [
                {"signal_id": revenue["signal_id"],
                 "explanation": f"Trailing revenue has fallen to {ref(revenue, 0)} from {ref(revenue, 1)} a year "
                                f"earlier, a change of {ref(revenue, 2)}, so the same debt rests on a smaller business."},
                {"signal_id": usage["signal_id"],
                 "explanation": f"The line is {ref(usage, 2)} drawn, above the 90% trigger, which leaves little "
                                "room to absorb slower collections."},
                {"signal_id": past_due["signal_id"],
                 "explanation": f"A payment is {ref(past_due)} past due while the line is nearly full."}],
            "ranking": ranking + [e["signal_id"] for e in entries if e["signal_id"] not in ranking]})

    llm = FlowClient([respond])
    result = explain_signals(db, borrower, PERIOD, llm)
    assert len(llm.requests) == 1 and llm.requests[0].tools == []  # one call, no tools
    assert result.notes == [] and len(result.explained) == 3

    after = signals(db, borrower)
    assert snapshot(db, borrower) == before  # no signal was added, removed or altered
    assert sorted(s.rank for s in after.values()) == list(range(1, 14))
    assert [after[i].rank for i in result.ranking] == list(range(1, 14))
    first = after[result.ranking[0]]
    assert first.rule_id == "payment_past_due" and first.rank == 1
    assert first.explanation["rendered"] == "A payment is 12 days past due while the line is nearly full."

    revenue = next(s for s in after.values() if s.rule_id == "revenue_ttm_decline")
    assert "{{fact:" in revenue.explanation["text"] and "{{" not in revenue.explanation["rendered"]
    assert "$43,861,000" in revenue.explanation["rendered"] and "$49,870,000" in revenue.explanation["rendered"]
    assert "-12.1%" in revenue.explanation["rendered"]  # the change code computed: -0.1205
    assert revenue.explanation["agent_run_id"] == str(result.run_id)
    usage = next(s for s in after.values() if s.rule_id == "line_usage_high")
    assert "92.7%" in usage.explanation["rendered"] and "90% trigger" in usage.explanation["rendered"]
    assert sum(1 for s in after.values() if s.explanation) == 3

    # a figure the rules computed is stored as a calculated fact whose calculation names its inputs
    for fact_id in re.findall(r"\{\{fact:([0-9a-f-]{36})\}\}", revenue.explanation["text"]):
        fact = db.get(Fact, uuid.UUID(fact_id))
        assert fact.kind == "calculated" and fact.borrower_id == borrower.id
        calc = db.get(CalcRun, fact.calc_run_id)
        assert calc.inputs and all(i["fact_id"] for i in calc.inputs)

    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "signals.explained")).scalar_one()
    assert event.payload["explained"] == 3 and verify_chain(db)[0]

    # a second run reuses the facts code derived the first time
    facts_before = len(db.execute(select(Fact.id).where(Fact.key.like("signal.%"))).all())
    explain_signals(db, borrower, PERIOD, FlowClient([respond]))
    assert len(db.execute(select(Fact.id).where(Fact.key.like("signal.%"))).all()) == facts_before


def test_an_invented_signal_is_ignored_and_a_typed_figure_drops_only_the_explanation(book):
    db, borrower = setup(book)
    before = snapshot(db, borrower)
    invented = str(uuid.uuid4())

    def respond(request):
        entries = listing(request)
        dso, leverage, margin = (by_rule(entries, r) for r in ("dso_increase", "leverage_increase", "ebitda_margin_decline"))
        return answer({
            "explanations": [
                {"signal_id": invented, "explanation": "The borrower has lost its largest customer."},
                {"signal_id": dso["signal_id"], "explanation": "Collections have slowed by 19 days in a year."},
                {"signal_id": leverage["signal_id"],
                 "explanation": f"Leverage has risen to {ref(leverage, 0)}; the bank should contact the borrower."},
                {"signal_id": margin["signal_id"],
                 "explanation": "Margin is quoted from {{fact:" + str(uuid.uuid4()) + "}}, a fact that was not given."}],
            "ranking": [invented, dso["signal_id"], dso["signal_id"]]})

    result = explain_signals(db, borrower, PERIOD, FlowClient([respond]))
    after = signals(db, borrower)
    assert snapshot(db, borrower) == before and invented not in after
    assert db.get(Signal, uuid.UUID(invented)) is None
    noted = [(n["check"], n["action"]) for n in result.notes]
    assert noted.count(("unknown_signal", "ignored")) == 2  # once explained, once ranked
    assert ("figure_untraceable", "explanation_dropped") in noted
    assert ("prohibited_phrase", "explanation_dropped") in noted
    assert ("fact_unknown", "explanation_dropped") in noted
    assert ("ranking_incomplete", "completed_by_code") in noted

    # the signals themselves remain, unexplained, and every one is still ranked
    assert result.explained == [] and all(s.explanation is None for s in after.values())
    dso = next(s for s in after.values() if s.rule_id == "dso_increase")
    assert dso.rank == 1 and sorted(s.rank for s in after.values()) == list(range(1, 14))
    # those the model left out follow in code's order: the high-severity signal first
    assert after[result.ranking[1]].rule_id == "payment_past_due"


def test_a_failed_run_leaves_the_signals_as_code_fired_them(book):
    db, borrower = setup(book)
    before = snapshot(db, borrower)
    result = explain_signals(db, borrower, PERIOD, FlowClient([]))
    assert [(n["layer"], n["action"]) for n in result.notes] == [("runtime", "nothing_stored")]
    assert snapshot(db, borrower) == before
    assert all(s.explanation is None and s.rank is None for s in signals(db, borrower).values())


def test_no_signals_means_no_model_call(book):
    db, borrower = setup(book)
    llm = FlowClient([])
    result = explain_signals(db, borrower, date(2019, 12, 31), llm)
    assert llm.requests == [] and result.run_id is None and result.ranking == []

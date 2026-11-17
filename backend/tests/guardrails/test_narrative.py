from decimal import Decimal as D

import pytest
from app.guardrails.narrative import FactView, check_narrative, format_fact, referenced_fact_ids, render
from app.guardrails.policy import apply_policy

A, B, C = (f"00000000-0000-4000-8000-00000000000{i}" for i in (1, 2, 3))
FACTS = {
    A: FactView(A, D("1.18"), "ratio"),
    B: FactView(B, D("4187345"), "usd"),
    C: FactView(C, D("0.1254"), "pct"),
}


def test_text_with_only_references_is_clean_and_renders():
    text = f"Coverage of {{{{fact:{A}}}}} on revenue of {{{{fact:{B}|usd_m}}}}; margin {{{{fact:{C}}}}}."
    assert check_narrative(text, FACTS) == []
    assert render(text, FACTS) == "Coverage of 1.18x on revenue of $4.2 million; margin 12.5%."
    assert referenced_fact_ids(text) == [A, B, C]


def test_a_typed_figure_is_reported_even_when_it_equals_a_fact():
    # the rule is "never type a number": the reference is the only way to state a fact
    notes = check_narrative("Coverage fell to 1.18x.", FACTS)
    assert [n.check for n in notes] == ["figure_untraceable"]


def test_a_typed_figure_from_a_cited_quote_is_allowed():
    text = f"The agreement requires 1.25 to 1.00; the calculated ratio is {{{{fact:{A}}}}}."
    assert check_narrative(text, FACTS, known_ratios=[D("1.25")]) == []
    assert [n.check for n in check_narrative(text, FACTS)] == ["figure_untraceable", "figure_untraceable"]


def test_unknown_fact_malformed_reference_and_unknown_format():
    unknown = "00000000-0000-4000-8000-00000000000f"
    assert [n.check for n in check_narrative(f"{{{{fact:{unknown}}}}}", FACTS)] == ["fact_unknown"]
    assert [n.check for n in check_narrative("{{fact:123}}", FACTS)] == ["reference_malformed"]
    assert [n.check for n in check_narrative(f"{{{{fact:{A}|euros}}}}", FACTS)] == ["format_unknown"]


def test_dates_sections_and_words_do_not_trip_the_check():
    text = (f"For the quarter ended September 30, 2026 (Q3 2026), under Section 7.11(a) as amended by "
            f"Amendment No. 2, coverage was {{{{fact:{A}}}}} over the trailing twelve months.")
    assert check_narrative(text, FACTS) == []


@pytest.mark.parametrize("fact,fmt,expected", [
    (FactView("x", D("4187345"), "usd"), None, "$4,187,345"),
    (FactView("x", D("-1200.5"), "usd"), None, "($1,201)"),
    (FactView("x", D("4187345"), "usd"), "usd_k", "$4,187 thousand"),
    (FactView("x", D("4150000"), "usd"), "usd_m", "$4.2 million"),
    (FactView("x", D("1.245"), "ratio"), None, "1.25x"),
    (FactView("x", D("0.1254"), "pct"), None, "12.5%"),
    (FactView("x", D("46.5"), "days"), None, "47 days"),
    (FactView("x", D("17"), "count"), None, "17"),
])
def test_format_fact_rounds_half_up(fact, fmt, expected):
    assert format_fact(fact, fmt) == expected


def test_policy_only_makes_a_recommendation_more_cautious():
    base = dict(steps_count=5, governing_passed=True, governing_headroom_pct=D("0.04"), surviving_claims=2)
    assert apply_policy("resolve", text="Explained by the amendment.", **base).recommendation == "resolve"
    assert apply_policy("resolve", text="We should waive the covenant.", **base).recommendation == "escalate"
    assert apply_policy("resolve", text="ok", **{**base, "steps_count": 12}).recommendation == "abstain"
    assert apply_policy("resolve", text="ok", **{**base, "governing_passed": False}).recommendation == "escalate"
    assert apply_policy("resolve", text="ok", **{**base, "surviving_claims": 0}).recommendation == "escalate"
    assert apply_policy("request", text="ok", **{**base, "governing_headroom_pct": D("-0.20")}).recommendation == "escalate"
    assert apply_policy("abstain", text="contact the borrower", **base).recommendation == "abstain"
    assert apply_policy("escalate", text="ok", **base).recommendation == "escalate"

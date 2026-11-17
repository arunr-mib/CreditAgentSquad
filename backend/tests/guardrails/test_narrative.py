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


# ---- found by the independent review: figures that slipped past as "not a figure" --------------

_RATIO = "11111111-1111-4111-8111-111111111111"
_USD = "22222222-2222-4222-8222-222222222222"
_FACTS = {_RATIO: FactView(_RATIO, D("3.62"), "ratio"), _USD: FactView(_USD, D("48250000"), "usd")}


@pytest.mark.parametrize("text", [
    "EBITDA was USD4,500,000 for the period.",
    "EBITDA was USD-4,500,000 for the period.",
    "Leverage improved to x-3.25 against the covenant.",
    "Leverage stood at ratio-3.1 for the quarter.",
    "Leverage of approx.3.10 is compliant.",
    "Revenue was EUR12.5m.",
    "Revenue reached Item 4,500,000 in the period.",
    "Total debt per Note 4500000 is unchanged.",
    "Headroom per Schedule 2.75x is ample.",
    "EBITDA of 2050 covers interest.",
    "Capex was (12) and distributions (45).",
    "Revenue grew ¹² percent.",
    "Revenue grew ４５００ over the year.",
    "Cash fell to Mar 4500 levels.",
    "Leverage 3/25/100 basis.",
    "Borrower paid 1st and 2nd 4500000th dollars.",
    "Revenue of v48250 thousand.",
    "Leverage was four point two times, well inside the covenant.",
    "EBITDA fell to twelve million dollars.",
    "Margin fell by fifteen percent.",
    "Leverage is half of last year and EBITDA has doubled.",
    "Revenue was several million higher.",
])
def test_a_typed_quantity_is_refused_however_it_is_dressed(text):
    assert check_narrative(text, _FACTS), text


@pytest.mark.parametrize("text", [
    f"Revenue of {{{{fact:{_USD}}}}},000.",
    f"Leverage of 1{{{{fact:{_RATIO}}}}}.",
    f"Leverage of {{{{fact:{_RATIO}}}}}0 for the period.",
    f"Leverage of {{{{fact:{_RATIO}}}}} million.",
    f"Revenue {{{{fact:{_USD}|usd_k}}}} thousand thousand.",
    f"Revenue of ${{{{fact:{_USD}}}}}.",
    f"Margin of {{{{fact:{_RATIO}}}}}%.",
])
def test_text_joined_onto_a_reference_is_refused(text):
    assert "reference_joined" in {n.check for n in check_narrative(text, _FACTS)}, text


@pytest.mark.parametrize("fid,fmt", [(_RATIO, "pct"), (_RATIO, "usd_m"), (_USD, "ratio"), (_USD, "days"), (_USD, "pct")])
def test_a_format_that_does_not_fit_the_unit_is_refused_and_never_applied(fid, fmt):
    text = f"The figure was {{{{fact:{fid}|{fmt}}}}} for the period."
    assert "format_wrong_for_unit" in {n.check for n in check_narrative(text, _FACTS)}
    # even unchecked, the renderer falls back to the unit's own format
    assert render(text, _FACTS) == f"The figure was {format_fact(_FACTS[fid])} for the period."


@pytest.mark.parametrize("text", [
    f"Total leverage was {{{{fact:{_RATIO}}}}} at September 30, 2026, against the maximum in Section 7.11(a).",
    f"Revenue of {{{{fact:{_USD}|usd_m}}}} for the nine months ended 2026-09-30 was below the prior year.",
    f"Revenue ({{{{fact:{_USD}}}}}) fell; leverage rose to {{{{fact:{_RATIO}}}}}, and the trend continued in Q3 2026.",
    "The borrower has two facilities and one open exception; the amendment (Amendment No. 2) is not yet approved.",
    "Results for the first half of the year were stronger than the second half.",
    "Statements were delivered late for the quarter and the certificate was received on October 30, 2026.",
    "Since 2024 the company has reported on a trailing twelve month basis under clauses (a) and (b).",
    "Covenant headroom has narrowed for three quarters in a row.",
])
def test_ordinary_commentary_is_not_refused(text):
    assert check_narrative(text, _FACTS) == [], [n.detail for n in check_narrative(text, _FACTS)]

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
    base = dict(cap_reached=False, governing_passed=True, governing_headroom_pct=D("0.04"), surviving_claims=2)
    assert apply_policy("resolve", text="Explained by the amendment.", **base).recommendation == "resolve"
    assert apply_policy("resolve", text="We should waive the covenant.", **base).recommendation == "escalate"
    assert apply_policy("resolve", text="ok", **{**base, "cap_reached": True}).recommendation == "abstain"
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
    f"Revenue of {{{{fact:{_USD}}}}} fell; leverage rose to {{{{fact:{_RATIO}}}}}, and the trend continued in Q3 2026.",
    "The borrower has two facilities and one open exception; the amendment (Amendment No. 2) is not yet approved.",
    "Results for the first half of the year were stronger than the second half.",
    "Statements were delivered late for the quarter and the certificate was received on October 30, 2026.",
    "Since 2024 the company has reported on a trailing twelve month basis under clauses (a) and (b).",
    "Covenant headroom has narrowed for three quarters in a row.",
])
def test_ordinary_commentary_is_not_refused(text):
    assert check_narrative(text, _FACTS) == [], [n.detail for n in check_narrative(text, _FACTS)]


# ---- second independent review: every kind of "allowed" digit was used to carry an amount -------

@pytest.mark.parametrize("text", [
    "Leverage above 4 may trigger a default under the agreement.",          # "4 may" read as a date
    "Total leverage reached 5 Mar quarter-end, against a limit of 3 Dec onward.",
    "Total leverage (4) is above the covenant maximum (3).",                # list markers
    "Revenue is up-12 percent and EBITDA down-30 percent year over year.",  # identifiers
    "Leverage closed the quarter sub-4 and coverage near-1.",
    "Trailing EBITDA (ebitda_4500000) covers interest (ratio_3_2).",
    "Leverage stood at Note 4.25 against a maximum in Item 3.5.",           # references
    "The borrower reports leverage on Page 5 and coverage on Page 1.",
    "EBITDA came in 2040 and capex ended 1995, both in thousands.",         # years
    "Leverage v4 exceeds covenant v3.", "Leverage ratio No. 4 against limit No. 3.", "Leverage sits in the 4th turn.",
    "Leverage rose to four and a half times.", "Leverage is now four turns against a limit of three.",
    "Availability fell to zero and EBITDA was nil for the quarter.",
    "Revenue fell by nearly a quarter and margin by two-thirds.",
    "EBITDA is in the tens of millions and debt in the hundreds of millions.",
    "The borrower drew a dozen times; losses reached seven figures.",
    "Coverage fell below one. Leverage is above four.",
    "Revenue quintupled; costs rose sixfold; debt rose a hundredfold.",
    "EBITDA fell by a half and debt rose by a third.", "Leverage is 4½ turns.", "Leverage is IV times.",
    "Leverage is ٤٫٢.", "EBITDA of ④ million.", "EBITDA of 4.5 MM", "USD 4.5mn",
])
def test_no_class_of_allowed_digits_or_words_carries_an_amount(text):
    assert check_narrative(text, _FACTS), text


@pytest.mark.parametrize("text", [
    f"Net loss was ({{{{fact:{_USD}}}}}).",                     # brackets read as a negative
    f"Cash on hand is {{{{fact:{_USD}}}}} K.", f"Cash on hand is {{{{fact:{_USD}}}}} (in thousands).",
    f"Cash on hand is {{{{fact:{_USD}}}}} in millions.", f"Count {{{{fact:{_USD}}}}}{{{{fact:{_USD}}}}} breaches.",
    f"Leverage improved by {{{{fact:{_RATIO}}}}} turns.", f"EBITDA fell minus {{{{fact:{_USD}}}}}.",
    f"Revenue was double {{{{fact:{_USD}}}}}.", f"Margin moved {{{{fact:{_RATIO}}}}} percentage points.",
])
def test_words_and_marks_around_a_reference_that_change_what_it_shows_are_refused(text):
    assert check_narrative(text, _FACTS), text


@pytest.mark.parametrize("text", [
    f"Net revenue for the nine months ended September 30, 2026 was {{{{fact:{_USD}|usd_m}}}}, up from the prior-year period.",
    f"Total leverage of {{{{fact:{_RATIO}}}}} exceeds the maximum permitted under Section 6.12(a) of the Credit Agreement.",
    "The borrower has breached the fixed charge coverage covenant for the second consecutive quarter.",
    "EBITDA margin compressed as two of the borrower's three largest customers reduced orders.",
    f"Receivables more than 90 days past due rose to {{{{fact:{_USD}}}}} and are excluded from the borrowing base.",
    "Collections slowed, consistent with the trend noted in Q2 2026.",
    "The FY2025 audited statements were received on March 14, 2026, inside the 120-day reporting requirement.",
    "Management attributes the decline to a one-time inventory write-down and expects margins to recover in the second half.",
    "We recommend a waiver of the Q3 breach, conditional on delivery of a 13-week cash flow forecast.",
    f"Liquidity is adequate: cash of {{{{fact:{_USD}}}}} covers the next twelve months of scheduled principal.",
    "Amendment No. 2, effective July 1, 2026, reset the fixed charge coverage minimum; see Section 6.12(b).",
    f"Revenue of {{{{fact:{_USD}}}}} is down, the first decline since 2023, driven by the loss of the top-10 customer noted in the 10-K.",
])
def test_what_a_credit_analyst_would_honestly_write_is_let_through(text):
    assert check_narrative(text, _FACTS) == [], [n.subject for n in check_narrative(text, _FACTS)]


# ---- third independent review: the allowances made for honest prose were used to carry figures --

@pytest.mark.parametrize("text", [
    "Receivables are now collected on a 74-day cycle.", "The largest customer is 120 days past due.",
    "Revenue is a third lower than a year ago.", "EBITDA fell a fifth while debt rose a quarter.",
    "Gross margin has slipped into the low twenties.", "DSO is now in the high seventies.",
    "Fixed charge coverage is one-to-one.", "Leverage trebled over the year.",
    "A couple of turns of leverage were added in the buyout.", "Liquidity covers four months of fixed charges.",
    f"Revenue was {{{{fact:{_USD}}}}} (figures in thousands).", f"Revenue was {{{{fact:{_USD}}}}}, in thousands.",
    f"Revenue was {{{{fact:{_USD}}}}} (USD millions).", f"Revenue was {{{{fact:{_USD}}}}}, stated in millions.",
    "Leverage stood at Section 4.25 against the limit of Section 3.50.", "Leverage is north of Schedule 4.5.",
    "EBITDA came in 2031 against plan.", f"Leverage was {{{{fact:{_RATIO}}}}} per quarter.",
    f"Net income was {{{{fact:{_USD}}}}} a month.", f"Revenue rose {{{{fact:{_USD}}}}}-fold.",
    "The line is fully drawn and availability is nil.",
    "Top 10 customers are 90 days past due on the 180-day terms.",
])
def test_the_allowances_for_honest_prose_do_not_carry_a_figure(text):
    assert check_narrative(text, _FACTS), text


@pytest.mark.parametrize("text", [
    f"Revenue for the nine months was {{{{fact:{_USD}}}}}, up from {{{{fact:{_USD}}}}} a year earlier.",
    f"Fixed charge coverage fell to {{{{fact:{_RATIO}}}}}, below the minimum required by Section 6.12(b) of the credit agreement.",
    f"Margin narrowed to {{{{fact:{_RATIO}}}}} in the third quarter of 2025.",
    f"Leverage ({{{{fact:{_RATIO}}}}}) remains above the limit ({{{{fact:{_RATIO}}}}}) for the second consecutive quarter.",
    f"Revenue grew to {{{{fact:{_USD}}}}} compared with 2025, while gross margin held steady.",
    "The borrower has reported late in three of the last four quarters.",
    f"Net income of {{{{fact:{_USD}|usd_k}}}} for the first nine months of 2026 was lower than the same period last year.",
    "Receivables more than 90 days past due are excluded, and a 13-week cash flow forecast was requested.",
])
def test_the_third_reviewers_honest_sentences_are_let_through(text):
    assert check_narrative(text, _FACTS) == [], [n.subject or n.detail for n in check_narrative(text, _FACTS)]


# ---- first run with a real model (18 November 2026): honest sentences the strict check dropped --

@pytest.mark.parametrize("text", [
    f"Trailing twelve-month revenue rose from {{{{fact:{_USD}}}}} to {{{{fact:{_USD}}}}}.",
    f"Last twelve-month EBITDA was {{{{fact:{_USD}}}}}.",
    f"The certificate figures match the bank's calculations for all three covenants: {{{{fact:{_RATIO}}}}}.",
    "The reported figures agree with the spread.",
])
def test_sentences_from_the_first_live_run_are_let_through(text):
    assert [n.check for n in check_narrative(text, _FACTS)] == []


@pytest.mark.parametrize("text", [
    "Losses reached seven figures.", "The borrower booked a six-figure loss.", "Margins are in the high single figures.",
    "Cash gives a six-month runway.", "Trailing twelve-month cover is thin.", "Twelve months of revenue were lost.",
    "Revenue over the twelve-month period fell by four.", "The trailing twelve months of payroll were unpaid.",
])
def test_the_narrowed_rules_still_refuse_an_amount_in_words(text):
    assert "number_in_words" in [n.check for n in check_narrative(text, _FACTS)]


@pytest.mark.parametrize("text", [
    # the Spreading Agent's note from the live run of 19 November 2026, withheld before this rule
    "The debt schedule on page 5 (revolving line of credit, term notes payable, total debt outstanding) was not "
    "mapped as the template has no separate lines for it.",
    "The aging report on page 3 was read in full.",
    "The inventory listing on page 4 was not mapped.",
])
def test_a_page_of_the_document_is_let_through(text):
    assert [n.check for n in check_narrative(text, _FACTS)] == []


@pytest.mark.parametrize("text", [
    "Leverage stood on page 4.25 this quarter.",      # a decimal is a measurement, not a page
    "Revenue came from page 12,500 of sales.",       # a comma makes it an amount
    "The shortfall shown on page 5 percent.",
    "Coverage on page 3x is thin.",
    "The loss on page 7 million was booked.",
    "Leverage is page 4 against the limit.",          # no word that introduces a page
    "Margin fell 4 points, shown on page 2.",         # the page is allowed; the other figure is not
    "The ratio stood at 1,250 on page 5.",
    "Leverage on page 5 is above the limit.",         # a page after a measure, as a reviewer used it
    "See page 4 for leverage.",                       # no part of a document named before the page
    "The schedule on page 4.25 shows leverage.",
])
def test_a_page_reference_cannot_carry_a_figure(text):
    assert [n.check for n in check_narrative(text, _FACTS)] != []

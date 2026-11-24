"""Each normalisation rule is tested for what it must refuse and what it must still allow."""
from decimal import Decimal as D

import pytest
from app.guardrails.numbers import (
    extract_figures,
    parse_printed_figure,
    same_number,
    untraceable_figures,
)


def values(text, known_ratios=()):
    return [f.value for f in extract_figures(text, known_ratios)]


# --- basic reading ---------------------------------------------------------------------------

def test_commas_currency_and_decimals():
    assert values("Revenue was $4,187,345.50 and cash 950,000.") == [D("4187345.50"), D("950000")]


def test_accounting_negative_and_minus_sign():
    assert values("a net loss of (1,200) and a change of -350") == [D("-1200"), D("-350")]


def test_bracketed_ratio_and_percent_stay_positive():
    figs = extract_figures("coverage (1.25x) and margin (12.5%)")
    assert [(f.value, f.kind) for f in figs] == [(D("1.25"), "ratio"), (D("12.5"), "percent")]


def test_scale_suffix_counts_only_when_attached():
    assert values("about $4.2m of debt") == [D("4200000")]
    assert values("over 12 months") == [D("12")]  # not twelve million
    assert values("3 banks and 5 managers") == [D("3"), D("5")]  # not 3 billion, not 5 million


def test_scale_words_after_a_space():
    assert values("$4.2 million and 1.5 billion") == [D("4200000"), D("1500000000")]


def test_range_reads_both_ends_as_positive():
    assert values("between 10-15 customers") == [D("10"), D("15")]


# --- things that are not figures --------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "as of 2026-09-30",
    "dated 9/30/2026",
    "on September 30, 2026",
    "on 30 September 2026",
    "in March 2026",
    "for Q3 2026 and Q2-2026 and 3Q26",
    "in FY2025 and FY 2024",
    "terms version 3 (v3)",
    "under Section 7.11(a) and §6.2 and Article IV",
    "see Exhibit B-2, Schedule 1.1 and Amendment No. 2",
    "the 2nd amendment",
    "calc_3f9a2b and run-7 and doc_12",
    "fact 3f2b8c1e-9d4a-4c1b-8f6e-2a7b9c0d1e2f",
    "{{fact:3f2b8c1e-9d4a-4c1b-8f6e-2a7b9c0d1e2f|usd_m}}",
    "items (1) and (2) and (iv) and (a)",
    "during 2025 and again in 2026",
])
def test_not_figures(text):
    assert values(text) == []


def test_a_year_like_amount_with_currency_or_comma_is_still_a_figure():
    assert values("capex of $2025") == [D("2025")]
    assert values("capex of 2,025") == [D("2025")]
    assert values("a ratio of 2025x") == [D("2025")]


def test_bracketed_amount_is_not_mistaken_for_a_list_number():
    assert values("net loss (120)") == [D("-120")]
    assert values("loss of (1,200)") == [D("-1200")]


def test_section_reference_does_not_swallow_a_following_figure():
    assert values("Section 7.1 requires 1.25x") == [D("1.25")]


# --- "N to 1" ---------------------------------------------------------------------------------

def test_to_one_is_dropped_only_for_a_known_ratio():
    assert values("not less than 1.25 to 1.00", known_ratios=[D("1.25")]) == [D("1.25")]
    assert values("not less than 1.25:1", known_ratios=[D("1.25")]) == [D("1.25")]
    # unknown ratio: the 1.00 stays and must be traced like any other figure
    assert values("not less than 1.40 to 1.00", known_ratios=[D("1.25")]) == [D("1.40"), D("1.00")]


def test_to_one_at_the_end_of_a_sentence_is_dropped_but_a_decimal_is_not_cut():
    # found by the Terms Agent: "...exceed 2.00 to 1.00." ends with a full stop
    assert values("shall not exceed 2.00 to 1.00.", known_ratios=[D("2.00")]) == [D("2.00")]
    assert values("a ratio of 2.00 to 1.00, tested quarterly", known_ratios=[D("2.00")]) == [D("2.00")]
    # "1.5" is not "1" followed by a full stop: the figure is kept whole
    assert values("moved from 2.00 to 1.5 over the year", known_ratios=[D("2.00")]) == [D("2.00"), D("1.5")]


def test_to_one_does_not_create_a_phantom_from_a_range_of_amounts():
    assert values("fell from 2,400,000 to 1,900,000", known_ratios=[D("2400000")]) == [
        D("2400000"), D("1900000")]


# --- tracing ----------------------------------------------------------------------------------

def test_traceable_figures_pass_and_strays_are_reported():
    allowed = [D("1.18"), D("1.25"), D("620000")]
    assert untraceable_figures("DSCR of 1.18x against a 1.25x minimum; add-back 620,000.", allowed) == []
    problems = untraceable_figures("DSCR of 1.28x against a 1.25x minimum.", allowed)
    assert [p.figure.value for p in problems] == [D("1.28")]


def test_percent_matches_either_form():
    assert untraceable_figures("margin of 12.5%", [D("0.125")]) == []
    assert untraceable_figures("margin of 12.5%", [D("12.5")]) == []
    assert len(untraceable_figures("margin of 12.5%", [D("0.13")])) == 1


def test_unsigned_prose_matches_a_negative_fact_but_not_the_reverse():
    assert untraceable_figures("a net loss of 1,200", [D("-1200")]) == []
    assert len(untraceable_figures("a gain of (1,200)", [D("1200")])) == 1


def test_quoted_covenant_figures_are_valid_when_allowed():
    # the trap: accepting only calculated numbers would abstain on every good explanation
    text = "The agreement requires 1.25 to 1.00; the calculated ratio is 1.31x."
    assert untraceable_figures(text, [D("1.31")], known_ratios=[D("1.25")]) == []


def test_same_number_tolerance():
    assert same_number(D("1.2500001"), D("1.25"))
    assert not same_number(D("1.26"), D("1.25"))
    assert same_number(D("4187345"), D("4187345.000001"))


# --- figures as printed in a statement cell ---------------------------------------------------

@pytest.mark.parametrize("text,value", [
    ("1,234", D("1234")), ("$ 1,234", D("1234")), ("(1,234)", D("-1234")), ("$(1,234)", None),
    ("($1,234)", D("-1234")), ("-1,234", D("-1234")), ("1.25x", D("1.25")), ("12.5%", D("12.5")),
    ("0", D("0")),
])
def test_parse_printed_figure(text, value):
    parsed = parse_printed_figure(text)
    assert (parsed.value if parsed else None) == value


def test_parse_printed_dash_is_zero_and_flagged():
    parsed = parse_printed_figure("—")
    assert parsed.value == 0 and parsed.is_dash


@pytest.mark.parametrize("text", ["(1,234", "1,234)", "1,234 5,678", "about 1,234", "", "n/a", "1,23,4"])
def test_parse_printed_figure_refuses_anything_unclear(text):
    assert parse_printed_figure(text) is None

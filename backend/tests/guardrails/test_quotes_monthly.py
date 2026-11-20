"""Monthly period phrases: number words one..twelve, "month ended", "for the month of"."""
from datetime import date

import pytest
from app.guardrails.quotes import column_for_period, durations_in, locate
from tests.guardrails.test_quotes import right, row


@pytest.mark.parametrize("heading,months", [
    ("For the ten months ended October 31, 2026", {10}),
    ("One month ended October 31, 2026", {1}),
    ("For the month ended October 31, 2026", {1}),
    ("For the month of October 2026", {1}),
    ("Nine months ended September 30, 2026", {9}),
    ("Three months ended September 30, 2026", {3}),
    ("Year ended December 31, 2025", {12}),
    ("Eleven months ended November 30, 2026", {11}),
    ("2 months ended February 28, 2026", {2}),
    ("12 months ended December 31, 2026", {12}),
])
def test_period_phrases(heading, months):
    assert durations_in(heading) == months


@pytest.mark.parametrize("n,word", list(enumerate(
    "one two three four five six seven eight nine ten eleven twelve".split(), start=1)))
def test_every_number_word_and_digit(n, word):
    assert durations_in(f"{word.title()} months ended June 30, 2026") == {n}
    assert durations_in(f"{n} months ended June 30, 2026") == {n}


def test_a_ten_month_header_still_places_the_column_and_a_row_label_with_ten_parses():
    page = (row(20, right(500, "Ten months ended October 31, 2026"),
                right(900, "Ten months ended October 31, 2025"))
            + row(60, (40, "Ten largest customers revenue"), right(500, "48,250"), right(900, "45,100")))
    figure = locate(page, "48,250")[0].bbox
    assert column_for_period(page, figure, date(2026, 10, 31), 10) is None
    assert column_for_period(page, figure, date(2026, 10, 31), 9) is not None
    assert column_for_period(page, locate(page, "45,100")[0].bbox, date(2026, 10, 31), 10) is not None


def test_three_and_nine_month_columns_are_still_told_apart():
    page = (row(20, right(500, "Three months ended September 30, 2026"),
                right(900, "Nine months ended September 30, 2026"))
            + row(60, (40, "Net revenue"), right(500, "48,250"), right(900, "140,000")))
    period = date(2026, 9, 30)
    assert column_for_period(page, locate(page, "48,250")[0].bbox, period, 3) is None
    assert column_for_period(page, locate(page, "140,000")[0].bbox, period, 9) is None
    assert column_for_period(page, locate(page, "140,000")[0].bbox, period, 3) is not None

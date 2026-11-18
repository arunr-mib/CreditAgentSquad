from decimal import Decimal as D

from app.guardrails.quotes import locate, number_in_quote, quote_on_page, row_label, verify_cell


def row(y, *cells):
    """Build words for one printed row: (x0, text) pairs; each word is 8 points per character."""
    words = []
    for x0, text in cells:
        x = x0
        for token in text.split():
            words.append([x, y, x + 8 * len(token), y + 10, token])
            x += 8 * len(token) + 4
    return words


def right(x1, text):
    """A right-aligned cell ending at x1."""
    return (x1 - 8 * len(text), text)


PAGE = (
    row(40, (300, "September 30, 2026"), (460, "September 30, 2025"))
    + row(60, (40, "Net revenue"), right(440, "$ 48,250"), right(600, "$ 45,100"))
    + row(75, (40, "Cost of goods sold"), right(440, "(33,775)"), right(600, "(31,120)"))
    + row(90, (40, "Gross profit"), right(440, "14,475"), right(600, "13,980"))
    + row(105, (40, "Interest expense"), right(440, "(1,200)"), right(600, "(1,200)"))
)


def test_locate_whole_words_only():
    assert len(locate(PAGE, "48,250")) == 1
    assert locate(PAGE, "8,250") == []  # part of a number is not a match
    assert len(locate(PAGE, "$ 48,250")) == 1 and len(locate(PAGE, "$48,250")) == 1
    assert len(locate(PAGE, "Cost of goods sold")) == 1


def test_verified_cell_returns_value_parsed_from_the_page():
    check = verify_cell(PAGE, printed_figure="(33,775)", printed_label="Cost of goods sold",
                        column_header="September 30, 2026")
    assert check.ok and check.value == D("-33775") and check.bbox is not None


def test_figure_printed_without_brackets_is_not_found_when_the_page_has_brackets():
    # the model dropped the brackets: refuse, so a sign is never lost
    assert verify_cell(PAGE, printed_figure="33,775", printed_label="Cost of goods sold").status == "not_found"


def test_figure_on_the_wrong_row_is_refused():
    check = verify_cell(PAGE, printed_figure="14,475", printed_label="Net revenue")
    assert check.status == "label_mismatch"


def test_prior_year_column_is_not_accepted_for_the_current_column():
    check = verify_cell(PAGE, printed_figure="45,100", printed_label="Net revenue",
                        column_header="September 30, 2026")
    assert check.status == "column_unconfirmed"
    ok = verify_cell(PAGE, printed_figure="45,100", printed_label="Net revenue",
                     column_header="September 30, 2025")
    assert ok.ok and ok.value == D("45100")


def test_same_figure_in_both_columns_resolves_by_header():
    check = verify_cell(PAGE, printed_figure="(1,200)", printed_label="Interest expense",
                        column_header="September 30, 2026")
    assert check.ok and check.value == D("-1200") and check.bbox[2] <= 441


def test_missing_label_or_unreadable_figure_is_refused():
    assert verify_cell(PAGE, printed_figure="48,250", printed_label="Total revenue").status == "label_mismatch"
    assert verify_cell(PAGE, printed_figure="about 48,250").status == "unparseable"
    assert verify_cell(PAGE, printed_figure="99,999").status == "not_found"


def test_quote_on_page_ignores_line_breaks_and_typographic_variants():
    page = "7.11 Fixed Charge Coverage Ratio. Borrower shall not permit the Fixed Charge\nCoverage Ratio to be less than 1.20 to 1.00 – tested quarterly."
    assert quote_on_page(page, "shall not permit the Fixed Charge Coverage Ratio to be less than 1.20 to 1.00 - tested")
    assert not quote_on_page(page, "to be less than 1.25 to 1.00")
    assert not quote_on_page(page, "   ")


def test_number_in_quote():
    quote = "an advance rate of 85% of Eligible Accounts, not to exceed $5,000,000"
    assert number_in_quote(D("0.85"), quote) and number_in_quote(D("5000000"), quote)
    assert not number_in_quote(D("0.80"), quote)
    assert number_in_quote(D("1.20"), "less than 1.20 to 1.00", known_ratios=[D("1.20")])


# --- the row label is read by code, and the column is fixed by the period's date ---------------

def test_row_label_is_everything_left_of_the_first_figure_on_the_row():
    check = verify_cell(PAGE, printed_figure="(33,775)", printed_label="goods sold",
                        column_header="September 30, 2026")
    assert check.ok and check.row_label == "Cost of goods sold"  # the fragment the reader chose is not the label
    prior = verify_cell(PAGE, printed_figure="45,100", printed_label="Net revenue",
                        column_header="September 30, 2025")
    assert prior.ok and prior.row_label == "Net revenue"  # the current-year figure and the $ are not part of it


def test_row_label_stops_at_a_dash_cell_and_skips_leader_dots():
    page = row(40, (300, "September 30, 2026"), (460, "September 30, 2025")) + row(
        60, (40, "Subordinated debt ......"), right(440, "—"), right(600, "1,250"))
    figure = locate(page, "1,250")[0]
    assert row_label(page, figure.bbox) == "Subordinated debt"


def test_a_header_spanning_two_columns_does_not_place_a_figure_in_the_current_one():
    wide = "September 30, 2026 September 30, 2025"
    assert verify_cell(PAGE, printed_figure="45,100", printed_label="Net revenue", column_header=wide).ok
    anchored = verify_cell(PAGE, printed_figure="45,100", printed_label="Net revenue", column_header=wide,
                           column_anchor="September 30, 2026")
    assert anchored.status == "column_unconfirmed"
    assert verify_cell(PAGE, printed_figure="48,250", printed_label="Net revenue", column_header=wide,
                       column_anchor="September 30, 2026").ok


def test_a_quote_may_not_begin_or_end_inside_a_number_or_a_word():
    page = "The Borrower shall not permit the ratio to be less than 1.20 to 1.00. Reserves of $12,000,000 apply."
    assert quote_on_page(page, "to be less than 1.20 to 1.00")
    assert quote_on_page(page, "less than 1.20 to 1.00.")
    assert not quote_on_page(page, "0 to 1.00")          # inside 1.20
    assert not quote_on_page(page, "2,000,000")          # inside 12,000,000
    assert not quote_on_page(page, "less than 1.2")      # stops inside 1.20
    assert not quote_on_page(page, "orrower shall not")  # starts inside a word
    assert quote_on_page(page, "$12,000,000") and quote_on_page(page, "12,000,000 apply")


# ---- third independent review: column geometry ---------------------------------------------------

def _figure(words, text):
    return locate(words, text)[0].bbox


def test_a_budget_or_pro_forma_column_is_not_the_period_whatever_date_stands_over_it():
    from datetime import date

    from app.guardrails.quotes import column_for_period
    period = date(2026, 9, 30)
    page = (row(20, right(440, "September 30, 2026"), right(600, "September 30, 2026"))
            + row(32, right(440, "Actual"), right(600, "Budget"))
            + row(60, (40, "Net revenue"), right(440, "48,250"), right(600, "52,000")))
    assert column_for_period(page, _figure(page, "52,000"), period) is not None
    page = (row(20, right(600, "Pro forma")) + row(32, right(440, "September 30, 2026"), right(600, "September 30, 2026"))
            + row(60, (40, "Net revenue"), right(440, "48,250"), right(600, "55,900")))
    assert column_for_period(page, _figure(page, "55,900"), period) is not None
    assert column_for_period(page, _figure(page, "48,250"), period) is None


def test_a_row_with_a_blank_current_cell_does_not_make_the_prior_figure_current():
    from datetime import date

    from app.guardrails.quotes import column_for_period
    page = (row(20, right(440, "September 30, 2026"), right(600, "September 30, 2025"))
            + row(60, (40, "Net revenue"), right(440, "48,250"), right(600, "45,100"))
            + row(75, (40, "Financed capital expenditures"), right(600, "120")))
    assert column_for_period(page, _figure(page, "120"), date(2026, 9, 30), 9) is not None
    assert column_for_period(page, _figure(page, "120"), date(2025, 9, 30), 9) is None

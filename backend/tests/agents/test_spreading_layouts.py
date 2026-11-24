"""Page layouts and printing habits found by the second independent review (2026-11-17).

Each layout is tested both ways: a reader that takes figures from the wrong column, row or page
is held for a person, and an honest reading of the same layout is spread with no person.
"""
import copy
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.spreading import spread_document
from app.core.config import get_settings
from app.domain import corrections
from app.domain.credit import Borrower
from app.domain.documents_service import ingest_pdf
from app.domain.facts import Fact
from app.domain.facts_service import confirm_fact, current_fact, label_confirmed
from app.domain.monitoring import WorkItem
from app.domain.org import User
from sqlalchemy import select
from support import statement_pdf as sp
from support.layout_pdf import CUR, PRIOR, answer, cells, mk, std_header, std_rows

PERIOD = date(2026, 9, 30)
PRIOR_CASH = D(sp.PRIOR_FYE_CASH_THOUSANDS * 1000)
SUP = ("sup.cash_interest_paid", "sup.cash_taxes_paid", "sup.scheduled_principal", "sup.financed_capex")


@pytest.fixture()
def borrower(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    row = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add(row)
    db.flush()
    yield row
    get_settings.cache_clear()


def spread(db, borrower, reading, pdf, prior_cash=PRIOR_CASH, period=PERIOD, months=9):
    doc = ingest_pdf(db, borrower_id=borrower.id, data=pdf, file_name=f"statements-{period}.pdf",
                     doc_type="interim_statements", doc_type_source="system", period_end=period)
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(reading)}], stop_reason="end_turn")])
    return spread_document(db, borrower=borrower, document=doc, period_end=period, months=months, cycle=None,
                           llm=llm, prior_fye_cash=prior_cash)


def usable(db, borrower, key, months=9):
    fact = current_fact(db, borrower.id, key, PERIOD, 0 if key.startswith("bs.") else months)
    return None if fact is None else fact.value


def held(result):
    return {u["key"] for u in result.unverified}


def distinct_pages():
    """The standard statements with every supplemental figure different between the two columns."""
    pages = copy.deepcopy(sp.PAGES)
    change = {"bs.intangibles": "1,450", "bs.cpltd": "1,150", "cf.term_debt_repayments": "(850)",
              "sup.scheduled_principal": "450", "sup.financed_capex": "25"}
    for n in pages:
        pages[n] = [(k, lab, ("40" if k == "sup.financed_capex" else c), change.get(k, pr)) for k, lab, c, pr in pages[n]]
    return pages


def supplemental_from(pages, other_cells):
    other = {c["key"]: c for c in other_cells}
    return [other[c["key"]] if c["key"].startswith("sup.") else c for c in cells("current", pages=pages)]


def assert_supplemental_held(db, borrower, result):
    assert result.status == "needs_person" and set(SUP) <= held(result)
    assert all(usable(db, borrower, key) is None for key in SUP)
    assert db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).first() is not None


# ---- which column is the period ----------------------------------------------------------------

LAYOUTS = {
    "two-line header": lambda p: mk([{"pre": [("r", 440, 718, "September 30,"), ("r", 560, 718, "September 30,"),
                                              ("r", 440, 706, "2026"), ("r", 560, 706, "2025")],
                                      "rows": std_rows(n, pages=p)} for n in (1, 2, 3)]),
    "years under a centred date": lambda p: mk([{"pre": [("c", 490, 724, CUR), ("r", 470, 706, "2026"),
                                                         ("r", 540, 706, "2025")],
                                                 "rows": std_rows(n, cur_x=470, prior_x=540, pages=p)} for n in (1, 2, 3)]),
    "years under a dated subtitle": lambda p: mk([{"pre": [("r", 560, 724, f"As of and for the nine months ended {CUR}"),
                                                           ("r", 440, 706, "2026"), ("r", 560, 706, "2025")],
                                                   "rows": std_rows(n, pages=p)} for n in (1, 2, 3)]),
}


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_supplemental_lines_from_the_prior_year_column_are_held(db, borrower, layout):
    pages = distinct_pages()
    reading = answer(supplemental_from(pages, cells("prior", header=CUR, pages=pages)))
    assert_supplemental_held(db, borrower, spread(db, borrower, reading, LAYOUTS[layout](pages)))


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_the_whole_prior_year_column_is_refused_even_with_no_prior_cash_on_file(db, borrower, layout):
    pages = distinct_pages()
    result = spread(db, borrower, answer(cells("prior", header=CUR, pages=pages)), LAYOUTS[layout](pages), prior_cash=None)
    assert result.status == "needs_person"
    assert db.execute(select(Fact).where(Fact.borrower_id == borrower.id,
                                         Fact.status.in_(("verified", "confirmed", "proposed")))).first() is None


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_an_honest_reading_of_the_same_layout_needs_no_person(db, borrower, layout):
    pages = distinct_pages()
    result = spread(db, borrower, answer(cells("current", pages=pages)), LAYOUTS[layout](pages))
    assert result.status == "spread" and result.unverified == [], result.unverified[:3]
    assert usable(db, borrower, "sup.scheduled_principal") == D("900000")
    assert usable(db, borrower, "bs.total_assets") == D("34500000")


def quarter_pages():
    """Flow statements with a three-month column (x=440) and a nine-month column (x=560), both
    dated September 30, 2026; the three-month figures foot on their own."""
    q = copy.deepcopy(sp.PAGES)
    q[1] = [("is.revenue", "Net revenue", "$ 16,000", "$ 48,250"), ("is.cogs", "Cost of goods sold", "11,200", "33,775"),
            ("is.gross_profit", "Gross profit", "4,800", "14,475"),
            ("is.sga", "Selling, general and administrative", "2,700", "8,100"),
            ("is.depreciation_amortization", "Depreciation and amortization", "380", "1,150"),
            ("is.other_operating_expense", "Other operating expense", "130", "400"),
            ("is.nonrecurring_expense", "Restructuring and other non-recurring charges", "—", "620"),
            ("is.operating_income", "Operating income", "1,590", "4,205"),
            ("is.interest_expense", "Interest expense", "400", "1,200"),
            ("is.other_income_net", "Other income (expense), net", "25", "75"),
            ("is.pretax_income", "Income before taxes", "1,215", "3,080"),
            ("is.income_tax_expense", "Income tax expense", "290", "740"), ("is.net_income", "Net income", "$ 925", "$ 2,340")]
    q[3] = [("cf.net_income", "Net income", "$ 925", "$ 2,340"),
            ("cf.depreciation_amortization", "Depreciation and amortization", "380", "1,150"),
            ("cf.change_in_working_capital", "Changes in working capital", "(400)", "(1,090)"),
            ("cf.other_operating", "Other operating items", "15", "50"),
            ("cf.cfo", "Net cash from operating activities", "920", "2,450"),
            ("cf.capex", "Purchases of property and equipment", "(300)", "(1,400)"),
            ("cf.cfi", "Net cash from investing", "(300)", "(1,400)"),
            ("cf.revolver_net", "Net borrowings on line of credit", "100", "500"),
            ("cf.term_debt_repayments", "Repayments of long-term debt", "(300)", "(900)"),
            ("cf.distributions", "Distributions to owners", "(100)", "(600)"),
            ("cf.cff", "Net cash from financing", "(300)", "(1,000)"), ("cf.net_change_in_cash", "Net change in cash", "$ 320", "$ 50"),
            ("sup.cash_interest_paid", "Cash paid for interest", "390", "1,180"),
            ("sup.cash_taxes_paid", "Cash paid for income taxes", "100", "700"),
            ("sup.scheduled_principal", "Scheduled principal payments on term debt", "300", "900"),
            ("sup.financed_capex", "Capital expenditures financed with purchase-money debt", "40", "120")]
    return q


def quarter_pdf(q):
    flows = [("r", 440, 718, "Three months ended"), ("r", 560, 718, "Nine months ended"), ("r", 440, 706, CUR), ("r", 560, 706, CUR)]
    balance = [("r", 440, 706, CUR), ("r", 560, 706, PRIOR)]
    return mk([{"pre": flows, "rows": std_rows(1, pages=q)}, {"pre": balance, "rows": std_rows(2, pages=q)},
               {"pre": flows, "rows": std_rows(3, pages=q)}])


def quarter_cells(q, column_for):
    out = []
    for page, rows in q.items():
        for key, label, first, second in rows:
            figure = first if page == 2 or column_for(key) == "quarter" else second
            out.append({"key": ("stated." + key) if key in sp.COMPUTED else key, "page": page, "printed_figure": figure,
                        "printed_label": label, "column_header": CUR})
    return out


def test_two_columns_with_the_same_date_are_told_apart_by_length_of_period(db, borrower):
    q = quarter_pages()
    reading = answer(quarter_cells(q, lambda key: "quarter" if key.startswith("sup.") else "ytd"))
    assert_supplemental_held(db, borrower, spread(db, borrower, reading, quarter_pdf(q)))


def test_a_three_month_column_is_not_taken_as_nine_months(db, borrower):
    q = quarter_pages()
    result = spread(db, borrower, answer(quarter_cells(q, lambda key: "quarter")), quarter_pdf(q), prior_cash=None)
    assert result.status == "needs_person" and usable(db, borrower, "is.revenue") is None


def test_the_nine_month_column_of_that_layout_is_spread_with_no_person(db, borrower):
    q = quarter_pages()
    result = spread(db, borrower, answer(quarter_cells(q, lambda key: "ytd")), quarter_pdf(q))
    assert result.status == "spread" and result.unverified == [], result.unverified[:3]
    assert usable(db, borrower, "is.revenue") == D("48250000") and usable(db, borrower, "sup.financed_capex") == D("120000")


# ---- units, signs, duplicates, another entity ---------------------------------------------------

@pytest.mark.parametrize("phrase", ["(000's omitted)", "(in 000s)", "(000 omitted)", "(USD '000)", "(amounts in thousand)",
                                    "(expressed in $K)", "(in thousands of U.S. dollars)"])
def test_a_thousands_phrase_in_any_common_wording_is_read_as_thousands(db, borrower, phrase):
    result = spread(db, borrower, sp.perfect_answer(scale_statement=phrase), sp.build_pdf(scale_phrase=phrase), prior_cash=None)
    assert result.status == "spread", [n for n in result.notes if n.get("action") == "person"]
    assert usable(db, borrower, "is.revenue") == D("48250000")


@pytest.mark.parametrize("phrase,reported", [("(in millions)", "(in millions)"), ("(in millions)", ""),
                                             ("(000's omitted)", ""), ("(figures in lakhs)", "(figures in lakhs)")])
def test_units_that_are_not_understood_or_not_reported_go_to_a_person(db, borrower, phrase, reported):
    result = spread(db, borrower, sp.perfect_answer(scale_statement=reported, scale_page=1 if reported else 0),
                    sp.build_pdf(scale_phrase=phrase), prior_cash=None)
    assert result.status == "needs_person" and usable(db, borrower, "is.revenue") is None


def with_page_three(changes):
    pages = copy.deepcopy(sp.PAGES)
    pages[3] = [(k, lab, changes.get(k, c), pr) for k, lab, c, pr in pages[3]]
    return pages


@pytest.mark.parametrize("key,printed", [("sup.cash_taxes_paid", "(700)"), ("sup.scheduled_principal", "(900)")])
def test_a_figure_printed_in_brackets_where_only_a_positive_amount_is_expected_is_held(db, borrower, key, printed):
    pages = with_page_three({key: printed})
    pdf = mk([{"pre": std_header(), "rows": std_rows(n, pages=pages)} for n in (1, 2, 3)])
    result = spread(db, borrower, answer(cells("current", pages=pages)), pdf)
    assert result.status == "needs_person" and key in held(result) and usable(db, borrower, key) is None


def test_the_same_printed_figure_reported_several_times_is_not_added_up(db, borrower):
    pages = with_page_three({"sup.financed_capex": "400"})
    pdf = mk([{"pre": std_header(), "rows": std_rows(n, pages=pages)} for n in (1, 2, 3)])
    reading = cells("current", pages=pages)
    reading += [dict(next(c for c in reading if c["key"] == "sup.financed_capex"))] * 3
    result = spread(db, borrower, answer(reading), pdf)
    assert result.status == "needs_person" and usable(db, borrower, "sup.financed_capex") is None


def test_figures_from_another_entitys_pages_in_the_same_file_are_held(db, borrower):
    other = copy.deepcopy(sp.PAGES)
    other[3] = [(k, lab, {"sup.cash_interest_paid": "210", "sup.cash_taxes_paid": "95",
                          "sup.scheduled_principal": "150"}.get(k, c), p) for k, lab, c, p in other[3]]
    pages = [{"pre": std_header(), "rows": std_rows(n)} for n in (1, 2, 3)]
    pages += [{"pre": std_header(), "rows": std_rows(n, pages=other),
               "title": "Harrowgate Holdings, Inc. (parent company only)"} for n in (1, 2, 3)]
    theirs = {c["key"]: c for c in cells("current", pages=other, page_map={1: 4, 2: 5, 3: 6})}
    reading = [theirs[c["key"]] if c["key"].startswith("sup.") else c for c in cells("current")]
    result = spread(db, borrower, answer(reading), mk(pages))
    assert result.status == "needs_person" and {"sup.cash_interest_paid", "sup.scheduled_principal"} <= held(result)
    assert usable(db, borrower, "sup.scheduled_principal") is None


# ---- what a person's confirmation of a label is worth -------------------------------------------

def swapped(reading):
    for cell in reading:
        cell["key"] = {"bs.long_term_debt": "bs.other_noncurrent_liabilities",
                       "bs.other_noncurrent_liabilities": "bs.long_term_debt"}.get(cell["key"], cell["key"])
    return reading


@pytest.mark.parametrize("then", ["corrected", "rejected"])
def test_a_confirmed_label_stops_counting_once_the_figure_is_corrected_or_rejected(db, borrower, then):
    analyst = User(email="an@x.example", name="Analyst", role="analyst", password_hash="x")
    db.add(analyst)
    db.flush()
    june = date(2026, 6, 30)
    pdf = mk([{"pre": [("r", 440, 706, "June 30, 2026"), ("r", 560, 706, "June 30, 2025")], "rows": std_rows(n)}
              for n in (1, 2, 3)], scale_line="Unaudited, six months ended June 30, 2026 (in thousands)")
    first = spread(db, borrower, answer(swapped(cells("current", header="June 30, 2026"))), pdf, period=june, months=6)
    assert first.status == "needs_person"
    assert "filed under" in first.work_items[0].question  # the question is about the mapping, in so many words
    facts = [db.get(Fact, u["fact_id"]) for u in first.unverified]
    for fact in facts:
        confirm_fact(db, fact, analyst.id)
    assert label_confirmed(db, borrower.id, ["bs.long_term_debt"], "Other liabilities")
    for fact in facts:
        if then == "corrected":
            corrections.correct(db, fact, value=fact.value + 1, user_id=analyst.id, reason="Filed under the wrong line.")
        else:
            corrections.reject(db, fact, user_id=analyst.id, reason="Filed under the wrong line.")
    assert not label_confirmed(db, borrower.id, ["bs.long_term_debt"], "Other liabilities")
    again = spread(db, borrower, answer(swapped(cells("current"))), sp.build_pdf())
    assert again.status == "needs_person" and usable(db, borrower, "bs.long_term_debt") is None


# ---- third independent review: blocks stacked on one page, and a document for another company ----

QUARTER_BLOCK = [("sup.cash_interest_paid", "Cash paid for interest", "390", "380"),
                 ("sup.cash_taxes_paid", "Cash paid for income taxes", "100", "260"),
                 ("sup.scheduled_principal", "Scheduled principal payments on term debt", "300", "300"),
                 ("sup.financed_capex", "Capital expenditures financed with purchase-money debt", "1,150", "40")]


def stacked_pdf():
    """Page three carries the nine-month figures, then a second block headed "Three months ended"."""
    page_three = [("Nine months ended September 30, 2026", {})] + std_rows(3) + [("", {}),
                 ("Three months ended September 30, 2026", {})] + \
                 [(label, {440: cur, 560: prior}) for _key, label, cur, prior in QUARTER_BLOCK]
    return mk([{"pre": std_header(), "rows": std_rows(1)}, {"pre": std_header(), "rows": std_rows(2)},
               {"pre": std_header(), "rows": page_three, "y0": 690, "dy": 14}])


def test_figures_from_a_three_month_block_lower_on_the_page_are_held(db, borrower):
    quarter = {key: figure for key, _label, figure, _prior in QUARTER_BLOCK}
    reading = [{**c, "printed_figure": quarter[c["key"]]} if c["key"] in quarter else c for c in cells("current")]
    result = spread(db, borrower, answer(reading), stacked_pdf())
    assert result.status == "needs_person"
    assert all(usable(db, borrower, key) is None for key in ("sup.cash_interest_paid", "sup.scheduled_principal"))


def test_the_nine_month_block_of_that_page_is_spread_with_no_person(db, borrower):
    result = spread(db, borrower, answer(cells("current")), stacked_pdf())
    assert result.status == "spread" and result.unverified == [], result.unverified[:3]
    assert usable(db, borrower, "sup.cash_interest_paid") == D("1180000")


def test_a_document_that_names_only_another_company_is_not_read(db, borrower):
    pages = [{"pre": std_header(), "rows": std_rows(n), "title": "Northfield Castings Group, LLC"} for n in (1, 2, 3)]
    result = spread(db, borrower, answer(cells("current")), mk(pages))
    assert result.status == "needs_person"
    assert db.execute(select(Fact).where(Fact.borrower_id == borrower.id)).first() is None
    item = db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).scalar_one()
    assert "another company" in item.question

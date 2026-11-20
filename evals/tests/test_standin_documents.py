"""The stand-in reads every document of both books the way a careful reader would, and where print and
truth disagree the disagreement is recorded, not smoothed. Builds requests straight from the PDFs."""
import base64
import json
from datetime import date

import pymupdf
import pytest
from app.agents.llm import LLMRequest

from evals.book import BOOKS, load_book
from evals.standin import StandInReader, _lines

READ = ("monthly_financials", "mrr_report", "bank_statement", "annual_financial_statements",
        "interim_financial_statements")


def _request(book, borrower, meta, agent):
    data = (book.root / meta["path"]).read_bytes()
    block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                            "data": base64.standard_b64encode(data).decode()}}
    text = "Spread the statements."
    if agent == "certificate":
        covenants = [c for v in borrower.truth["terms_versions"] for c in v["terms"]["covenants"]]
        text = "Covenants:\n" + "\n".join(f"- {c['id']} | {c['name']}" for c in covenants)
    key = f"{agent}/{borrower.code}/{meta['period_end']}" + ("/x" if agent == "spreading" else "")
    return LLMRequest(model="m", system="", messages=[{"role": "user", "content": [block, {"type": "text", "text": text}]}],
                      record_key=key)


def _answer(reader, request):
    return json.loads(reader.create(request).content[0]["text"])


@pytest.mark.parametrize("name", ["legacy", "innovation"])
def test_every_pack_mrr_report_and_bank_statement_is_read_in_full(name):
    book = load_book(BOOKS[name])
    reader = StandInReader(book)
    short = []
    for borrower in book:
        for meta in borrower.truth["documents"]:
            if meta["type"] not in READ or "figures" not in meta or not (book.root / meta["path"]).exists():
                continue
            answer = _answer(reader, _request(book, borrower, meta, "spreading"))
            expected = {k for k in meta["figures"] if k not in meta.get("unreadable_keys", [])}
            got = {c["key"].removeprefix("stated.").replace("bank.", "bs.") for c in answer["cells"]}
            if expected - got:
                short.append((meta["id"], sorted(expected - got)[:4]))
    assert short == []
    assert reader.disagreements == []


def test_the_monthly_pack_reports_the_year_to_date_column_first():
    book = load_book(BOOKS["innovation"], ["ferrogate-cloud"])
    ferro = book.get("ferrogate-cloud")
    meta = ferro.document_by_file("mf-2026-10-31.pdf")
    answer = _answer(StandInReader(book), _request(book, ferro, meta, "spreading"))
    assert answer["cells"] and all(c["column_header"].startswith("October 31, 2026") or "2026" in c["column_header"]
                                   for c in answer["cells"])
    printed = {c["key"]: c["printed_figure"] for c in answer["cells"]}
    assert printed["stated.is.total_revenue"] == meta["figures"]["is.total_revenue"]["printed"]  # the ten-months column, not the month


@pytest.mark.parametrize("name", ["legacy", "innovation"])
def test_every_certificate_row_is_read_including_text_actuals_and_wrapped_cells(name):
    book = load_book(BOOKS[name])
    reader = StandInReader(book)
    for borrower in book:
        for meta in borrower.truth["documents"]:
            if meta["type"] != "compliance_certificate" or not (book.root / meta["path"]).exists():
                continue
            answer = _answer(reader, _request(book, borrower, meta, "certificate"))
            truth = borrower.certificate(date.fromisoformat(meta["period_end"]))
            assert {r["covenant_id"] for r in answer["rows"]} == set(truth["reported"]), meta["id"]
    assert reader.disagreements == []


def test_ferrogate_runway_is_reported_as_the_text_the_certificate_prints():
    book = load_book(BOOKS["innovation"], ["ferrogate-cloud"])
    ferro = book.get("ferrogate-cloud")
    meta = ferro.document_by_file("mcc-2026-10-31.pdf")
    rows = {r["covenant_id"]: r for r in _answer(StandInReader(book), _request(book, ferro, meta, "certificate"))["rows"]}
    assert rows["min_runway_months"]["actual_printed"].startswith("Not meaningful")
    assert rows["dscr"]["actual_printed"].endswith("to 1.00") or rows["dscr"]["actual_printed"].endswith("x")


def test_filed_only_documents_and_the_held_export_get_a_type_and_no_figures():
    book = load_book(BOOKS["innovation"], ["stripple-tech"])
    stripple = book.get("stripple-tech")
    reader = StandInReader(book)
    meta = stripple.document_by_file("mrr_export.pdf")
    head = "\n".join(_lines(pymupdf.open(book.root / meta["path"])[0]))
    text = f'<document number="1" file="mrr_export.pdf" pages="1">\n{head}\n</document>'
    request = LLMRequest(model="m", system="", messages=[{"role": "user", "content": text}],
                         record_key="intake/stripple-tech/2026-10-31")
    doc = _answer(reader, request)["documents"][0]
    assert doc["doc_type"] == "other" and doc["period_end_text"] == ""

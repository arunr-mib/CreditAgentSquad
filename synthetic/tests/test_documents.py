"""The rendered PDFs, read back with PyMuPDF only (never with the renderer's own code)."""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal

import pymupdf

from synthetic.generate import generate
from synthetic.model import LINES

D = Decimal
CURRENT = "2026-09-30"
MARKER = "SYNTHETIC - FOR DEMONSTRATION"
NUMBER = re.compile(r"^\(?\d[\d,]*\)?$|^-$")


def parse_printed(text: str) -> Decimal:
    """Accounting format: commas, parentheses for negatives, a dash for zero."""
    text = text.strip()
    if text == "-":
        return D(0)
    negative = text.startswith("(") and text.endswith(")")
    value = D(text.strip("()").replace(",", ""))
    return -value if negative else value


def page_rows(page) -> list[tuple[str, list[str]]]:
    """Each printed row as (label, [figures left to right]), rebuilt from word positions."""
    lines: dict[int, list[tuple[float, str]]] = {}
    for x0, _y0, _x1, y1, word, *_ in page.get_text("words"):
        lines.setdefault(round(y1), []).append((x0, word))
    rows = []
    for key in sorted(lines):
        words = [w for _, w in sorted(lines[key])]
        figures: list[str] = []
        while words and NUMBER.match(words[-1]):
            figures.insert(0, words.pop())
        rows.append((" ".join(words), figures))
    return rows


def squash(text: str) -> str:
    return " ".join(text.split())


def test_two_runs_with_the_same_seed_are_identical(generated, tmp_path):
    second = generate(tmp_path / "out")
    first_files = sorted((generated.out / "truth").glob("*.json"))
    assert len(first_files) == 21
    for path in first_files:
        assert path.read_bytes() == (tmp_path / "out" / "truth" / path.name).read_bytes(), path.name
    assert generated.oracle.read_bytes() == (tmp_path / "oracle.csv").read_bytes()
    assert second["documents"] == generated.manifest["documents"]  # includes sha256 of each PDF's text
    for doc in generated.manifest["documents"][::37]:
        with pymupdf.open(generated.out / doc["path"]) as a, pymupdf.open(tmp_path / "out" / doc["path"]) as b:
            assert [p.get_text() for p in a] == [p.get_text() for p in b]


def test_a_different_seed_changes_the_book(generated, tmp_path):
    other = generate(tmp_path / "out", seed=7)
    assert other["documents"] != generated.manifest["documents"]


def test_every_document_is_listed_exists_and_carries_the_marker(generated):
    listed = {d["id"]: d for d in generated.manifest["documents"]}
    image_pages = set()
    for truth in generated.truths.values():
        for doc in truth["documents"]:
            assert doc["id"] in listed and listed[doc["id"]]["path"] == doc["path"]
            for defect in doc.get("defects", []):
                if defect["type"] == "image_only_page":
                    image_pages.add((doc["id"], defect["page"]))
    assert len(listed) == sum(len(t["documents"]) for t in generated.truths.values())
    assert len(image_pages) == 1
    for doc in generated.manifest["documents"]:
        with pymupdf.open(generated.out / doc["path"]) as pdf:
            assert pdf.page_count == doc["pages"] >= 2
            for number, page in enumerate(pdf, start=1):
                text = page.get_text()
                if (doc["id"], number) in image_pages:
                    continue
                assert MARKER in text, (doc["id"], number)
                assert "CreditFleet" not in text and "Credit Agent Squad" not in text


def test_document_set_per_borrower(generated):
    for bid, truth in generated.truths.items():
        kinds = Counter(d["type"] for d in truth["documents"])
        late = truth["scenario"]["code"] == "late_reporting"
        assert kinds["credit_agreement"] == 1
        assert kinds["annual_financial_statements"] == 2
        assert kinds["interim_financial_statements"] == (5 if late else 6), bid
        assert kinds["compliance_certificate"] == (6 if late else 7), bid
        assert kinds["borrowing_base_certificate"] == (3 if truth["borrowing_base"] else 0)
        agreement = next(d for d in truth["documents"] if d["type"] == "credit_agreement")
        assert 8 <= agreement["pages"] <= 14, (bid, agreement["pages"])
        for doc in truth["documents"]:
            assert doc["received_date"] <= "2026-11-17"
    assert sum(d["type"] == "amendment" for t in generated.truths.values() for d in t["documents"]) == 2


def test_current_statement_figures_are_on_the_stated_page_and_parse_to_truth(generated):
    checked_borrowers = 0
    for bid, truth in generated.truths.items():
        doc = next((d for d in truth["documents"] if d["id"] == f"{bid}.ifs-{CURRENT}"), None)
        if doc is None:
            assert truth["scenario"]["code"] == "late_reporting"
            continue
        values = next(p for p in truth["periods"] if p["period_end"] == CURRENT)["values"]
        scale = doc["scale"]
        assert scale == truth["borrower"]["statement_scale"]
        # Every template line is printed, or absent because it is zero, or on a page that cannot be read.
        for key in LINES:
            if key in doc["figures"] or key in doc["unreadable_keys"]:
                continue
            assert key in doc["absent_keys"] and D(values[key]) == 0, (bid, key)
        with pymupdf.open(generated.out / doc["path"]) as pdf:
            rows_by_page = {n: page_rows(pdf[n - 1]) for n in {f["page"] for f in doc["figures"].values()}}
        for key, figure in doc["figures"].items():
            matches = [figs for label, figs in rows_by_page[figure["page"]] if label == figure["label"] and figs]
            assert len(matches) == 1, (bid, key, figure)
            assert matches[0][0] == figure["printed"], (bid, key)
            stored = parse_printed(matches[0][0]) * scale * LINES[key].sign
            assert stored == D(values[key]), (bid, key)
        if not doc["unreadable_keys"]:
            assert set(doc["figures"]) | set(doc["absent_keys"]) == set(LINES)
            checked_borrowers += 1
    assert checked_borrowers >= 18


def test_annual_statement_figures_parse_to_truth(generated):
    for bid in ("harrowgate-precision", "dunmore-industrial-supply", "sablewood-dental", "pellham-grain", "vantry-freight"):
        truth = generated.truths[bid]
        doc = next(d for d in truth["documents"] if d["id"] == f"{bid}.afs-2025")
        values = next(p for p in truth["periods"] if p["period_end"] == "2025-12-31")["values"]
        with pymupdf.open(generated.out / doc["path"]) as pdf:
            assert "In our opinion" in pdf[1].get_text()
            for key, figure in doc["figures"].items():
                rows = [figs for label, figs in page_rows(pdf[figure["page"] - 1]) if label == figure["label"] and figs]
                assert len(rows) == 1, (bid, key)
                assert parse_printed(rows[0][0]) * doc["scale"] * LINES[key].sign == D(values[key]), (bid, key)
                # The comparative column is the prior fiscal year as previously reported.
                prior = next(p for p in truth["periods"] if p["period_end"] == "2024-12-31")["values"]
                assert parse_printed(rows[0][1]) * doc["scale"] * LINES[key].sign == D(prior[key]), (bid, key)


def test_every_citation_quotes_a_sentence_printed_on_the_cited_page(generated):
    count = 0
    for bid, truth in generated.truths.items():
        paths = {d["id"]: generated.out / d["path"] for d in truth["documents"]}
        pages: dict[str, list[str]] = {}

        def check(citation: dict, bid=bid, paths=paths, pages=pages) -> None:
            doc_id = citation["document_id"]
            if doc_id not in pages:
                with pymupdf.open(paths[doc_id]) as pdf:
                    pages[doc_id] = [squash(p.get_text()) for p in pdf]
            assert citation["quote"].endswith(".") and citation["section"]
            assert squash(citation["quote"]) in pages[doc_id][citation["page"] - 1], (bid, citation["field"])

        for version in truth["terms_versions"]:
            terms = version["terms"]
            for covenant in terms["covenants"]:
                assert covenant["citations"]
                for citation in covenant["citations"]:
                    check(citation)
                    count += 1
                threshold = next(c for c in covenant["citations"] if c["field"] == "test.threshold")
                shown = covenant["test"]["threshold"]
                printed = shown if covenant["test"]["unit"] == "ratio" else f"{int(shown):,}"
                assert printed in threshold["quote"], (bid, covenant["id"])
                for i, step in enumerate(covenant["test"]["steps"]):
                    cited = next(c for c in covenant["citations"] if c["field"] == f"test.steps[{i}]")
                    assert step["value"] in cited["quote"]
            for addback in terms["definitions"]["ebitda"]["addbacks"]:
                check(addback["citation"])
                if addback["cap"] and addback["cap"]["type"] == "amount":
                    assert f"{int(addback['cap']['value']):,}" in addback["citation"]["quote"]
            for requirement in terms["reporting_requirements"]:
                check(requirement["citation"])
                assert f"{requirement['due_days_after_period_end']} days" in requirement["citation"]["quote"]
            if terms["borrowing_base"]:
                check(terms["borrowing_base"]["citation"])
            for citation in version["clause_index"]:
                check(citation)
        details = truth["scenario"]["details"]
        if truth["scenario"]["code"] == "unapproved_amendment":
            check(details)
            assert f"{int(details['amended_cap']):,}" in details["quote"]
    assert count > 100


def test_image_only_page_has_no_extractable_text(generated):
    truth = next(t for t in generated.truths.values() if t["scenario"]["code"] == "image_only")
    doc = next(d for d in truth["documents"] if d.get("defects"))
    defect = doc["defects"][0]
    assert doc["period_end"] == CURRENT and defect["type"] == "image_only_page"
    with pymupdf.open(generated.out / doc["path"]) as pdf:
        page = pdf[defect["page"] - 1]
        assert page.get_text().strip() == ""
        assert page.get_text("words") == []
        assert len(page.get_images()) == 1
        others = [p.get_text() for i, p in enumerate(pdf) if i != defect["page"] - 1]
    assert all(MARKER in text for text in others)
    assert "is.revenue" in doc["unreadable_keys"] and "is.revenue" not in doc["figures"]
    assert "bs.cash" in doc["figures"]


def test_missing_page_leaves_the_balance_sheet_unable_to_foot(generated):
    truth = next(t for t in generated.truths.values() if t["scenario"]["code"] == "missing_page")
    doc = next(d for d in truth["documents"] if d.get("defects"))
    earlier = next(d for d in truth["documents"] if d["id"].endswith("ifs-2026-06-30"))
    assert doc["period_end"] == CURRENT and doc["pages"] == earlier["pages"] - 1
    with pymupdf.open(generated.out / doc["path"]) as pdf:
        text = "\n".join(p.get_text() for p in pdf)
        numbers = re.findall(r"Page (\d+)", text)
    assert "Total assets" in text
    assert "Total liabilities" not in text and "Accounts payable" not in text
    assert str(doc["defects"][0]["printed_page_number"]) not in numbers  # the printed numbering skips a page
    assert "bs.total_liabilities_and_equity" in doc["unreadable_keys"]
    assert "bs.total_assets" in doc["figures"] and "is.revenue" in doc["figures"]


def test_restated_comparative_differs_from_the_statement_delivered_a_year_ago(generated):
    for bid, truth in generated.truths.items():
        doc = next((d for d in truth["documents"] if d["id"] == f"{bid}.ifs-{CURRENT}"), None)
        if doc is None:
            continue
        a_year_ago = next(d for d in truth["documents"] if d["id"] == f"{bid}.ifs-2025-09-30")
        was_printed = {key: figure["printed"] for key, figure in a_year_ago["figures"].items()}
        was_printed.update(dict.fromkeys(a_year_ago["absent_keys"], "-"))  # a line left off the statement is zero
        changed = {key for key, printed in doc["comparative_printed"].items() if was_printed[key] != printed}
        if truth["scenario"]["code"] == "restated_comparative":
            assert changed == {"is.revenue", "is.cogs"}
            lines = {x["key"]: x for x in truth["scenario"]["details"]["restated_lines"]}
            prior = next(p for p in truth["periods"] if p["period_end"] == "2025-09-30")["values"]
            for key in changed:
                assert lines[key]["as_previously_reported"] == prior[key]
                assert parse_printed(doc["comparative_printed"][key]) * doc["scale"] == D(lines[key]["as_restated"])
        elif not doc["unreadable_keys"]:
            assert changed == set(), bid


def test_scale_trap_certificate_is_in_whole_dollars(generated):
    truth = next(t for t in generated.truths.values() if t["scenario"]["code"] == "scale_trap")
    doc = next(d for d in truth["documents"] if d["id"].endswith(f"cc-{CURRENT}"))
    statement = next(d for d in truth["documents"] if d["id"].endswith(f"ifs-{CURRENT}"))
    reported = next(c for c in truth["certificates"] if c["period_end"] == CURRENT)["reported"]["min_tnw"]
    with pymupdf.open(generated.out / doc["path"]) as pdf:
        text = "\n".join(p.get_text() for p in pdf)
    assert "whole U.S. dollars" in text
    assert f"{int(D(reported['value'])):,}" in text  # the full dollar figure, not thousands
    assert statement["scale"] == 1000 and doc["scale"] == 1


def test_certificates_print_what_the_borrower_reported(generated):
    for truth in generated.truths.values():
        for certificate in truth["certificates"]:
            if certificate["period_end"] != CURRENT:
                continue
            doc = next(d for d in truth["documents"] if d["id"] == certificate["document_id"])
            with pymupdf.open(generated.out / doc["path"]) as pdf:
                text = squash("\n".join(p.get_text() for p in pdf))
            for reported in certificate["reported"].values():
                if reported["unit"] == "ratio":
                    assert f"{D(reported['value']):.2f}x" in text
            compliant = all(r["in_compliance"] for r in certificate["reported"].values())
            assert ("was in compliance with each of the financial covenants" in text) == compliant

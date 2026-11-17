"""Packages over the seeded book: files are generated, every figure resolves to the snapshot, a
tampered file is caught, drafts block release, and schedules run once."""
import shutil
import subprocess
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from app.calc import template
from app.core import clock
from app.core.ledger import LedgerEvent
from app.domain import review_service
from app.domain.facts import Fact
from app.domain.facts_service import correct_fact, current_fact
from app.domain.monitoring import Cycle
from app.domain.org import User
from app.domain.reviews import Package, ReviewSheet, Snapshot
from app.publishing import excel as excel_format
from app.publishing import service
from app.publishing import word as word_format
from app.publishing.formula import evaluate
from app.publishing.style import DRAFT_LABEL, WITHHELD
from app.publishing.verify import figures_in, verify_package
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from openpyxl import load_workbook
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from publishing.world import CODES, PERIOD, borrower_of
from sqlalchemy import select


def generate(db, code, formats=service.FORMATS) -> Package:
    return service.generate_package(db, scope="borrower", period_end=PERIOD, borrower_id=borrower_of(db, code).id,
                                    formats=formats)


def file_of(package, fmt) -> Path:
    return Path(next(f["path"] for f in package.files if f["format"] == fmt))


def user(db, email) -> User:
    return db.execute(select(User).where(User.email == f"{email}@bankofstoic.example")).scalar_one()


def events(db, action, entity_id) -> list[LedgerEvent]:
    return list(db.execute(select(LedgerEvent).where(LedgerEvent.action == action,
                                                     LedgerEvent.entity_id == str(entity_id))).scalars())


def docx_paragraphs(doc):
    return [Paragraph(p, doc) for p in doc.element.body.iter(qn("w:p"))]


def docx_text(path) -> str:
    return "\n".join(p.text for p in docx_paragraphs(Document(str(path))))


def pptx_text(path) -> str:
    out = []
    for slide in Presentation(str(path)).slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
    return "\n".join(out)


def add_commentary(db, code, sections: dict[str, str], *, approve: bool = False) -> ReviewSheet:
    borrower = borrower_of(db, code)
    cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.period_end == PERIOD)).scalar_one()
    sheet = db.execute(select(ReviewSheet).where(ReviewSheet.cycle_id == cycle.id)).scalar_one_or_none()
    if sheet is None:
        sheet = ReviewSheet(borrower_id=borrower.id, cycle_id=cycle.id)
        db.add(sheet)
        db.flush()
    analyst = user(db, "priya.raman")
    for section, body in sections.items():
        review_service.write_section(db, sheet, section=section, body=body, user=analyst)
    if approve:
        approve_commentary(db, sheet)
    return sheet


def approve_commentary(db, sheet) -> None:
    manager = user(db, "dana.whitfield")
    for c in review_service.current_commentary(db, sheet):
        c.status, c.approved_by = "approved", manager.id
    db.flush()


@pytest.mark.parametrize("code", CODES)
def test_each_borrower_gets_three_files_and_every_figure_resolves(pub, code):
    package = generate(pub, code)
    assert package.status == "generated" and package.trigger == "on_demand"
    assert [f["format"] for f in package.files] == ["docx", "xlsx", "pptx"]
    assert all(Path(f["path"]).exists() and f["size"] > 20_000 for f in package.files)
    snapshot = pub.get(Snapshot, package.snapshot_id)
    assert snapshot.sha256 == service.content_hash(snapshot.content) and len(snapshot.content["facts"]) > 700
    assert {f["name"]: f["sha256"] for f in snapshot.content["files"]} == {f["name"]: f["sha256"] for f in package.files}
    # every frozen fact carries a source a person can follow
    for record in snapshot.content["facts"].values():
        assert record["kind"] in ("seeded", "calculated", "system")
        assert record.get("calculation") or record.get("connector") or record["kind"] == "seeded", record
    report = verify_package(pub, package)
    assert report.ok, [p.describe() for p in report.problems[:5]]
    by_format = {f["format"]: f["figures"] for f in report.files}
    assert by_format["xlsx"] > 700 and by_format["docx"] > 100 and by_format["pptx"] > 30
    assert len(events(pub, "package.generated", package.id)) == 1
    assert events(pub, "snapshot.frozen", snapshot.id)[0].payload["sha256"] == snapshot.sha256
    content = snapshot.content["borrowers"][0]
    assert len(content["trend"]["periods"]) == 8 and len(content["trend"]["rows"]) >= 10
    if code == "kestrel-bay-packaging":
        assert "breach_reported_compliant" in {c["outcome"] for c in content["covenants"]}
        assert "Breach, certified as compliant" in docx_text(file_of(package, "docx"))
    if code == "briarstone-beverage":
        assert content["borrowing_base"]["outcome"] == "over_advance"
        assert "Borrowing base" in load_workbook(file_of(package, "xlsx")).sheetnames
    if code == "thornbury-metal":
        assert len(content["signals"]) > 8
    if code == "sablewood-dental":
        assert content["signals"] == [] and content["work_items"] == []


def test_portfolio_package_covers_every_borrower_and_verifies(pub):
    package = service.generate_package(pub, scope="portfolio", period_end=PERIOD)
    assert [f["format"] for f in package.files] == ["docx", "xlsx", "xlsx", "xlsx", "xlsx", "pptx"]
    snapshot = pub.get(Snapshot, package.snapshot_id)
    portfolio = snapshot.content["portfolio"]
    assert len(portfolio["rows"]) == 4
    assert {w["code"] for w in portfolio["watch_list"]} >= {"kestrel-bay-packaging", "briarstone-beverage"}
    assert "sablewood-dental" not in {w["code"] for w in portfolio["watch_list"]}
    deck = Presentation(str(file_of(package, "pptx")))
    titles = [s.shapes[1].text_frame.text for s in deck.slides]
    assert titles[:3] == ["Portfolio review", "Portfolio summary", "Watch list"] and titles[-1].startswith("Sources")
    assert sum(1 for s in deck.slides for sh in s.shapes if getattr(sh, "has_chart", False) and sh.has_chart) == 4
    charts = [s for s in deck.slides if any(getattr(sh, "has_chart", False) and sh.has_chart for sh in s.shapes)]
    assert all("fact " in s.notes_slide.notes_text_frame.text and 'Chart "' in s.notes_slide.notes_text_frame.text
               for s in charts)
    report = verify_package(pub, package)
    assert report.ok, [p.describe() for p in report.problems[:5]]


# the verifier is the proof behind the success measure: it must catch a changed file ----------------
def test_verifier_catches_a_changed_cell_and_a_formula_replaced_by_a_number(pub):
    package = generate(pub, "kestrel-bay-packaging", ["xlsx"])
    path = file_of(package, "xlsx")
    wb = load_workbook(path)
    ws = wb["Income statement"]
    row = next(r for r in range(1, 40) if ws.cell(row=r, column=1).value == "Net revenue")
    total = next(r for r in range(1, 40) if ws.cell(row=r, column=1).value == "Gross profit")
    ws.cell(row=row, column=5).value = ws.cell(row=row, column=5).value + 1000
    assert str(ws.cell(row=total, column=3).value).startswith("=")
    ws.cell(row=total, column=3).value = 123456
    wb.save(path)
    report = verify_package(pub, package)
    reasons = {(p.where, p.reason.split(" (")[0].split(" but ")[0]) for p in report.problems}
    cell, gross, replaced = f"Income statement!E{row}", f"Income statement!E{total}", f"Income statement!C{total}"
    assert not report.ok
    assert any(w == cell and r.startswith("does not match its fact") for w, r in reasons)  # the changed input
    assert any(w == gross and r.startswith("does not match its fact") for w, r in reasons)  # the total that reads it
    assert any(w == replaced and r == "is listed as formula" for w, r in reasons)
    assert any(p.reason == "has changed since the snapshot was frozen" for p in report.problems)


def test_verifier_catches_a_changed_figure_and_an_unsourced_one_in_the_memo(pub):
    package = generate(pub, "kestrel-bay-packaging", ["docx"])
    path = file_of(package, "docx")
    doc = Document(str(path))
    target = next(r for p in docx_paragraphs(doc) for r in p.runs if r.text == "2.60x")
    target.text = "2.40x"
    doc.add_paragraph("Leverage is expected to improve to 1.90x by year end.")
    doc.save(str(path))
    report = verify_package(pub, package)
    found = {(p.figure, p.reason.split(" its source")[0]) for p in report.problems}
    assert ("2.40x", "does not match") in found and ("1.90x", "has no source reference") in found
    assert len(report.problems) == 3  # the two figures and the changed file


def test_verifier_catches_changed_chart_data_and_table_text_in_the_deck(pub):
    package = generate(pub, "kestrel-bay-packaging", ["pptx"])
    path = file_of(package, "pptx")
    deck = Presentation(str(path))
    slide = next(s for s in deck.slides if any(getattr(sh, "has_chart", False) and sh.has_chart for sh in s.shapes))
    chart = next(sh.chart for sh in slide.shapes if getattr(sh, "has_chart", False) and sh.has_chart)
    plot = chart.plots[0]
    data = CategoryChartData()
    data.categories = list(plot.categories)
    for n, series in enumerate(plot.series):
        values = list(series.values)
        if n == 0:
            values[-1] = values[-1] * 1.1
        data.add_series(series.name, values)
    chart.replace_data(data)
    table = next(sh.table for sh in slide.shapes if sh.has_table)
    run = next(r for row in table.rows for c in row.cells for p in c.text_frame.paragraphs for r in p.runs
               if r.text == "2.50x")
    run.text = "3.00x"
    deck.save(str(path))
    report = verify_package(pub, package)
    assert any('chart series "Revenue"' in p.where and p.reason.startswith("does not match") for p in report.problems)
    assert any(p.figure == "3.00x" and p.reason.startswith("does not match") for p in report.problems)
    assert len(report.problems) == 3


def test_verifier_fails_when_a_file_is_missing_or_the_snapshot_is_altered(pub):
    package = generate(pub, "sablewood-dental", ["docx"])
    snapshot = pub.get(Snapshot, package.snapshot_id)
    fact_id = next(iter(snapshot.content["facts"]))
    changed = {**snapshot.content, "facts": {**snapshot.content["facts"],
                                             fact_id: {**snapshot.content["facts"][fact_id], "value": "999"}}}
    snapshot.content = changed
    pub.flush()
    reasons = [p.reason for p in verify_package(pub, package).problems]
    assert "is not the hash of the snapshot's content" in reasons
    assert any(r.startswith("is frozen as 999 but stored as") for r in reasons)
    file_of(package, "docx").unlink()
    assert "is missing from the file store" in [p.reason for p in verify_package(pub, package).problems]


# Excel: computed lines are live formulas that reproduce the stored computed facts -------------------
def workbook_cells(path):
    wb = load_workbook(path)

    def cell(sheet, address):
        raw = wb[sheet][address].value
        if raw is None:
            return None
        return evaluate(raw, sheet, cell) if isinstance(raw, str) and raw.startswith("=") else D(str(raw))

    return wb, cell


def test_statement_formulas_follow_the_template_and_recompute_to_the_stored_totals(pub):
    borrower = borrower_of(pub, "thornbury-metal")
    package = generate(pub, "thornbury-metal", ["xlsx"])
    wb, cell = workbook_cells(file_of(package, "xlsx"))
    checked = 0
    for title, statements in excel_format.STATEMENT_SHEETS:
        ws = wb[title]
        rows = {ws.cell(row=r, column=1).value: r for r in range(1, ws.max_row + 1)}
        header = [c.value for c in ws[excel_format.HEADER_ROW]]
        for line in template.LINES:
            if line.statement not in statements:
                continue
            r = rows[line.label]
            for col in range(2, len(header) + 1):
                end = header[col - 1].date()
                raw = ws.cell(row=r, column=col).value
                letter = ws.cell(row=r, column=col).column_letter
                fact = current_fact(pub, borrower.id, line.key, end, 0) or next(
                    f for m in (3, 6, 9, 12) if (f := current_fact(pub, borrower.id, line.key, end, m)))
                if not line.computed:
                    assert D(str(raw)) == fact.value  # an input cell holds the stored fact
                    continue
                # structure: the formula is the template's formula over this column's input cells
                expected = "".join(("+" if sign > 0 else "-") + f"{letter}{rows[template.LINE_BY_KEY[key].label]}"
                                   for sign, key in line.formula).lstrip("+")
                assert raw == "=" + expected, (line.key, raw)
                # value: recomputed with the test's evaluator, it equals the stored computed fact
                assert cell(title, f"{letter}{r}") == fact.value, (line.key, end)
                checked += 1
    assert checked == 12 * sum(1 for line in template.LINES if line.computed)


def test_ratio_formulas_recompute_to_the_stored_metric_facts(pub):
    borrower = borrower_of(pub, "kestrel-bay-packaging")
    package = generate(pub, "kestrel-bay-packaging", ["xlsx"])
    wb, cell = workbook_cells(file_of(package, "xlsx"))
    ws = wb["Ratios"]
    labels = {v: k for k, v in review_service.METRIC_LABELS.items()}
    formulas = 0
    for r in range(excel_format.HEADER_ROW + 1, ws.max_row + 1):
        name = labels[ws.cell(row=r, column=1).value]
        for col in range(2, 10):
            raw = ws.cell(row=r, column=col).value
            if raw is None:
                continue
            end = ws.cell(row=excel_format.HEADER_ROW, column=col).value.date()
            assert raw.startswith("=ROUND(") and "'Income statement'!" in raw or "'Balance sheet'!" in raw
            fact = current_fact(pub, borrower.id, f"metric.{name}", end, 0)
            assert fact.kind == "calculated" and cell("Ratios", ws.cell(row=r, column=col).coordinate) == fact.value
            formulas += 1
    assert formulas > 85
    # the Sources sheet maps every figure cell, with the fact and what stands behind it
    src = wb[excel_format.SOURCES_SHEET]
    rows = list(src.iter_rows(min_row=excel_format.HEADER_ROW + 1, values_only=True))
    listed = {(row[0], row[1]) for row in rows}
    figures = {(s.title, c.coordinate) for s in wb.worksheets if s.title != excel_format.SOURCES_SHEET
               for row in s.iter_rows() for c in row
               if isinstance(c.value, int | float) and not isinstance(c.value, bool)
               or isinstance(c.value, str) and c.value.startswith("=")}
    assert figures == listed and all(row[3] and pub.get(Fact, row[3]) is not None for row in rows)
    assert wb["Income statement"].freeze_panes == "B7" and wb["Ratios"].freeze_panes == "B6"


def test_libreoffice_recalculates_the_workbook_to_the_same_values(pub, tmp_path):
    """An independent engine: LibreOffice recalculates on load; its values must match ours."""
    soffice = shutil.which("soffice")
    if soffice is None:
        pytest.skip("LibreOffice is not installed")
    package = generate(pub, "briarstone-beverage", ["xlsx"])
    path = file_of(package, "xlsx")
    done = subprocess.run([soffice, f"-env:UserInstallation=file://{tmp_path}/profile", "--headless", "--convert-to",
                           "xlsx:Calc MS Excel 2007 XML", "--outdir", str(tmp_path / "out"), str(path)],
                          capture_output=True, timeout=180)
    converted = tmp_path / "out" / path.name
    if done.returncode != 0 or not converted.exists():
        pytest.skip("LibreOffice could not convert the workbook here")
    _, cell = workbook_cells(path)
    cached = load_workbook(converted, data_only=True)
    formulas = load_workbook(path)
    compared = 0
    for ws in formulas.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    theirs = cached[ws.title][c.coordinate].value
                    assert theirs is not None and abs(D(str(theirs)) - cell(ws.title, c.coordinate)) <= D("0.000001")
                    compared += 1
    assert compared > 250


# Word: every figure carries a numbered reference that the Sources section lists --------------------
def test_every_figure_in_the_memo_has_a_reference_listed_in_sources(pub):
    package = generate(pub, "briarstone-beverage", ["docx"])
    snapshot = pub.get(Snapshot, package.snapshot_id)
    doc = Document(str(file_of(package, "docx")))
    sources = next(t for t in doc.tables if tuple(c.text for c in t.rows[0].cells) == word_format.SOURCE_COLUMNS)
    listed = {int(row.cells[0].text): row.cells[1].text for row in sources.rows[1:]}
    inside = set(sources._tbl.iter(qn("w:p")))  # holding the elements keeps their identity
    cited, figures = set(), 0
    for p in docx_paragraphs(doc):
        if p._p in inside:
            continue
        runs = p.runs
        for i, run in enumerate(runs):
            if run.style.name == word_format.REF_STYLE:
                assert run.font.superscript or run.style.font.superscript
                cited.add(int(run.text))
                continue
            found = figures_in(run.text)  # dates, ids and the snapshot hash are not figures
            figures += len(found)
            if found:  # the run that prints a figure is followed at once by its reference number
                assert len(found) == 1 and i + 1 < len(runs) and runs[i + 1].style.name == word_format.REF_STYLE, run.text
    assert figures > 150 and cited == set(listed)
    facts, derived = snapshot.content["facts"], snapshot.content["derived"]
    assert all(sid in facts or sid in derived for sid in listed.values())
    for row in sources.rows[1:]:
        record = facts[row.cells[1].text]
        detail = row.cells[5].text
        if record["kind"] == "calculated":
            assert record["calculation"]["id"] in detail and "Inputs:" in detail
        elif record["kind"] == "system":
            assert "System of record" in detail
    section = doc.sections[0]
    assert "Briarstone Beverage Company" in section.header.paragraphs[0].text
    assert "Bank of Stoic" in section.header.paragraphs[0].text
    footer = section.footer.paragraphs[0]
    assert "SYNTHETIC - FOR DEMONSTRATION" in footer.text
    assert [el.text.strip() for el in footer._p.iter(qn("w:instrText"))] == ["PAGE", "NUMPAGES"]
    headings = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
    assert headings == ["Commentary", "Borrower and loans", "Covenant compliance", "Key metrics, last eight quarters",
                        "Changes since the prior period", "Early warning signals", "Borrowing base",
                        "Open work items and actions", "Sources"]
    assert len(doc.tables) >= 8


def test_an_extracted_fact_is_cited_with_its_document_page_and_quote(pub):
    from app.domain.documents import Document as StoredDocument
    from app.domain.facts_service import add_fact

    borrower = borrower_of(pub, "sablewood-dental")
    old = current_fact(pub, borrower.id, "is.revenue", PERIOD, 9)
    stored = pub.execute(select(StoredDocument).where(StoredDocument.borrower_id == borrower.id,
                                                      StoredDocument.period_end == PERIOD)).scalars().first()
    old.status = "superseded"
    new = add_fact(pub, borrower_id=borrower.id, key="is.revenue", period_end=PERIOD, months=9, value=old.value,
                   kind="extracted", status="verified", document_id=stored.id, page=2, quote="12,345",
                   label_text="Net revenue", supersedes_fact_id=old.id)
    package = generate(pub, "sablewood-dental", ["xlsx"])
    record = pub.get(Snapshot, package.snapshot_id).content["facts"][str(new.id)]
    assert record["document"]["title"] == stored.title and record["page"] == 2 and record["quote"] == "12,345"
    src = load_workbook(file_of(package, "xlsx"))[excel_format.SOURCES_SHEET]
    row = next(r for r in src.iter_rows(min_row=6, values_only=True) if r[3] == str(new.id))
    assert row[4:9] == ("extracted", "input", stored.title, "2", 'Printed as "12,345" beside "Net revenue"')
    assert verify_package(pub, package).ok


# commentary: none, draft, approved -----------------------------------------------------------------
def test_draft_commentary_is_labelled_and_blocks_release_until_approved_and_regenerated(pub):
    code = "sablewood-dental"
    borrower = borrower_of(pub, code)
    officer, analyst = user(pub, "helen.strand"), user(pub, "priya.raman")
    none_yet = generate(pub, code, ["docx", "pptx"])
    assert "No commentary has been written" in docx_text(file_of(none_yet, "docx"))
    assert DRAFT_LABEL not in docx_text(file_of(none_yet, "docx"))

    revenue = current_fact(pub, borrower.id, "metric.revenue_ttm", PERIOD, 0)
    sheet = add_commentary(pub, code, {
        "summary": "The borrower remains in compliance with every covenant this quarter.",
        "performance": f"Revenue for the trailing twelve months was {{{{fact:{revenue.id}|usd_m}}}}. "
                       "Management expects margins near 14.5% next year."})  # a typed figure with no source
    draft = generate(pub, code, ["docx", "pptx"])
    text = docx_text(file_of(draft, "docx"))
    assert text.count(DRAFT_LABEL) == 3 and DRAFT_LABEL in pptx_text(file_of(draft, "pptx"))  # title block + sections
    assert "million" in text and "{{fact" not in text
    assert WITHHELD in text and "14.5%" not in text  # the typed figure is withheld, and reported
    snapshot = pub.get(Snapshot, draft.snapshot_id)
    assert len(snapshot.content["warnings"]) == 1 and "14.5%" in snapshot.content["warnings"][0]
    assert [(c["section"], c["version"], c["status"]) for c in snapshot.content["borrowers"][0]["commentary"]] == [
        ("summary", 1, "draft"), ("performance", 1, "draft")]
    assert verify_package(pub, draft).ok

    with pytest.raises(service.ReleaseRefused, match="still a draft .*summary.*Approve the commentary"):
        service.release_package(pub, draft, officer)
    assert draft.status == "generated" and events(pub, "package.released", draft.id) == []

    approve_commentary(pub, sheet)
    with pytest.raises(service.ReleaseRefused, match="still a draft"):  # the files still say draft
        service.release_package(pub, draft, officer)
    approved = generate(pub, code, ["docx", "pptx"])
    text = docx_text(file_of(approved, "docx"))
    assert DRAFT_LABEL not in text and "Approved by Dana Whitfield" in text

    with pytest.raises(PermissionError, match="release_package"):
        service.release_package(pub, approved, analyst)
    service.release_package(pub, approved, officer)
    assert approved.status == "released" and approved.released_by == officer.id and approved.released_at is not None
    (event,) = events(pub, "package.released", approved.id)
    assert event.actor_type == "user" and event.actor_id == str(officer.id)
    assert event.payload["snapshot_sha256"] == pub.get(Snapshot, approved.snapshot_id).sha256
    with pytest.raises(service.ReleaseRefused, match="already been released"):
        service.release_package(pub, approved, officer)
    # a package with no commentary at all carries no draft, so it can be released
    service.release_package(pub, none_yet, officer)
    assert none_yet.status == "released"


def test_release_is_refused_when_a_file_no_longer_verifies(pub):
    package = generate(pub, "sablewood-dental", ["docx"])
    doc = Document(str(file_of(package, "docx")))
    doc.add_paragraph("Debt service coverage of 9.99x.")
    doc.save(str(file_of(package, "docx")))
    with pytest.raises(service.ReleaseRefused, match="did not pass verification"):
        service.release_package(pub, package, user(pub, "helen.strand"))
    assert package.status == "generated"


# snapshot ------------------------------------------------------------------------------------------
def test_snapshot_hash_is_stable_for_identical_content_and_changes_with_a_fact(pub):
    code = "sablewood-dental"
    borrower = borrower_of(pub, code)
    first, second = generate(pub, code, ["xlsx"]), generate(pub, code, ["docx"])
    a, b = pub.get(Snapshot, first.snapshot_id), pub.get(Snapshot, second.snapshot_id)
    assert a.id != b.id and a.sha256 == b.sha256 and len(a.sha256) == 64
    assert a.content["files"][0]["sha256"] == first.files[0]["sha256"]

    revenue = current_fact(pub, borrower.id, "is.revenue", PERIOD, 9)
    corrected = correct_fact(pub, revenue, value=revenue.value + D(1000), user_id=user(pub, "priya.raman").id,
                             reason="Credit memo reclassified from other income.")
    third = generate(pub, code, ["xlsx"])
    c = pub.get(Snapshot, third.snapshot_id)
    assert c.sha256 != a.sha256
    record = c.content["facts"][str(corrected.id)]
    assert record["kind"] == "manual" and record["entered_by"] == "Priya Raman" and "reclassified" in record["reason"]
    assert str(revenue.id) in a.content["facts"] and str(revenue.id) not in c.content["facts"]
    # the stored totals were not recomputed after the correction, and the verifier says so
    report = verify_package(pub, third)
    assert not report.ok and all("Income statement!" in p.where or "Ratios!" in p.where for p in report.problems)
    assert verify_package(pub, first).ok  # the earlier package still stands on its own snapshot


# schedules -----------------------------------------------------------------------------------------
def test_a_schedule_generates_on_its_due_date_only_once(pub):
    borrower = borrower_of(pub, "sablewood-dental")
    clock.set_today(pub, date(2026, 10, 1))
    schedule = service.create_schedule(pub, title="Sablewood quarterly review", scope="borrower", cadence="quarterly",
                                       days_after_period_end=45, formats=["docx", "xlsx"], borrower_id=borrower.id)
    assert schedule.next_run == date(2026, 11, 14)  # 30 September plus 45 days
    assert service.run_due_schedules(pub, date(2026, 11, 13)) == []
    (run,) = service.run_due_schedules(pub, date(2026, 11, 14))
    assert run.error is None and run.period_end == PERIOD
    assert run.package.trigger == "scheduled" and [f["format"] for f in run.package.files] == ["docx", "xlsx"]
    assert run.package.prepared_by_id == "schedule" and verify_package(pub, run.package).ok
    assert schedule.next_run == date(2027, 2, 14)  # 31 December plus 45 days
    assert service.run_due_schedules(pub, date(2026, 11, 14)) == []  # the same day again: nothing
    assert service.run_due_schedules(pub, date(2026, 12, 20)) == []
    scheduled = pub.execute(select(Package).where(Package.trigger == "scheduled")).scalars().all()
    assert len(scheduled) == 1
    assert events(pub, "package_schedule.ran", schedule.id)[0].payload["package_id"] == str(run.package.id)
    # the next quarter has no cycle yet: nothing is generated, the reason is recorded, and it stays due
    (later,) = service.run_due_schedules(pub, date(2027, 2, 14))
    assert later.package is None and "no monitoring cycle" in later.error and schedule.next_run == date(2027, 2, 14)
    # an inactive schedule never runs
    schedule.active = False
    assert service.run_due_schedules(pub, date(2027, 3, 1)) == []
    with pytest.raises(ValueError, match="cadence"):
        service.create_schedule(pub, title="x", scope="portfolio", cadence="weekly", days_after_period_end=5,
                                formats=["docx"])


def test_unknown_borrower_period_or_format_is_refused_with_a_reason(pub):
    from app.publishing.content import ContentError

    borrower = borrower_of(pub, "sablewood-dental")
    with pytest.raises(ContentError, match="no monitoring cycle"):
        service.generate_package(pub, scope="borrower", period_end=date(2027, 3, 31), borrower_id=borrower.id)
    with pytest.raises(ContentError, match="pdf is not one"):
        service.generate_package(pub, scope="borrower", period_end=PERIOD, borrower_id=borrower.id, formats=["pdf"])
    with pytest.raises(ContentError, match="needs a borrower"):
        service.generate_package(pub, scope="borrower", period_end=PERIOD)

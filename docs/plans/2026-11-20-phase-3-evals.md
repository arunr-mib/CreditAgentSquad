# Phase 3 — Evaluations on Both Books, Then a Live Model Run: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the stand-in suite agree with the truth in full on both synthetic books with the gate unchanged, then (after the owner signs the new answer key and says go) run one live record pass for the new borrowers and replay the rest.

**Architecture:** Tasks 1–9 need no model and no money: a book-aware harness, grader and recorder fixes, a stand-in reader for the new document types, a recording version check, and four engine gaps the stand-in run will expose (live reading of MRR reports and bank statements, the Tidewell cash reconciliation, venture signal source facts, spreadsheet intake). Task 10 prepares the one short sign-off table for the owner. Task 11 is the only billable task and starts with an estimate and a hard STOP.

**Tech Stack:** Python 3.13, uv, pytest, SQLAlchemy 2 / Postgres 16 (test DB `credit_agent_squad_test`), PyMuPDF, openpyxl (new, for spreadsheets), the repo's `evals/` harness.

**Spec:** `docs/specs/2026-11-20-innovation-book-and-lending-layer-design.md` §11 (Evals), §8 (Documents and intake), §10 (Scenarios). Owner standing approvals: `docs/owner-questions.md` (live evaluation up to about $15, an estimate, once the stand-in gate passes and the key is signed; the key arrives as one short table; "accept spreadsheets", 20 Nov). Carry list: `.superpowers/sdd/2026-11-20-phase-2-innovation-book/progress.md` ("CARRY to Phase 3").

## Global Constraints

- **The model never types a number.** Agent text uses `{{fact:<id>}}`; code renders figures. The gate stays exactly as it is: fail on any `invented-number` or `false-compliant` (`GATED` in `evals/grade.py`). No task weakens, widens or "explains away" it.
- **Live model runs are billable. Ask the owner first, with an estimate labelled as an estimate.** Tests and CI use recorded responses only; no test in this plan calls a model.
- **Never patch the generator to match the engine or the engine to match the generator.** `synthetic/` computes expected values independently of `backend/app/calc`. A disagreement is investigated and reported; the fix goes where the defect is. When a stand-in disagreement is a product finding, report it; do not adjust the grader or the reader to agree (lesson `seeded-replay-hides-live-path-defects`).
- **A rule change moves the product and the answer key together** (lesson `a-rule-change-moves-the-product-and-the-answer-key-together`). If a task here changes what the product raises, the key row changes in the same commit and returns to "unsigned".
- **Signed rows stay signed.** `synthetic/books/innovation/oracle.csv` rows with `owner_signed_off=yes` (the kept four's) are never edited by hand. Only Task 10's `apply` command, run after the owner's written reply, sets `yes` on other rows.
- **`backend/app/calc/` and `backend/app/guardrails/` are pure** (no database, network, model, file access; no imports from other `app` packages; Decimals only; a missing input is an error, never zero; unmeasured metrics are null).
- **Facts are never edited; the ledger is append-only; scope is injected by code; a proposed terms version never governs a test.**
- **Synthetic data only**, every document carries `SYNTHETIC - FOR DEMONSTRATION`; lender Bank of Stoic.
- **Commit after every task** with a conventional prefix (`feat(p3):`, `test(p3):`, `fix(p3):`, `chore(p3):`) and end each message with the attribution trailer lines the session's system reminder gives. Run tests and the commit in one chain (lesson `run-tests-before-commit-in-one-chain`). Never commit `.env`; never push.
- **Another agent edits `backend/` and `synthetic/` concurrently while this plan is being written.** At execution time, start each task by re-reading the files it names and anchor edits by text (`grep -n`), not by line number. Line numbers below are from 20 Nov and will drift.
- Pricing used for the estimate (Claude API skill, cached 2026-11-03): `claude-opus-5-5` is $4.00 input / $20.00 output per million tokens, cache reads $0.20, cache writes 1.25x input. `backend/app/core/config.py` sets `squad_model = "claude-opus-5-5"`; no agent spec overrides it. Check the price again at estimate time.

## Review Focus

Input classes the spec implies but no happy-path test exercises; each has a test in the named task.

1. **Ferrogate's "Not meaningful (cash-flow positive)" runway on the certificate**, with a `null` value in the truth: nothing may call `Decimal(None)` (grader) and the stand-in must report the text as printed, not a number. (Task 2, Task 3)
2. **A bank statement is the first document with figures for an innovation client**: `Truth.statements` must pick the period's financial pack by type, never a bank statement or MRR report. (Task 2)
3. **Wrapped required cells and `RESTRICTED` suffixes** in certificates and bank statements: a figure label that wraps over two lines, an account line ending `RESTRICTED`. A careful reader copies print exactly; the stand-in must not drop the row or merge the suffix into the figure. (Task 3)
4. **A recording made under an older prompt replays silently** (spreading@4 replaying spreading@3 text). A stale recording must refuse to replay unless the run says so, aloud. (Task 4)
5. **An item the system raises before the cycle starts** (the funding check at seed time raises `funding_slipped`) must still reach the recorder and be graded as the exception it is, not skipped as "seeded". (Task 2)
6. **One cause, one question.** Dataflake's certificate counts pledged cash and already raises a covenant item; the cash reconciliation must not add a second `cash.statement_mismatch` for the same cause, while Tidewell (a passing variance that raises nothing today) must get exactly one. (Task 6)
7. **A spreadsheet with no company name and the wrong year** must be held with one question, never filed by guess, and every cell it yields must cite a sheet and cell. (Task 8)
8. **Unsigned rows in scope of a billable run**, now across two books and two oracles: the guard must read the oracle that belongs to the book being run. (Task 1)

## File map

| File | Responsibility | Tasks |
|---|---|---|
| `evals/book.py` | book registry (legacy, innovation), per-book oracle, workbook companion lookup | 1, 8 |
| `evals/run.py` | `--book`, per-book billable guard, funding items in the recorder, `DECISIONS` for new items, `--accept-stale` | 1, 2, 4, 6, 11 |
| `evals/grade.py` | truth selection by document type, null certificate values, stage map, MRR/bank expected facts | 2, 5 |
| `evals/standin.py` | reader for monthly packs, MRR, bank statements, certificates, filed-only types, spreadsheets | 3, 8 |
| `evals/estimate.py` (new) | cost estimate from a stand-in dry run and recorded usage | 11 |
| `evals/signoff.py` (new) | the one-table sign-off view and the apply step | 10 |
| `evals/stamp_recordings.py` (new) | one-off: stamp the kept recordings with the spec they were made under | 4 |
| `backend/app/agents/llm.py`, `runtime.py` | `LLMRequest.spec`, recording stamp, `RecordingStale` | 4 |
| `backend/app/calc/template.py` | optional `bank` statement lines for `vc-1` | 5 |
| `backend/app/agents/spreading.py`, `backend/app/domain/stages.py` | read MRR reports and bank statements live; spreading@5 | 5 |
| `backend/app/domain/cash_reconciliation.py` (new), `stages.py` | statements-to-certificate cash reconciliation | 6 |
| `backend/app/domain/signals_service.py` | source facts for venture signals | 7 |
| `backend/app/domain/documents_service.py`, `seed_book.py`, `api/routes_credit.py`, `agents/intake.py` | spreadsheet intake | 8 |
| `evals/tests/*`, `backend/tests/**` | tests per task | all |
| `evals/README.md`, `docs/HANDOFF.md`, `docs/owner-questions.md`, `docs/lessons/` | records | 9, 10, 11 |

## Rulings where the spec was silent

- **Default book.** The harness defaults to the innovation book (the v2 default per CLAUDE.md); the legacy book stays runnable with `--book legacy`; `--book both` runs both and the gate must pass on both. Results of the default book go to `evals/results/latest.*`; the other goes to `latest-legacy.*`.
- **Oracle per book.** The billable guard reads the oracle beside the book's `out/` directory (`<book>/../oracle.csv`), which is how both generators write it.
- **Bank-statement facts** are stored under new keys `bank.cash_unrestricted` and `bank.cash_restricted` (a `bank` statement in `vc-1`), not under `bs.cash_unrestricted`, so a bank statement never competes with the monthly pack for the same fact.
- **Cash reconciliation rule.** `cash.statement_mismatch` (severity high, once per borrower and period) is raised when the certificate's reported unrestricted-cash figure differs from the bank statements' unrestricted total and no covenant item for that covenant is already open for the period (a covenant item already asks the person the same question).
- **Stale recordings.** A recording carries the spec it was made under; the kept three's old recordings are stamped from git history, not guessed. A stale recording does not replay unless the run passes `--accept-stale agent@version`, which is printed in the scorecard. The default is to re-record what is stale; its cost is a separate line in the estimate.
- **Spreadsheets.** Stored as the original `.xlsx`/`.csv` bytes; each sheet becomes one text "page" of `Sheet!A1 | value` lines, and a cell citation quotes that line. The Stripple export is ingested as the workbook (the PDF print is no longer loaded).
- **Estimate method.** Count requests per agent from a stand-in dry run; add the agents the stand-in does not answer from their call sites; take tokens per call from recorded usage; apply a stated range. The live pass includes Pellham Grain (the fourth kept borrower has no recordings), 17 borrowers in all.

---

### Task 1: A book-aware harness (both books, each with its own oracle)

**Files:**
- Modify: `evals/book.py` (registry, `oracle_for`, `generate_book`, `unsigned_oracle_rows` call sites)
- Modify: `evals/run.py` (`check_may_start`, `run_suite`, `main`)
- Modify: `evals/tests/conftest.py`, `evals/tests/test_run_guards.py`, `evals/tests/test_standin_suite.py`
- Modify: `evals/README.md` (modes table: book flag; oracle counts)
- Test: `evals/tests/test_book_registry.py` (new)

**Interfaces:**
- Produces: `BOOKS: dict[str, Path]`, `DEFAULT_BOOK = BOOKS["innovation"]`, `oracle_for(root: Path | str) -> Path`, `generate_book(out, book="legacy") -> Path`, `check_may_start(mode, codes, *, oracle: Path | None = None, ...)`, `run_suite(..., book_root=...)` unchanged signature but its guard now reads `oracle_for(book_root)`; CLI `--book legacy|innovation|both|<path>`.

- [ ] **Step 1: Write the failing test**

```python
# evals/tests/test_book_registry.py
"""The harness knows both books and reads the oracle that belongs to the one it runs."""
import csv

from evals.book import BOOKS, DEFAULT_BOOK, load_book, oracle_for, unsigned_oracle_rows


def test_both_books_are_registered_and_innovation_is_the_default():
    assert set(BOOKS) == {"legacy", "innovation"}
    assert DEFAULT_BOOK == BOOKS["innovation"]
    assert (BOOKS["legacy"] / "truth").is_dir() and (BOOKS["innovation"] / "truth").is_dir()


def test_each_book_has_its_own_oracle_and_covers_every_borrower_in_it():
    for name, root in BOOKS.items():
        oracle = oracle_for(root)
        assert oracle.name == "oracle.csv" and oracle.is_file(), name
        codes = [b.code for b in load_book(root)]
        rows = list(csv.DictReader(oracle.open(newline="")))
        assert {r["borrower_id"] for r in rows} >= set(codes), name


def test_the_legacy_oracle_is_not_consulted_for_an_innovation_borrower():
    new = oracle_for(BOOKS["innovation"])
    unsigned = unsigned_oracle_rows(["dataflake"], new)
    assert unsigned and all(r["borrower_id"] == "dataflake" for r in unsigned)
    assert unsigned_oracle_rows(["dataflake"], oracle_for(BOOKS["legacy"]))[0]["item"] == "no oracle row"
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest evals/tests/test_book_registry.py -q`
Expected: FAIL (`cannot import name 'BOOKS'`).

- [ ] **Step 3: Implement the registry**

In `evals/book.py` replace the `DEFAULT_BOOK` / `ORACLE` block with:

```python
BOOKS = {"legacy": REPO / "synthetic" / "out",
         "innovation": REPO / "synthetic" / "books" / "innovation" / "out"}
DEFAULT_BOOK = BOOKS["innovation"]
ORACLE = REPO / "synthetic" / "oracle.csv"  # the legacy oracle; kept for old imports


def oracle_for(root: Path | str) -> Path:
    """The owner's oracle for the book generated into `root`: both generators write it beside `out/`."""
    return Path(root).parent / "oracle.csv"


_GENERATORS = {"legacy": "synthetic.generate", "innovation": "synthetic.books.innovation.generate"}
```

Change `generate_book(out)` to `generate_book(out, book: str = "legacy")` running `_GENERATORS[book]` with `--out`. (Verify the innovation generator takes `--out`: `uv run python -m synthetic.books.innovation.generate --help`; if its flag differs, use that flag.)

In `evals/run.py`: add `oracle: Path | None = None` to `check_may_start`; replace `unsigned_oracle_rows(codes)` by `unsigned_oracle_rows(codes, oracle or oracle_for(DEFAULT_BOOK))`; in `run_suite` pass `oracle=oracle_for(book_root)` to `check_may_start` and use it in the `unsigned_oracle_rows=` count. In `main` replace `--book` default with `"innovation"` and add:

```python
    books = ["legacy", "innovation"] if args.book == "both" else [args.book]
    worst = 0
    for name in books:
        root = BOOKS.get(name, Path(name))
        ...  # the existing body of main, run per book; the second book writes latest-legacy.json / .md
```

Implement by moving the body of `main` after argument parsing into `_run_one(args, root, label)` returning the exit code, writing to `RESULTS_DIR` for the default book and to `RESULTS_DIR / "legacy"`-suffixed names (`write_results(results, out_dir, stem="latest-legacy")`) otherwise; `main` returns `max` of the codes. Add a `stem: str = "latest"` parameter to `write_results`.

Update `evals/tests/test_run_guards.py::_oracle` to take the oracle from `oracle_for(DEFAULT_BOOK)` instead of `ORACLE` and to pass `oracle=path` to `check_may_start`; update `test_standin_suite.py` and `conftest.py` to a `book` parametrisation:

```python
@pytest.fixture(scope="session", params=["legacy", "innovation"])
def book_name(request):
    return request.param

@pytest.fixture(scope="session")
def book_root(book_name, tmp_path_factory):
    return generate_book(tmp_path_factory.mktemp(f"book-{book_name}"), book_name)
```

and replace the hard-coded `21` in `test_all_21_borrowers_ran_without_a_crash` by `len(load_book(book_root))` (rename the test `test_every_borrower_ran_without_a_crash`). Update the README counts ("21 borrowers" becomes "the borrowers in the book: 21 legacy, 20 innovation").

- [ ] **Step 4: Run the tests**

Run: `uv run pytest evals/tests/test_book_registry.py evals/tests/test_run_guards.py -q`
Expected: PASS. (The full-suite file needs Postgres and is run in Task 9.)

- [ ] **Step 5: Commit**

```bash
uv run ruff check evals && git add evals && git commit -m "feat(p3): evals know both books and read each book's own oracle"
```

---

### Task 2: Grader and recorder fixes from the carry list

**Files:**
- Modify: `evals/grade.py` (`Truth.__init__`, `Truth.expected_facts`, `STAGE_OF_ITEM`, `_d` use)
- Modify: `evals/run.py` (`LoadedBorrower._cycle`: `seeded_items`)
- Test: `evals/tests/test_grade_innovation.py` (new, no database), `evals/tests/test_run_recorder.py` (new, needs the test database)

**Interfaces:**
- Consumes: `Borrower.documents(period_end)`, `Borrower.certificate(period_end)` from Task 1's book.
- Produces: `Truth.statements` is the period's financial pack (`annual_financial_statements`, `interim_financial_statements`, `monthly_financials`) with figures; `Truth.expected_facts()` skips certificate rows whose reported value is `None`; `STAGE_OF_ITEM` gains `"funding_slipped": "signals"` and `"cash": "covenant_testing"`; the recorder includes work items of type `funding_slipped` raised before the cycle.

- [ ] **Step 1: Write the failing tests**

```python
# evals/tests/test_grade_innovation.py
from datetime import date

from evals.book import BOOKS, load_book
from evals.grade import STAGE_OF_ITEM, Truth

PACKS = {"annual_financial_statements", "interim_financial_statements", "monthly_financials"}


def test_statements_are_the_periods_financial_pack_never_a_bank_statement():
    for borrower in load_book(BOOKS["innovation"]):
        truth = Truth(borrower)
        if truth.statements is not None:
            assert truth.statements["type"] in PACKS, borrower.code


def test_every_innovation_client_with_a_current_pack_has_it_selected():
    book = load_book(BOOKS["innovation"], ["tidewell-medical", "stripple-tech"])
    tide = Truth(book.get("tidewell-medical"))
    assert tide.statements["type"] == "monthly_financials"
    assert tide.statements["period_end"] == "2026-10-31"


def test_a_not_meaningful_runway_has_no_expected_numeric_certificate_value():
    ferrogate = Truth(load_book(BOOKS["innovation"], ["ferrogate-cloud"]).get("ferrogate-cloud"))
    expected = ferrogate.expected_facts()  # must not raise on Decimal(None)
    assert "cert.min_runway_months.value" not in expected
    assert "cert.min_runway_months.threshold" in expected
    assert "cert.min_unrestricted_cash.value" in expected


def test_funding_and_cash_exceptions_map_to_stages():
    assert STAGE_OF_ITEM["funding_slipped"] == "signals"
    assert STAGE_OF_ITEM["cash"] == "covenant_testing"
```

```python
# evals/tests/test_run_recorder.py  (uses the engine/file_store fixtures from conftest)
from evals.book import BOOKS, load_book
from evals.run import LoadedBorrower
from evals.standin import StandInReader


def test_a_funding_item_raised_at_seed_time_reaches_the_recording(engine, file_store):
    book = load_book(BOOKS["innovation"], ["nimbusfield-security"])
    borrower = book.get("nimbusfield-security")
    with LoadedBorrower(engine, book, borrower) as loaded:
        recording = loaded.run(lambda: StandInReader(book), decide=False)
    assert "funding_slipped" in {w["type"] for w in recording["work_items"]}
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest evals/tests/test_grade_innovation.py -q`
Expected: FAIL (a bank statement is selected for at least one borrower; `Decimal(None)` raises for Ferrogate; KeyError on `funding_slipped`).
Run (database): `TEST_DATABASE_URL=postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad_test uv run pytest evals/tests/test_run_recorder.py -q`
Expected: FAIL (`funding_slipped` missing).

- [ ] **Step 3: Implement**

In `evals/grade.py`:

```python
PACK_TYPES = frozenset({"annual_financial_statements", "interim_financial_statements", "monthly_financials"})
```

`Truth.__init__`: replace the `self.statements = next(...)` line with

```python
        self.statements = next((d for d in self.docs if d["type"] in PACK_TYPES and "figures" in d), None)
```

In `expected_facts`, guard the certificate block:

```python
            for covenant_id, entry in self.cert["reported"].items():
                if entry.get("value") is not None:  # "Not meaningful": the certificate prints text, not a figure
                    out[f"cert.{covenant_id}.value"] = (Decimal(entry["value"]), self.end.isoformat(), file)
                out[f"cert.{covenant_id}.threshold"] = (Decimal(entry["threshold"]), self.end.isoformat(), file)
                out[f"cert.{covenant_id}.in_compliance"] = (
                    Decimal(1 if entry["in_compliance"] else 0), self.end.isoformat(), file)
```

Extend `STAGE_OF_ITEM` with `"funding_slipped": "signals", "cash": "covenant_testing"`. (An item type `cash.statement_mismatch` has prefix `cash`; `funding_slipped` has no dot, so `kind.split(".")[0]` is the whole name.)

In `evals/run.py::_cycle`, change the `seeded_items` line so items the system's funding check raised while seeding are not treated as seeded:

```python
        seeded_items = set(db.execute(select(WorkItem.id).where(
            WorkItem.borrower_id == row.id, WorkItem.item_type != "funding_slipped")).scalars())
```

with a comment: `# funding_slipped is raised by check_funding_events at seed time; it is the product's own exception and is graded`. Also grep `evals/grade.py` for other uses of `certificate["reported"][...]["value"]` (`grep -n '\["value"\]' evals/grade.py evals/standin.py`) and guard each against `None`; `StandInReader._certificate` already compares `printed * factor != _dec(reported["value"])` — Task 3 rewrites that.

- [ ] **Step 4: Run the tests**

Run: the three commands above.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
uv run ruff check evals && git add evals && git commit -m "fix(p3): grader picks the period's pack, tolerates a null certificate value; recorder keeps funding items"
```

---

### Task 3: Stand-in reader for the new document types

**Files:**
- Modify: `evals/standin.py` (`_intake`, `_spreading`, `_certificate`, helper `_label_rows`)
- Test: `evals/tests/test_standin_documents.py` (new; builds requests from the generated PDFs, no database)

**Interfaces:**
- Consumes: truth document entries (`type`, `figures`, `months`, `period_basis`, `held`) and `Borrower.document_by_file`.
- Produces: `StandInReader` answers (a) `spreading/` requests for `monthly_financials` with the year-to-date column first, `mrr_report` and `bank_statement` documents; (b) `certificate/` requests whose actuals are `"15.1 months"`, `"105.23%"`, `"6.54 to 1.00"`, `"Not meaningful (cash-flow positive)"` and whose required cell wraps over two lines; (c) `intake/` for term sheets, investor updates (filed only: type and date, no figures) and the held export (`doc_type: "other"`, concern text). Agreement with the truth is asserted per document in the tests.

- [ ] **Step 1: Write the failing test**

```python
# evals/tests/test_standin_documents.py
"""The stand-in reads every document of both books the way a careful reader would, and where print and
truth disagree the disagreement is recorded, not smoothed. Builds requests straight from the PDFs."""
import base64
import json

import pytest
from app.agents.llm import LLMRequest

from evals.book import BOOKS, load_book
from evals.standin import StandInReader

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
            got = {c["key"].removeprefix("stated.") for c in answer["cells"]}
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
    assert printed["is.revenue"] == meta["figures"]["is.revenue"]["printed"]  # the ten-months column, not the month


@pytest.mark.parametrize("name", ["legacy", "innovation"])
def test_every_certificate_row_is_read_including_text_actuals_and_wrapped_cells(name):
    book = load_book(BOOKS[name])
    reader = StandInReader(book)
    for borrower in book:
        for meta in borrower.truth["documents"]:
            if meta["type"] != "compliance_certificate" or not (book.root / meta["path"]).exists():
                continue
            answer = _answer(reader, _request(book, borrower, meta, "certificate"))
            truth = borrower.certificate(__import__("datetime").date.fromisoformat(meta["period_end"]))
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
    head = "\n".join(__import__("evals.standin", fromlist=["_lines"])._lines(
        __import__("pymupdf").open(book.root / meta["path"])[0]))
    text = f'<document number="1" file="mrr_export.pdf" pages="1">\n{head}\n</document>'
    request = LLMRequest(model="m", system="", messages=[{"role": "user", "content": text}],
                         record_key="intake/stripple-tech/2026-10-31")
    doc = _answer(reader, request)["documents"][0]
    assert doc["doc_type"] == "other" and doc["period_end_text"] == ""
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run python -m synthetic.books.innovation.generate && uv run pytest evals/tests/test_standin_documents.py -q`
Expected: FAIL (the certificate scan stops on non-numeric actuals; MRR/bank/monthly cells are short; ferrogate rows missing).

- [ ] **Step 3: Implement the reader changes**

In `evals/standin.py`:

1. **Spreading** already walks `meta["figures"]` row by row (`label`, then `printed`, then the comparative on the same row) and is document-type agnostic, so MRR and bank statements work once the page text yields `label, printed` adjacent lines. Two changes: (a) for `monthly_financials` with `period_basis == "fiscal_year_to_date"` the YTD column is the first figure after the label (as for annual), and the monthly column is the second; keep the existing "figure follows label" rule and set `column_header` from the header that the page prints for that column: replace the single `current` header with a lookup `header_for(lines, page)` returning the first printed date header on the page (YTD column header first) and fall back to `current`; (b) the units phrase for these documents may be absent on bank statements and MRR reports: only look for `_UNITS` when some figure is in `meta["figures"]` **and** `meta.get("scale", 1) != 1`; otherwise leave `scale_statement=""`, `scale_page=0`. A key that is `bs.cash_unrestricted` on a bank statement is reported as `bank.cash_unrestricted` (the product key, Task 5):

```python
BANK_KEYS = {"bs.cash_unrestricted": "bank.cash_unrestricted", "bs.cash_restricted": "bank.cash_restricted"}
...
name = BANK_KEYS[key] if meta["type"] == "bank_statement" and key in BANK_KEYS else (f"stated.{key}" if key in TOTALS else key)
```

2. **Certificate**: replace the fixed five-line row scan with a row reader that tolerates wrapped cells and non-numeric actuals:

```python
_COMPLIANCE = ("Yes", "No")


def _certificate_rows(lines: list[str], start: int) -> list[tuple[str, str, str, str, str]]:
    """Rows after the header: covenant, section, required, actual, in-compliance. A cell may wrap onto the
    next line, so a row ends at the Yes/No that closes it and its cells are the lines before it."""
    rows, current = [], []
    for line in lines[start:]:
        if line in _COMPLIANCE:
            if len(current) >= 4:
                # first line is the covenant, the next the section, the last two are required and actual;
                # anything between the covenant and the section is the wrapped covenant name
                actual, required = current[-1], current[-2]
                section = next((c for c in current[1:-2] if re.match(r"^(Section\s+)?\d", c)), "")
                name = " ".join(c for c in current[:-2] if c != section)
                rows.append((name, section, required, actual, line))
            current = []
        elif line.lower().startswith(("dollar amounts", "certif", "signed", "supporting")):
            break
        else:
            current.append(line)
    return rows
```

Use it in `_certificate`: `rows_found = _certificate_rows(lines, start + 5)` then build the same `rows` dicts (`by_name.get(label.lower())`; if the joined name does not match, try the first line only). The `_is_figure(lines[i + 3])` guard is removed: an actual such as `15.1 months`, `105.23%`, `6.54 to 1.00` or `Not meaningful (cash-flow positive)` is copied as printed. The agreement check below it must compare printed text to the truth through a helper:

```python
def _printed_matches(printed: str, reported: dict[str, Any], factor: Decimal) -> bool:
    if reported["value"] is None:
        return printed.lower().startswith("not meaningful")
    head = printed.replace(" months", "").replace(" to 1.00", "").strip()
    value = parse_printed(head) if head else None
    if value is None:
        return False
    unit = reported.get("unit", "ratio")
    if unit == "pct":
        value = value / 100 if printed.endswith("%") else value
    return value * factor == _dec(reported["value"])
```

(Check how `synthetic/render/innovation.py` prints `pct`: `grep -n "format_actual" -r synthetic backend`; if the book prints `105.23%` for a stored `1.0523`, dividing by 100 is exact; if the printed precision loses digits, compare at the printed precision with `quantize`. The truth value `1.0527` prints as `105.27%`.) Wrap `printed * factor != _dec(reported["value"])` in `_certificate` with `not _printed_matches(...)`.

3. **Intake**: term sheets and investor updates already pass through `_intake` (type from the truth, period or document date found on the head). Add the held export: `meta` has `"held": True` and type `unclassified` → `DOC_TYPES.get("unclassified")` is not a product type, so map it to `"other"` with `quality="na"` and a concern `"The file names no company and shows a different year."` (print-based: only when `squash(period_text)` is absent from `flat`). Add `"unclassified": "other"` to `DOC_TYPES` in `evals/book.py`; keep `title_as_printed` empty when no title line matches. Add `_TITLE` alternatives for the new heads: `term sheet|investor update|monthly recurring revenue|account statement|management financial statements`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest evals/tests/test_standin_documents.py -q`
Expected: PASS. If a document stays short, the page layout differs from the assumption: read that page with `python -c "import pymupdf;print(pymupdf.open('<path>')[0].get_text())"`, fix the reader (never the truth), and record any print-vs-truth disagreement in `reader.disagreements` as a finding.

- [ ] **Step 5: Commit**

```bash
uv run ruff check evals && git add evals && git commit -m "feat(p3): stand-in reads monthly packs, MRR reports, bank statements and non-numeric certificates"
```

---

### Task 4: Recordings carry the spec they were made under

**Files:**
- Modify: `backend/app/agents/llm.py` (`LLMRequest.spec`, `RecordingClient`, `RecordedClient`, `RecordingStale`)
- Modify: `backend/app/agents/runtime.py` (the `LLMRequest(...)` call: set `spec`)
- Create: `evals/stamp_recordings.py`
- Modify: `evals/run.py` (`--accept-stale`, `make_client`)
- Test: `backend/tests/agents/test_recordings_spec.py` (new)

**Interfaces:**
- Produces: `LLMRequest.spec: str = ""` formatted `"<agent>@<version>:<prompt sha-256, 12 hex>"`; `RecordingStale(Exception)`; recordings gain a top-level `"_spec"` string; `RecordedClient(root, accept_stale: frozenset[str] = frozenset())` raises `RecordingStale` when a stamped recording's `_spec` differs from the request's, and when a recording has no stamp (old format) unless the agent name is in `accept_stale`; `python -m evals.stamp_recordings` stamps every unstamped recording from git history.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agents/test_recordings_spec.py
import json

import pytest
from app.agents.llm import LLMRequest, LLMResponse, RecordedClient, RecordingClient, RecordingStale, ScriptedClient


def _request(spec):
    return LLMRequest(model="m", system="s", messages=[{"role": "user", "content": "x"}],
                      record_key="spreading/b/2026-09-30/abc/01", spec=spec)


def _response():
    return LLMResponse(content=[{"type": "text", "text": "{}"}], stop_reason="end_turn", model="m", usage={})


def test_a_recording_is_stamped_with_the_spec_and_replays_under_the_same_spec(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request("spreading@5:aaaaaaaaaaaa"))
    stored = json.loads((tmp_path / "spreading/b/2026-09-30/abc/01.json").read_text())
    assert stored["_spec"] == "spreading@5:aaaaaaaaaaaa"
    assert RecordedClient(tmp_path).create(_request("spreading@5:aaaaaaaaaaaa")).stop_reason == "end_turn"


def test_a_recording_from_another_version_or_prompt_refuses_to_replay(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request("spreading@3:aaaaaaaaaaaa"))
    with pytest.raises(RecordingStale, match="spreading@3"):
        RecordedClient(tmp_path).create(_request("spreading@5:aaaaaaaaaaaa"))
    with pytest.raises(RecordingStale):
        RecordedClient(tmp_path).create(_request("spreading@3:bbbbbbbbbbbb"))  # same version, edited prompt


def test_an_unstamped_old_recording_is_stale_unless_the_run_accepts_it_by_agent(tmp_path):
    path = tmp_path / "spreading/b/2026-09-30/abc/01.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({**_response().to_json()}))
    with pytest.raises(RecordingStale, match="no stamp"):
        RecordedClient(tmp_path).create(_request("spreading@5:aaaaaaaaaaaa"))
    assert RecordedClient(tmp_path, accept_stale=frozenset({"spreading"})).create(
        _request("spreading@5:aaaaaaaaaaaa")).stop_reason == "end_turn"
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest backend/tests/agents/test_recordings_spec.py -q`
Expected: FAIL (`RecordingStale` not defined).

- [ ] **Step 3: Implement**

In `backend/app/agents/llm.py`: add `spec: str = ""` to `LLMRequest` (after `record_key`); define

```python
class RecordingStale(Exception):
    """A saved model response was made under another version or prompt of the agent than the one asking."""
```

`RecordingClient.create` writes `{**response.to_json(), "_spec": request.spec}`. `LLMResponse.from_json` must ignore the extra key: check it (`from_json` builds from named keys; if it uses `**data`, pop `_spec` first). `RecordedClient.__init__(self, root=None, accept_stale=frozenset())`; in `create`, after reading the JSON:

```python
        data = json.loads(path.read_text())
        stamp = data.get("_spec")
        agent = request.spec.split("@", 1)[0] if request.spec else request.record_key.split("/", 1)[0]
        if request.spec and stamp != request.spec and agent not in self.accept_stale:
            raise RecordingStale(f"{path} was recorded under {stamp or 'no stamp'}, this request is {request.spec}"
                                 + ("" if stamp else " (no stamp: an old recording)"))
        return LLMResponse.from_json({k: v for k, v in data.items() if k != "_spec"})
```

(The test expects "no stamp" in the message for the unstamped case; the message above contains it.) A request with an empty `spec` (tests that script requests by hand) skips the check.

In `backend/app/agents/runtime.py`, in the `LLMRequest(...)` call add `spec=f"{spec.name}@{spec.version}:{hashlib.sha256(spec.prompt().encode()).hexdigest()[:12]}"` (import `hashlib`). Grep other construction sites (`grep -n "LLMRequest(" -r backend/app`) and give each agent that builds its own requests the same `spec`.

`evals/stamp_recordings.py`:

```python
"""One-off: stamp the recordings made before specs were stamped, from git history, never by guess.

For each unstamped recording, find the commit that added it, read the agent file and prompt as they
were in that commit, and write "<agent>@<version>:<prompt sha>" into the file."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from evals.book import REPO

AGENT_FILE = {"intake": ("intake.py", "intake.md", "intake"), "spreading": ("spreading.py", "spreading.md", "spreading"),
              "certificate": ("certificate.py", "certificate.md", "certificate_reader"),
              "collateral": ("collateral.py", "collateral.md", "collateral_reader"),
              "covenant": ("covenant.py", "covenant.md", "covenant"),
              "early_warning": ("early_warning.py", "early_warning.md", "early_warning"),
              "review": ("review.py", "review.md", "review")}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True, text=True).stdout


def stamp(recordings: Path) -> list[str]:
    done = []
    for path in sorted(recordings.rglob("*.json")):
        data = json.loads(path.read_text())
        if "_spec" in data:
            continue
        agent = path.relative_to(recordings).parts[0]
        code_file, prompt_file, name = AGENT_FILE[agent]
        commit = _git("log", "--diff-filter=A", "--format=%H", "--", str(path.relative_to(REPO))).split()[-1]
        source = _git("show", f"{commit}:backend/app/agents/{code_file}")
        version = re.search(r'version="(\d+)"', source).group(1)
        prompt = _git("show", f"{commit}:backend/app/agents/specs/{prompt_file}")
        data["_spec"] = f"{name}@{version}:{hashlib.sha256(prompt.encode()).hexdigest()[:12]}"
        path.write_text(json.dumps(data, indent=1, sort_keys=True))
        done.append(f"{path.relative_to(recordings)} -> {data['_spec']}")
    return done


if __name__ == "__main__":
    for line in stamp(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "evals" / "recordings"):
        print(line)
```

(Verify the agent `name=` strings with `grep -n 'name="' backend/app/agents/*.py` and fix `AGENT_FILE`; the `version=` regex fails loudly if a file declares it differently: then read that file.) The prompt hash at the recording's commit will differ from today's for any agent whose prompt moved, which is the point: those recordings are then stale and Task 11 decides re-record or `--accept-stale`.

In `evals/run.py`: `parser.add_argument("--accept-stale", nargs="*", default=[], metavar="AGENT", help="recorded mode: replay stale recordings of these agents (printed in the scorecard)")`; thread `accept_stale` through `run_suite` → `make_client(mode, ..., accept_stale=frozenset(...))` → `client_for` is bypassed for recorded mode: `RecordedClient(recordings, accept_stale)`; add `results["meta"]["accepted_stale"] = sorted(accept_stale)`; render it in `evals/scorecard.py::render_markdown` as a line "Stale recordings replayed by choice: ...".

- [ ] **Step 4: Run the tests, then stamp**

Run: `uv run pytest backend/tests/agents/test_recordings_spec.py evals/tests/test_run_guards.py -q` → PASS.
Run: `uv run python -m evals.stamp_recordings` → prints one line per recording (23 expected today). Read the output: each agent version must be plausible (intake 2 or 3, spreading 2 or 3). Then `uv run pytest backend/tests/agents -q` → PASS (scripted tests have empty `spec`).

- [ ] **Step 5: Commit**

```bash
uv run ruff check backend evals && git add backend evals && git commit -m "feat(p3): recordings carry the agent spec; stale ones refuse to replay unless accepted by agent"
```

---

### Task 5: Read MRR reports and bank statements in the live cycle

**Files:**
- Modify: `backend/app/calc/template.py` (an optional `bank` statement of two lines for `vc-1`)
- Modify: `backend/app/agents/spreading.py` (`_statements_for`, `REQUIRED_TOTALS` handling, SPEC version)
- Modify: `backend/app/agents/specs/spreading.md` (one paragraph: bank statements)
- Modify: `backend/app/domain/stages.py` (`spreading_stage`)
- Modify: `evals/grade.py` (`expected_facts`: MRR and bank facts)
- Test: `backend/tests/calc/test_template_bank.py`, `backend/tests/domain/test_spreading_stage_documents.py` (new), `evals/tests/test_grade_innovation.py` (extend)

**Interfaces:**
- Consumes: `Document.doc_type in {"mrr_report", "bank_statement"}`, `_documents(db, cycle, *types)` in `stages.py`.
- Produces: template lines `bank.cash_unrestricted` ("Total operating accounts (unrestricted)") and `bank.cash_restricted` ("Total pledged and restricted accounts"), both optional inputs of statement `bank`; `_statements_for(document)` returns `("bank",)` for a bank statement and `("saas",)` for an MRR report; `spreading_stage` spreads the financial pack, **then every MRR report and bank statement of the period**, one `spread_document` call each; SPEC `spreading` version `"5"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/calc/test_template_bank.py
from decimal import Decimal

from app.calc import template


def test_bank_lines_exist_for_the_venture_template_only_and_are_optional():
    keys = {l.key: l for l in template.template_lines("vc-1")}
    assert keys["bank.cash_unrestricted"].optional and keys["bank.cash_restricted"].optional
    assert not any(l.key.startswith("bank.") for l in template.template_lines("ci-1"))


def test_a_bank_statement_is_checked_for_the_bank_statement_only():
    values = {"bank.cash_unrestricted": Decimal("4300000"), "bank.cash_restricted": Decimal("1100000")}
    report = template.check_statement(values, scale=1, prior_fye_cash=None, absent=[], statements=("bank",),
                                      template_id="vc-1")
    assert [e for e in report.errors] == []
```

```python
# backend/tests/domain/test_spreading_stage_documents.py   (database test; reuse the fixtures of
# backend/tests/domain/ for a seeded innovation borrower in live mode, and the KeyedScriptedClient)
def test_the_stage_spreads_the_pack_then_each_mrr_report_and_bank_statement(live_cycle_for):
    """live_cycle_for("tidewell-medical") returns (db, cycle) with the current period's documents filed,
    exactly as test_seed_innovation.py loads a borrower with current="live" and runs intake."""
    db, cycle = live_cycle_for("tidewell-medical")
    stages.spreading_stage(db, cycle, workflow.stages(db, cycle)[2])
    keys = {f.key for f in db.execute(select(Fact).where(Fact.borrower_id == cycle.borrower_id,
                                                         Fact.period_end == cycle.period_end)).scalars()}
    assert {"saas.mrr", "saas.arr", "saas.customers"} <= keys
    assert {"bank.cash_unrestricted", "bank.cash_restricted"} <= keys
```

(The fixture is the one the Phase 2 Task 8 tests use; `grep -n "def .*live" backend/tests/test_seed_innovation.py backend/tests/domain/*.py backend/tests/conftest.py`. If none returns a cycle ready at spreading, build it from `seed_book(db, root=INNOVATION_ROOT, current="live", only=[code])`, `workflow.tick/drain` until the intake stage is done, driven by the stand-in via `evals.standin.StandInReader` through `stages.LLM_FACTORY`.)

Add to `evals/tests/test_grade_innovation.py`:

```python
def test_expected_facts_include_mrr_and_bank_figures_for_a_monthly_client():
    book = load_book(BOOKS["innovation"], ["tidewell-medical"])
    expected = Truth(book.get("tidewell-medical")).expected_facts()
    assert expected["saas.mrr"][2] == "mrr-2026-10-31.pdf"
    assert expected["bank.cash_unrestricted"][0] == 4300000 and expected["bank.cash_restricted"][0] == 1100000
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest backend/tests/calc/test_template_bank.py evals/tests/test_grade_innovation.py -q` → FAIL.

- [ ] **Step 3: Implement**

`backend/app/calc/template.py`: mirror how the optional `saas.*` lines and the `"saas"` statement are declared for `vc-1` (`grep -n "saas" backend/app/calc/template.py`). Add, with the same helper used there (`_line(key, label, section, optional=True)` or its equivalent), a statement `"bank"` containing the two lines above, registered so `_selected(("bank",))` accepts it and `statements=None` (a full pack) does not require them. Add the keys to the set at the end of the file that lists input lines allowed to be absent (the line near `"bs.cash_unrestricted", "bs.cash_restricted"` in the tuple at the bottom; read what that tuple is before touching it).

`backend/app/agents/spreading.py`:

```python
def _statements_for(document: Document | None) -> tuple[str, ...] | None:
    """The statements a document is read for. An MRR/ARR report holds only the SaaS lines and a bank
    statement only the two cash lines, so only those are checked; any other document is read for every
    statement of the template."""
    kind = document.doc_type if document is not None else None
    return {"mrr_report": ("saas",), "bank_statement": ("bank",)}.get(kind)
```

Where `spread_document` applies `REQUIRED_TOTALS[tid]` after checking footing, skip the required-total demand when `_statements_for(document)` is not `None` (it already must be skipped for MRR reports: find that branch with `grep -n "mrr_report\|_statements_for" backend/app/agents/spreading.py` and extend the same condition to bank statements). Bump `SPEC` to `version="5"`. Add to `specs/spreading.md` one paragraph: "A bank statement or MRR report is not a set of statements: report only the lines of the template named in the listing that the page prints (the account totals); do not report totals you compute." (Keep it in the prompt's existing style.)

`backend/app/domain/stages.py::spreading_stage` — after the existing `spread_document(...)` for the pack, add:

```python
    for extra in _documents(db, cycle, "mrr_report", "bank_statement"):
        extra_result = spreading.spread_document(
            db, borrower=borrower, document=extra, period_end=cycle.period_end, months=cycle.months,
            cycle=cycle, llm=_llm(), prior_fye_cash=None)
        st.detail = {**st.detail, f"read_{extra.doc_type}_{extra.id}": extra_result.status}
```

The early `return "waiting"` when there is no pack stays (the cycle waits for the pack). A statement spread that raised a blocking item must not be followed by more calls: guard with `if result.status != "spread": return "done"` before the loop only if `spread_document` already raised a blocking item for the pack (read `SpreadResult.status` values first).

`evals/grade.py::expected_facts`: after the pack block, add MRR and bank expectations (skipped when `self.halted`):

```python
        for d in self.docs:
            if d["type"] in ("mrr_report", "bank_statement") and "figures" in d and not self.halted:
                file, scale = Path(d["path"]).name, Decimal(d.get("scale", 1))
                for key, figure in d["figures"].items():
                    name = BANK_KEYS.get(key, key) if d["type"] == "bank_statement" else key
                    out[name] = (self._printed(key, figure["printed"], scale), d["period_end"], file)
```

with `BANK_KEYS` defined once in `evals/book.py` and imported by both `grade.py` and `standin.py` (Task 3's local constant moves there). `value_for` must then answer for `bank.*` and `saas.*` facts: `saas.*` keys are already in `period["values"]`; for `bank.*` the expected dict answers (it is consulted first).

- [ ] **Step 4: Run the tests**

Run: `uv run pytest backend/tests/calc backend/tests/agents/test_spreading_saas.py backend/tests/agents/test_spreading_vc.py evals/tests/test_grade_innovation.py -q`; then the database test. Expected: PASS. Run `uv run python -m evals.run --mode standin --book innovation --only tidewell-medical stripple-tech ferrogate-cloud --no-eval-run` (needs Postgres) and confirm the three show extraction at 100 percent including the MRR and bank documents in `by_document`.

- [ ] **Step 5: Commit**

```bash
uv run ruff check backend evals && git add backend evals && git commit -m "feat(p3): the live cycle reads MRR reports and bank statements; spreading 5"
```

---

### Task 6: The statements-to-certificate cash reconciliation (`cash.statement_mismatch`)

**Files:**
- Create: `backend/app/domain/cash_reconciliation.py`
- Modify: `backend/app/domain/stages.py` (`covenant_stage` tail), `backend/app/domain/workflow.py` (allowed decisions map, if items need decisions to be handled), `evals/run.py` (`DECISIONS`)
- Test: `backend/tests/domain/test_cash_reconciliation.py` (new), `evals/tests/test_standin_suite.py` (Task 9 asserts the end result)

**Interfaces:**
- Consumes: facts `bank.cash_unrestricted` (Task 5), `CovenantTest.reported_value` for `min_unrestricted_cash`, `raise_item(... dedupe_key=...)`.
- Produces: `reconcile_cash(db, *, borrower, cycle) -> WorkItem | None`; item type `cash.statement_mismatch`, severity `high`, `blocks_stage=False`, `allowed_decisions=["reviewed", "ask_borrower", "escalate_to_committee"]`, `required_permission="decide_breach"`, dedupe key `cash.statement_mismatch:<borrower>:<period>`, evidence `{"bank_fact_id", "certificate_value", "bank_value", "covenant_test_id"}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/domain/test_cash_reconciliation.py
from decimal import Decimal

from app.domain.cash_reconciliation import reconcile_cash


def test_tidewell_gets_one_mismatch_for_the_certificate_that_counts_the_escrow_account(innovation_cycle):
    db, borrower, cycle = innovation_cycle("tidewell-medical", through="covenant_testing")
    first = reconcile_cash(db, borrower=borrower, cycle=cycle)
    again = reconcile_cash(db, borrower=borrower, cycle=cycle)
    assert first is not None and first.item_type == "cash.statement_mismatch" and first.severity == "high"
    assert first.evidence["bank_value"] == "4300000" and first.evidence["certificate_value"] == "5300000"
    assert again is None or again.id == first.id  # once per period


def test_dataflake_already_asks_the_question_so_it_gets_no_second_item(innovation_cycle):
    db, borrower, cycle = innovation_cycle("dataflake", through="covenant_testing")
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None  # covenant.reported_mismatch is open


def test_a_client_whose_certificate_agrees_with_the_bank_gets_nothing(innovation_cycle):
    db, borrower, cycle = innovation_cycle("ferrogate-cloud", through="covenant_testing")
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None


def test_no_bank_statement_means_no_reconciliation_and_no_zero(innovation_cycle):
    db, borrower, cycle = innovation_cycle("lumora-health", through="covenant_testing")  # October bank statement is late
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None
```

(`innovation_cycle(code, through=...)` is a new fixture in `backend/tests/domain/conftest.py`: seed the borrower with `current="live"` and run the cycle to the end of the named stage with the stand-in as `stages.LLM_FACTORY`, as `evals.run.LoadedBorrower` does. Reuse `LoadedBorrower` machinery if it is simpler: `from evals.run import LoadedBorrower`.)

- [ ] **Step 2: Run it to see it fail**

Run: `TEST_DATABASE_URL=... uv run pytest backend/tests/domain/test_cash_reconciliation.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/domain/cash_reconciliation.py
"""Bank statements against the compliance certificate: does the cash the borrower counts as unrestricted
match what the bank's own statements show as unrestricted? One question per cause: if a covenant item
already asks it for this period, no second item is raised."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.credit import Borrower
from app.domain.facts import current_fact
from app.domain.monitoring import CovenantTest, Cycle, WorkItem
from app.domain.work_items import raise_item

COVENANT = "min_unrestricted_cash"
COVENANT_ITEMS = ("covenant.breach", "covenant.reported_mismatch")


def reconcile_cash(db: Session, *, borrower: Borrower, cycle: Cycle) -> WorkItem | None:
    bank = current_fact(db, borrower.id, "bank.cash_unrestricted", cycle.period_end, 0)
    test = db.execute(select(CovenantTest).where(
        CovenantTest.cycle_id == cycle.id, CovenantTest.covenant_id == COVENANT,
        CovenantTest.superseded.is_(False))).scalars().first()
    if bank is None or test is None or test.reported_value is None:
        return None  # a missing input is never zero: nothing to reconcile
    if bank.value == test.reported_value:
        return None
    asked = db.execute(select(WorkItem.id).where(
        WorkItem.cycle_id == cycle.id, WorkItem.item_type.in_(COVENANT_ITEMS),
        WorkItem.evidence["covenant_test_id"].astext == str(test.id))).first()
    if asked is not None:
        return None
    return raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing", item_type="cash.statement_mismatch",
        severity="high", blocks_stage=False,
        title=f"{borrower.name}: bank statements and the certificate disagree on unrestricted cash",
        question="The bank statements show less unrestricted cash than the certificate counts. An account may be "
                 "pledged or restricted. What should we do?",
        allowed_decisions=["reviewed", "ask_borrower", "escalate_to_committee"], required_permission="decide_breach",
        evidence={"bank_fact_id": str(bank.id), "covenant_test_id": str(test.id),
                  "bank_value": format(bank.value, "f"), "certificate_value": format(test.reported_value, "f")},
        dedupe_key=f"cash.statement_mismatch:{borrower.code}:{cycle.period_end}", actor=("system", "reconciliation"))
```

(Before writing, read `raise_item`'s signature and `current_fact`'s, and `WorkItem.cycle_id`; align the keyword names. `format(Decimal('4300000'), 'f')` is `"4300000"`; if the fact stores `4300000.00`, compare with `Decimal.normalize`-safe formatting or change the test's expected strings to match what the fact stores, never the other way round.)

In `stages.py::covenant_stage`, at the point after covenant tests are stored and before the stage returns done: `reconcile_cash(db, borrower=borrower, cycle=cycle)`. Where an item type needs a workflow decision mapping (`("funding_slipped", "reserve_rights"): "decide_breach"` in `workflow.py`), add `("cash.statement_mismatch", d): "decide_breach"` for each allowed decision, mirroring that block. In `evals/run.py::DECISIONS` add `"cash.statement_mismatch": ("reviewed", "Bank statements and the certificate differ on unrestricted cash; reviewed with the analyst and carried into the review.")`. Add `cash.statement_mismatch` to the item list in `docs/owner-questions.md` item 7 ("the tests pin it as pending until Phase 3") by deleting the "pending" pin: find that test with `grep -rn "statement_mismatch" backend/tests synthetic/tests` and change it from pending to asserting the exception is raised.

- [ ] **Step 4: Run the tests**

Run: the new test file, then `uv run python -m evals.run --mode standin --book innovation --only tidewell-medical dataflake ferrogate-cloud --no-eval-run`. Expected: Tidewell raises `cash.statement_mismatch`; Dataflake and Ferrogate raise exactly their expected exceptions.

- [ ] **Step 5: Commit**

```bash
uv run ruff check backend evals && git add backend evals docs/owner-questions.md && git commit -m "feat(p3): cash reconciliation of bank statements to the certificate raises cash.statement_mismatch"
```

---

### Task 7: Venture signals store their source facts

**Files:**
- Modify: `backend/app/domain/signals_service.py` (`_source_facts`)
- Modify: `backend/app/domain/metrics_service.py` only if venture metrics are not storable there (read first)
- Test: `backend/tests/domain/test_signals_source_facts_vc.py` (new)

**Interfaces:**
- Consumes: `store_metric(db, borrower, metric, end) -> Fact | None`, `_RULES[rule].params["metric"]`, `sig.Signal.basis`.
- Produces: every fired venture signal's `basis["metric_fact_ids"]` is a non-empty dict `{"current": id, "year_earlier"?: id}` whose ids are stored facts; the grader's `untraced-figure` observation count is 0 on the innovation book.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/domain/test_signals_source_facts_vc.py
import pytest

from app.domain.monitoring import Signal
from sqlalchemy import select

VENTURE_RULES = ("runway_below_watch", "runway_falling", "burn_rising", "revenue_below_plan",
                 "covenant_headroom_falling")


@pytest.mark.parametrize("code", ["brightvane-energy", "nimbusfield-security", "corvane-analytics", "dataflake"])
def test_every_venture_signal_basis_links_each_figure_to_a_stored_fact(innovation_cycle, code):
    db, borrower, cycle = innovation_cycle(code, through="signals")
    signals = db.execute(select(Signal).where(Signal.cycle_id == cycle.id)).scalars().all()
    assert signals
    for s in signals:
        if s.rule_id not in VENTURE_RULES:
            continue
        ids = (s.basis or {}).get("metric_fact_ids") or {}
        assert ids, f"{code} {s.rule_id}: the basis shows figures with no source fact"
```

(`covenant_headroom_falling` carries `headroom` facts via `cov.<id>.headroom_pct`; see `_series`. If a rule's figure is a headroom value, the id belongs under `basis["headroom_fact_ids"]`; set the assertion per rule after reading `calc/signals.py` for which keys each rule's basis carries: `grep -n "basis" backend/app/calc/signals.py | head -40`.)

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest backend/tests/domain/test_signals_source_facts_vc.py -q` → FAIL for the rules whose `metric` is not in `lib.METRICS` / `EXTRA`.

- [ ] **Step 3: Implement**

Read `backend/app/domain/metrics_service.py` (`EXTRA`, `store_metric`) and the venture rule params (`grep -n "_RULES\|params" backend/app/calc/signals.py`). Venture signal rules use metrics such as runway months and net burn that the vc-1 metric library defines separately from the C&I `lib.METRICS`. Extend the guard in `_source_facts` so it asks the vc library when the borrower is a venture borrower:

```python
    metric = _RULES[fired.rule_id].params.get("metric") if fired.rule_id in _RULES else None
    known = metric and (metric in EXTRA or metric in lib.METRICS or metric in lib.VC_METRICS)
```

(Use the real name of the venture metric registry found by the read; `store_metric` must accept it, adding `vc-1` names to its dispatch if it does not. The store writes a `calc` fact through the same formula path as covenant metrics; it never edits an existing fact.) For `revenue_below_plan` the figures are the trailing revenue and the approved plan; store both as metric facts and record them under `metric_fact_ids` keys `current` and `plan`. For rules with no `metric` param (burn_rising uses a three-month average), store the metric the rule names in `RULE_METRIC` instead of a param: add a small mapping `VENTURE_RULE_METRIC = {"burn_rising": "net_burn_3m_avg", "runway_falling": "runway_months", "runway_below_watch": "runway_months", "revenue_below_plan": "revenue_vs_plan"}` using the metric names the library actually defines (verify each by `python -c "from app.calc import metrics as m; print(sorted(m.METRICS))"`).

- [ ] **Step 4: Run the tests**

Run: the new test; `uv run pytest backend/tests/calc/test_signals_vc.py -q`; then the stand-in on `brightvane-energy nimbusfield-security corvane-analytics dataflake` and confirm `observations` has no `untraced-figure`.

- [ ] **Step 5: Commit**

```bash
uv run ruff check backend && git add backend && git commit -m "fix(p3): venture signals store the facts behind their figures"
```

---

### Task 8: Spreadsheet intake (.xlsx and .csv), plus the intake-rule carry items

**Files:**
- Modify: `pyproject.toml` (add `openpyxl` to backend dependencies), `uv.lock`
- Create: `backend/app/domain/spreadsheets.py`
- Modify: `backend/app/domain/documents_service.py` (`ingest_document`, `_store` extension), `backend/app/api/routes_credit.py` (accept the types), `backend/app/seed_book.py` (the held export is the workbook), `backend/app/agents/intake.py` (the `credit_agreement` heading anchor)
- Modify: `evals/book.py` (`document_by_file` finds a workbook companion), `evals/standin.py` (`_intake` reads sheet text)
- Test: `backend/tests/domain/test_spreadsheet_intake.py` (new), `backend/tests/agents/test_intake_rules_on_books.py` (generate PDFs in a fixture; no silent skip), `backend/tests/agents/test_intake.py` (anchor cases)

**Interfaces:**
- Produces: `spreadsheet_pages(data: bytes, file_name: str) -> list[SheetPage]` with `SheetPage(name: str, lines: list[str], cells: dict[str, str])`; each line is `"<Sheet>!<A1> | <label> | <value>"` per non-empty row cell pair (label = first text cell on the row, value = the cell); `ingest_document(db, *, data, file_name, ...)` accepts `%PDF`, `.xlsx` (zip magic `PK`) and `.csv`, and stores a `DocumentPage` per sheet with `text` = the lines joined by newline, `words` = `[]`, `meta = {"format": "xlsx" | "csv", "sheets": [names]}`; `ingest_pdf` stays as the PDF path and is called by `ingest_document`. A cell citation is the line text; the quote guardrail finds it because page `text` holds it.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/domain/test_spreadsheet_intake.py
from pathlib import Path

import pytest
from app.domain.documents import DocumentPage
from app.domain.documents_service import DocumentRefused, ingest_document
from app.domain.spreadsheets import spreadsheet_pages
from sqlalchemy import select

EXPORT = Path(__file__).resolve().parents[3] / "synthetic/books/innovation/out/documents/stripple-tech/mrr_export.xlsx"


def test_each_sheet_becomes_a_page_of_cell_cited_lines():
    pages = spreadsheet_pages(EXPORT.read_bytes(), "mrr_export.xlsx")
    assert pages and all(p.lines for p in pages)
    assert all("!" in line and " | " in line for p in pages for line in p.lines)


def test_the_export_is_ingested_as_a_document_with_cell_level_text(db, borrower):
    doc = ingest_document(db, borrower_id=borrower.id, data=EXPORT.read_bytes(), file_name="mrr_export.xlsx")
    pages = db.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id)).scalars().all()
    assert doc.file_name.endswith(".xlsx") and doc.meta["format"] == "xlsx" and doc.page_count == len(pages)
    assert doc.storage_path.endswith(".xlsx")


def test_a_csv_is_ingested_as_one_sheet_and_garbage_is_refused(db, borrower):
    doc = ingest_document(db, borrower_id=borrower.id, data=b"Month,MRR\n2025-01,100\n", file_name="m.csv")
    assert doc.meta["format"] == "csv"
    with pytest.raises(DocumentRefused):
        ingest_document(db, borrower_id=borrower.id, data=b"MZ\x00\x00", file_name="x.exe")


def test_the_export_is_held_with_one_question_and_never_filed(live_cycle_for):
    db, cycle = live_cycle_for("stripple-tech")  # seeds the workbook, runs intake with the stand-in
    from app.domain.monitoring import WorkItem
    held = db.execute(select(WorkItem).where(WorkItem.borrower_id == cycle.borrower_id,
                                             WorkItem.item_type == "intake.unclassified")).scalars().all()
    assert len(held) == 1 and "mrr_export.xlsx" in held[0].title
```

Intake-rule carry (replace the skip): in `test_intake_rules_on_books.py` add a session fixture that runs both generators into `tmp_path_factory` and use it instead of reading `synthetic/out`:

```python
@pytest.fixture(scope="session")
def books(tmp_path_factory):
    import subprocess, sys
    roots = {}
    for name, module in (("legacy", "synthetic.generate"), ("innovation", "synthetic.books.innovation.generate")):
        out = tmp_path_factory.mktemp(name) / "out"
        subprocess.run([sys.executable, "-m", module, "--out", str(out)], check=True, capture_output=True)
        roots[name] = out
    return roots
```

then parametrise over `books` and delete the `pytest.skip`; if no PDFs are generated the test must fail (`assert docs`).

Anchor cases in `test_intake.py`:

```python
@pytest.mark.parametrize("head", [
    "AMENDED AND RESTATED CREDIT AGREEMENT\ndated as of March 1, 2024",
    "Second Amendment to Amended and Restated Credit Agreement",   # an amendment, not a credit agreement
    "VENTURE LOAN AND SECURITY AGREEMENT",
    "Loan and Security Agreement among Veridia Payments and Bank of Stoic",
])
def test_the_credit_agreement_heading_anchor_handles_real_titles(head):
    expected = "amendment" if head.startswith("Second Amendment") else "credit_agreement"
    assert rule_type(head) == expected
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest backend/tests/domain/test_spreadsheet_intake.py backend/tests/agents/test_intake.py -q` → FAIL (`spreadsheets` missing; the "Amended and Restated" title is not matched).

- [ ] **Step 3: Implement**

`uv add openpyxl` (a dependency addition: pin through `uv.lock`; no network call other than the package index). `backend/app/domain/spreadsheets.py`:

```python
"""Spreadsheets as documents: one text page per sheet, one line per row, each line naming its sheet and cell so
a figure can be cited to the cell it came from."""
import csv
import io
from dataclasses import dataclass, field

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


@dataclass
class SheetPage:
    name: str
    lines: list[str] = field(default_factory=list)
    cells: dict[str, str] = field(default_factory=dict)


def _rows_to_page(name: str, rows) -> SheetPage:
    page = SheetPage(name)
    for r, row in enumerate(rows, start=1):
        label = next((str(v) for v in row if isinstance(v, str) and v.strip()), "")
        for c, value in enumerate(row, start=1):
            if value is None or str(value).strip() == "" or (isinstance(value, str) and str(value) == label):
                continue
            ref = f"{get_column_letter(c)}{r}"
            page.cells[ref] = str(value)
            page.lines.append(f"{name}!{ref} | {label} | {value}")
    return page


def spreadsheet_pages(data: bytes, file_name: str) -> list[SheetPage]:
    if file_name.lower().endswith(".csv"):
        text = data.decode("utf-8-sig")
        return [_rows_to_page("Sheet1", list(csv.reader(io.StringIO(text))))]
    book = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    return [_rows_to_page(ws.title, ws.iter_rows(values_only=True)) for ws in book.worksheets]
```

`documents_service.py`: change `_store(data, sha)` to `_store(data, sha, suffix=".pdf")`; add

```python
def ingest_document(db, *, borrower_id, data: bytes, file_name: str, **kwargs) -> Document:
    """A PDF, an .xlsx workbook or a .csv file. Anything else is refused."""
    name = file_name.lower()
    if data.startswith(b"%PDF"):
        return ingest_pdf(db, borrower_id=borrower_id, data=data, file_name=file_name, **kwargs)
    if name.endswith((".xlsx", ".csv")) and (name.endswith(".csv") or data[:2] == b"PK"):
        return _ingest_sheets(db, borrower_id=borrower_id, data=data, file_name=file_name, **kwargs)
    raise DocumentRefused("Only PDF, Excel (.xlsx) and CSV files are accepted.")
```

where `_ingest_sheets` mirrors `ingest_pdf`'s `Document(...)` construction (copy its keyword list), stores bytes with the file's suffix, adds one `DocumentPage` per `SheetPage` (`text="\n".join(page.lines)`, `words=[]`, `width=0.0`, `height=0.0`, `has_text=bool(page.lines)`), sets `doc.meta = {"image_only_pages": [], "format": "xlsx"|"csv", "sheets": [...]}`, status `"indexed"`, and records the same `document.received` ledger event with `"format"` in the payload. `read_file` and `_fallback_file` look for `.pdf` only: make `_fallback_file` glob `*.pdf`, `*.xlsx`, `*.csv`. `routes_credit.py` (upload route near line 221): call `ingest_document` and widen the content check message. `seed_book.py`: a truth document with `held` and a `workbook` entry is ingested from the workbook path via `ingest_document` and its PDF print is counted skipped (reverse of today): replace the `path.suffix != ".pdf"` skip with

```python
        workbook = d.get("workbook")
        if workbook and held_doc and (docs_root / workbook["path"]).exists():
            path = docs_root / workbook["path"]          # the real file is what arrives; the PDF print is not loaded
        elif path.suffix.lower() not in (".pdf",):
            report.skipped_documents += 1
            continue
```

(and remove the trailing "workbook companion counted as skipped" block; count the print as skipped instead). Adjust `test_seed_innovation.py` counts accordingly (read what it pins for `skipped_documents`). The intake classification text (`_head` in `intake.py`) reads `DocumentPage.text` for the first pages, so a sheet page works unchanged; `rule_type` finds no rule and the Intake Agent answers `other`; the company/date checks already raise `intake.unclassified` for "names no company, wrong year".

`intake.py` credit agreement anchor: read the current regex (`grep -n "credit_agreement" -B3 -A6 backend/app/agents/intake.py`) and widen it to `^\s*(?:(?:first|second|third|fourth)\s+)?(?:amended\s+and\s+restated\s+)?(?:venture\s+)?(?:credit|loan)(?:\s+and\s+security)?\s+agreement\b` with `re.I | re.M`, applied **after** the amendment and waiver rules so "Second Amendment to Amended and Restated Credit Agreement" is an amendment (the rule order test above pins it). Intake agent version stays 3 (a rule, not the prompt); if the prompt text changes, bump to 4 and note that the kept recordings go stale.

`evals/book.py::Borrower.document_by_file`: after the existing lookup, `or next((d for d in docs if (d.get("workbook") or {}).get("path", "").endswith("/" + file_name)), None)`. `evals/standin.py::_intake`: the `head` of a sheet document is its lines; `meta` resolves to the held export; the existing branch for `meta.get("held")` (Task 3) gives `other` with the concern text.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest backend/tests/domain/test_spreadsheet_intake.py backend/tests/agents/test_intake.py backend/tests/agents/test_intake_rules_on_books.py -q` → PASS (the last must run, not skip: `-rs` shows no skips). Then `uv run pytest backend/tests/test_seed_innovation.py -q` once, alone (it needs the database; lesson: one database test file at a time).

- [ ] **Step 5: Commit**

```bash
uv run ruff check backend evals && git add pyproject.toml uv.lock backend evals && git commit -m "feat(p3): spreadsheets are documents with cell-level text; Stripple's export is ingested and held"
```

---

### Task 9: The stand-in gate passes on both books (no model, no cost)

**Files:**
- Modify: `evals/tests/test_standin_suite.py`, `evals/tests/test_mutations.py` (book parametrisation if needed), `evals/known_findings.json` (stays empty), `evals/README.md`, `docs/HANDOFF.md`, `docs/owner-questions.md`
- Modify: anything the run exposes (a product defect is fixed in the product with a test, a reader defect in `standin.py`; a truth disagreement is reported, never patched)

**Interfaces:**
- Consumes: Tasks 1–8.
- Produces: `uv run python -m evals.run --mode standin --book both --mutations` exits 0; the stand-in suite agrees with the truth in full: extraction 100 percent, covenant outcomes 100 percent, exception precision and recall 100 percent, no `untraced-figure`, no disagreements, `known_findings.json` has an empty `findings` list, every cycle either reaches signals or rests on an item its scenario expects.

- [ ] **Step 1: Run the cross-checks first (generator against `app/calc`), both books**

Run: `uv run pytest backend/tests/calc/test_synthetic_truth.py backend/tests/calc/test_synthetic_innovation_truth.py synthetic -q`
Expected: PASS (726 innovation covenant tests exact, the legacy set exact). If anything disagrees: stop, investigate, report. Never patch either side to match the other.

- [ ] **Step 2: Add the scenario-level assertions to the suite**

In `evals/tests/test_standin_suite.py` add (parametrised by `book_name` via the `suite` fixture from Task 1):

```python
def test_no_untraced_figures_and_no_disagreements(suite):
    for code, graded in suite["borrowers"].items():
        assert [o for o in graded["observations"] if o["kind"] == "untraced-figure"] == [], code
        assert graded["disagreements"] == [], code
    assert suite["standin"]["disagreements"] == []


def test_the_scenarios_raise_exactly_what_the_book_expects(suite, book_name):
    if book_name != "innovation":
        pytest.skip("the legacy scenarios are covered by test_every_cycle_reaches_signals_or_rests_on_an_item_its_scenario_expects")
    raised = {c: set(g["raised_exceptions"]) for c, g in suite["borrowers"].items()}
    assert "cash.statement_mismatch" in raised["tidewell-medical"]
    assert "funding_slipped" in raised["nimbusfield-security"]
    assert "intake.unclassified" in raised["stripple-tech"] and "spread.value_unverified" in raised["stripple-tech"]
    assert raised["ferrogate-cloud"] == set()          # compliant, runway "not meaningful", nothing raised
```

(`suite["standin"]["disagreements"]` — confirm where `build_results` stores `standin_disagreements`: `grep -n "standin_disagreements" evals/grade.py` and use that key.)

- [ ] **Step 3: Run the whole suite on both books**

Run:
```bash
service postgresql start
export TEST_DATABASE_URL=postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad_test
uv run python -m evals.run --mode standin --book both --mutations
```
Expected: both gates PASSED. Read `evals/results/latest.md` and `latest-legacy.md` in full. For each difference, apply the rule from the lesson `seeded-replay-hides-live-path-defects`: a product defect gets a failing test in the product's tests and a fix there (commit separately with a `fix(p3):` prefix); a reader defect gets a test in `evals/tests/test_standin_documents.py` and a fix in `standin.py`; a truth-versus-print disagreement is recorded as a finding to the owner, listed in `known_findings.json` only if it is an open reported product finding (the gate tolerates exactly those, and an entry that no longer occurs fails the gate). Iterate until clean. The mutation checks (`evals/mutations.py`) must all be caught; add one mutation per new document type that asserts a tampered MRR figure and a tampered bank figure are caught by the product's verification or by the grader (follow the existing `Mutation` entries in `evals/mutations.py`).

- [ ] **Step 4: Run the full suites once**

Run: `uv run pytest evals/tests -q`, then `uv run pytest backend/tests/calc backend/tests/agents synthetic -q`, then `uv run ruff check .` (database tests that are not eval tests run one file at a time).
Expected: PASS.

- [ ] **Step 5: Update the records and commit**

`evals/README.md`: two books, `--book`, the new reader coverage table rows (MRR, bank, monthly pack, certificate forms, spreadsheets), `--accept-stale`. `docs/HANDOFF.md`: Phase 3 stand-in gate passed on both books; what remains (sign-off, live pass). `docs/owner-questions.md`: item 5 (spreadsheets) built; item 7 (cash mismatch) built.

```bash
git add -A evals docs backend synthetic && git commit -m "feat(p3): stand-in gate passes on both books; records updated"
```

---

### Task 10: The answer-key sign-off table (owner gate)

**Files:**
- Create: `evals/signoff.py`
- Test: `evals/tests/test_signoff.py` (new)
- Modify: `docs/owner-questions.md` (the table is posted there for the owner), `docs/HANDOFF.md`

**Interfaces:**
- Produces: `uv run python -m evals.signoff table` prints one short markdown table (counts derived from `oracle.csv` at run time, grouped by borrower and kind, with a "what the key expects" column in plain words) and a first line stating the totals; `uv run python -m evals.signoff apply --rows <file>` sets `owner_signed_off=yes` on exactly the keys listed in `<file>` and refuses an empty file, a key not in the oracle, or a file edit that touches any other column; `apply --all` signs every row (used only when the owner's reply says "approve all").

- [ ] **Step 1: Write the failing test**

```python
# evals/tests/test_signoff.py
import csv
from pathlib import Path

import pytest

from evals import signoff

HEADER = "borrower_id,borrower_name,period_end,kind,item,expected_value,threshold,expected_outcome,terms_version,scenario,owner_signed_off\n"


def _oracle(tmp_path: Path) -> Path:
    path = tmp_path / "oracle.csv"
    path.write_text(HEADER
                    + "acme,Acme,2026-10-31,covenant_test,min_cash,4600000,>= 5000000,breach,tv-1,s,no\n"
                    + "acme,Acme,2026-10-31,signal,runway_below_watch,7.1,,high,,s,no\n"
                    + "kept,Kept,2026-09-30,covenant_test,dscr,1.5,>= 1.2,compliant,tv-2,s,yes\n")
    return path


def test_the_table_counts_unsigned_rows_by_borrower_and_kind(tmp_path):
    text = signoff.table(_oracle(tmp_path))
    assert text.splitlines()[0].startswith("2 unsigned rows (1 signal) of 3")
    assert "| acme | 1 | 1 | 0 |" in text and "kept" not in text


def test_apply_signs_exactly_the_listed_rows_and_nothing_else(tmp_path):
    oracle = _oracle(tmp_path)
    rows = tmp_path / "rows.txt"
    rows.write_text("acme|2026-10-31|covenant_test|min_cash\n")
    assert signoff.apply(oracle, rows) == 1
    got = {(r["item"]): r for r in csv.DictReader(oracle.open(newline=""))}
    assert got["min_cash"]["owner_signed_off"] == "yes" and got["runway_below_watch"]["owner_signed_off"] == "no"
    assert got["min_cash"]["expected_value"] == "4600000"  # no other column moved


def test_apply_refuses_an_empty_file_and_a_row_that_is_not_in_the_key(tmp_path):
    oracle = _oracle(tmp_path)
    empty, bad = tmp_path / "e.txt", tmp_path / "b.txt"
    empty.write_text("")
    bad.write_text("acme|2026-10-31|covenant_test|nope\n")
    with pytest.raises(ValueError, match="no rows"):
        signoff.apply(oracle, empty)
    with pytest.raises(ValueError, match="not in the oracle"):
        signoff.apply(oracle, bad)
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest evals/tests/test_signoff.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# evals/signoff.py
"""The owner's answer key, as one short table, and the step that records the owner's reply."""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

from evals.book import BOOKS, oracle_for

KINDS = ("covenant_test", "signal", "exception", "funding_event", "borrowing_base")
KEY = ("borrower_id", "period_end", "kind", "item")


def _rows(oracle: Path) -> tuple[list[str], list[dict[str, str]]]:
    with oracle.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def table(oracle: Path) -> str:
    _, rows = _rows(oracle)
    unsigned = [r for r in rows if r["owner_signed_off"].strip().lower() != "yes"]
    by: dict[str, Counter] = defaultdict(Counter)
    for r in unsigned:
        by[r["borrower_id"]][r["kind"]] += 1
    signals = sum(1 for r in unsigned if r["kind"] == "signal")
    out = [f"{len(unsigned)} unsigned rows ({signals} signal{'s' if signals != 1 else ''}) of {len(rows)}; "
           "the signed rows are the kept four's and are not shown.", "",
           "| Client | Covenant tests | Signals | Exceptions and events | What the key expects |",
           "|---|---|---|---|---|"]
    for code in sorted(by):
        c = by[code]
        events = c["exception"] + c["funding_event"] + c["borrowing_base"]
        expects = "; ".join(sorted({r["scenario"] for r in unsigned if r["borrower_id"] == code}))
        out.append(f"| {code} | {c['covenant_test']} | {c['signal']} | {events} | {expects} |")
    return "\n".join(out)


def apply(oracle: Path, rows_file: Path | None, *, everything: bool = False) -> int:
    fields, rows = _rows(oracle)
    wanted = set()
    if not everything:
        lines = [l.strip() for l in (rows_file.read_text().splitlines() if rows_file else []) if l.strip()]
        if not lines:
            raise ValueError("no rows given: list the rows the owner approved, or use --all when the reply says approve all")
        wanted = {tuple(l.split("|")) for l in lines}
        known = {tuple(r[k] for k in KEY) for r in rows}
        missing = sorted(wanted - known)
        if missing:
            raise ValueError(f"not in the oracle: {missing[:3]}")
    signed = 0
    for r in rows:
        if r["owner_signed_off"].strip().lower() != "yes" and (everything or tuple(r[k] for k in KEY) in wanted):
            r["owner_signed_off"] = "yes"
            signed += 1
    with oracle.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return signed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.signoff")
    parser.add_argument("command", choices=("table", "apply"))
    parser.add_argument("--oracle", default=str(oracle_for(BOOKS["innovation"])))
    parser.add_argument("--rows")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "table":
        print(table(Path(args.oracle)))
        return 0
    print(f"signed {apply(Path(args.oracle), Path(args.rows) if args.rows else None, everything=args.all)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

(The `rows` file format is `borrower_id|period_end|kind|item` per line, which the table's long form below prints.)

- [ ] **Step 4: Run the test, then prepare the owner's table**

Run: `uv run pytest evals/tests/test_signoff.py -q` → PASS.
Run: `uv run python -m evals.signoff table` and paste the output into `docs/owner-questions.md` under a new heading "Sign the answer key (Phase 3)". Under the table write, in plain words:
- how many rows are unsigned and how many are low-severity signals (the count comes from the command's first line; today it is 94 and 31, and the Phase 2 signal fix may change it);
- "Each row is one thing the engine must produce for that client, with the value and threshold the generator computed independently of the product. Full rows: `synthetic/books/innovation/oracle.csv`. Reply 'approve all', or name the rows you reject (client and item); rejected rows are re-examined, not edited to fit."
- that signing is required before the live pass, and that nothing live runs until the owner also says go on the cost estimate (Task 11).

Run the table command once more and check the table has one line per client (16 clients) and is under about 25 lines. Update `docs/HANDOFF.md` ("Waiting for the owner: sign the key").

- [ ] **Step 5: Commit, then STOP**

```bash
uv run ruff check evals && git add evals docs && git commit -m "feat(p3): sign-off table and apply step for the new answer key"
```

**STOP. Tell the owner the table is ready and wait for the written reply. Do not run `apply` on your own. Do not start Task 11.** On the reply "approve all" run `uv run python -m evals.signoff apply --all`; on a partial approval write the approved keys (the table's long form is `uv run python -c "import csv;[print('|'.join(r[k] for k in ('borrower_id','period_end','kind','item'))) for r in csv.DictReader(open('synthetic/books/innovation/oracle.csv'))]"`) to a scratch file and use `--rows`. Rejected rows: investigate with the owner; per the lesson, a rule change moves the product and the key together. Then regenerate the book into a scratch folder and diff it against `synthetic/books/innovation/out` to prove the signed rows survive a regeneration (`uv run python -m synthetic.books.innovation.generate --out <scratch>/out`), run `uv run pytest synthetic/tests/innovation/test_kept_and_oracle.py -q`, and commit `chore(p3): owner signs the answer key` with the date and the owner's words in the commit body.

---

### Task 11: Cost estimate, then the gated live record pass and the replay

**Files:**
- Create: `evals/estimate.py`
- Create: `evals/results/estimate-2026-11-20.md` (output of the script, labelled as an estimate)
- Modify: `evals/run.py` (`--only` already exists; add `--recordings` use), `evals/results/` (scorecards from the live pass), `docs/HANDOFF.md`, `docs/lessons/` (what the live run taught)
- Test: `evals/tests/test_estimate.py` (new)

**Interfaces:**
- Consumes: a stand-in dry run's `StandInReader.requests` (`results["recordings"][code]["model_outputs"]` and `reader.requests`), recorded usage in `evals/recordings/**/*.json` (`usage` keys `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`), `PRICES`.
- Produces: `estimate(requests_by_agent, calibration, prices) -> Estimate(total_low, total_mid, total_high, lines)`; a markdown report whose first line reads "ESTIMATE, not a measurement".

- [ ] **Step 1: Write the failing test**

```python
# evals/tests/test_estimate.py
from decimal import Decimal

from evals.estimate import PRICES, Calibration, estimate


def test_the_estimate_multiplies_calls_by_calibrated_tokens_and_current_prices():
    cal = {"spreading": Calibration(input_tokens=12_000, output_tokens=6_000),
           "intake": Calibration(input_tokens=3_000, output_tokens=800)}
    result = estimate({"spreading": 10, "intake": 20}, cal, PRICES["claude-opus-5-5"])
    # spreading: 10 * (12000*4 + 6000*20) / 1e6 = 1.68 ; intake: 20 * (3000*4 + 800*20) / 1e6 = 0.56
    assert result.total_mid == Decimal("2.24")
    assert result.total_low < result.total_mid < result.total_high
    assert result.lines[0].agent in ("spreading", "intake")


def test_an_agent_with_no_calibration_fails_loudly_instead_of_costing_zero():
    import pytest
    with pytest.raises(KeyError, match="no recorded usage"):
        estimate({"covenant": 5}, {}, PRICES["claude-opus-5-5"])
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest evals/tests/test_estimate.py -q` → FAIL.

- [ ] **Step 3: Implement the estimator**

```python
# evals/estimate.py
"""A cost ESTIMATE for a live record pass. Nothing here calls a model. Method:
1. run the stand-in over the borrowers in scope and count requests per agent;
2. for agents the stand-in does not answer (covenant, early_warning), count from their call sites:
   covenant = covenant tests x exchanges per test seen in the recordings; early_warning = one per borrower;
3. tokens per call = the mean recorded usage of that agent (cache writes count as input at 1.25x);
   an agent never recorded has no calibration and the estimate refuses to price it at zero;
4. range = 0.6x to 1.6x of the middle (the book's documents are longer than the three recorded borrowers')."""
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from evals.book import REPO

PRICES = {"claude-opus-5-5": {"input": Decimal("4.00"), "output": Decimal("20.00"),
                              "cache_write": Decimal("5.00"), "cache_read": Decimal("0.20")}}  # USD per 1M tokens
LOW, HIGH = Decimal("0.6"), Decimal("1.6")


@dataclass
class Calibration:
    input_tokens: int
    output_tokens: int


@dataclass
class Line:
    agent: str
    calls: int
    mid: Decimal


@dataclass
class Estimate:
    lines: list[Line]
    total_low: Decimal
    total_mid: Decimal
    total_high: Decimal


def calibrate(recordings: Path = REPO / "evals" / "recordings") -> dict[str, Calibration]:
    by: dict[str, list[tuple[int, int]]] = {}
    for path in recordings.rglob("*.json"):
        usage = json.loads(path.read_text()).get("usage") or {}
        if not usage:
            continue
        tokens_in = (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                     + usage.get("cache_read_input_tokens", 0))
        by.setdefault(path.relative_to(recordings).parts[0], []).append((tokens_in, usage.get("output_tokens", 0)))
    return {agent: Calibration(sum(i for i, _ in v) // len(v), sum(o for _, o in v) // len(v)) for agent, v in by.items()}


def estimate(calls: dict[str, int], calibration: dict[str, Calibration], price: dict[str, Decimal]) -> Estimate:
    lines, total = [], Decimal(0)
    for agent, n in sorted(calls.items()):
        if agent not in calibration:
            raise KeyError(f"no recorded usage for {agent}: record one call first or give a calibration")
        c = calibration[agent]
        cost = Decimal(n) * (Decimal(c.input_tokens) * price["input"] + Decimal(c.output_tokens) * price["output"]) / Decimal(1_000_000)
        lines.append(Line(agent, n, cost))
        total += cost
    return Estimate(lines, total * LOW, total, total * HIGH)
```

A `main` that: loads the innovation book for the borrowers in scope (default: the 16 new plus pellham-grain), runs `run_suite(mode="standin", only=..., keep_recordings=True)` to a scratch results dir with `--no-eval-run`, counts `reader.requests` by `record_key.split("/")[0]`, adds `covenant` = sum of covenant tests in scope × the mean exchanges per test from the recordings (read `evals/recordings/covenant/*/*/*/` counts: five per test today) and `early_warning` = one per borrower, prints the table (agent, calls, mid cost), the low, mid and high totals, and writes `evals/results/estimate-2026-11-20.md` whose first line is **"ESTIMATE, not a measurement. Prices: claude-opus-5-5 at $4 input / $20 output per million tokens (Claude API skill, cached 2026-11-03); tokens per call from the three recorded borrowers; the range is 0.6x to 1.6x."** The `calibrate()` result must contain `intake`, `spreading`, `certificate_reader`/`certificate`, `collateral`, `covenant`, `early_warning`, `review` (the recorded directories use the short names; map `certificate`, `collateral`, `review`, `intake`, `spreading`, `covenant`, `early_warning` as they appear in `evals/recordings/`); an agent with no recording (the Terms Agent is not called in this book's cycles; check) is listed as "not called" only if the stand-in dry run shows zero requests for it.

Also print a second block, "if the kept three are stale": the number of stale recordings the stand-in/recorded dry run would hit (run `uv run python -m evals.run --mode recorded --book innovation --only briarstone-beverage harrowgate-precision kestrel-bay-packaging --no-eval-run`; each `RecordingStale` raised is a stale call) priced the same way. This is the extra cost of re-recording them.

- [ ] **Step 4: Run the test and the estimate**

Run: `uv run pytest evals/tests/test_estimate.py -q` → PASS. Run: `uv run python -m evals.estimate` (stand-in only, no key needed). Read the report. Commit it: `git add evals && git commit -m "feat(p3): cost estimate for the live record pass (an estimate, not a measurement)"`.

- [ ] **Step 5: STOP and ask the owner for the go-ahead**

**STOP. Do not run a billable command.** Prerequisites that must all be true; check each and say so:
- the stand-in gate passed on both books (Task 9) and `uv run python -m evals.run --mode standin --book both` exits 0 on the current commit;
- every oracle row for the borrowers in scope is signed (`uv run python -m evals.signoff table` prints "0 unsigned rows");
- a model key is present in the environment (`SQUAD_ANTHROPIC_API_KEY` or `ANTHROPIC_API_KEY`), never printed.

Send the owner this message, with the numbers from the report (all labelled estimates): "Ready for the live record pass. ESTIMATE: about $X (range $L to $H) for N borrowers, using claude-opus-5-5 at $4/$20 per million tokens. Your standing approval covers about $15. [If H exceeds $15 or the mid estimate does: this is above what you approved; I will not start without your fresh go.] Extra if the three kept borrowers must be re-recorded because the prompts moved: about $Y (estimate). Reply 'go' to run it." **Even when the high estimate is under $15, wait for the explicit "go" in this session: the standing approval says up to about $15, and this plan treats the actual run as billable, which CLAUDE.md says to ask first. If the mid estimate exceeds $15, re-confirm the exact figure before starting; do not rely on the standing approval.**

- [ ] **Step 6 (after the owner's go): the one record pass**

Run (the first command runs one borrower to measure real cost against the estimate; if the measured cost of that one borrower times the number of borrowers exceeds the figure the owner approved, STOP and re-confirm):

```bash
uv run python -m evals.run --mode record --book innovation --only tidewell-medical --confirm-billable --out evals/results/live-2026-11-20-one --no-eval-run
```

Read the one-borrower scorecard and its token line, compute the real cost per borrower from `agent_runs` tokens, compare with the estimate, and report to the owner in one line. If inside the approved figure, run the pass for every borrower that has no valid recording:

```bash
uv run python -m evals.run --mode record --book innovation --only <the 16 new clients and pellham-grain, minus tidewell-medical> --confirm-billable --out evals/results/live-2026-11-20-record
```

Add `briarstone-beverage harrowgate-precision kestrel-bay-packaging` to `--only` only if the stale recordings were not accepted (the default per the rulings). The guard refuses unsigned rows; do not pass `--allow-unsigned`.

- [ ] **Step 7: Replay the whole book from recordings, read every refusal, record what was learned**

```bash
uv run python -m evals.run --mode recorded --book innovation --out evals/results
```

(add `--accept-stale <agent> ...` only if the owner chose replay over re-record for the kept three; it is printed in the scorecard). Read `evals/results/latest.md`. The live gate is the same gate: any `invented-number` or `false-compliant` fails. Per the lesson `the-first-live-run-finds-what-stand-ins-cannot`, read every refused honest sentence and every `wrong-abstain`: a refusal of honest text is a defect with the same weight as a hole, the refused text is the test case, and a narrowing of a guardrail ships with refusal tests for the amounts that must still be refused (`an-allowance-for-honest-text-is-a-hole`). Fixes that change a prompt bump the agent version and make the new recordings stale on purpose: they are re-recorded only after a new estimate and a new go. Write what the pass found to `docs/lessons/` (one lesson per file, summary on the first line; update an existing lesson instead of duplicating it), update `docs/HANDOFF.md` and `docs/owner-questions.md` (measured cost against estimate, the gate result, known findings), and run `uv run pytest evals/tests -q -m "not slow"` (recordings replay in tests; no test calls a model).

- [ ] **Step 8: Commit**

```bash
git add evals docs && git commit -m "feat(p3): live record pass for the innovation book; recordings replay"
```

---

## Self-review

**Spec coverage (§11 and the brief):**
- Generator independent of `app/calc`; cross-check on both books — Task 9 step 1 runs both existing cross-checks and the Global Constraints forbid patching either side.
- New answer-key rows signed before any live or record run — Task 10 (gate), enforced again by `check_may_start` reading the right oracle (Task 1); live Task 11 step 5 checks "0 unsigned rows".
- Stand-in reader for the new document types agreeing in full on both books — Tasks 3, 5 (MRR, bank, monthly packs, certificates, filed-only types, held export), Task 8 (spreadsheets), asserted in Task 9.
- Gate unchanged — Global Constraints; Task 9 asserts `GATED` counts and an empty `known_findings.json`.
- Kept-three recordings replay; new recordings from one live record pass asked first with an estimate — Task 4 (stale check) and Task 11.
- Owner approvals: about $15 estimate, stand-in gate and signed key first, table of rows, "accept spreadsheets" — Tasks 9, 10, 11 and 8.
- Carry list, each with a task: `evals/book.py` defaults (1); `Truth.statements` and `Decimal(None)` (2); stand-in reader forms (3); MRR and bank statements not spread live (5); Tidewell reconciliation (6); funding check hiding `funding_slipped` and `STAGE_OF_ITEM` (2); venture signals source facts (7); recordings unkeyed by spec version (4); intake-rules test skipping, credit-agreement anchor (8); spreadsheet intake (8). Stripple "value_unverified row covers two scenarios" (carry from the final review) is not a task: the key expects both `intake.unclassified` and `spread.value_unverified` for Stripple and Task 9's scenario test asserts both are raised; if the sign-off owner wants them split, that is a key change under the rule-change lesson.

**Placeholder scan:** no "TBD"/"TODO". Where the plan says "read X first" it names the exact grep and the decision rule, because the code is being edited concurrently and several anchors (template helper names, `raise_item` keyword names, venture metric registry, test fixtures `innovation_cycle`/`live_cycle_for`) could not be verified from here and are flagged in the task text.

**Type consistency:** `BANK_KEYS` (Task 3 defines locally, Task 5 moves it to `evals/book.py`); `oracle_for` (Task 1) used by Tasks 10; `RecordedClient(accept_stale=frozenset)` and `--accept-stale` (Task 4) used by Task 11; item type `cash.statement_mismatch` identical in Tasks 2, 6, 9; `PACK_TYPES` (Task 2) is not reused elsewhere; `innovation_cycle` fixture introduced in Task 6 and reused in Task 7; `live_cycle_for` introduced in Task 5 and reused in Task 8.

**Review Focus:** items 1–8 map to tests in Tasks 2, 3, 4, 6, 8, 1 as listed.

**Known risks the executor should expect:** the stand-in run is likely to expose product findings not on the carry list (the first live run did in November). Treat each under the lesson rule: failing test, fix where the defect is, key changes only with the owner. Tasks 5–8 touch `backend/` and `synthetic/` that another agent was editing on 20 Nov: rebase on their work and re-read before each task.

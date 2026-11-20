# Evaluations

The proof layer for Credit Agent Squad. It runs the live monitoring cycle over the synthetic
borrowers of a book (21 in the legacy book, 20 in the innovation book) whose truth is known, grades the outcome with deterministic code (never a model judging
a model), names each failure, and fails the build on the two failures that must never happen: an
invented number and a false "compliant".

## Run it

```bash
service postgresql start                                   # cloud container
uv run python -m synthetic.generate                        # legacy book into synthetic/out/ (5 s)
uv run python -m synthetic.books.innovation.generate       # innovation book (the default) into synthetic/books/innovation/out/
export TEST_DATABASE_URL=postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad_test

uv run python -m evals.run --mode standin                  # whole innovation book, about two minutes
uv run python -m evals.run --mode standin --book legacy    # --book legacy|innovation|both|<path>; both writes latest-legacy.* too
uv run python -m evals.run --mode standin --book legacy --only harrowgate-precision kestrel-bay-packaging
uv run python -m evals.run --mode standin --mutations      # also the mutation checks, one more minute
uv run python -m evals.run --mode standin --no-decide      # stop at the first item that needs a person

TEST_DATABASE_URL=... uv run pytest evals/tests            # everything, about four minutes
TEST_DATABASE_URL=... uv run pytest evals/tests -m "not slow"   # about 35 seconds
uv run ruff check evals backend/app/api/routes_evals.py
```

The command exits 0 when the gate passes, 1 when it fails, 2 when the run was refused. It writes
`evals/results/latest.json` and `evals/results/latest.md`, and commits one `eval_runs` row (the
scorecard) to the database it ran against. Everything else is rolled back: each borrower is
loaded in live mode inside a transaction that is never committed. Use a database that does not
already hold the book (the test database); the run refuses a database where the borrower exists.
The API serves the latest scorecard at `GET /api/v1/evals/latest` (and `/evals/runs`), from the
`eval_runs` table or, failing that, from `evals/results/latest.json`.

## Modes

| Mode | Who answers the agents | Cost | Starts when |
|---|---|---|---|
| `standin` (default; `--book` picks the book, innovation by default) | a perfect reader built from the book's ground truth | none | always |
| `recorded` | saved model responses under `evals/recordings/` (`RecordedClient`) | none | recordings exist |
| `live` | the model, through `app.agents.llm.client_for` | billable | every oracle row in scope is signed, and `--confirm-billable` |
| `record` | the model, and each response is saved for replay | billable | as `live` |

**A stand-in run is not model performance.** It proves the pipeline, the workflow and the grader
end to end when no model key is available. Its scorecard says so in its first lines, every agent
run it produces has `llm_mode = standin` and `served_model = stand-in-perfect-reader`, and the
API adds a notice. The same runner runs a real model by changing one setting: `--mode live`.

`live` and `record` print a cost warning and refuse to start while any row of
the oracle that belongs to the book being run (`oracle.csv` beside its `out/`: `synthetic/oracle.csv` for legacy, `synthetic/books/innovation/oracle.csv` for innovation) for the borrowers in scope has `owner_signed_off` other than `yes` (check the file for the current count). `--allow-unsigned` is the deliberate exception and is stated in the output.
Live runs are billable: ask the owner first. No test calls a model.

## What the stand-in answers

`evals/standin.py` answers each request by its record key and its content, the way a careful
reader would: it reports a figure only when the label and the figure are printed on the page it
cites, copies printed text exactly and computes nothing. A missing page or an image-only page
simply yields fewer items. Where print and truth disagree it reports the print and records the
disagreement (none in the current book).

| Agent | Record key | Stand-in |
|---|---|---|
| Intake | `intake/<borrower>/<batch>` | type, period, quality and title from the first pages |
| Spreading | `spreading/<borrower>/<period>/<sha>` | cells, comparative cells, absent lines, units phrase |
| Certificate reader | `certificate/<borrower>/<period>` | the summary table rows, as printed |
| Borrowing base reader | `collateral/<borrower>/<period>` | certificate lines, aging rows with notes, inventory rows |
| Review | `review/<borrower>/<period>` | a minimal draft in which every figure is a fact reference |
| Covenant, Early Warning, Terms | `covenant/`, `early_warning/`, `terms/` | not answered: the product must fall back safely (an abstain written by code, no explanation, the amendment item left open) |

## Scripted decisions

With `--decide` (the default) a user with the right role applies one sensible decision where the
cycle needs a person (`DECISIONS` in `evals/run.py`): a breach is escalated, a borrowing base
difference is settled on the bank's figures, a high signal is acknowledged, commentary is
approved. Items that wait for the borrower or for a person to key figures are left open
(`spread.does_not_foot`, `spread.image_only`, `spread.value_unverified`, `intake.*`), and so is
`terms.unapproved_amendment`, whose sensible decision starts the Terms Agent. Those cycles rest
on the item their scenario expects.

## Grading

`evals/grade.py` reads the recording of what the product did and the truth files. It imports
nothing from the product.

| Failure | Meaning |
|---|---|
| `invented-number` (gated) | a usable fact that differs from the truth for its key and period; a covenant value or availability shown with no stored fact behind it; agent text that types a figure or references a fact that does not exist |
| `false-compliant` (gated) | a covenant recorded compliant where the truth says breach; a recommendation to resolve a covenant exception where the truth is a breach |
| `false-breach` | a covenant recorded in breach where the truth says it passes |
| `missed-exception` | an exception the scenario expects that was not raised |
| `false-exception` | an exception raised for a clean borrower, or beyond the expected ones |
| `wrong-citation` | a fact whose cited page does not print its quote or its row label |
| `wrong-abstain` | cannot test, cannot compute, no result, or an agent run that did not complete, where the truth has an answer |
| `missed-abstain` | an answer where the truth says there is none (a halted period, an unreadable line) |
| `stale-terms` | a test under the wrong terms version or threshold, or under terms that are not approved |

Differences with no name in that list are `disagreements` (a signal, a recalculated borrowing
base line, the filing of a document, a failed stage). Things that are not differences from the
truth are `observations`.

Metrics: extraction accuracy (verified facts equal to truth, over facts expected) with its
abstain rate beside it, covenant outcome accuracy and abstain rate, exception precision and
recall, the share of cycles needing no person (commentary approval, which every review needs, is
not counted as an exception), and a count per failure. An unmeasured metric is `null`, never zero
(no tokens in a stand-in run; no extraction accuracy for a package that never arrived).

Conventions the grader had to choose:

- Exceptions are compared by type per borrower, as `backend/tests/test_seed_book.py` does.
- For the three halting scenarios only the statements are expected to be read; for an image-only
  statement nothing is expected, because the product asks a person before reading any of it.
- The review metrics `cash`, `total_debt`, `revenue_ttm` and `net_income_ttm` are checked against
  the truth periods; the other eight are counted as ungraded (the book states no value for them).
- Figures in work item titles written by code (for example the days past due) are not checked.

## Gate

Any `invented-number` or `false-compliant` in any pass fails; every pass is checked separately.
Accuracy of a real model is reported, not gated. The stand-in suite must also agree with the
truth in full. `evals/known_findings.json` may list open, reported product findings that the
stand-in gate tolerates; an entry that no longer occurs fails the gate until it is removed, and
no entry can excuse the two gated failures. It is empty today.

## Mutation checks

`evals/mutations.py` tampers with the stand-in's answer in 35 ways a model could be wrong and
records who caught each one (`evals/tests/test_mutations.py`):

- **product**: refused into a work item or a guardrail note;
- **product and grader**: refused by the product, and the grader also names what followed (for
  example, the cycle stopped before the exception its scenario expects);
- **grader**: accepted by the product and named only by the grader. That is a finding about the
  product. None today;
- **SLIPPED**: caught by neither. None today; if one appears, report it, do not patch the grader.

What this list does and does not show. It shows that these 35 specific mistakes are refused. It
does not show that every mistake is: seven of the first 29 were accepted when the harness was
first run, and an independent reviewer then found six more that the 29 did not cover (a reader
reporting only a fragment of a row label, figures for lines that no total covers read from
another row, a column header naming two periods, printed totals left unread). Each was fixed in
the product and added here. Treat the list as a record of what has been tried, and expect a
real model to find mistakes that are not on it.

There is no switch that turns the guardrails off, on purpose, so there is no "guardrails off"
run to compare with. The comparison this harness offers is per mistake: the tampered answer is
what a model without guardrails would have stored, and the column shows what stopped it.

`evals/tests/test_grade.py` tampers with recordings instead, and shows each of the nine named
failures raised by name.

## Files

| File | Role |
|---|---|
| `book.py` | truth files, documents, oracle; an independent reading of printed figures |
| `standin.py` | the stand-in reader |
| `run.py` | runner and command line: load, run the cycle, record, decide, write results |
| `grade.py` | grader, metrics, gate |
| `scorecard.py` | `latest.md` and the terminal summary |
| `mutations.py` | mutation checks |
| `known_findings.json` | open product findings the stand-in gate tolerates |
| `results/` | `latest.json`, `latest.md` |
| `recordings/` | saved model responses (none yet) |
| `../backend/app/api/routes_evals.py` | the scorecard for the governance screen |

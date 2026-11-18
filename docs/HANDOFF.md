# Handoff

Current state of the build, for whoever (person or agent) continues it. Updated 2026-11-18.

## Where things stand

Branch `slice-1/monitoring-cycle`. `main` holds only the README and licence.

| Milestone | State | Evidence |
|---|---|---|
| 0 Foundation | Done | Schema, hash-chained ledger with database guards, sign-in, roles, second-person rule |
| 1 Synthetic bank | Done | 21 borrowers, 360 PDFs, 13 scenarios plus 8 clean |
| 2 Calculation core | Done | Agrees with the book on 378 covenant tests and 24 borrowing base reviews |
| 3 Agent runtime and guardrails | Done | Tool loop, scope from code, step cap, number / quote / narrative / label / units / column guardrails |
| 4 Agents and workflow | Done, scripted and stand-in readers only | Nine agents, stage handlers, background worker, a repair path for every held item, recalculation when a figure is corrected |
| 5 Workspace | Done | Screens on the real API, source drawer for every figure, repair of held figures, commentary editing, document upload, package schedules; two sets of browser journeys |
| 6 Publishing | Done | Word, Excel, PowerPoint, snapshots, a verifier that every figure traces to a fact |
| 7 Hardening | Done, with the limits below | Three independent reviews; every hole they found is fixed and has a permanent test; 47 tampering checks; autonomy setting; hosting files |

## The number-safety promise: read this before relying on it

The promise is that no invented or wrong number reaches a person or a covenant test unnoticed.

- **Three independent reviewers each broke it.** Each was given only the promise and told to break it. Review one found 10 holes, review two found 7, review three found 7. Every hole reported is fixed, each with a permanent test, and the tampering list in `evals/mutations.py` grew from 29 to 47.
- **No fourth review has been run.** After reviews one and two I believed the holes were closed, and the next reviewer found more. Expect a fourth to find something.
- **What changed in kind, not only in number.** The readers no longer trust anything the reader supplies to locate a figure: code reads the row label, the column, the units, the sign, the certificate's compliance entry, an inventory row's category and an aging row's note from the page itself. Agent text is refused unless every digit is inside a fact reference or a narrow list of date and reference forms.
- **The default is now that a person confirms every document reading** (`EXTRACTION_AUTONOMY=assisted`). A reading that passes every check still raises one question per document. `automatic` uses a clean reading without a person; choose it only when accuracy measured on the bank's own documents justifies it. The test suite and the evaluation measure the automatic path.
- **Nothing here has been measured with a real model.** Every figure in the scorecard comes from a stand-in reader built from the synthetic book's own ground truth.

## Verified on 2026-11-18

- Complete evaluation on the committed code (`evals/results/latest.md`): 21 borrowers, extraction 2,677 of 2,677 facts, covenant outcomes 100%, exception precision and recall 100%, 17 of 21 cycles closed, the other 4 resting on the exceptions their scenarios expect, 47.6% of cycles needing no person on the automatic path. Stand-in reader.
- 47 tampering checks: 46 refused by the product, 1 recovered (code reads the dropped note from the page itself), none slipped.
- Test suite: the complete run on the final code gave 973 passed, 5 failed. The five were two tests that read a developer's local `.env` and three stale expectations in the tampering tests; all five were fixed and the two files then passed (65 tests). The complete suite was not run again after those test-only fixes. It takes about 13 minutes (`uv run pytest`), about 10 without the slow evaluation tests (`-m "not slow"`).
- Workspace: 164 unit tests pass and the type check is clean; the repair, commentary, upload and schedule screens were exercised in a browser by the worker that built them, except rejecting a figure and clicking Confirm, which are covered by unit tests only.
- `scripts/demo.sh` run on Linux against an empty database: created the database, loaded the book, started the API and the workspace, sign-in worked.
- `scripts/start-hosted.sh` run locally against an empty database: migrations, demo data, worker and API came up.

## Open decisions for the owner

1. Sign the oracle (`synthetic/oracle.csv`, 76 rows, all `owner_signed_off=no`). The owner said they will review it later.
2. A typed figure in agent text: the spec says one retry, then abstain; the Covenant Agent, Copilot and Review Agent currently abstain or drop the section with no retry. Decide which holds.
3. Seeded history has no page citations, so the workspace has code locate the stored value on the period's document when a seeded figure is opened, labelled "Located by code, not extracted". Decide whether to keep that or show no page.

Decided on 2026-11-17: receivable-days and payable-days signals are medium severity; the borrowing base block accepts several citations and each of its numbers is checked against a cited clause; no second independent extraction.

## Known weaknesses

- **Residual holes in the prose check that are understood and left open.** A four-digit amount that looks like a nearby year after a word of time ("EBITDA came in 2026"); a fact used with a meaning it does not have ("leverage is {{fact}} below the limit", where the fact is the leverage itself); small counts in words ("in three of the last four quarters"), which are allowed on purpose.
- **Honest readings that are held.** A statement whose columns are headed "Actual" and "Budget" under one date, a row label wrapped onto two lines, a statement page that does not print the borrower's name, units in millions, and any label that is not the template's own or a listed synonym are all held for a person. That is the safe direction, but it will raise the number of touches on real documents.
- **The layout rules are heuristics over word positions.** They were written against the synthetic book and the reviewers' layouts. Real statements will show layouts neither covered.
- The memo's Sources section is long (13 of 16 pages in the example).
- Borrowing base lines, risk rating and days late are not stored as facts everywhere, so the Copilot can describe some of them only in words.
- Work item titles written by code contain typed figures ("3 days past due").
- The workspace shows a recalculation's covenant changes and a held figure's reason, but has no screen for boarding terms by hand, and document upload cannot set the type or period (intake classifies it).
- **The ledger can still be rewritten by a database owner or superuser.** The application's own role can no longer do it (it may only read and append, and owns nothing), but anyone with owner-level access can switch off the trigger, change events and recompute every hash, and the rewritten chain verifies. Without a copy of the chain's head kept outside the database this cannot be detected; that is true of any log held in a database. `verify-ledger` prints the head and `--expect-head <seq>:<hash>` checks a stored one. Nothing yet sends the head anywhere on a schedule, and events written after the stored head are not covered by it.
- Local development and the tests still use one database role, the owner. `verify-ledger` warns when it is connected that way.
- Sign-in lockout is per account (5 failures in 15 minutes): someone who knows an email address can keep that account locked, and the "too many attempts" answer shows the account exists. Failures for unknown addresses are not counted or recorded.
- An upload is refused at 25 MB by its declared length before it is read. A body sent with no declared length is received in full by the server first and refused afterwards.
- Whenever covenant tests are run again (a correction, `input_provided`, `terms_approved`, a confirmed certificate figure), a breach that is still a breach raises its question again even if a person had already decided it.
- When terms are approved inside a cycle (the `terms.approval_needed` item at the covenant stage), the stage is released by that decision and the covenant tests are not run again under the new version.
- "Restated: update the prior period" is no longer offered on a restatement item. Carrying it out needs several prior-period figures corrected and everything recalculated once, which `corrections.py` cannot yet do in one step.
- "Correct the listing" is no longer offered on a borrowing base item: there is no way for a person to edit a collateral listing. A certificate that cannot be read can be read again or set aside for a new one.
- A worker that dies while running a stage leaves the stage and its job marked running, with no item for a person. A stage whose handler raises is covered; a process that disappears is not.
- The workspace has no screen for boarding terms by hand (`POST /facilities/{id}/terms` exists), and no hint text for the new decisions `retry` and `escalate`.

## Next steps, in order

1. On the owner's machine: sign the oracle, then the first recorded live run (`uv run python -m evals.run --mode record --confirm-billable`), and fix what it shows. This is the first time a real model's reading meets these checks.
2. A fourth independent review of number safety, after the live run, briefed with the promise and the list of what has already been found (`docs/lessons/`).
3. Finish the test deployment (`docs/DEPLOY.md`, option A). The workspace and API are live at `https://credit-agent-squad.vercel.app` but no database is connected: the owner needs to create a PostgreSQL database and set `DATABASE_URL` on the Vercel project; then run the one-time setup routes.
4. Remember a confirmed layout per borrower, so that in assisted mode a person confirms a borrower's first statements and later periods with the same layout go through; this is the planned way to earn `automatic`.
5. Slice two: underwriting.

## Running it

```bash
service postgresql start                                   # cloud container
uv sync && uv run pytest                                   # all tests, about 13 minutes
uv run python -m synthetic.generate                        # build the book into synthetic/out/
cd backend && uv run alembic upgrade head && cd ..         # create the schema
PYTHONPATH=backend uv run python -m app.seed_book          # load users and the book (demo password: squad-demo)
PYTHONPATH=backend uv run uvicorn app.main:app --port 8000 # API
PYTHONPATH=backend uv run python -m app.worker              # background worker (runs cycles)
PYTHONPATH=backend uv run python -m app.cli verify-ledger  # check the audit chain
```

The local folder is still named `creditfleet` in this container; the repository is `arunr-mib/CreditAgentSquad`. The spec file keeps its old file name (`docs/specs/2026-11-17-credit-agent-squad-design.md`); rename it when no worker is reading it.

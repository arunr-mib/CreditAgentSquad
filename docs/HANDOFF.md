# Handoff

Current state of the build, for whoever (person or agent) continues it. Updated 2026-11-20.

## v2 "Credit Squad" (from 20 November 2026)

The owner chose to rebuild around the Squad experience (`docs/specs/2026-11-20-squad-experience-design.md`) on a book of 16 innovation-banking clients plus 4 kept C&I clients (`docs/specs/2026-11-20-innovation-book-and-lending-layer-design.md`). The clickable demo `https://c-squad.vercel.app` is frozen (`docs/DEPLOY.md`). The version before v2 work is commit 2292b38 (no tag: owner skipped it). Owner questions, answers and standing approvals: `docs/owner-questions.md`.

| Phase | State |
|---|---|
| 0 Freeze and specs | Done |
| 1 Lending layer (`docs/plans/2026-11-20-phase-1-lending-layer.md`) | Done: tasks 1–9, per-task reviews, a final whole-branch review and one fix wave, re-reviewed and approved |
| 2 Innovation book (`docs/plans/2026-11-20-phase-2-innovation-book.md`, 10 tasks) | Done: tasks 1–10; full suite, `ruff` and the legacy stand-in evaluation pass (21 November) |
| 3 Evals (`docs/plans/2026-11-20-phase-3-evals.md`) | Stand-in gate passed on both books (21 November): legacy 21 borrowers, extraction 2,677 of 2,677, covenants 100%; innovation 20 borrowers, extraction 1,621 of 1,621, covenants 94.9% (Stripple's three tests unmeasured: its cycle rests on the held figures the key expects), exception precision and recall 100%. Remaining: owner sign-off of the new answer key rows, then the live pass (billable, owner's go-ahead first; up to about $15, estimate) |
| 4 Squad experience (`docs/plans/2026-11-20-phase-4-squad-experience.md`, 4a: 15 tasks; 4b outlined) | 4a done and merged (20 Nov): per-task reviews, final review, one fix wave, re-review approved; merged suite green, vitest 570, browser journeys 14/14 on the innovation book. First-look findings for 4b: `docs/product/v2-first-look-findings.md`. 4b plan not written yet |
| 5 Hosted release (new Vercel project, schema `squad2`) and usability sessions | Pre-approved, not started |

**What Phase 1 added** (C&I behaviour unchanged; the legacy 21-borrower book and its tests stay green):

- Template registry: `ci-1` and the venture template `vc-1` (SaaS lines; standard-spread sections, `calc/TEMPLATES.md`); every borrower names its template (`borrowers.template_id`, migration 0004). Optional memo/metric lines sit outside every total; counts and ratios (customers, net revenue retention) are never scaled by "(in thousands)".
- Flows are stored year-to-date; trailing three months (`t3m`) is derived from YTD differences, across a fiscal year end, and a missing month is an error.
- Covenants: `min_unrestricted_cash` (pledged/restricted cash excluded), `min_runway_months` (RML = unrestricted cash ÷ average three-month net burn; burn ≤ 0 is "not meaningful: cash-flow positive", stored as a note on the test, migration 0005), `revenue_vs_plan` (plan figures are approved terms data), DSCR for venture borrowers. The terms agent (`terms@2`) knows the new archetypes; a revenue-vs-plan row is left for a person because the plan is approved separately.
- Signals: runway below watch (high < 9, medium < 12), runway falling (three monthly declines), burn rising (> 20%), revenue below plan; `net_loss` off for `vc-1`; going concern, line usage and availability apply to both templates.
- Funding events: record, update (legal status changes only; a slipped round comes back only with a future close; a closed event is final), evidence must belong to the borrower; the worker marks passed dates slipped and raises one item with four responses (ask for a new timeline (default), note and watch, reserve rights, escalate); reserve rights and escalate need `decide_breach`.
- Lessons: `POST /api/v1/lessons` writes a person's own words.
- Monthly reporting: intake files monthly packs, MRR/ARR reports (title only), bank statements, term sheets, investor updates; the quote guardrail reads "one … eleven months ended" and "month ended"; cycles open per reporting frequency; spreading, corrections, publishing, Copilot and routes follow the borrower's template; a line from the other template is refused and asked about.

**Verified at Phase 1 close (20 November 2026):** full test suite passed; `ruff` clean; migration 0005 upgraded, downgraded and re-upgraded on a scratch Postgres database; stand-in evaluation on the legacy book unchanged from v1: 21 borrowers, extraction 2,677 of 2,677, covenant outcomes 100%, exception precision and recall 100%, gate passed (stand-in reader, not model performance). Nothing has been run with a real model in v2.

**Known gaps carried to later phases:** waiver conditions that reference a funding event (Phase 4b approvals); venture metrics in publishing packages; quarterly-reporting venture borrowers use quarter windows for runway-falling and burn-rising; `pytest-xdist` deferred (needs one test database per worker).


## Where things stand

**Phase 2 (v2 innovation book, done 21 November 2026):** `synthetic/books/innovation/` holds the 20-borrower book: 16 venture-backed clients on a monthly cadence plus the four kept C&I borrowers, byte-identical to v1. The v1 generator and `synthetic/out/` are frozen and pinned by digest. `python -m app.seed_book` loads the innovation book by default (`--book legacy` for v1, unchanged); the innovation seed takes about 3 minutes. SaaS lines come from the monthly MRR report (a pack without them still spreads) and revenue-vs-plan reads the approved plan. Expected values are computed independently of `app/calc`; `backend/tests/calc/test_synthetic_innovation_truth.py` runs the book through the engine.

- **Verified counts:** 20 borrowers, 301 documents, 917 pages. Answer key `synthetic/books/innovation/oracle.csv`: 107 rows = 16 signed (the kept borrowers' v1 rows) + 91 unsigned (63 tests, funding events and exceptions, plus 28 current-period signals), waiting for the owner's signature. 726 covenant tests agree exactly with `app.calc`.
- **Built in Phase 3:** the stand-in reader for the new document types, `--book both`, Tidewell's reconciliation exception, spreadsheet intake (Stripple's export is held with one question; no agent reads figures from a sheet yet). **Not built:** recordings and the live run (billable).
- **Decisions:** Ferrogate has a TTM DSCR of at least 1.25x from 2026-05-31 (second terms version); Corvane's plan miss is a breach; Lumora's October tests are `cannot_test` (late package). All in `docs/owner-questions.md`.

Branch `slice-1/monitoring-cycle`. `main` holds only the README and licence.

**Since the table below was written (all on 18 November 2026):**

- **Hosted test link:** `https://credit-agent-squad.vercel.app` (Vercel and Supabase; see `docs/DEPLOY.md`). A model key is set there, so "Run … now" on a borrower's cycle and the Copilot make billable calls. No background worker: a person runs a cycle one stage at a time (`POST /cycles/{id}/run`).
- **Interface redesigned as a cockpit** (`docs/specs/2026-11-18-cockpit-design.md`): command centre with summary cards and bars, one workspace drawer for the selected exception and the Copilot, an authority gate that routes a decision to a person who may take it, borrower tear-sheet, agent activity timeline, governance matrix, source drawer beside the page, phone and tablet layouts. Every route measured at 360 to 1440 px with no sideways scrolling.
- **Held figures panel rebuilt** (on file, read from the document, why held, one clear action); a figure filed under another line keeps its page citation.
- **Product documents:** `docs/product/explainer.md` and `docs/product/PRD.md`.
- **Independent review of the redesign (18 November 2026):** five P0 findings (a threshold's source showed the base clause and the ratio's calculation instead of the step in force; headroom had no derivation; the trend chart drew today's limit across past quarters; a breach did not mention an unapproved amendment; the server accepted decisions without a reason and routing to someone without the permission). All are fixed with tests, as are the P1 and P2 findings. On the owner's decision the Administrator now holds only view, policy, users and the demonstration clock (no credit decision). Every open item has a due date by severity (critical 2, high 5, medium 10, low 20 business days); the hosted book was backfilled on 18 November 2026 (14 items, one ledger event each). A figure an agent types is sent back to it once to be rewritten with fact references; if it still fails, the text is withheld. Browser journeys (`frontend/e2e/run.mjs`) are rewritten for the cockpit and pass (10 journeys) on a freshly seeded local database; they decide the seeded breaches, so reseed before rerunning. `repair.mjs` has not been re-run.

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
- **Nothing here has been measured with a real model.** Every figure in the scorecard comes from a stand-in reader built from the synthetic book's own ground truth. One live run exists (Review Agent, Brindlewood, on the hosted link, 18 November 2026): every figure was a fact reference, and two of four sections were dropped by wording rules that were too strict (`docs/lessons/the-first-live-run-finds-what-stand-ins-cannot.md`). The document readers have never run with a real model.

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

- **Residual holes in the prose check that are understood and left open.** A four-digit amount that looks like a nearby year after a word of time ("EBITDA came in 2026"); a fact used with a meaning it does not have ("leverage is {{fact}} below the limit", where the fact is the leverage itself); small counts in words ("in three of the last four quarters"), which are allowed on purpose; a page number after the name of a document part ("the leverage schedule on page 4"), allowed since 19 November 2026.
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
3. The test deployment is live (`docs/DEPLOY.md`, option A): `https://credit-agent-squad.vercel.app`, all 21 borrowers loaded, the application's database login cannot rewrite the ledger. A model key is set, so agents are on and billable; a person runs a cycle one stage at a time from the borrower page. One stage has run with a real model (Review Agent, one borrower, 18 November 2026); accuracy with a real model is not yet measured.
4. Remember a confirmed layout per borrower, so that in assisted mode a person confirms a borrower's first statements and later periods with the same layout go through; this is the planned way to earn `automatic`.
5. Slice two: underwriting.

## Next: the first live measurement (approved by the owner on 18 November 2026)

Approved: three borrowers, estimated 3 to 7 US dollars in total (an estimate, not a measurement). The answer key is signed (75 rows). The key goes in the CreditAgentSquad cloud environment as the variable `SQUAD_ANTHROPIC_API_KEY` (a Claude API key cannot be a network secret, and a cloud session does not pass `ANTHROPIC_API_KEY` to its commands); a new session picks it up. Check first with `[ -n "$SQUAD_ANTHROPIC_API_KEY" ] && echo present || echo missing`. Then:

```bash
service postgresql start
uv run python -m evals.run --mode live --only kestrel-bay-packaging briarstone-beverage harrowgate-precision --confirm-billable
```

Report the scorecard (`evals/results/latest.md`) with its real token counts and cost, misses included; nothing on the hosted link changes (each borrower runs inside a rolled-back transaction).

## Done: the first live measurement (18 November 2026)

- **Run 1, three borrowers, live** (`evals/results/latest.md`): gate passed; extraction 57.8%, covenants 28.6%. Kestrel Bay closed with its hidden breach caught (102 of 102 figures). Harrowgate and Briarstone stopped at spreading because of a collision between the spreading prompt and the template over total equity (`docs/lessons/the-first-live-run-finds-what-stand-ins-cannot.md`). Tokens 78,407 in / 28,924 out.
- **Fixed:** spreading prompt version 2; the evaluation keeps held figures and unshown agent prose.
- **Run 2, the same two borrowers, record mode** (`evals/results/live-2026-11-18-record-two-borrowers.md`, responses in `evals/recordings/`): gate passed; extraction 400 of 400, covenants 100%, exception recall 100%, both cycles closed. Two false exceptions, both `intake.unclassified`. Tokens 79,567 in / 28,679 out. Estimated cost of both runs together about 2 US dollars (an estimate from token counts, not an invoice).
- **Run 3, the same two borrowers, record mode, 19 November 2026** (`evals/results/latest.md`, also `evals/results/live-2026-11-19-record-intake-fix.md`; responses in `evals/recordings/`), after intake version 2 (unseen pages are not missing; reported results belong to later stages): gate passed; extraction 400 of 400, covenants 100%, exception precision and recall 100%, both cycles closed, 50% of cycles needing no person (the book expects 50%). No differences from the answer key. Tokens 76,703 in / 25,746 out. Estimated cost of all three runs about 2.60 US dollars (an estimate from token counts).
- **Open from the live runs:**
  1. Fixed 19 November 2026: run 3 withheld an honest spreading note ("the debt schedule on page 5"). Agent text may now name a page only straight after the name of a part of a document ("schedule", "statement", "table", "report", "aging", "listing", "certificate", "sheet", "note"), as a whole number with nothing after it that makes it a measurement; "leverage on Page 5", a reviewer's attack, is still refused. Not yet attacked by someone who did not write it. Notes from the Certificate and Collateral agents are not shown to anyone; some carry useful facts (an eligibility statement with no matching category).
  2. **Run 4, Kestrel Bay, record mode, 19 November 2026** (`evals/results/latest.md`, also `evals/results/live-2026-11-19-record-kestrel.md`), after the intake and page-reference fixes: gate passed; extraction 102 of 102, covenant outcomes 100%, exception precision and recall 100%, cycle closed with the hidden breach caught; the intake false exception of run 1 did not recur. Tokens 42,519 in / 13,110 out / 35,258 cache read. One miss: the Covenant Agent reached its step cap again (both runs). It made five model calls with two or three tool calls each; `max_steps` (12) counts tool calls, and on reaching it the runtime abstains at once without letting the model answer from what it has read. Proposed: count model turns, or give the model one last turn without tools to answer or abstain; or raise the covenant cap.
  3. Recorded replay cannot reproduce agents that cite facts (new fact ids each run), so a replay of run 2 does not close its cycles. Tests and CI that replay the Review or Early Warning agents need stable fact ids or a mapping from recorded ids.
  4. Run 2's results JSON was overwritten by a replay; its scorecard is kept. Run 1's results are in git history (commit `bd298f9`).

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

# Handoff

Current state of the build, for whoever (person or agent) continues it. Updated 2026-11-17.

## Where things stand

Branch `slice-1/monitoring-cycle`. `main` holds only the README and licence.

| Milestone | State | Evidence |
|---|---|---|
| 0 Foundation | Done | Schema, hash-chained ledger with database guards, sign-in, roles, second-person rule |
| 1 Synthetic bank | Done | 21 borrowers, 360 PDFs, 13 scenarios plus 8 clean |
| 2 Calculation core | Done | Agrees with the book on 378 covenant tests and 24 borrowing base reviews |
| 3 Agent runtime and guardrails | Done | Tool loop, scope from code, step cap, number / quote / narrative / label / policy guardrails |
| 4 Agents and workflow | Done, scripted models only | Nine agents (see the README), stage handlers, background worker, repair paths for held spreads and unapproved amendments |
| 5 Workspace | Done for the main journeys | Screens on the real API, source drawer for every figure, five browser journeys. Not built: document upload screen, commentary editing, package schedules, screens for the fact confirm / correct / key routes |
| 6 Publishing | Done | Word, Excel, PowerPoint, snapshots, a verifier that every figure traces to a fact |
| 7 Hardening | Partly done | Evaluation harness with 29 tampering checks (none caught by the grader alone); ledger verification command. Not done: independent check by a fresh reviewer, a guardrail on-versus-off comparison, running the container stack |

## Not yet verified

- **No live model call has been made, and none can be made from this cloud session.** The credential form does not accept Anthropic keys and the session's own sign-in may not be used for product calls; both are deliberate limits. Live runs must happen on the owner's machine or a deployment with `ANTHROPIC_API_KEY` in `.env`: `uv run python -m evals.run --mode record --confirm-billable` (add `--allow-unsigned` only as a deliberate exception). Until then every agent result comes from scripted or stand-in answers, and the strict output schemas and request shape in `backend/app/agents/llm.py` are unproven against the real API.
- The container stack (`docker-compose.yml`) has never been run: no Docker daemon here.
- CI has not been observed running on GitHub.
- The published Word, Excel and PowerPoint files were rendered with LibreOffice only, not opened in Microsoft Office.
- In the workspace, an agent recommendation with claims, a review sheet with drafted commentary, signal explanations and a Copilot answer were each seen only with injected or failed responses, because the seeded book contains none.
- The environment's setup script (`CreditAgentSquad` environment) has not run in a fresh session.
- **The runtime database role has not been exercised end to end.** Migration `0003` and `app.cli runtime-login` need a database user that may create roles; the local user (`squad`) may not, and the cloud session was not permitted to act as the database superuser. What ran: migrations `0001` to `0003` on an empty database through the path that warns and skips the role; the grants read back from the database's privilege tables against a stand-in role; the operator commands' refusals. The test that runs ALTER, UPDATE, DELETE and TRUNCATE as a non-owner (`backend/tests/test_ledger_roles.py`) is **skipped** until a superuser runs `CREATE ROLE squad_runtime_test NOLOGIN; GRANT squad_runtime_test TO squad;` once, or the test user may create roles. The `migrate` service in `docker-compose.yml` and the API running as `squad_app` have never run.

## Open decisions for the owner

1. Sign the oracle (`synthetic/oracle.csv`, 76 rows, all `owner_signed_off=no`). The owner said they will review it later.
2. A typed figure in agent text: the spec says one retry, then abstain; the Covenant Agent, Copilot and Review Agent currently abstain or drop the section with no retry. Decide which holds.
3. Seeded history has no page citations, so the workspace has code locate the stored value on the period's document when a seeded figure is opened, labelled "Located by code, not extracted". Decide whether to keep that or show no page.

Decided on 2026-11-17: receivable-days and payable-days signals are medium severity; the borrowing base block accepts several citations and each of its numbers is checked against a cited clause; no second independent extraction.

## Known weaknesses

- If a person corrects an extracted input after totals were stored, the stored totals and metrics are not recomputed (the publishing verifier reports the mismatch).
- The row-label check only fires when a printed label clearly reads as another template line. A borrower's own wording that matches no known line is left to the footing checks, which cannot see a swap inside one total. Synonyms for common labels would widen it.
- The memo's Sources section is long (13 of 16 pages in the example).
- Borrowing base lines, risk rating and days late are not stored as facts everywhere, so the Copilot can describe some of them only in words.
- Work item titles written by code contain typed figures ("3 days past due").
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

1. Independent check against the four success measures by a reviewer with fresh context.
2. On the owner's machine: sign the oracle, then the first recorded live run, and fix what it shows (prompts, schema shape).
3. Workspace: screens for confirming, correcting and keying figures; commentary editing; document upload; package schedules.
4. Recompute totals and metrics when an input is corrected.
5. Guardrail on-versus-off comparison in the evaluation harness.
6. Slice two: underwriting.

## Running it

```bash
service postgresql start                                   # cloud container
uv sync && uv run pytest                                   # all tests, about two minutes
uv run python -m synthetic.generate                        # build the book into synthetic/out/
cd backend && uv run alembic upgrade head && cd ..         # create the schema
PYTHONPATH=backend uv run python -m app.seed_book          # load users and the book (demo password: squad-demo)
PYTHONPATH=backend uv run uvicorn app.main:app --port 8000 # API
PYTHONPATH=backend uv run python -m app.worker              # background worker (runs cycles)
PYTHONPATH=backend uv run python -m app.cli verify-ledger  # check the audit chain
```

The local folder is still named `creditfleet` in this container; the repository is `arunr-mib/CreditAgentSquad`. The spec file keeps its old file name (`docs/specs/2026-11-17-credit-agent-squad-design.md`); rename it when no worker is reading it.

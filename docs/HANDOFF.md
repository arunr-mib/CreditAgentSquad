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

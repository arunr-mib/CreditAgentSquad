# Handoff

Current state of the build, for whoever (person or agent) continues it. Updated 2026-11-17.

## Where things stand

Branch `slice-1/monitoring-cycle`. `main` holds only the README and licence.

| Milestone | State | Evidence |
|---|---|---|
| 0 Foundation | Done | Schema (32 tables), hash-chained ledger with database guards, sign-in, roles, second-person rule, CI workflow |
| 1 Synthetic bank | Done | 21 borrowers, 360 PDFs, 13 scenarios; `uv run pytest synthetic/tests` passes (32) |
| 2 Calculation core | Done | `backend/app/calc`, 276 tests; agrees with the book on 378 covenant tests and 24 borrowing base reviews |
| 3 Agent runtime and guardrails | Done | Tool loop, scope injection, step cap, live / recorded / scripted model clients, number / quote / narrative / policy guardrails |
| 4 Agents and workflow | Mostly done | Built and tested with scripted model responses: Intake, Spreading, certificate reader, borrowing base reader and Review agents; covenant testing, terms approval, borrowing base review, signals, calendar, review sheet and commentary approval; stage handlers that run the live cycle; background worker. In progress (workers): Covenant Agent investigation and Early Warning explanation. Not started: Terms Agent, Copilot |
| 5 Workspace | In progress | API routes for credit, work, reviews, meetings and actions are built and tested. `frontend/` has the design system, shell and three showcase screens; a worker is wiring it to the API |
| 6 Publishing | In progress | A worker is building Word, Excel and PowerPoint output with snapshots and a verifier |
| 7 Hardening | Started | Second-person rule and ledger guards are enforced and tested; `python -m app.cli verify-ledger`; `Dockerfile`, `frontend/Dockerfile` and `docker-compose.yml` are written but could not be run here (no Docker daemon) |

Last full run: `uv run pytest` gave 458 passed, 1 failed; the one failure was a stale expectation, fixed in the next commit, after which the fast suites (420 tests) passed. The slow full-book test passed in the 458 run and has not been rerun since.

## Not yet verified

- **No live model call has been made, and none can be made from this cloud session.** The credential form does not accept Anthropic keys and the session's own sign-in may not be used for product calls; both are deliberate limits. Live runs must happen on the owner's machine or a deployment with `ANTHROPIC_API_KEY` in `.env` and `SQUAD_LLM_MODE=live` (or `record` to save responses for replay). Every agent test so far uses a scripted model, so the strict output schema and request shape in `backend/app/agents/llm.py` are unproven against the real API.
- The frontend's typecheck, 114 unit tests and build were rerun by the orchestrator and pass. Its accessibility run and its final screenshots were reported by the worker and not rechecked; it shows fixture data and is not wired to the API.
- CI has not been observed running on GitHub.

## Open decisions for the owner

1. Sign the oracle (`synthetic/oracle.csv`, 76 rows, all `owner_signed_off=no`). The owner said they will review it later.

Decided on 2026-11-17: receivable-days and payable-days signals are medium severity; the borrowing base block accepts several citations and each of its numbers is checked against a cited clause; no second independent extraction.

## Next steps, in order

1. Collect and verify the four workers' results (covenant investigation and early warning; workspace wiring; publishing; evaluation harness), integrate them into the stage handlers, and commit each after its tests pass.
2. Start the Terms Agent and the Copilot (briefs were written; their first runs stopped on a usage limit before writing anything).
3. Run the evaluation harness's stand-in suite over all 21 borrowers and fix every product finding it reports.
4. Independent check against the four success measures by a worker with fresh context.
5. On the owner's machine: first live evaluation with a real key (billable; the oracle should be signed first).

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

The local folder is still named `creditfleet` in this container; the repository is `arunr-mib/CreditAgentSquad`. The spec file keeps its old file name (`docs/specs/2026-11-17-creditfleet-design.md`); rename it when no worker is reading it.

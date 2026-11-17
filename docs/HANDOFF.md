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
| 4 Agents and workflow | Partly done | Built: Spreading and Intake agents, covenant testing, terms approval, borrowing base review, signals, calendar, cycle state machine, book loader. Not built: Terms, Covenant (investigation), Borrowing Base (extraction), Early Warning (explanation), Review and Copilot agents; stage handlers that join the agents into the live cycle |
| 5 Workspace | Started | API routes exist and are tested. `frontend/` has the design system, shell and three showcase screens on fixture data; not yet wired to the API |
| 6 Publishing | Not started | |
| 7 Hardening | Not started | |

Last full run: `uv run pytest` gave 458 passed, 1 failed; the one failure was a stale expectation, fixed in the next commit, after which the fast suites (420 tests) passed. The slow full-book test passed in the 458 run and has not been rerun since.

## Not yet verified

- **No live model call has been made.** Every agent test uses a scripted model. The strict output schema and the request shape in `backend/app/agents/llm.py` have not been exercised against the real API. This needs an Anthropic API key (ask the owner; use the secure credential form) and the owner's go-ahead for cost.
- The frontend's typecheck, 114 unit tests and build were rerun by the orchestrator and pass. Its accessibility run and its final screenshots were reported by the worker and not rechecked; it shows fixture data and is not wired to the API.
- CI has not been observed running on GitHub.

## Open decisions for the owner

1. Sign the oracle (`synthetic/oracle.csv`, 76 rows, all `owner_signed_off=no`). Live evaluations should refuse unsigned rows.
2. Severity of the receivable-days and payable-days signals: the calculation core says low, the synthetic book says medium. The full-book test compares rule ids only until this is settled.
3. Borrowing base citations: the terms carry one citation for the block, while advance rates, limits and the commitment sit in several clauses. The provenance check verifies the quote only. Either allow several citations on the block or keep it as is.
4. Second independent extraction for high-impact values (in the spec, not built).

## Next steps, in order

1. Terms Agent (credit agreement and amendments to proposed terms with citations), following the pattern in `backend/app/agents/spreading.py`: one extraction call, code verifies everything, work item for anything not cleared.
2. Stage handlers in `backend/app/domain/workflow.py` (`STAGE_HANDLERS`) that join intake, spreading, covenant testing, borrowing base and signals into the live cycle; then certificate and borrowing base certificate extraction.
3. Covenant Agent investigation on breach items; Early Warning explanation; Review Agent commentary with fact references; Copilot with read-only tools.
4. Wire the frontend to `/api/v1`, then build the remaining screens.
5. Publishing to Word, Excel and PowerPoint; snapshots.
6. First live evaluation (billable; ask first), then the independent check against the four success measures.

## Running it

```bash
service postgresql start                                   # cloud container
uv sync && uv run pytest                                   # all tests, about two minutes
uv run python -m synthetic.generate                        # build the book into synthetic/out/
cd backend && uv run alembic upgrade head && cd ..         # create the schema
PYTHONPATH=backend uv run python -m app.seed_book          # load users and the book (demo password: squad-demo)
PYTHONPATH=backend uv run uvicorn app.main:app --port 8000 # API
```

The local folder is still named `creditfleet` in this container; the repository is `arunr-mib/CreditAgentSquad`. The spec file keeps its old file name (`docs/specs/2026-11-17-creditfleet-design.md`); rename it when no worker is reading it.

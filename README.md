# Credit Agent Squad

**Agents reason. Code calculates. Guardrails verify. People decide.**

Credit Agent Squad is a fleet of AI agents for commercial lending teams at a mid-sized bank. It runs credit work end to end, from reading a borrower's reporting package to delivering a portfolio review package, and brings a person in only where credit judgement is needed. Every number it shows traces to a page in a source document, a logged calculation, a system of record, or a named person.

The first slice is the portfolio monitoring cycle: reporting-package intake, financial spreading, covenant extraction and testing, borrowing base review, early warning signals, portfolio review, credit actions and package delivery.

**Status:** a working pilot foundation on synthetic data. Every agent has been tested with scripted model responses only; no live model run has been made yet (see `docs/HANDOFF.md`). All data is synthetic and every generated document is marked `SYNTHETIC - FOR DEMONSTRATION`. The lender, "Bank of Stoic", and all borrowers are fictional.

## Run the demo with one command

```bash
./scripts/demo.sh
```

It creates `.env`, installs packages, creates the database if it can, generates and loads the synthetic book, starts the API and the workspace, and prints the address and demo sign-ins. It needs `uv`, Node 20+ with `pnpm`, and PostgreSQL 16 (or Docker, in which case it starts a PostgreSQL container). `./scripts/demo.sh --reset` empties the demo database first. Tested on Linux with a local PostgreSQL; the macOS and Docker paths are written but have not been run.

## How it keeps its promises

- **The model never types a number.** Agents say where a figure is printed; code finds it on the page, reads the number itself and stores a cited fact. Agent text may only reference stored facts, and code renders the figure.
- **Code calculates.** Spreads, covenants, borrowing bases and signals are computed by a decimal-only calculation core, with a logged record naming every input.
- **Guardrails verify.** Quotes are checked on the cited page, statements must foot and tie, a row label that reads as another line is held for a person, and a recommendation that cannot be traced is replaced by an abstain.
- **People decide.** Terms govern only after a second person approves them. Breaches, over-advances and review commentary always end with a named person's decision. Every action is written to a hash-chained ledger the database refuses to edit.

## The agents

| Agent | Does | A person is needed when |
|---|---|---|
| Intake | Says what each received document is and which period it covers | Code's own filing rules disagree, or the period is not on the page |
| Terms | Proposes covenant terms from the agreement and amendments, each number read from its quoted clause | Always: a second person approves before terms govern |
| Spreading | Locates statement figures for the template | A figure cannot be verified on the page, a label reads as another line, or the statements do not foot |
| Certificate reader | Locates what the borrower reported for each covenant | A row cannot be verified |
| Borrowing base reader | Locates certificate lines, the aging and inventory | A figure cannot be verified, or the recalculation disagrees |
| Covenant | Investigates a breach, with a cited what-if recalculation | Always: it recommends, a credit officer decides |
| Early Warning | Explains and ranks signals that code fired | A high-severity signal is acknowledged |
| Review | Drafts review commentary using fact references | Always: commentary is approved by a person |
| Copilot | Answers questions with fact references and verified citations | Never acts; it only reads |

## Run it locally

```bash
uv sync
service postgresql start                                    # or any Postgres 16; see .env.example
uv run python -m synthetic.generate                         # build the synthetic book into synthetic/out/
(cd backend && uv run alembic upgrade head)                 # create the schema
PYTHONPATH=backend uv run python -m app.seed_book           # demo users and 21 borrowers (password: squad-demo)
PYTHONPATH=backend uv run uvicorn app.main:app --port 8000  # API
PYTHONPATH=backend uv run python -m app.worker              # background worker
(cd frontend && pnpm install && pnpm dev)                   # workspace on http://localhost:5173
```

Sign in as `priya.raman@bankofstoic.example` (analyst), `helen.strand@bankofstoic.example` (credit officer) or `admin@bankofstoic.example`.

Copy `.env.example` to `.env` first. `SQUAD_ENV=local` in it is what allows a sign-in cookie over plain HTTP and serves `/docs`; with it unset the app behaves as a deployment (HTTPS-only cookie, no `/docs` or `/openapi.json`). An account is locked for 15 minutes after 5 failed sign-ins, and an upload over 25 MB is refused.

`docker compose up --build` starts the same stack in containers; it has not been run yet (see the handoff). It needs `RUNTIME_DATABASE_PASSWORD` in `.env`.

### Two database roles

The application must not connect as the owner of its tables: an owner can switch off the ledger's append-only trigger, rewrite an event and recompute the hash chain.

- **Migrations run as the owner** (`MIGRATION_DATABASE_URL`, or `alembic -x url=...`). Migration `0003` creates the role `squad_runtime` and grants it the working tables, and only SELECT and INSERT on `ledger_events`. It owns nothing, so it cannot alter the table or its triggers.
- **The API and the worker run as a login that is a member of `squad_runtime`** (`DATABASE_URL`). Create it as the owner: `RUNTIME_DATABASE_PASSWORD=... PYTHONPATH=backend uv run python -m app.cli runtime-login squad_app`. `docker-compose.yml` does both steps in its `migrate` service.
- The local commands above use one role for both, which is fine for development. Creating a role needs CREATEROLE; where the owner lacks it, the migration warns and skips the role. Then a superuser runs `CREATE ROLE squad_runtime NOLOGIN` and the owner runs `python -m app.cli grant-runtime-role`.
- `python -m app.cli verify-ledger` warns when it is connected as a role that could change ledger rows.

### Keep the ledger's head outside the database

`verify-ledger` prints the chain's head as `<sequence number>:<hash>`. Store it where no database administrator can change it (a ticket, a write-once bucket, another system), then check later with `verify-ledger --expect-head <seq>:<hash>`. Without that outside copy, a user with owner or superuser rights on the database can still rewrite history and recompute the chain so that it verifies; that is true of any log held in a database.

## Check it

```bash
uv run pytest                                # everything, about 17 minutes
uv run pytest -m "not slow"                  # skips the full-book and tampering suites
uv run python -m evals.run --mode standin    # all 21 borrowers through the live cycle; writes evals/results/latest.md
PYTHONPATH=backend uv run python -m app.cli verify-ledger   # prints the head; add --expect-head <seq>:<hash> to compare
(cd frontend && pnpm typecheck && pnpm lint && pnpm test && pnpm build)
```

The stand-in evaluation answers each agent request from the synthetic book's ground truth. It proves the pipeline, the workflow and the grader; it says nothing about how a model reads these documents. A live run needs `ANTHROPIC_API_KEY` in `.env`, is billable, and should wait until the oracle (`synthetic/oracle.csv`) is signed.

## Where things are

| | |
|---|---|
| Design spec | `docs/specs/2026-11-17-credit-agent-squad-design.md` |
| Current state and next steps | `docs/HANDOFF.md` |
| Lessons | `docs/lessons/` |
| Example outputs | `docs/examples/` |
| Calculation core | `backend/app/calc/` (see its README) |
| Guardrails | `backend/app/guardrails/` |
| Agents and prompts | `backend/app/agents/`, `backend/app/agents/specs/` |
| Workflow and stages | `backend/app/domain/workflow.py`, `stages.py` |
| Publishing | `backend/app/publishing/` |
| Synthetic bank | `synthetic/` |
| Evaluation harness | `evals/` |
| Workspace | `frontend/` (design rules in `frontend/DESIGN.md`) |

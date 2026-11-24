# Hosting a test deployment

Two ways to host it. Option A is in use; option B is written but has never been deployed.

## Option A: Vercel only, plus a PostgreSQL database (in use)

The workspace is served as static files and the API runs as one Python serverless function in the same Vercel project, so there is one address and no second host.

**State on 18 November 2026:** live at `https://credit-agent-squad.vercel.app` (Vercel project `credit-agent-squad`).

- **Database:** Supabase project "Credit Agent Squad" (free plan, region us-east-1), reached through the session pooler. All tables are in the schema `squad`.
- **Two database logins.** `squad_app` owns the tables and runs migrations (`MIGRATION_DATABASE_URL`). `squad_web` is what the application serves with (`DATABASE_URL`): it is a member of `squad_runtime`, which may read and write the working tables but only SELECT and INSERT on `ledger_events`. `GET /api/v1/ledger/verify` reports `append_only_for_this_role: true`. Passwords were generated in the session, stored only as SCRAM verifiers in the database and as secret variables on Vercel; they are in no file in this repository.
- **Loaded:** the 9 demo users and all 21 borrowers of the synthetic book (seed 20261117).
- **Model:** `SQUAD_LLM_MODE=live` with `ANTHROPIC_API_KEY` set (added by the owner on 18 November 2026), so agents are on: "Run … now" on a borrower's cycle and the Copilot call a real model, and **every run is billable**. Removing the key and redeploying switches them off again.
- **Checked on the live site:** sign-in, every menu page in a browser with no failed request, a source PDF, the ledger chain, the run route's refusal without a model.

| File | Role |
|---|---|
| `deploy/vercel/api/index.py` | Starts the API inside the function; adds three one-time setup routes |
| `deploy/vercel/vercel.json` | Sends `/api/*` to the function and every other path to the workspace |
| `deploy/vercel/requirements.txt` | Trimmed, pinned packages so the function fits Vercel's size limit |
| `scripts/build-vercel.sh` | Assembles `.vercel-build/` (API, backend, synthetic documents, built workspace) |

Steps:

1. Create a PostgreSQL database (16 or later; the Supabase project in use is on 17). With Supabase use the **session pooler** string and change the scheme: `postgresql+psycopg://postgres.<ref>:<password>@<pooler-host>:5432/postgres`.
2. In the Vercel project's environment variables set `DATABASE_URL` (step 1), `SESSION_SECRET` and `DEMO_SETUP_TOKEN` (long random strings), `SQUAD_ENV=production`, `EXTRACTION_AUTONOMY=assisted`, `DB_SCHEMA=squad`, `DB_POOL=null`. For the two-login arrangement create the roles as a database administrator (`squad_runtime` NOLOGIN, an owner login that owns the schema, a serving login that is a member of `squad_runtime`), run `python -m app.cli grant-runtime-role` as the owner, and set `MIGRATION_DATABASE_URL` to the owner login and `DATABASE_URL` to the serving login. For agents to run set `SQUAD_LLM_MODE=live` and `ANTHROPIC_API_KEY`.
3. `./scripts/build-vercel.sh`, then from `.vercel-build/`: `npx vercel@66.0.0 deploy --prod --yes`.
4. One-time setup, each call with the header `X-Setup-Token: <DEMO_SETUP_TOKEN>`: `POST /api/_setup/migrate`, then `POST /api/_setup/seed/<borrower-code>` once per borrower (`GET /api/_setup/status` lists the codes and what is loaded). Without the header these routes answer 404.
5. Sign in as `priya.raman@bankofstoic.example`, password `squad-demo`.

Limits of option A:

- All tables live in their own schema, `squad`, so the database can be shared with other work without collisions.
- There is no background worker. A cycle moves when a person with the right to run agents presses "Run … now" on the borrower's cycle (`POST /api/v1/cycles/{id}/run`): one stage per press, in the request.
- While a stage is running, anything else that writes to the ledger (a sign-in, a decision) waits for it, because the ledger is written under one lock per transaction. Reading is not affected.
- The build folder must be linked to the right project: `scripts/build-vercel.sh` copies `.vercel/` from the repository root. If that folder is missing, `vercel deploy` creates a new project named after the build folder (this happened once; the stray project was deleted).
- The function's disk is temporary. The synthetic documents ship with the deployment and are found by content hash; a file uploaded by hand is lost when the function restarts.
- A request may run for at most 300 seconds, which is why the book is loaded one borrower per call.

## Option B: Vercel, Railway and Neon (written, never deployed)

The pattern is the owner's own from SpreadSense: the workspace on Vercel, the API in one Docker container on Railway, the database on Neon. The files were written and the start script was run locally only.

### What is in the repository

| File | Role |
|---|---|
| `Dockerfile` | API and worker image |
| `railway.json` | Tells Railway to build the Dockerfile and start `scripts/start-hosted.sh` |
| `scripts/start-hosted.sh` | Runs migrations, loads the demo book into an empty database when `SEED_DEMO=1`, restores document files, starts the worker and the API on `$PORT` |
| `frontend/vercel.json` | Builds the Vite workspace and passes `/api/*` to the API host |

### Steps

1. **Neon.** Create a PostgreSQL 16 database. Take its connection string and change the scheme to `postgresql+psycopg://`, keeping `?sslmode=require`.
2. **Railway.** New project from the GitHub repository, branch `slice-1/monitoring-cycle`. Variables:
   - `DATABASE_URL` = the Neon string from step 1
   - `SESSION_SECRET` = a long random string
   - `SEED_DEMO` = `1`
   - `SQUAD_ENV` = `production`
   - `EXTRACTION_AUTONOMY` = `assisted`
   - leave `ANTHROPIC_API_KEY` unset: the demo runs on loaded data and calls no model
   The first start loads the synthetic book and takes a few minutes. Note the public host Railway gives the service.
3. **Vercel.** New project from the same repository with root directory `frontend`. In `frontend/vercel.json` replace `REPLACE-WITH-THE-API-HOST` with the Railway host from step 2, commit, and deploy.
4. Open the Vercel address and sign in as `priya.raman@bankofstoic.example`, password `squad-demo`.

## v2: Credit Squad on `squad2` (live since 24 November 2026)

`https://credit-squad.vercel.app` (Vercel project `credit-squad`, free plan) serves the v2 build: the Squad experience on the 20-client innovation book. It shares the Supabase project "Credit Agent Squad" (PostgreSQL 17, session pooler host `aws-1-us-east-1.pooler.supabase.com`) with v1 but has its own schema and its own logins, so neither site can reach the other's tables.

- **Schema `squad2`**, owned by `squad2_app`.
- **Three roles.** `squad2_app` (login) owns the schema and runs migrations (`MIGRATION_DATABASE_URL`). `squad2_web` (login) is what the site serves with (`DATABASE_URL`); it is a member of `squad2_runtime` only. `squad2_runtime` (no login) may read and write the working tables and only SELECT and INSERT on `ledger_events`. None is a member of a v1 role or has any privilege on schema `squad`, and v1's roles have none on `squad2` (checked 24 November).
- **Variables on the project (production), by name:** `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `SESSION_SECRET`, `SQUAD_ENV`, `EXTRACTION_AUTONOMY`, `DB_SCHEMA`, `DB_RUNTIME_ROLE`, `DB_POOL`, `SQUAD_LLM_MODE`. `DEMO_SETUP_TOKEN` exists only while a load is running.
- **Agents are off.** `SQUAD_LLM_MODE=live` with no model key: nothing is billable, questions to Squad and "Run … now" are refused, and the composer says so before anyone types. Turning agents on needs the owner's go-ahead and a key the owner adds (plan Task 17).
- **Deploy only with `./scripts/hosted/deploy-v2.sh`.** It builds the v2 target, links the build folder to `credit-squad` by name, refuses any other link, and pins the deploy to it. The Vercel token is the cloud environment's network secret; no token goes in a command or a file.
- **Load only with `uv run python -I scripts/hosted/v2_setup.py run --base https://credit-squad.vercel.app --project-dir .vercel-build-v2`.** It puts a one-time token on the project, redeploys, migrates, seeds one client per call, loads the squad demo, removes the token and redeploys, so the setup routes answer 404 afterwards. Measured: 27 to 41 seconds per client, about 20 minutes for the whole run with its two deploys.
- **Before anyone uses it:** `uv run python -I scripts/hosted/v2_setup.py check --base https://credit-squad.vercel.app` must print `ready: the book is unused, agents as expected, ledger append-only`.
- **Reset (owner's yes on record, `docs/owner-questions.md`, 22 Nov).** The ledger cannot be undone, so a used book is replaced: save what people's actions wrote to `docs/product/usability/ledger/` (the seed's events are reproducible and are not exported: the ledger is about 24,500 events, 14 MB), drop the schema, and load again. The Supabase administrator is not the schema's owner and may not `SET ROLE` to it by default, so the drop is one statement that takes and returns that right: `GRANT squad2_app TO postgres WITH SET TRUE, INHERIT FALSE; SET ROLE squad2_app; DROP SCHEMA squad2 CASCADE; RESET ROLE; REVOKE squad2_app FROM postgres;`. Never run a drop that names `squad`.
- **New passwords** (if a login fails with "password authentication failed"): `uv run python -I scripts/hosted/v2_secrets.py --project-dir .vercel-build-v2 --ref <project ref> --pooler-host aws-1-us-east-1.pooler.supabase.com --alter`, pass the two printed `ALTER ROLE … PASSWORD` statements to the database, then load or redeploy. The database gets verifiers only; the strings exist only on Vercel.
- **Free-tier pause.** A paused Supabase project makes sign-in fail on both sites; the owner restores it from the Supabase dashboard.
- **Briefing timings on the hosted site** (`GET /me/briefing`, five calls each, 24 November): analysts 0.34 to 0.61 s, credit officer 0.61 to 0.83 s.

## Frozen: the clickable demo (c-squad.vercel.app)

`https://c-squad.vercel.app` (Vercel project `csquad`) is the reference copy of the Squad demo, frozen on 20 November 2026 by the owner's decision. **Do not redeploy it, change its settings or its `ANTHROPIC_API_KEY`.** Its source is in `docs/product/prototype/` (page) and `docs/product/prototype/site/` (live-answer function); later changes to those files are for new work and must not be deployed to `csquad`. Its Vercel-assigned second address, `csquad-kappa.vercel.app`, is left as is. v2 gets its own Vercel project and its own database schema (`squad2`); see `docs/specs/2026-11-20-innovation-book-and-lending-layer-design.md`.

## Things to know

- The demo accounts and their password are public knowledge once this is on the internet. The data is synthetic; do not load anything else into a deployment that has demo accounts.
- Railway's disk is replaced on each deploy. The database keeps the document records; the start script regenerates the synthetic PDFs and puts each file back by content hash. Files uploaded by hand are lost on redeploy unless a volume is mounted at `/data/files`.
- The application connects as the database owner in this setup, so the ledger's append-only guard can be switched off by the application's own login. `docs/HANDOFF.md` describes the runtime role that closes this; it needs a database user that may create roles.
- A live model run needs `ANTHROPIC_API_KEY` and `SQUAD_LLM_MODE=live`, and is billable.

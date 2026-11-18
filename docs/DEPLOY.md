# Hosting a test deployment

Two ways to host it. Option A is in use; option B is written but has never been deployed.

## Option A: Vercel only, plus a PostgreSQL database (in use)

The workspace is served as static files and the API runs as one Python serverless function in the same Vercel project, so there is one address and no second host.

**State on 18 November 2026:** live at `https://credit-agent-squad.vercel.app` (Vercel project `credit-agent-squad`).

- **Database:** Supabase project "Credit Agent Squad" (free plan, region us-east-1), reached through the session pooler. All tables are in the schema `squad`.
- **Two database logins.** `squad_app` owns the tables and runs migrations (`MIGRATION_DATABASE_URL`). `squad_web` is what the application serves with (`DATABASE_URL`): it is a member of `squad_runtime`, which may read and write the working tables but only SELECT and INSERT on `ledger_events`. `GET /api/v1/ledger/verify` reports `append_only_for_this_role: true`. Passwords were generated in the session, stored only as SCRAM verifiers in the database and as secret variables on Vercel; they are in no file in this repository.
- **Loaded:** the 9 demo users and all 21 borrowers of the synthetic book (seed 20261117).
- **Model:** `SQUAD_LLM_MODE=live`, and **no `ANTHROPIC_API_KEY` is set**, so agents cannot run and the "Run … now" button on a borrower's cycle is off and says why. Adding the key (Vercel project settings, Production) and redeploying switches agents on; every run is then billable.
- **Checked on the live site:** sign-in, every menu page in a browser with no failed request, a source PDF, the ledger chain, the run route's refusal without a model.

| File | Role |
|---|---|
| `deploy/vercel/api/index.py` | Starts the API inside the function; adds three one-time setup routes |
| `deploy/vercel/vercel.json` | Sends `/api/*` to the function and every other path to the workspace |
| `deploy/vercel/requirements.txt` | Trimmed, pinned packages so the function fits Vercel's size limit |
| `scripts/build-vercel.sh` | Assembles `.vercel-build/` (API, backend, synthetic documents, built workspace) |

Steps:

1. Create a PostgreSQL 16 database (Supabase, Neon or any other). With Supabase use the **session pooler** string and change the scheme: `postgresql+psycopg://postgres.<ref>:<password>@<pooler-host>:5432/postgres`.
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

## Things to know

- The demo accounts and their password are public knowledge once this is on the internet. The data is synthetic; do not load anything else into a deployment that has demo accounts.
- Railway's disk is replaced on each deploy. The database keeps the document records; the start script regenerates the synthetic PDFs and puts each file back by content hash. Files uploaded by hand are lost on redeploy unless a volume is mounted at `/data/files`.
- The application connects as the database owner in this setup, so the ledger's append-only guard can be switched off by the application's own login. `docs/HANDOFF.md` describes the runtime role that closes this; it needs a database user that may create roles.
- A live model run needs `ANTHROPIC_API_KEY` and `SQUAD_LLM_MODE=live`, and is billable.

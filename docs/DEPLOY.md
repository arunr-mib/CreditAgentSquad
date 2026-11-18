# Hosting a test deployment

Two ways to host it. Option A is in use; option B is written but has never been deployed.

## Option A: Vercel only, plus a PostgreSQL database (in use)

The workspace is served as static files and the API runs as one Python serverless function in the same Vercel project, so there is one address and no second host.

**State on 18 November 2026:** deployed at `https://credit-agent-squad.vercel.app` (Vercel project `credit-agent-squad`). The workspace page and the API health route answer. **No database is connected yet, so sign-in and every screen with data fail until `DATABASE_URL` is set.**

| File | Role |
|---|---|
| `deploy/vercel/api/index.py` | Starts the API inside the function; adds three one-time setup routes |
| `deploy/vercel/vercel.json` | Sends `/api/*` to the function and every other path to the workspace |
| `deploy/vercel/requirements.txt` | Trimmed, pinned packages so the function fits Vercel's size limit |
| `scripts/build-vercel.sh` | Assembles `.vercel-build/` (API, backend, synthetic documents, built workspace) |

Steps:

1. Create a PostgreSQL 16 database (Supabase, Neon or any other). With Supabase use the **session pooler** string and change the scheme: `postgresql+psycopg://postgres.<ref>:<password>@<pooler-host>:5432/postgres`.
2. In the Vercel project's environment variables set `DATABASE_URL` (step 1), `SESSION_SECRET` and `DEMO_SETUP_TOKEN` (long random strings), `SQUAD_ENV=production`, `EXTRACTION_AUTONOMY=assisted`, `DB_SCHEMA=squad`, `DB_POOL=null`.
3. `./scripts/build-vercel.sh`, then from `.vercel-build/`: `npx vercel@66.0.0 deploy --prod --yes`.
4. One-time setup, each call with the header `X-Setup-Token: <DEMO_SETUP_TOKEN>`: `POST /api/_setup/migrate`, then `POST /api/_setup/seed/<borrower-code>` once per borrower (`GET /api/_setup/status` lists the codes and what is loaded). Without the header these routes answer 404.
5. Sign in as `priya.raman@bankofstoic.example`, password `squad-demo`.

Limits of option A:

- All tables live in their own schema, `squad`, so the database can be shared with other work without collisions.
- There is no background worker. A cycle advances only when a request asks it to.
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

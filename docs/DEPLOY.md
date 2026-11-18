# Hosting a test deployment

The pattern is the owner's own from SpreadSense: the workspace on Vercel, the API in one Docker container on Railway, the database on Neon. **Nothing has been deployed; these files were written and the start script was run locally only.**

## What is in the repository

| File | Role |
|---|---|
| `Dockerfile` | API and worker image |
| `railway.json` | Tells Railway to build the Dockerfile and start `scripts/start-hosted.sh` |
| `scripts/start-hosted.sh` | Runs migrations, loads the demo book into an empty database when `SEED_DEMO=1`, restores document files, starts the worker and the API on `$PORT` |
| `frontend/vercel.json` | Builds the Vite workspace and passes `/api/*` to the API host |

## Steps

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

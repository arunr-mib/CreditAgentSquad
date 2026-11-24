# Public demo site (c-squad.vercel.app)

The Squad demo page plus one serverless function, `api/ask.mjs`, that gives live answers outside Claude.

- `build.mjs` wraps `../carly-morning.html` in a document skeleton and generates `api/_evidence.mjs`
  (the evidence packs and prompt, copied from the page so the server and the page ask the same question).
- `api/ask.mjs` accepts only `{ctx, q, history}` for the demo's four contexts, builds the prompt itself,
  calls `claude-haiku-5-5` with structured JSON output, and rate-limits each visitor to 30 questions an hour
  (per server instance). The page still checks every figure in the answer against the evidence.
- The Vercel project `csquad` holds `ANTHROPIC_API_KEY` as a production secret. It is never committed.

Deploy (from a scratch folder, never from the repo root):

```bash
node build.mjs ../carly-morning.html <out-dir>   # then copy api/ask.mjs, package.json into <out-dir>
cd <out-dir> && npx vercel@66.0.0 deploy --prod --yes
```

Live answers are billable on the owner's Anthropic account (an estimate: well under one cent a question).

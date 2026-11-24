# Phase 5: Hosted v2 Release and Usability Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Credit Squad v2 (the Phase 4b build on the 20-client innovation book) on its own Vercel project and its own Supabase schema `squad2`, prove it works with a smoke test, leave both frozen sites exactly as they were, and hand the owner a kit for five usability sessions run by people whose findings are triaged before v2 is called done.

**Architecture:** Same shape as v1 (`docs/DEPLOY.md`, option A): one Vercel project serves the built workspace as static files and the API as one Python function. The build gets a **v2 target**: it ships the innovation book, writes `api/target.json` (schema `squad2`, runtime role `squad2_runtime`), and never copies the repository's `.vercel/` (which is linked to v1). Deploys go through one script that links the build folder to the new project by name, checks the link against the two frozen projects' ids, and pins `VERCEL_ORG_ID`/`VERCEL_PROJECT_ID`. The database gets three roles of its own (`squad2_app` owner, `squad2_web` serving login, `squad2_runtime` NOLOGIN), so nothing v2 does can reach schema `squad` and nothing v1 does can reach `squad2`.

**Tech Stack:** Vercel CLI `vercel@66.0.0` (via `npx`), Vercel REST API (read-only calls), Supabase MCP tools (controller session only: `execute_sql`, `get_project_url`, `list_projects`), PostgreSQL 17 (Supabase) / 16 (local), Python 3.12 + FastAPI + Alembic, `uv`, Playwright (library, no tracing), pnpm + vitest.

**Spec:** `docs/specs/2026-11-20-innovation-book-and-lending-layer-design.md` section 12 (Data and hosting); `docs/specs/2026-11-20-squad-experience-design.md` (sections 3, 7, 10, 14 for what the smoke test and the session script cover); the original plan `/root/.claude/plans/scalable-sauteeing-eich.md`, "Phase 5" and "Verification"; `docs/DEPLOY.md`; `docs/owner-questions.md` standing approvals 6 and 7.

---

## What was found before writing this plan (22 November 2026, read-only checks)

- **Vercel authentication:** this cloud environment (`CreditAgentSquad`) holds a network secret named "Vercel access token" for host `api.vercel.com` (header `Authorization`); the proxy injects it. `curl https://api.vercel.com/v2/user` returned 200 with no token in the command, and the project list is readable (`csquad`, `credit-agent-squad` and eight unrelated projects; no `credit-squad`). So the CLI is run with a **dummy** `--token proxy-injected`; the real value never appears in a command, a file or chat. No `VERCEL_TOKEN` variable exists and there is no `auth.json` in `~/.local/share/com.vercel.cli/`. A past session put a token-shaped literal into a command line; this plan forbids that.
- **Supabase:** the Supabase MCP tools are available to the controller session. `list_projects` shows "Credit Agent Squad", ref `tkeoiengqvxywmqzdxes`, region `us-east-1`, `ACTIVE_HEALTHY`, **PostgreSQL 17** (DEPLOY.md says 16). v1's roles were created as a database administrator with passwords sent only as SCRAM verifiers (DEPLOY.md, option A). The session pooler host is not returned by any MCP tool available here.
- **Build defects for v2 found in the current files:**
  1. `scripts/build-vercel.sh` ships `synthetic/out` (the frozen legacy book) and copies the repository's `.vercel/` (its `project.json` names `credit-agent-squad`, the v1 project) into the build. `.vercel-build/.vercel/project.json` also names `credit-agent-squad`. A v2 deploy from either would replace v1.
  2. `deploy/vercel/api/index.py` defaults `DB_SCHEMA` to `squad` (v1's schema) and serves the legacy book.
  3. `backend/app/core/ledger.py` hard-codes `RUNTIME_ROLE = "squad_runtime"`, used by migration `0003`, `app.cli grant-runtime-role` and `runtime-login`. Running v2's migrations as-is would grant v1's `squad_runtime` (and so v1's serving login `squad_web`) full working-table rights on `squad2`, and a v2 serving login made a member of `squad_runtime` could write v1's `squad` tables.
  4. No setup route loads `app.squad_demo` (the question and draft the Squad journeys need).
- **Agents with no key:** `SQUAD_LLM_MODE=live` with no key makes `/api/v1/agents/status` report `model_connected: false` with the reason "No model key is set for this deployment."; "Run … now" refuses; `POST /copilot/ask` answers 503 "The Copilot's model is not available." The thread's composer (`frontend/src/squad/thread/Composer.tsx`) does not read the status, so a person types a question and only then sees the error. Recorded mode is not a real option on a hosted copy: a fresh seed has new fact ids, and the Review, Early Warning and Covenant agents' recordings cannot replay against them except inside the evaluation harness (`docs/lessons/a-recorded-model-run-cannot-replay-agents-that-cite-fact-ids.md`).
- **State is consumed by use:** the Squad journeys that answer the demo question, send the draft, route and decide a breach, and create a review meeting write to the ledger, which refuses UPDATE, DELETE and TRUNCATE by design. A second usability participant would find those tasks already done unless `squad2` is rebuilt between sessions (owner question 2).
- **Demo users with clients:** Priya Raman owns 8 clients (including Stripple Tech and Lumora Health, which carry the demo question and draft), Tomas Keller 8; 4 clients belong to analysts with no login (Jules Hartmann, Theo Lindqvist), which no analyst may decide (owner answer 9, 22 Nov). Helen Strand is the credit officer.
- **Open owner item that gates outside participants:** "Names to check against real companies" (`docs/owner-questions.md`, "Waiting for you" item 2) is marked "Owner: to check".

## Global Constraints

- **Frozen, untouched:** `https://c-squad.vercel.app` (Vercel project `csquad`, also `csquad-kappa.vercel.app`) and `https://credit-agent-squad.vercel.app` (Vercel project `credit-agent-squad`, schema `squad`). No redeploy, no setting or environment-variable change, no schema, grant, role or data change by this phase. Verified by Task 8 (baseline) and Task 13 (after-check); any difference stops the phase and is reported to the owner.
- **Never call c-squad's live-answer function** (`/api/*` on c-squad): it holds a model key and is billable. Only its static pages are fetched.
- **New Vercel project** for v2 (name: owner question 3, default `credit-squad`) and **new schema `squad2`** in the existing Supabase project "Credit Agent Squad"; free tiers (standing approval 6).
- **Three v2 database roles:** `squad2_app` (LOGIN, owns `squad2`, runs migrations, `MIGRATION_DATABASE_URL`), `squad2_web` (LOGIN, member of `squad2_runtime` only, `DATABASE_URL`), `squad2_runtime` (NOLOGIN; working tables read/write, `ledger_events` SELECT and INSERT only). None of them is a member of `squad_runtime`, `squad_app` or `squad_web`, and none has any privilege on schema `squad`.
- **Passwords and secrets:** generated inside one process in the session; the database receives only SCRAM-SHA-256 verifiers; Vercel receives the connection strings, `SESSION_SECRET` and the transient `DEMO_SETUP_TOKEN` through `vercel env add` on standard input. Never printed, never written to a file (repo, scratchpad or `var/`), never in chat or a commit. No secret in the repository.
- **Vercel token:** only the proxy-injected network secret; commands pass `--token proxy-injected`. If a Vercel call returns 401/403, stop and raise the credential card (owner step O-1); no workaround.
- **Linking is explicit and checked:** a v2 build folder (`.vercel-build-v2/`) never contains a copied `.vercel/`; it is linked with `vercel link --project <v2 name>` and `scripts/hosted/check_link.py` must pass before any `vercel deploy`. The v1 build folder `.vercel-build/` and the repository's `.vercel/` are never used for v2 and never modified.
- **No model key by default:** `SQUAD_LLM_MODE=live`, no `ANTHROPIC_API_KEY`/`SQUAD_ANTHROPIC_API_KEY` on the v2 project. Turning agents on is Task 17, only with the owner's go-ahead and an estimate labelled as an estimate.
- **Environment variables on the v2 project (production):** `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `SESSION_SECRET` (secret, generated), `SQUAD_ENV=production`, `EXTRACTION_AUTONOMY=assisted`, `DB_SCHEMA=squad2`, `DB_RUNTIME_ROLE=squad2_runtime`, `DB_POOL=null`, `SQUAD_LLM_MODE=live`; `DEMO_SETUP_TOKEN` exists only while a setup run is in progress.
- **Seed:** the innovation book (20 clients, `synthetic/books/innovation/out`) plus `app.squad_demo`, through the setup routes, one borrower per call (300 s function limit).
- **SQL against Supabase runs only in the controller session through the Supabase MCP tools**, statement by statement as written in this plan. Read-only checks use SELECT only. A subagent without those tools does not run Tasks 8, 9, 10, 12 or 13.
- **Synthetic data only.** Every document carries `SYNTHETIC - FOR DEMONSTRATION`; lender Bank of Stoic; participants enter no real data.
- **Usability sessions are run by people** (a facilitator and a note-taker chosen by the owner), not agents. The owner recruits 4 analysts and 1 credit officer (standing approval 7).
- **Widths:** the Squad screens are designed for 1000 to 1920 px (spec section 13); sessions use a laptop or desktop at least 1000 px wide. Phone and tablet widths are measured and reported, not fixed, in this phase.
- **Commits:** conventional prefixes `feat(p5):`, `fix(p5):`, `docs(p5):`, `test(p5):`; tests and commit chained with `&&` (`docs/lessons/run-tests-before-commit-in-one-chain.md`); each commit adds only the files of its task (`git add <paths> && git commit -m ... -- <paths>`). End each commit message with the session's attribution lines. Do not push.
- **Report only what a tool result verified**; say what is unverified.

## Review Focus

1. **A deploy lands on the wrong project.** A build folder that carries a copied or stale `.vercel/`, or none (Vercel then creates a project named after the folder), replaces v1 or creates a stray project. Expected: the deploy script refuses unless the link names the v2 project and its id differs from both frozen projects' ids. Pinned by `test_check_link.py` (Task 2) and the Task 10/11 output.
2. **v2's serving login reaches v1's tables (or the reverse)** through the shared `squad_runtime` role. Expected: separate `squad2_runtime`; `has_schema_privilege` false both ways. Pinned by `test_runtime_role_name.py` (Task 1) and the Task 9 privilege query.
3. **A participant asks Squad a question with agents off** and gets an error only after typing. Expected: the composer says up front, in the server's words, that questions are off on this deployment, and Ask is disabled. Pinned by `composerOff.test.tsx` (Task 5).
4. **The second participant finds the first one's work done** (demo question answered, draft sent, breach decided). Expected: a pre-session check refuses to start a session on a used book. Pinned by `v2_setup.py check` (Task 4) and run before every session (Task 16).
5. **Cold starts and the briefing on serverless** (per-item engine predicate, HANDOFF "measure in Phase 5"). Expected: every screen loads with no failed request, and `GET /me/briefing` timings are measured and reported (estimate threshold 3 s for a warm call). Pinned by `hosted-smoke.mjs` (Task 6) timings output.

---

## File structure

| File | Responsibility | Task |
|---|---|---|
| `backend/app/core/config.py` | add `db_runtime_role` setting (`DB_RUNTIME_ROLE`, default `squad_runtime`) | 1 |
| `backend/app/core/ledger.py` | `runtime_role_name()` reads the setting; `RUNTIME_ROLE` kept as the default | 1 |
| `backend/migrations/versions/0003_runtime_role_for_the_ledger.py` | use `runtime_role_name()` | 1 |
| `backend/app/cli.py` | use `runtime_role_name()` | 1 |
| `backend/tests/test_runtime_role_name.py` | tests for the configurable role | 1 |
| `scripts/build-vercel.sh` | `--target v1|v2`; v2 ships the innovation book, writes `api/target.json`, never copies `.vercel/` | 2 |
| `deploy/vercel/api/index.py` | read `target.json`; refuse a schema/role that differs; `POST /api/_setup/squad-demo`; status reports target | 2 |
| `scripts/hosted/check_link.py` | refuse a build folder not linked to the expected v2 project | 2 |
| `scripts/hosted/deploy-v2.sh` | build, link, check, deploy (the only way v2 is deployed) | 2 |
| `backend/tests/deploy/test_vercel_entry.py`, `backend/tests/deploy/test_check_link.py` | tests | 2 |
| `.gitignore` | add `.vercel-build-v2/` | 2 |
| `scripts/hosted/v2_secrets.py` | generate passwords and session secret, put them on Vercel, print only role SQL with SCRAM verifiers | 3 |
| `backend/tests/deploy/test_v2_secrets.py` | SCRAM verifier checked against PostgreSQL's own; nothing secret printed | 3 |
| `scripts/hosted/v2_setup.py` | run the setup routes (migrate, seed per client, squad demo); `check` before a session | 4 |
| `backend/tests/deploy/test_v2_setup.py` | tests against a fake HTTP server | 4 |
| `frontend/src/squad/thread/Composer.tsx` | say up front when the model is off; disable Ask | 5 |
| `frontend/src/squad/__tests__/composerOff.test.tsx` | test | 5 |
| `frontend/e2e/hosted-smoke.mjs` | smoke test for any base URL (sign-in per role, every screen, PDF, ledger, Approvals hand-off) | 6 |
| `frontend/package.json` | script `e2e:smoke` | 6 |
| `scripts/hosted/frozen_check.py`, `backend/tests/deploy/test_frozen_check.py` | capture and compare the frozen sites (content hashes, Vercel metadata without values) | 8 |
| `docs/DEPLOY.md`, `docs/HANDOFF.md` | v2 section, state | 14 |
| `docs/product/usability/facilitator-script.md`, `consent-note.md`, `observation-sheet.md`, `session-log.md` | session kit | 15 |
| `docs/product/v2-usability-findings.md` | findings and triage | 15, 16 |

---

### Task 1: The runtime role is configurable, so v2 gets `squad2_runtime`

**Files:**
- Modify: `backend/app/core/config.py` (beside `db_schema`, line 35)
- Modify: `backend/app/core/ledger.py:163-166`
- Modify: `backend/migrations/versions/0003_runtime_role_for_the_ledger.py`
- Modify: `backend/app/cli.py:64-90`
- Test: `backend/tests/test_runtime_role_name.py`

**Interfaces:**
- Produces: `Settings.db_runtime_role: str = "squad_runtime"` (env `DB_RUNTIME_ROLE`); `ledger.runtime_role_name() -> str` (validated plain name; raises `ValueError` otherwise). `ledger.RUNTIME_ROLE` stays `"squad_runtime"` (the default; v1 and local behaviour unchanged).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_runtime_role_name.py
"""v2 runs beside v1 on one database server, so each needs its own runtime role: a login that is a
member of v1's role must not be able to write v2's tables, and the reverse."""
import pytest
from app.core import ledger
from app.core.config import get_settings


@pytest.fixture()
def settings_env(monkeypatch):
    def set_role(value):
        if value is None:
            monkeypatch.delenv("DB_RUNTIME_ROLE", raising=False)
        else:
            monkeypatch.setenv("DB_RUNTIME_ROLE", value)
        get_settings.cache_clear()
    yield set_role
    get_settings.cache_clear()


def test_without_a_setting_the_runtime_role_is_v1s(settings_env):
    settings_env(None)
    assert ledger.runtime_role_name() == "squad_runtime" == ledger.RUNTIME_ROLE


def test_the_runtime_role_comes_from_the_setting_and_the_grants_name_it(settings_env):
    settings_env("squad2_runtime")
    assert ledger.runtime_role_name() == "squad2_runtime"
    sql = ledger.runtime_role_sql(ledger.runtime_role_name(), schema="squad2")
    assert "GRANT SELECT, INSERT ON squad2.ledger_events TO squad2_runtime;" in sql
    assert "squad_runtime;" not in sql.replace("squad2_runtime", "")


def test_a_runtime_role_setting_that_is_not_a_plain_name_is_refused(settings_env):
    settings_env("squad2_runtime; DROP TABLE ledger_events")
    with pytest.raises(ValueError):
        ledger.runtime_role_name()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_runtime_role_name.py -q`
Expected: FAIL with `AttributeError: module 'app.core.ledger' has no attribute 'runtime_role_name'`

- [ ] **Step 3: Write minimal implementation**

In `backend/app/core/config.py`, after `db_schema: str = ""`:

```python
    # The role the serving login is a member of (`app.core.ledger`). v1 uses the default; a second
    # deployment on the same server (v2: `squad2_runtime`) needs its own, or each could write the other's tables.
    db_runtime_role: str = "squad_runtime"
```

In `backend/app/core/ledger.py`, keep `RUNTIME_ROLE = "squad_runtime"` and add below it:

```python
def runtime_role_name() -> str:
    """The runtime role of this deployment: `DB_RUNTIME_ROLE`, `squad_runtime` when unset."""
    from app.core.config import get_settings

    name = get_settings().db_runtime_role.strip() or RUNTIME_ROLE
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name):
        raise ValueError(f"not a plain role name: {name!r}")
    return name
```

(If `ledger.py` already imports `get_settings` at module level, use that import instead of the local one.)

In `0003_runtime_role_for_the_ledger.py`: replace `from app.core.ledger import RUNTIME_ROLE, runtime_role_sql` with `from app.core.ledger import runtime_role_name, runtime_role_sql`; at the top of `upgrade()` and `downgrade()` add `role = runtime_role_name()`; replace every `RUNTIME_ROLE` in both functions with `role`; call `runtime_role_sql(role, schema=...)`. In `downgrade()` replace the hard-coded `public` with `schema = get_settings().db_schema.strip() or "public"` and use `{schema}`.

In `backend/app/cli.py`: in `grant_runtime_role` and `runtime_login` set `role = ledger.runtime_role_name()` first and use `role` wherever `ledger.RUNTIME_ROLE` appears, including `ledger.runtime_role_sql(role, schema=...)` and `GRANT {role} TO {name}`; `runtime_login` also refuses `name == role`.

- [ ] **Step 4: Run tests to verify they pass, then the existing role and migration tests**

Run: `service postgresql start; uv run pytest backend/tests/test_runtime_role_name.py backend/tests/test_ledger_roles.py -q && uv run ruff check backend`
Expected: PASS (the existing `test_ledger_roles.py` tests unchanged and passing or skipping exactly as before).

Then prove migration 0003 grants the configured role on a scratch schema (local only):

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE squad2_runtime_local NOLOGIN" -c "GRANT CREATE ON DATABASE credit_agent_squad_test TO squad"
cd backend && DB_SCHEMA=squad2_local DB_RUNTIME_ROLE=squad2_runtime_local uv run alembic -x url="$(grep ^TEST_DATABASE_URL ../.env | cut -d= -f2-)" upgrade head && cd ..
sudo -u postgres psql -d credit_agent_squad_test -Atc "SELECT has_table_privilege('squad2_runtime_local','squad2_local.ledger_events','UPDATE'), has_table_privilege('squad2_runtime_local','squad2_local.ledger_events','INSERT'), has_schema_privilege('squad_runtime','squad2_local','USAGE')"
sudo -u postgres psql -d credit_agent_squad_test -v ON_ERROR_STOP=1 -c "DROP SCHEMA squad2_local CASCADE" -c "DROP OWNED BY squad2_runtime_local" -c "DROP ROLE squad2_runtime_local"
```
Expected: the SELECT prints `f|t|f` (the v2 role may insert but not update the ledger; v1's role has no usage on the v2 schema). If `sudo` is unavailable use `su postgres -c "psql ..."`. If `squad_runtime` does not exist locally, the third column errors; then drop it from the query and say so.

- [ ] **Step 5: Commit**

```bash
uv run pytest backend/tests/test_runtime_role_name.py backend/tests/test_ledger_roles.py -q && \
git add backend/app/core/config.py backend/app/core/ledger.py backend/migrations/versions/0003_runtime_role_for_the_ledger.py backend/app/cli.py backend/tests/test_runtime_role_name.py && \
git commit -m "feat(p5): the ledger's runtime role is a setting, so v2 runs as squad2_runtime" -- backend/app/core/config.py backend/app/core/ledger.py backend/migrations/versions/0003_runtime_role_for_the_ledger.py backend/app/cli.py backend/tests/test_runtime_role_name.py
```

---

### Task 2: A v2 build target that cannot be deployed to the wrong project

**Files:**
- Modify: `scripts/build-vercel.sh`
- Modify: `deploy/vercel/api/index.py`
- Create: `scripts/hosted/check_link.py`, `scripts/hosted/deploy-v2.sh`
- Modify: `.gitignore` (add `.vercel-build-v2/`)
- Test: `backend/tests/deploy/__init__.py` (empty), `backend/tests/deploy/test_vercel_entry.py`, `backend/tests/deploy/test_check_link.py`

**Interfaces:**
- Consumes: `ledger.runtime_role_name()` and `DB_RUNTIME_ROLE` (Task 1); `app.squad_demo.seed_squad_demo(db) -> dict`.
- Produces: `./scripts/build-vercel.sh --target v2` writes `.vercel-build-v2/` with `api/target.json` = `{"target": "v2", "schema": "squad2", "runtime_role": "squad2_runtime"}` and the innovation book at `synthetic/out/`; with no argument the script behaves exactly as before (v1). `check_link.py <build-dir> <project-name> [--frozen-ids ID ...] [--export]` exits 0 and, with `--export`, prints `export VERCEL_ORG_ID=...` and `export VERCEL_PROJECT_ID=...`; exits 1 with a reason otherwise. Setup route `POST /api/_setup/squad-demo` returns `seed_squad_demo`'s dict. `GET /api/_setup/status` adds `"target"` and `"schema"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/deploy/test_vercel_entry.py
"""The Vercel entry point must serve the schema and runtime role its build was made for, and
nothing else: a v2 build that starts with v1's schema would write into v1's record."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ENTRY = Path(__file__).resolve().parents[3] / "deploy" / "vercel" / "api" / "index.py"


def load(tmp_path, monkeypatch, target=None, **env):
    api = tmp_path / "api"
    api.mkdir()
    shutil.copy(ENTRY, api / "index.py")
    if target is not None:
        (api / "target.json").write_text(json.dumps(target))
    for key in ("DB_SCHEMA", "DB_RUNTIME_ROLE", "DEMO_SETUP_TOKEN", "FILE_FALLBACK_DIR", "FILE_STORE_DIR", "DB_POOL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    from app.core.config import get_settings
    get_settings.cache_clear()
    spec = importlib.util.spec_from_file_location(f"entry_{tmp_path.name}", api / "index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V2 = {"target": "v2", "schema": "squad2", "runtime_role": "squad2_runtime"}


def test_a_build_without_a_target_file_keeps_v1s_schema_and_role(tmp_path, monkeypatch):
    module = load(tmp_path, monkeypatch)
    import os
    assert module.TARGET["target"] == "v1"
    assert os.environ["DB_SCHEMA"] == "squad" and os.environ["DB_RUNTIME_ROLE"] == "squad_runtime"


def test_a_v2_build_takes_squad2_when_nothing_is_set(tmp_path, monkeypatch):
    module = load(tmp_path, monkeypatch, V2)
    import os
    assert module.TARGET == V2
    assert os.environ["DB_SCHEMA"] == "squad2" and os.environ["DB_RUNTIME_ROLE"] == "squad2_runtime"


@pytest.mark.parametrize("env", [{"DB_SCHEMA": "squad"}, {"DB_RUNTIME_ROLE": "squad_runtime"}])
def test_a_v2_build_refuses_to_start_on_v1s_schema_or_role(tmp_path, monkeypatch, env):
    with pytest.raises(RuntimeError, match="built for"):
        load(tmp_path, monkeypatch, V2, **env)


def test_every_setup_route_is_hidden_without_the_token(tmp_path, monkeypatch):
    module = load(tmp_path, monkeypatch, V2)
    client = TestClient(module.app)
    assert client.get("/api/_setup/status").status_code == 404
    for path in ("/api/_setup/migrate", "/api/_setup/seed/stripple-tech", "/api/_setup/squad-demo"):
        assert client.post(path, headers={"X-Setup-Token": "anything"}).status_code == 404
```

```python
# backend/tests/deploy/test_check_link.py
"""A v2 deploy must refuse a build folder linked to anything but the v2 project."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "hosted" / "check_link.py"
FROZEN = ["prj_v1_frozen", "prj_csquad_frozen"]


def run(build, name, *extra):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), str(build), name, "--frozen-ids", *FROZEN, *extra],
                          capture_output=True, text=True)


def make(tmp_path, project=None, target="v2"):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "target.json").write_text(json.dumps({"target": target, "schema": "squad2",
                                                              "runtime_role": "squad2_runtime"}))
    if project is not None:
        (tmp_path / ".vercel").mkdir()
        (tmp_path / ".vercel" / "project.json").write_text(json.dumps(project))
    return tmp_path


def test_a_folder_linked_to_the_v2_project_passes_and_exports_its_ids(tmp_path):
    build = make(tmp_path, {"projectId": "prj_new", "orgId": "team_x", "projectName": "credit-squad"})
    result = run(build, "credit-squad", "--export")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "export VERCEL_PROJECT_ID=prj_new" in result.stdout and "export VERCEL_ORG_ID=team_x" in result.stdout


def test_an_unlinked_folder_is_refused(tmp_path):
    assert run(make(tmp_path), "credit-squad").returncode == 1


def test_a_folder_linked_to_v1_is_refused_by_name_and_by_id(tmp_path):
    by_name = make(tmp_path / "a", {"projectId": "prj_other", "orgId": "t", "projectName": "credit-agent-squad"})
    assert run(by_name, "credit-agent-squad").returncode == 1  # a frozen name is never a v2 target
    by_id = make(tmp_path / "b", {"projectId": "prj_v1_frozen", "orgId": "t", "projectName": "credit-squad"})
    assert run(by_id, "credit-squad").returncode == 1


def test_a_folder_linked_to_another_project_or_built_for_v1_is_refused(tmp_path):
    other = make(tmp_path / "a", {"projectId": "prj_y", "orgId": "t", "projectName": "spreadsense"})
    assert run(other, "credit-squad").returncode == 1
    v1_build = make(tmp_path / "b", {"projectId": "prj_new", "orgId": "t", "projectName": "credit-squad"}, target="v1")
    assert run(v1_build, "credit-squad").returncode == 1
```

(`make(tmp_path / "a", ...)` needs the folder: start `make` with `tmp_path.mkdir(parents=True, exist_ok=True)`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/deploy -q`
Expected: FAIL (`AttributeError: ... has no attribute 'TARGET'`; `check_link.py` not found).

- [ ] **Step 3: Write minimal implementation**

`deploy/vercel/api/index.py`: replace the two lines `os.environ.setdefault("DB_POOL", "null")` / `os.environ.setdefault("DB_SCHEMA", "squad")` with:

```python
import json  # noqa: E402

# The build says which deployment this is (scripts/build-vercel.sh --target v2 writes api/target.json).
# A v1 build has no such file and keeps v1's schema and role.
_TARGET_FILE = Path(__file__).with_name("target.json")
TARGET = (json.loads(_TARGET_FILE.read_text()) if _TARGET_FILE.exists()
          else {"target": "v1", "schema": "squad", "runtime_role": "squad_runtime"})
os.environ.setdefault("DB_POOL", "null")
os.environ.setdefault("DB_SCHEMA", TARGET["schema"])
os.environ.setdefault("DB_RUNTIME_ROLE", TARGET["runtime_role"])
if (os.environ["DB_SCHEMA"], os.environ["DB_RUNTIME_ROLE"]) != (TARGET["schema"], TARGET["runtime_role"]):
    raise RuntimeError(f"this build was built for {TARGET['target']} (schema {TARGET['schema']}, role "
                       f"{TARGET['runtime_role']}); the deployment sets DB_SCHEMA={os.environ['DB_SCHEMA']} "
                       f"and DB_RUNTIME_ROLE={os.environ['DB_RUNTIME_ROLE']}")
```

In `setup_status`, add `"target": TARGET["target"], "schema": os.environ["DB_SCHEMA"]` to both returned dicts. Add the route:

```python
@app.post("/api/_setup/squad-demo")
def setup_squad_demo(x_setup_token: str | None = Header(default=None)) -> dict:
    """Squad's demonstration question and draft (`app.squad_demo`), after every borrower is loaded. Idempotent."""
    _allowed(x_setup_token)
    from app.squad_demo import seed_squad_demo

    with _session() as db:
        return seed_squad_demo(db)
```

`scripts/build-vercel.sh`: replace the body after `cd "$(dirname "$0")/.."` with:

```bash
TARGET=v1
if [ "${1:-}" = "--target" ]; then TARGET="${2:-}"; fi
case "$TARGET" in
  v1) OUT=.vercel-build;    BOOK=synthetic/out;                  GEN="uv run python -m synthetic.generate" ;;
  v2) OUT=.vercel-build-v2; BOOK=synthetic/books/innovation/out; GEN="uv run python -m synthetic.books.innovation.generate" ;;
  *) echo "usage: $0 [--target v1|v2]" >&2; exit 2 ;;
esac

# the documents are git-ignored: a fresh checkout or worktree has the manifest but not the PDFs
{ [ -f "$BOOK/manifest.json" ] && [ -d "$BOOK/documents" ]; } || $GEN
(cd frontend && pnpm install --silent && pnpm build)

rm -rf "$OUT"
mkdir -p "$OUT/synthetic" "$OUT/public"
cp -r deploy/vercel/api deploy/vercel/vercel.json deploy/vercel/requirements.txt "$OUT/"
cp -r backend "$OUT/backend"
find "$OUT/backend" -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -rf "$OUT/backend/tests"
cp -r "$BOOK" "$OUT/synthetic/out"   # both targets serve their book from the same path
cp -r frontend/dist/. "$OUT/public/"
if [ "$TARGET" = v1 ]; then
  [ -d .vercel ] && cp -r .vercel "$OUT/.vercel" || true
else
  # never the repository's .vercel/: it is linked to v1. scripts/hosted/deploy-v2.sh links this folder.
  printf '{"target": "v2", "schema": "squad2", "runtime_role": "squad2_runtime"}\n' > "$OUT/api/target.json"
fi
echo "Built $OUT ($TARGET): $(du -sh "$OUT" | cut -f1) ($(find "$OUT" -type f | wc -l) files)"
```

Update the header comment to mention `--target v2` and `scripts/hosted/deploy-v2.sh`.

`scripts/hosted/check_link.py`:

```python
"""Refuse to deploy a build folder that is not linked to the expected v2 project.

    python scripts/hosted/check_link.py .vercel-build-v2 credit-squad [--export]

The frozen projects' ids are read from the Vercel API (the proxy adds the token); tests pass them
with --frozen-ids. Prints nothing secret: project and team ids only."""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

FROZEN_NAMES = ("csquad", "credit-agent-squad")


def frozen_ids() -> list[str]:
    ids = []
    for name in FROZEN_NAMES:
        with urllib.request.urlopen(f"https://api.vercel.com/v9/projects/{name}", timeout=30) as response:
            ids.append(json.load(response)["id"])
    return ids


def problems(build: Path, expected: str, frozen: list[str]) -> list[str]:
    found = []
    target = build / "api" / "target.json"
    if not target.exists() or json.loads(target.read_text()).get("target") != "v2":
        found.append("the folder is not a v2 build (api/target.json missing or not v2)")
    link = build / ".vercel" / "project.json"
    if not link.exists():
        return found + ["the folder is not linked: run vercel link --yes --project <name> in it"]
    project = json.loads(link.read_text())
    if expected in FROZEN_NAMES:
        found.append(f"{expected} is a frozen project and never a v2 target")
    if project.get("projectName") != expected:
        found.append(f"linked to {project.get('projectName')!r}, expected {expected!r}")
    if project.get("projectId") in frozen:
        found.append("linked to the id of a frozen project")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("project")
    parser.add_argument("--frozen-ids", nargs="*")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    found = problems(args.build, args.project, args.frozen_ids if args.frozen_ids is not None else frozen_ids())
    if found:
        print("REFUSED: " + "; ".join(found), file=sys.stderr)
        return 1
    project = json.loads((args.build / ".vercel" / "project.json").read_text())
    if args.export:
        print(f"export VERCEL_ORG_ID={project['orgId']}\nexport VERCEL_PROJECT_ID={project['projectId']}")
    else:
        print(f"linked to {project['projectName']}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`scripts/hosted/deploy-v2.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# The only way v2 is deployed. Builds the v2 target, links the build folder to the v2 project by name,
# refuses unless check_link.py passes, then deploys with the project pinned. The Vercel token is the
# environment's network secret: the CLI gets a dummy value and the proxy replaces it.
#   V2_PROJECT=credit-squad ./scripts/hosted/deploy-v2.sh [--no-build]
set -euo pipefail
cd "$(dirname "$0")/../.."
PROJECT="${V2_PROJECT:-credit-squad}"
VC=(npx --yes vercel@66.0.0)
TOKEN=(--token proxy-injected)
export VERCEL_TELEMETRY_DISABLED=1
[ "${1:-}" = "--no-build" ] || ./scripts/build-vercel.sh --target v2
cd .vercel-build-v2
[ ! -e .vercel ] || [ "${1:-}" = "--no-build" ] || { echo "a fresh build must not carry .vercel/" >&2; exit 1; }
"${VC[@]}" link --yes --project "$PROJECT" "${TOKEN[@]}" >/dev/null
uv run --no-project python -I ../scripts/hosted/check_link.py . "$PROJECT"
eval "$(uv run --no-project python -I ../scripts/hosted/check_link.py . "$PROJECT" --export)"
"${VC[@]}" deploy --prod --yes "${TOKEN[@]}"
```

`.gitignore`: add the line `.vercel-build-v2/` after `.vercel-build/`.

- [ ] **Step 4: Run tests, then build once and inspect the folder**

Run: `uv run pytest backend/tests/deploy -q && uv run ruff check deploy scripts backend && ./scripts/build-vercel.sh --target v2 && test ! -e .vercel-build-v2/.vercel && cat .vercel-build-v2/api/target.json && ls .vercel-build-v2/synthetic/out/truth | wc -l && jq -r .seed .vercel-build-v2/synthetic/out/manifest.json && git status --short .vercel .vercel-build`
Expected: tests PASS; no `.vercel` in the v2 folder; target v2; `20` truth files; the innovation seed; `git status` shows nothing for `.vercel` and `.vercel-build` (both untouched and git-ignored). Also confirm `cat .vercel-build/.vercel/project.json | jq -r .projectName` still prints `credit-agent-squad` (the v1 folder was not rebuilt or touched).

- [ ] **Step 5: Commit**

```bash
uv run pytest backend/tests/deploy -q && \
git add scripts/build-vercel.sh deploy/vercel/api/index.py scripts/hosted/check_link.py scripts/hosted/deploy-v2.sh .gitignore backend/tests/deploy && \
git commit -m "feat(p5): a v2 build target that ships the innovation book on squad2 and refuses any link but the v2 project" -- scripts/build-vercel.sh deploy/vercel/api/index.py scripts/hosted/check_link.py scripts/hosted/deploy-v2.sh .gitignore backend/tests/deploy
```

---

### Task 3: Passwords made in one process; the database gets verifiers, Vercel gets the strings

**Files:**
- Create: `scripts/hosted/v2_secrets.py`
- Test: `backend/tests/deploy/test_v2_secrets.py`

**Interfaces:**
- Produces: `scram_verifier(password: str, salt: bytes | None = None, iterations: int = 4096) -> str` (PostgreSQL's `SCRAM-SHA-256$<iter>:<salt>$<StoredKey>:<ServerKey>` format); `role_sql(owner_verifier: str, web_verifier: str) -> str`; `connection_url(role: str, ref: str, password: str, host: str) -> str`. CLI: `python scripts/hosted/v2_secrets.py --project-dir .vercel-build-v2 --ref <ref> --pooler-host <host> [--vercel "npx --yes vercel@66.0.0"]` puts `MIGRATION_DATABASE_URL`, `DATABASE_URL`, `SESSION_SECRET` on the linked project (production) and prints **only** `role_sql(...)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/deploy/test_v2_secrets.py
"""The passwords for v2's logins never leave one process except as verifiers (to the database)
and as connection strings on standard input (to Vercel)."""
import base64
import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "hosted" / "v2_secrets.py"
spec = importlib.util.spec_from_file_location("v2_secrets", SCRIPT)
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)


def test_the_verifier_matches_the_one_postgresql_computes_for_the_same_salt():
    """Checked against the server itself, not against our own arithmetic: needs a superuser URL
    (PG_SUPERUSER_URL, for example postgresql+psycopg://postgres@/credit_agent_squad_test?host=/var/run/postgresql)."""
    url = os.environ.get("PG_SUPERUSER_URL")
    if not url:
        pytest.skip("set PG_SUPERUSER_URL to compare with PostgreSQL's own verifier")
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("SET LOCAL password_encryption = 'scram-sha-256'"))
        db.execute(text("CREATE ROLE p5_scram_probe PASSWORD 'pencil-and-paper-12'"))
        stored = db.execute(text("SELECT rolpassword FROM pg_authid WHERE rolname = 'p5_scram_probe'")).scalar()
        db.execute(text("DROP ROLE p5_scram_probe"))
    iterations, rest = stored.removeprefix("SCRAM-SHA-256$").split(":", 1)
    salt = base64.b64decode(rest.split("$", 1)[0])
    assert v2.scram_verifier("pencil-and-paper-12", salt=salt, iterations=int(iterations)) == stored


def test_role_sql_creates_three_roles_and_names_no_v1_role():
    sql = v2.role_sql("SCRAM-SHA-256$4096:a$b:c", "SCRAM-SHA-256$4096:d$e:f")
    assert "CREATE ROLE squad2_runtime NOLOGIN;" in sql
    assert "CREATE ROLE squad2_app LOGIN" in sql and "CREATE ROLE squad2_web LOGIN" in sql
    assert "GRANT squad2_runtime TO squad2_web;" in sql
    assert "GRANT CREATE ON DATABASE postgres TO squad2_app;" in sql
    for v1 in ("squad_runtime", "squad_app", "squad_web", " squad;", "squad."):
        assert v1 not in sql


def test_the_url_uses_the_session_pooler_user_form_and_requires_tls():
    url = v2.connection_url("squad2_web", "ref123", "Abc123", "pooler.example")
    assert url == "postgresql+psycopg://squad2_web.ref123:Abc123@pooler.example:5432/postgres?sslmode=require"


def test_the_cli_prints_only_sql_and_hands_each_value_to_vercel_on_stdin(tmp_path):
    """A fake vercel records its arguments and the length of its input, never the input itself."""
    fake = tmp_path / "vercel"
    log = tmp_path / "calls.txt"
    fake.write_text(f"#!/bin/sh\nIN=$(cat)\necho \"$* len=${{#IN}}\" >> {log}\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    result = subprocess.run([sys.executable, "-I", str(SCRIPT), "--project-dir", str(tmp_path), "--ref", "ref123",
                             "--pooler-host", "pooler.example", "--vercel", str(fake)],
                            capture_output=True, text=True, check=True)
    calls = log.read_text().splitlines()
    assert [c.split()[2] for c in calls] == ["MIGRATION_DATABASE_URL", "DATABASE_URL", "SESSION_SECRET"]
    assert all("production" in c and "--token proxy-injected" in c for c in calls)
    assert "postgresql" not in result.stdout and "postgresql" not in result.stderr
    assert result.stdout.count("SCRAM-SHA-256$") == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/deploy/test_v2_secrets.py -q`
Expected: FAIL (`FileNotFoundError` for `v2_secrets.py`).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/hosted/v2_secrets.py
"""Make v2's database passwords and session secret in this process and nowhere else.

    python scripts/hosted/v2_secrets.py --project-dir .vercel-build-v2 --ref <supabase ref> --pooler-host <host>

Puts MIGRATION_DATABASE_URL (squad2_app), DATABASE_URL (squad2_web) and SESSION_SECRET on the linked
Vercel project's production environment through `vercel env add` on standard input, then prints the
SQL that creates the roles with SCRAM verifiers only. Paste that SQL into the Supabase MCP tool
`execute_sql`. Running it again makes new passwords: run the printed SQL with ALTER instead of CREATE
(`--alter`). No value is printed or written to a file."""
import argparse
import base64
import hashlib
import hmac
import secrets
import shlex
import string
import subprocess
import sys

ALPHABET = string.ascii_letters + string.digits  # placed in a URL: letters and digits only


def new_password(length: int = 40) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def scram_verifier(password: str, salt: bytes | None = None, iterations: int = 4096) -> str:
    salt = salt if salt is not None else secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    stored = hashlib.sha256(hmac.new(salted, b"Client Key", "sha256").digest()).digest()
    server = hmac.new(salted, b"Server Key", "sha256").digest()
    b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored)}:{b64(server)}"


def role_sql(owner_verifier: str, web_verifier: str, alter: bool = False) -> str:
    verb = "ALTER" if alter else "CREATE"
    lines = [] if alter else ["CREATE ROLE squad2_runtime NOLOGIN;"]
    lines += [f"{verb} ROLE squad2_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{owner_verifier}';",
              f"{verb} ROLE squad2_web LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{web_verifier}';"]
    if not alter:
        lines += ["GRANT squad2_runtime TO squad2_web;",
                  "GRANT CREATE ON DATABASE postgres TO squad2_app;"]  # its migration creates schema squad2
    return "\n".join(lines)


def connection_url(role: str, ref: str, password: str, host: str) -> str:
    return f"postgresql+psycopg://{role}.{ref}:{password}@{host}:5432/postgres?sslmode=require"


def put(vercel: list[str], project_dir: str, name: str, value: str) -> None:
    done = subprocess.run([*vercel, "env", "add", name, "production", "--token", "proxy-injected"],
                          input=value + "\n", text=True, capture_output=True, cwd=project_dir)
    if done.returncode != 0:
        reason = (done.stderr or done.stdout).replace(value, "<value>")[-400:]
        sys.exit(f"vercel env add {name} failed ({done.returncode}): {reason}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--pooler-host", required=True)
    parser.add_argument("--vercel", default="npx --yes vercel@66.0.0")
    parser.add_argument("--alter", action="store_true")
    args = parser.parse_args()
    vercel = shlex.split(args.vercel)
    owner, web = new_password(), new_password()
    put(vercel, args.project_dir, "MIGRATION_DATABASE_URL", connection_url("squad2_app", args.ref, owner, args.pooler_host))
    put(vercel, args.project_dir, "DATABASE_URL", connection_url("squad2_web", args.ref, web, args.pooler_host))
    put(vercel, args.project_dir, "SESSION_SECRET", secrets.token_urlsafe(48))
    print(role_sql(scram_verifier(owner), scram_verifier(web), alter=args.alter))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Before Task 10 uses it, check the flag set of the pinned CLI once: `npx --yes vercel@66.0.0 env add --help | grep -E "sensitive|force"`. If `--sensitive` is listed, add it to the `put` arguments and to the test's expected call (one-line change, its own commit `fix(p5): env values are marked sensitive`). If not, leave as is (Vercel stores production values encrypted either way).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/deploy/test_v2_secrets.py -q` and once with the server's own verifier: `PG_SUPERUSER_URL='postgresql+psycopg://postgres@/credit_agent_squad_test?host=/var/run/postgresql' sudo -E -u postgres $(which uv) run pytest backend/tests/deploy/test_v2_secrets.py -q -k matches` (or run that test as any local superuser; say which).
Expected: 4 PASS (the superuser test must PASS, not skip, at least once; report it).

- [ ] **Step 5: Commit**

```bash
uv run pytest backend/tests/deploy -q && \
git add scripts/hosted/v2_secrets.py backend/tests/deploy/test_v2_secrets.py && \
git commit -m "feat(p5): v2 database passwords live in one process; the database gets SCRAM verifiers only" -- scripts/hosted/v2_secrets.py backend/tests/deploy/test_v2_secrets.py
```

---

### Task 4: One command loads the book through the setup routes and turns them off again; one command checks a book is unused

**Files:**
- Create: `scripts/hosted/v2_setup.py`
- Test: `backend/tests/deploy/test_v2_setup.py`

**Interfaces:**
- Consumes: setup routes (Task 2): `GET /api/_setup/status` → `{"migrated", "users", "loaded", "to_load", "book_borrowers", "book_seed", "target", "schema"}`; `POST /api/_setup/migrate`; `POST /api/_setup/seed/{code}` → `{"code", "loaded": "now"|"already"}`; `POST /api/_setup/squad-demo` → `{"question_borrower_code", "draft_borrower_code", "work_item_id", "draft_id"}`. `scripts/hosted/deploy-v2.sh --no-build`.
- Produces: `load(base: str, token: str, post=..., get=...) -> dict` (returns the final status); `check(base: str, expect_model: bool) -> list[str]` (problems; empty means ready). CLI:
  - `python scripts/hosted/v2_setup.py run --base <url> --project-dir .vercel-build-v2` (hosted: makes a token, `vercel env add DEMO_SETUP_TOKEN`, redeploys, loads, `vercel env rm DEMO_SETUP_TOKEN --yes`, redeploys, confirms `/api/_setup/status` is 404);
  - `python scripts/hosted/v2_setup.py load --base <url>` (local rehearsal: the token is read from the `DEMO_SETUP_TOKEN` variable of the same shell that started the server);
  - `python scripts/hosted/v2_setup.py check --base <url> [--expect-model]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/deploy/test_v2_setup.py
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "hosted" / "v2_setup.py"
spec = importlib.util.spec_from_file_location("v2_setup", SCRIPT)
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)


class FakeHost:
    """The setup routes as the function answers them, with one seed call that times out once."""

    def __init__(self):
        self.loaded, self.calls, self.flaky = [], [], {"lumora-health"}
        self.book = ["dataflake-inc", "lumora-health", "stripple-tech"]

    def get(self, path, token):
        self.calls.append(("GET", path))
        return 200, {"migrated": bool(self.calls[:-1]), "users": 9, "loaded": list(self.loaded),
                     "to_load": [c for c in self.book if c not in self.loaded], "book_borrowers": 3,
                     "target": "v2", "schema": "squad2"}

    def post(self, path, token):
        self.calls.append(("POST", path))
        code = path.rsplit("/", 1)[-1]
        if code in self.flaky:
            self.flaky.discard(code)
            return 504, {"detail": "timeout"}
        if path.startswith("/api/_setup/seed/"):
            self.loaded.append(code)
            return 200, {"code": code, "loaded": "now"}
        return 200, {"migrated": True}


def test_load_migrates_seeds_one_client_per_call_retries_once_and_adds_the_squad_demo():
    host = FakeHost()
    status = v2.load("https://x", "t", post=host.post, get=host.get)
    posts = [p for m, p in host.calls if m == "POST"]
    assert posts[0] == "/api/_setup/migrate" and posts[-1] == "/api/_setup/squad-demo"
    assert posts.count("/api/_setup/seed/lumora-health") == 2  # one retry after the timeout
    assert status["to_load"] == [] and status["schema"] == "squad2"


def test_load_refuses_a_host_that_is_not_v2_on_squad2():
    host = FakeHost()
    host.get = lambda path, token: (200, {"migrated": True, "target": "v1", "schema": "squad", "to_load": []})
    try:
        v2.load("https://x", "t", post=host.post, get=host.get)
    except SystemExit as stop:
        assert "squad2" in str(stop)
    else:
        raise AssertionError("a v1 host was loaded")


def test_check_names_each_thing_a_used_book_has_lost():
    briefing = {"items": [{"item_type": "covenant.breach", "needs_you": True, "borrower_code": "dataflake-inc"}]}
    problems = v2.check_state(briefing=briefing, question_open=False, draft_sent=True,
                              model={"model_connected": False}, ledger={"ok": True, "append_only_for_this_role": True},
                              expect_model=False)
    assert any("question" in p for p in problems) and any("draft" in p for p in problems)


def test_check_passes_a_fresh_book_and_refuses_a_ledger_the_app_could_rewrite():
    fresh = dict(briefing={"items": [{"item_type": "question", "needs_you": True, "borrower_code": "stripple-tech"}]},
                 question_open=True, draft_sent=False, model={"model_connected": False}, expect_model=False)
    assert v2.check_state(**fresh, ledger={"ok": True, "append_only_for_this_role": True}) == []
    assert v2.check_state(**fresh, ledger={"ok": True, "append_only_for_this_role": False})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/deploy/test_v2_setup.py -q`
Expected: FAIL (`FileNotFoundError` for `v2_setup.py`).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/hosted/v2_setup.py
"""Load v2's book through the setup routes, and check that a hosted book is ready for a session.

    python scripts/hosted/v2_setup.py run   --base https://<v2>.vercel.app --project-dir .vercel-build-v2
    python scripts/hosted/v2_setup.py load  --base http://localhost:8010      # token from $DEMO_SETUP_TOKEN
    python scripts/hosted/v2_setup.py check --base https://<v2>.vercel.app [--expect-model]

`run` makes the setup token in this process, puts it on Vercel, redeploys, loads, removes the token
and redeploys again, so the setup routes answer 404 whenever nobody is loading. Nothing secret is printed."""
import argparse
import http.cookiejar
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERCEL = ["npx", "--yes", "vercel@66.0.0"]
ANALYST, PASSWORD = "priya.raman@bankofstoic.example", os.environ.get("SQUAD_DEMO_PASSWORD", "squad-demo")


def _call(base, method, path, token=None, body=None, opener=None, timeout=310):
    request = urllib.request.Request(base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **({"X-Setup-Token": token} if token else {})})
    try:
        with (opener or urllib.request.build_opener()).open(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, {"detail": error.read()[:300].decode(errors="replace")}
    except (TimeoutError, urllib.error.URLError) as error:
        return 504, {"detail": str(error)[:300]}


def load(base, token, post=None, get=None):
    post = post or (lambda path, t: _call(base, "POST", path, t))
    get = get or (lambda path, t: _call(base, "GET", path, t))
    code, status = get("/api/_setup/status", token)
    if code != 200 or status.get("target") != "v2" or status.get("schema") != "squad2":
        sys.exit(f"refused: {base} is not a v2 build on squad2 ({code}, {status.get('target')}, {status.get('schema')})")
    code, body = post("/api/_setup/migrate", token)
    if code != 200:
        sys.exit(f"migrate failed: {code} {body}")
    _, status = get("/api/_setup/status", token)
    for client in status["to_load"]:
        for attempt in (1, 2):
            started = time.monotonic()
            code, body = post(f"/api/_setup/seed/{client}", token)
            print(f"seed {client}: {code} {body.get('loaded')} {time.monotonic() - started:.1f}s (try {attempt})")
            if code == 200:
                break
        else:
            sys.exit(f"seed {client} failed twice: {code} {body}")
    code, body = post("/api/_setup/squad-demo", token)
    if code != 200:
        sys.exit(f"squad demo failed: {code} {body}")
    _, status = get("/api/_setup/status", token)
    if status["to_load"]:
        sys.exit(f"still to load: {status['to_load']}")
    print(json.dumps({k: status.get(k) for k in ("users", "book_borrowers", "book_seed", "target", "schema")}))
    return status


def check_state(*, briefing, question_open, draft_sent, model, ledger, expect_model):
    problems = []
    if not question_open:
        problems.append("Squad's demo question (Stripple) is not open: the book has been used")
    if draft_sent:
        problems.append("the demo draft (Lumora) has been sent: the book has been used")
    if not any(i.get("item_type") == "covenant.breach" or i.get("item_type", "").startswith("covenant") for i in briefing["items"]):
        problems.append("no covenant case is waiting for the analyst")
    if bool(model.get("model_connected")) != expect_model:
        problems.append(f"agents are {'on' if model.get('model_connected') else 'off'}; expected {'on' if expect_model else 'off'}")
    if not (ledger.get("ok") and ledger.get("append_only_for_this_role")):
        problems.append(f"ledger check failed: {ledger}")
    return problems


def check(base, expect_model):
    jar = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    code, _ = _call(base, "POST", "/api/v1/auth/login", body={"email": ANALYST, "password": PASSWORD}, opener=jar)
    if code != 200:
        return [f"sign-in as the analyst failed: {code} (a paused free database answers this way too)"]
    get = lambda path: _call(base, "GET", "/api/v1" + path, opener=jar)[1]  # noqa: E731
    briefing = get("/me/briefing")
    borrowers = {b["code"]: b["id"] for b in get("/borrowers")}
    thread = get(f"/threads/{borrowers['stripple-tech']}")
    drafts = get(f"/threads/{borrowers['lumora-health']}")
    question_open = any(m.get("type") == "ask" and m.get("status") == "open" for m in thread["messages"])
    draft_sent = any(m.get("type") == "draft" and m.get("sent_at") for m in drafts["messages"])
    return check_state(briefing=briefing, question_open=question_open, draft_sent=draft_sent,
                       model=get("/agents/status"), ledger=get("/ledger/verify"), expect_model=expect_model)


def _vercel(project_dir, *args, value=None):
    done = subprocess.run([*VERCEL, *args, "--token", "proxy-injected"], cwd=project_dir, text=True,
                          input=None if value is None else value + "\n", capture_output=True)
    if done.returncode:
        sys.exit(f"vercel {args[0]} {args[1]} failed: {(done.stderr or done.stdout)[-300:]}")


def run(base, project_dir):
    token = secrets.token_urlsafe(32)
    deploy = [str(ROOT / "scripts" / "hosted" / "deploy-v2.sh"), "--no-build"]
    _vercel(project_dir, "env", "add", "DEMO_SETUP_TOKEN", "production", value=token)
    try:
        subprocess.run(deploy, check=True)
        load(base, token)
    finally:
        _vercel(project_dir, "env", "rm", "DEMO_SETUP_TOKEN", "production", "--yes")
        subprocess.run(deploy, check=True)
    code, _ = _call(base, "GET", "/api/_setup/status", "anything")
    if code != 404:
        sys.exit(f"the setup routes still answer ({code}) after the token was removed")
    print("setup routes are off again (404)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "load", "check"))
    parser.add_argument("--base", required=True)
    parser.add_argument("--project-dir", default=str(ROOT / ".vercel-build-v2"))
    parser.add_argument("--expect-model", action="store_true")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    if args.command == "run":
        run(base, args.project_dir)
    elif args.command == "load":
        load(base, os.environ["DEMO_SETUP_TOKEN"])
    else:
        problems = check(base, args.expect_model)
        print("\n".join(problems) or "ready: the book is unused, agents as expected, ledger append-only")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Before relying on `check`, confirm the thread message shapes it reads (`type == "ask"` with `status`, `type == "draft"` with `sent_at`) against `backend/app/squad/` (the thread read model) and `frontend/src/squad/api/types.ts`; correct the two field names in `check` if they differ, and keep `check_state` (the tested part) unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest backend/tests/deploy/test_v2_setup.py -q && uv run ruff check scripts`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
uv run pytest backend/tests/deploy -q && \
git add scripts/hosted/v2_setup.py backend/tests/deploy/test_v2_setup.py && \
git commit -m "feat(p5): load v2 through the setup routes with a token that exists only while loading; check a book is unused" -- scripts/hosted/v2_setup.py backend/tests/deploy/test_v2_setup.py
```

---

### Task 5: With agents off, the composer says so before anyone types

**Files:**
- Modify: `frontend/src/squad/thread/Composer.tsx`
- Test: `frontend/src/squad/__tests__/composerOff.test.tsx`

**Interfaces:**
- Consumes: `useAgentsStatus()` from `@/api/hooks` → `{ data?: { model_connected: boolean; reason: string } }` (server words: "No model key is set for this deployment.").
- Produces: when `model_connected === false`, the textarea and Ask are disabled and the hint shows the server's `reason`; when the status is loading or connected, behaviour is unchanged.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/squad/__tests__/composerOff.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Composer } from '../thread/Composer';

const status = vi.hoisted(() => ({ data: undefined as undefined | { model_connected: boolean; reason: string } }));
vi.mock('@/api/hooks', () => ({ useAgentsStatus: () => ({ data: status.data }) }));
vi.mock('../api/hooks', () => ({ useAskCopilot: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
vi.mock('../presence/Presence', () => ({ usePresence: () => ({ beginWork: () => () => {}, pulse: () => {} }) }));

describe('Composer when the deployment has no model', () => {
  it('says why in the server words and offers no Ask', () => {
    status.data = { model_connected: false, reason: 'No model key is set for this deployment.' };
    render(<Composer borrowerId="b1" borrowerName="Stripple Tech" />);
    expect(screen.getByText('No model key is set for this deployment.')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /Ask Squad about Stripple Tech/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
  });

  it('is unchanged while the status loads or when the model is connected', () => {
    for (const data of [undefined, { model_connected: true, reason: '' }]) {
      status.data = data;
      const { unmount } = render(<Composer borrowerId={null} />);
      expect(screen.getByRole('textbox', { name: /whole portfolio/ })).toBeEnabled();
      expect(screen.getByText('Ctrl or Cmd + Enter to send')).toBeInTheDocument();
      unmount();
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/composerOff.test.tsx`
Expected: FAIL (the reason text is not found; the textbox is enabled).

- [ ] **Step 3: Write minimal implementation**

In `Composer.tsx` add `import { useAgentsStatus } from '@/api/hooks';`, then inside the component after `const ask = useAskCopilot();`:

```tsx
  const model = useAgentsStatus().data;
  const off = model?.model_connected === false; // unknown while loading: do not block
```

Change the textarea to add `disabled={off}`, the hint to `{off ? model?.reason : 'Ctrl or Cmd + Enter to send'}`, and the button to `disabled={off || !text.trim() || ask.isPending}`. The reason is the server's text, so no new words table is added in the browser (label-table guard).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm vitest run src/squad/__tests__/composerOff.test.tsx && pnpm vitest run && pnpm typecheck && pnpm lint && pnpm build`
Expected: the new tests PASS; the whole vitest suite passes (the other Composer users mock `Composer` or `@/api/hooks`; if one fails because its `@/api/hooks` mock lacks `useAgentsStatus`, add `useAgentsStatus: () => ({ data: undefined })` to that mock and say which files changed).

- [ ] **Step 5: Commit**

```bash
cd frontend && pnpm vitest run && pnpm typecheck && cd .. && \
git add frontend/src/squad/thread/Composer.tsx frontend/src/squad/__tests__/composerOff.test.tsx && \
git commit -m "feat(p5): with no model on the deployment the composer says so before anyone types" -- frontend/src/squad/thread/Composer.tsx frontend/src/squad/__tests__/composerOff.test.tsx
```
(Add any test file whose mock needed `useAgentsStatus` to both path lists.)

---

### Task 6: A smoke test for any deployment

**Files:**
- Create: `frontend/e2e/hosted-smoke.mjs`
- Modify: `frontend/package.json` (script `"e2e:smoke": "node e2e/hosted-smoke.mjs"`)

**Interfaces:**
- Consumes: `BASE_URL` (required, no default), `EXPECT_MODEL` (`off` default | `on`), `HANDOFF=1` (also run the Approvals hand-off, which writes), `SQUAD_DEMO_PASSWORD` (default `squad-demo`). API: `/api/v1/auth/login`, `/borrowers`, `/borrowers/{id}/documents`, `/documents/{id}/file`, `/ledger/verify`, `/agents/status`, `/me/briefing`.
- Produces: exit 0 only when every check passes; prints `PASS`/`FAIL` lines and a `TIMINGS` JSON line (`/me/briefing` milliseconds per call for analyst and officer); saves a failure screenshot under `frontend/e2e/failures/` (git-ignored); writes the fetched PDF to `$SMOKE_OUT` (default `/tmp/claude-0/hosted-smoke`, outside the repo). No Playwright tracing is started and no video is recorded (the equivalent of `--trace off`).

- [ ] **Step 1: Write the script**

```js
// frontend/e2e/hosted-smoke.mjs
// Smoke test for a deployment: sign-in for every demo role, every Squad screen per role with no failed
// request, a source PDF, the ledger check, agents on/off as expected, setup routes hidden, and (HANDOFF=1)
// the Approvals hand-off. Usage: BASE_URL=https://<host> pnpm e2e:smoke
// No tracing, no video: nothing about the session is kept except failure screenshots.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL;
if (!BASE) { console.error('set BASE_URL'); process.exit(2); }
const PASSWORD = process.env.SQUAD_DEMO_PASSWORD ?? 'squad-demo';
const EXPECT_MODEL = (process.env.EXPECT_MODEL ?? 'off') === 'on';
const OUT = process.env.SMOKE_OUT ?? '/tmp/claude-0/hosted-smoke';
const failuresDir = resolve(dirname(fileURLToPath(import.meta.url)), 'failures');
const ROLES = [
  ['analyst', 'priya.raman@bankofstoic.example'], ['analyst', 'tomas.keller@bankofstoic.example'],
  ['manager', 'dana.whitfield@bankofstoic.example'], ['manager', 'marcus.oyelaran@bankofstoic.example'],
  ['officer', 'helen.strand@bankofstoic.example'], ['admin_credit', 'li.zhang@bankofstoic.example'],
  ['admin_credit', 'omar.haddad@bankofstoic.example'], ['review', 'ruth.calloway@bankofstoic.example'],
  ['admin', 'admin@bankofstoic.example'],
];
let failed = 0;
const check = (ok, name, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : `  ${detail}`}`); if (!ok) failed += 1; };

function screens(kind, code) {
  if (kind === 'admin') return ['/', '/oversight', '/oversight/activity', '/oversight/ledger', '/oversight/governance', '/oversight/evaluations', '/oversight/clock'];
  const views = ['', '/spreads', '/covenants', '/documents', '/funding', '/loans', '/reviews', '/packages', '/runs', '/history'];
  const shared = ['/', `/clients/${code}`, ...views.map((v) => `/clients/${code}/file${v}`), '/portfolio', '/review-room'];
  return kind === 'officer' ? [...shared, '/approvals'] : shared;
}

async function signIn(browser, email) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const bad = [];
  page.on('requestfailed', (r) => bad.push(`${r.method()} ${r.url()} ${r.failure()?.errorText}`));
  page.on('response', (r) => { if (r.url().startsWith(BASE) && r.status() >= 400) bad.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
  await page.goto(`${BASE}/sign-in`);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(`${BASE}/`, { timeout: 60_000 });
  return { context, page, bad };
}
const api = async (page, path, init) => { const r = await page.request.fetch(`${BASE}/api/v1${path}`, init); return { status: r.status(), body: r.headers()['content-type']?.includes('json') ? await r.json() : await r.body(), headers: r.headers() }; };

const browser = await chromium.launch({ headless: true });
mkdirSync(failuresDir, { recursive: true });
mkdirSync(OUT, { recursive: true });
const timings = {};

// unauthenticated surface
{
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  check((await p.request.get(`${BASE}/api/_setup/status`)).status() === 404, 'setup routes are hidden without the token');
  check((await p.request.get(`${BASE}/api/v1/me/briefing`)).status() === 401, 'the API refuses a person who has not signed in');
  for (const path of ['/docs', '/openapi.json']) check((await p.request.get(`${BASE}${path}`)).status() === 404 || !(await p.request.get(`${BASE}${path}`)).headers()['content-type']?.includes('json'), `${path} is not served`);
  await ctx.close();
}

for (const [kind, email] of ROLES) {
  const { context, page, bad } = await signIn(browser, email);
  try {
    const cookie = (await context.cookies()).find((c) => c.httpOnly);
    check(Boolean(cookie?.secure), `${email}: session cookie is Secure and HttpOnly`);
    const borrowers = (await api(page, '/borrowers')).body;
    check(Array.isArray(borrowers) && borrowers.length === 20, `${email}: 20 clients`, `${borrowers?.length}`);
    // one innovation client and one kept C&I client, so both templates' screens load
    for (const code of ['stripple-tech', 'kestrel-bay-packaging']) {
      if (kind === 'admin' && code !== 'stripple-tech') continue;
      for (const path of screens(kind, code)) {
        await page.goto(`${BASE}${path}`);
        await page.waitForLoadState('networkidle', { timeout: 60_000 });
        check((await page.locator('h1').count()) > 0, `${email} ${path}: has a heading`);
      }
    }
    check(bad.length === 0, `${email}: no failed request on any screen`, bad.slice(0, 5).join(' | '));
    if (kind === 'analyst' || kind === 'officer') {
      timings[email] = [];
      for (let i = 0; i < 5; i += 1) { const t = Date.now(); await api(page, '/me/briefing'); timings[email].push(Date.now() - t); }
    }
    if (email.startsWith('priya')) {
      const id = borrowers.find((b) => b.code === 'stripple-tech').id;
      const docs = (await api(page, `/borrowers/${id}/documents`)).body;
      const pdf = await api(page, `/documents/${docs[0].id}/file`);
      const bytes = Buffer.from(pdf.body);
      check(pdf.status === 200 && pdf.headers['content-type']?.includes('pdf') && bytes.subarray(0, 5).toString() === '%PDF-', 'a source PDF is served');
      writeFileSync(resolve(OUT, 'source.pdf'), bytes);
      const ledger = (await api(page, '/ledger/verify')).body;
      check(ledger.ok === true && ledger.append_only_for_this_role === true, 'ledger verifies and is append-only for this role', JSON.stringify(ledger));
      const model = (await api(page, '/agents/status')).body;
      check(model.model_connected === EXPECT_MODEL, `agents are ${EXPECT_MODEL ? 'on' : 'off'}`, JSON.stringify(model));
    }
  } catch (error) {
    check(false, `${email}: walk`, error.message);
    await page.screenshot({ path: resolve(failuresDir, `smoke-${email.split('@')[0]}.png`) }).catch(() => {});
  }
  await context.close();
}

if (process.env.HANDOFF === '1') {
  // Writes: Priya routes a covenant case to Helen with her view; Helen sees it in Approvals and returns it;
  // Priya sees the return in the same thread. Run only on a book that will be rebuilt afterwards (Task 12).
  const a = await signIn(browser, 'priya.raman@bankofstoic.example');
  const o = await signIn(browser, 'helen.strand@bankofstoic.example');
  try {
    const item = (await api(a.page, '/me/briefing')).body.items.find((i) => i.needs_you && String(i.item_type).startsWith('covenant'));
    await a.page.goto(`${BASE}/clients/${item.borrower_code}?case=${item.work_item_id}`);
    const card = a.page.locator('[data-case-focus]').first();
    await card.getByLabel(/your view/i).fill('Smoke test: the breach is confirmed on the certificate; please decide.');
    const value = await card.locator('select option', { hasText: 'Helen Strand' }).first().getAttribute('value');
    await card.getByLabel('Send to').selectOption(value);
    await card.getByRole('button', { name: /^Send to / }).click();
    await o.page.goto(`${BASE}/approvals`);
    await o.page.getByRole('list', { name: 'Decisions waiting' }).getByText(item.borrower_name).first().waitFor({ timeout: 30_000 });
    check(true, 'Approvals: the routed case reaches the officer');
  } catch (error) {
    check(false, 'Approvals hand-off', error.message);
    await a.page.screenshot({ path: resolve(failuresDir, 'smoke-handoff.png') }).catch(() => {});
  }
  await a.context.close();
  await o.context.close();
}

console.log(`TIMINGS ${JSON.stringify(timings)}`);
await browser.close();
process.exit(failed ? 1 : 0);
```

The hand-off selectors (`[data-case-focus]`, "your view" label) must be the ones `frontend/e2e/squad.mjs` uses in its hand-off journey (lines 316-381): copy them from there exactly before the first run; that journey is the reference.

- [ ] **Step 2: Run it locally against a fresh seed and see it pass**

```bash
service postgresql start
createdb -h localhost -U squad p5_smoke 2>/dev/null || true
export DATABASE_URL=postgresql+psycopg://squad:squad@localhost:5432/p5_smoke
(cd backend && uv run alembic -x url="$DATABASE_URL" upgrade head) && \
PYTHONPATH=backend uv run python -m app.seed_book && PYTHONPATH=backend uv run python -m app.squad_demo
PYTHONPATH=backend uv run uvicorn app.main:app --port 8000 &   # API
(cd frontend && pnpm dev) &                                     # workspace on 5173
cd frontend && BASE_URL=http://localhost:5173 pnpm e2e:smoke; echo "exit $?"
```
Expected: every line PASS except, possibly, the Secure-cookie line: with `SQUAD_ENV=local` the API sends a cookie without `Secure`. That one FAIL is expected locally (say so in the report); it must PASS on the hosted run (Task 11). Then `HANDOFF=1 BASE_URL=http://localhost:5173 pnpm e2e:smoke` → the hand-off PASS. Also `uv run python -I -c "import fitz,sys; t=''.join(p.get_text() for p in fitz.open('/tmp/claude-0/hosted-smoke/source.pdf')); sys.exit(0 if 'SYNTHETIC - FOR DEMONSTRATION' in t else 1)"` → exit 0. Drop the database afterwards: `dropdb -h localhost -U squad p5_smoke`.

- [ ] **Step 3: Commit**

```bash
cd frontend && node --check e2e/hosted-smoke.mjs && cd .. && \
git add frontend/e2e/hosted-smoke.mjs frontend/package.json && \
git commit -m "test(p5): a smoke test for any deployment: every role, every screen, a source PDF, the ledger, the hand-off" -- frontend/e2e/hosted-smoke.mjs frontend/package.json
```

---

### Task 7: Dress rehearsal: the exact v2 build, its trimmed packages, three roles, on local PostgreSQL

Proves the function starts with only `deploy/vercel/requirements.txt` (v2 code has grown since v1's build), the setup routes load all 20 clients one per call inside 300 s each, and the serving login is append-only. No network service is touched.

**Files:** none committed unless a defect is found (then fix it in its own commit with a test, e.g. a package missing from `deploy/vercel/requirements.txt`, pinned to the version in `uv.lock`).

- [ ] **Step 1: Build and install the function's packages in a clean virtual environment**

```bash
./scripts/build-vercel.sh --target v2
R=/tmp/claude-0/p5-rehearsal && rm -rf $R && mkdir -p $R
uv venv $R/venv --python 3.12 && uv pip install --python $R/venv/bin/python -r .vercel-build-v2/requirements.txt
du -sh .vercel-build-v2 $R/venv/lib/python3.12/site-packages
```
Expected: installs; sizes printed (the function's bundle must stay under Vercel's 250 MB unzipped limit: record both numbers).

- [ ] **Step 2: Create the three roles and an empty database locally (throwaway passwords in this shell only)**

```bash
P_OWNER=$(openssl rand -hex 16); P_WEB=$(openssl rand -hex 16)
sudo -u postgres psql -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE p5_rehearsal" \
  -c "CREATE ROLE squad2_runtime NOLOGIN" \
  -c "CREATE ROLE squad2_app LOGIN PASSWORD '$P_OWNER'" \
  -c "CREATE ROLE squad2_web LOGIN PASSWORD '$P_WEB'" \
  -c "GRANT squad2_runtime TO squad2_web" \
  -c "GRANT CREATE ON DATABASE p5_rehearsal TO squad2_app"
```
(Local roles of the same names do not touch Supabase. Drop them in Step 5.)

- [ ] **Step 3: Start the built function and load it through the setup routes**

```bash
export DEMO_SETUP_TOKEN=$(openssl rand -hex 24) SQUAD_ENV=production EXTRACTION_AUTONOMY=assisted \
  DB_SCHEMA=squad2 DB_RUNTIME_ROLE=squad2_runtime DB_POOL=null SQUAD_LLM_MODE=live SESSION_SECRET=$(openssl rand -hex 32) \
  MIGRATION_DATABASE_URL="postgresql+psycopg://squad2_app:$P_OWNER@localhost:5432/p5_rehearsal" \
  DATABASE_URL="postgresql+psycopg://squad2_web:$P_WEB@localhost:5432/p5_rehearsal"
unset ANTHROPIC_API_KEY SQUAD_ANTHROPIC_API_KEY
(cd .vercel-build-v2 && $R/venv/bin/python -m uvicorn api.index:app --port 8010) &
sleep 5; uv run python scripts/hosted/v2_setup.py load --base http://localhost:8010
```
Expected: `migrate` 200; 20 `seed <code>: 200 now` lines, each well under 300 s (record the slowest); squad demo 200; final status `users 9, book_borrowers 20, target v2, schema squad2`. If the start fails with `ModuleNotFoundError`, that package is missing from `deploy/vercel/requirements.txt`: add it pinned to `uv.lock`'s version, rebuild, repeat.

- [ ] **Step 4: Check the roles, then the smoke test and the read-only journeys against the built app**

```bash
sudo -u postgres psql -d p5_rehearsal -Atc "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='squad2'; SELECT has_table_privilege('squad2_web','squad2.ledger_events','UPDATE'), has_table_privilege('squad2_web','squad2.ledger_events','INSERT')"
```
Expected: `squad2_app`, then `f|t`.

The built app serves `public/` only on Vercel; locally the workspace dev server proxies `/api` to the built function (`frontend/vite.config.ts` reads `PORT` and `API_TARGET`): `(cd frontend && PORT=5174 API_TARGET=http://localhost:8010 pnpm dev) &`. Then:

```bash
cd frontend && BASE_URL=http://localhost:5174 pnpm e2e:smoke
BASE_URL=http://localhost:5174 ONLY='^(?!(Squad asks|drafts|hand-off|review room))' pnpm e2e:squad
```
Expected: smoke PASS (this server runs with `SQUAD_ENV=production`, so the cookie is Secure; Chromium accepts it on `localhost`; report the line either way); every read-only journey PASS. Record the `TIMINGS` line. Then print the analyst's open covenant cases for the session script (Task 15): `curl -s -c $R/jar -H 'Content-Type: application/json' -d '{"email":"priya.raman@bankofstoic.example","password":"squad-demo"}' http://localhost:8010/api/v1/auth/login >/dev/null && curl -s -b $R/jar http://localhost:8010/api/v1/me/briefing | jq -r '.items[] | select(.needs_you) | [.borrower_name, .item_type, .title] | @tsv'` and keep the output in `$R/priya-briefing.tsv`.

- [ ] **Step 5: Clean up**

```bash
kill %1 %2 %3 2>/dev/null; unset P_OWNER P_WEB DEMO_SETUP_TOKEN SESSION_SECRET MIGRATION_DATABASE_URL DATABASE_URL
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "DROP DATABASE p5_rehearsal" -c "DROP ROLE squad2_web" -c "DROP ROLE squad2_app" -c "DROP ROLE squad2_runtime"
```
Report: package sizes, slowest seed call, timings, journeys passed. No commit unless a defect was fixed.

---

### Task 8: Baseline of the two frozen sites and of schema `squad` (controller session)

**Files:**
- Create: `scripts/hosted/frozen_check.py`
- Baselines (not committed, not secret): `var/hosted/frozen-before.json`, `var/hosted/squad-before.json` (`var/` is git-ignored)

**Interfaces:**
- Produces: `python scripts/hosted/frozen_check.py capture <out.json>`; `python scripts/hosted/frozen_check.py compare <before.json> <after.json>` (exit 1 and a list on any difference). Captured: for `https://c-squad.vercel.app/`, `https://csquad-kappa.vercel.app/` and `https://credit-agent-squad.vercel.app/`, the HTTP status and SHA-256 of `/` and of every `/assets/...` file it references; for credit-agent-squad also the status of `/api/_setup/status` (expect 404) and of `/api/v1/me/briefing` unauthenticated (expect 401); for Vercel projects `csquad` and `credit-agent-squad` (REST API, read-only, through the proxy): `id`, `name`, `updatedAt`, production deployment id, and the environment variables as `{key, target, type, updatedAt}` with **no value field** (never `decrypt=true`).

- [ ] **Step 1: Write the script and its unit test**

```python
# scripts/hosted/frozen_check.py
"""Record and compare what the frozen sites serve and how their Vercel projects are set, without
calling anything billable (c-squad's /api is never called) and without reading any secret value."""
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request

SITES = ["https://c-squad.vercel.app", "https://csquad-kappa.vercel.app", "https://credit-agent-squad.vercel.app"]
PROBES = {"https://credit-agent-squad.vercel.app": ["/api/_setup/status", "/api/v1/me/briefing"]}
PROJECTS = ["csquad", "credit-agent-squad"]


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""


def site(base):
    status, body = fetch(base + "/")
    out = {"/": [status, hashlib.sha256(body).hexdigest()]}
    for asset in sorted(set(re.findall(rb'(?:src|href)="(/assets/[^"]+)"', body))):
        s, b = fetch(base + asset.decode())
        out[asset.decode()] = [s, hashlib.sha256(b).hexdigest()]
    for path in PROBES.get(base, []):
        out[path] = [fetch(base + path)[0]]
    return out


def project(name):
    with urllib.request.urlopen(f"https://api.vercel.com/v9/projects/{name}", timeout=30) as response:
        p = json.load(response)
    with urllib.request.urlopen(f"https://api.vercel.com/v10/projects/{name}/env", timeout=30) as response:
        envs = json.load(response).get("envs", [])
    return {"id": p["id"], "name": p["name"], "updatedAt": p.get("updatedAt"),
            "production": (p.get("targets") or {}).get("production", {}).get("id"),
            "env": sorted(({k: e.get(k) for k in ("key", "target", "type", "updatedAt")} for e in envs),
                          key=lambda e: (e["key"], str(e["target"])))}


def capture():
    return {"sites": {s: site(s) for s in SITES}, "projects": {p: project(p) for p in PROJECTS}}


def differences(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        found = []
        for key in sorted(set(before) | set(after)):
            found += differences(before.get(key), after.get(key), f"{path}/{key}")
        return found
    return [] if before == after else [f"{path}: {before!r} -> {after!r}"]


if __name__ == "__main__":
    if sys.argv[1] == "capture":
        open(sys.argv[2], "w").write(json.dumps(capture(), indent=1, sort_keys=True))
    else:
        found = differences(json.load(open(sys.argv[2])), json.load(open(sys.argv[3])))
        print("\n".join(found) or "unchanged")
        sys.exit(1 if found else 0)
```

Add `backend/tests/deploy/test_frozen_check.py` with one test: `differences({"a": {"b": 1}}, {"a": {"b": 2}, "c": 3})` returns `["/a/b: 1 -> 2", "/c: None -> 3"]`, and `differences(x, x) == []`.

- [ ] **Step 2: Capture twice and compare (proves the capture is stable)**

```bash
mkdir -p var/hosted
uv run python -I scripts/hosted/frozen_check.py capture var/hosted/frozen-before.json && sleep 60 && \
uv run python -I scripts/hosted/frozen_check.py capture var/hosted/frozen-probe.json && \
uv run python -I scripts/hosted/frozen_check.py compare var/hosted/frozen-before.json var/hosted/frozen-probe.json
grep -c '"value"' var/hosted/frozen-before.json   # must print 0
```
Expected: `unchanged`; `0`. If something differs between two captures a minute apart (for example an asset served with a varying body), drop only that field from the capture, say which and why, and capture again.

- [ ] **Step 3: Baseline schema `squad` with the Supabase MCP tool `execute_sql` (SELECT only; controller)**

Run each statement and save the result rows into `var/hosted/squad-before.json` as `{"columns": ..., "alembic": ..., "grants": ..., "triggers": ..., "members": ..., "head": ...}`:

```sql
SELECT md5(string_agg(table_name||'.'||column_name||':'||data_type||':'||is_nullable, ',' ORDER BY table_name, ordinal_position)) AS columns FROM information_schema.columns WHERE table_schema = 'squad';
SELECT version_num FROM squad.alembic_version;
SELECT md5(string_agg(grantee||':'||table_name||':'||privilege_type, ',' ORDER BY grantee, table_name, privilege_type)) AS grants FROM information_schema.role_table_grants WHERE table_schema = 'squad';
SELECT string_agg(tgname, ',' ORDER BY tgname) AS triggers FROM pg_trigger WHERE tgrelid = 'squad.ledger_events'::regclass AND NOT tgisinternal;
SELECT string_agg(r.rolname||'>'||m.rolname, ',' ORDER BY r.rolname, m.rolname) AS members FROM pg_auth_members a JOIN pg_roles r ON r.oid = a.roleid JOIN pg_roles m ON m.oid = a.member WHERE r.rolname LIKE 'squad%' OR m.rolname LIKE 'squad%';
SELECT seq, hash FROM squad.ledger_events ORDER BY seq DESC LIMIT 1;
SELECT rolname FROM pg_roles WHERE rolname LIKE 'squad2%';
SELECT nspname FROM pg_namespace WHERE nspname = 'squad2';
```
Expected: the last two return no rows (nothing of v2 exists yet). If either returns a row, stop and ask the owner.

- [ ] **Step 4: Commit the script and test**

```bash
uv run pytest backend/tests/deploy/test_frozen_check.py -q && \
git add scripts/hosted/frozen_check.py backend/tests/deploy/test_frozen_check.py && \
git commit -m "test(p5): record and compare the frozen sites by content hash and project metadata, values never read" -- scripts/hosted/frozen_check.py backend/tests/deploy/test_frozen_check.py
```

---

### Task 9: The Vercel project, its link, and the v2 roles (controller session)

Owner steps O-2 (project name) and O-3 (pooler host) must be answered first.

- [ ] **Step 1: Create the project and link a fresh v2 build to it**

```bash
export VERCEL_TELEMETRY_DISABLED=1 V2_PROJECT=credit-squad   # owner question 3
curl -s -o /dev/null -w "%{http_code}\n" https://api.vercel.com/v9/projects/$V2_PROJECT   # must print 404 (no such project yet)
npx --yes vercel@66.0.0 project add "$V2_PROJECT" --token proxy-injected
./scripts/build-vercel.sh --target v2
(cd .vercel-build-v2 && npx --yes vercel@66.0.0 link --yes --project "$V2_PROJECT" --token proxy-injected >/dev/null) && \
uv run python -I scripts/hosted/check_link.py .vercel-build-v2 "$V2_PROJECT"
```
Expected: 404 first (if 200, the name is taken in this account: stop and ask); then `linked to credit-squad: ok`. A 401/403 from any call: stop, owner step O-1.

- [ ] **Step 2: Put the plain variables on the project**

```bash
cd .vercel-build-v2 && for kv in SQUAD_ENV=production EXTRACTION_AUTONOMY=assisted DB_SCHEMA=squad2 DB_RUNTIME_ROLE=squad2_runtime DB_POOL=null SQUAD_LLM_MODE=live; do
  printf '%s\n' "${kv#*=}" | npx --yes vercel@66.0.0 env add "${kv%%=*}" production --token proxy-injected >/dev/null || exit 1; done; cd ..
```

- [ ] **Step 3: Make the passwords and the role SQL in one process**

```bash
uv run python -I scripts/hosted/v2_secrets.py --project-dir .vercel-build-v2 --ref tkeoiengqvxywmqzdxes --pooler-host "<host from owner step O-3>"
```
Expected: five lines of SQL with two `SCRAM-SHA-256$...` verifiers, nothing else. The output goes straight into the next step; it is not saved.

- [ ] **Step 4: Create the roles with the Supabase MCP tool `execute_sql`**

Pass the printed SQL as one `execute_sql` call (project `tkeoiengqvxywmqzdxes`). If `GRANT CREATE ON DATABASE postgres TO squad2_app` is refused, run instead `CREATE SCHEMA squad2 AUTHORIZATION squad2_app;` (if that is refused too, first `GRANT squad2_app TO postgres;`, then the CREATE SCHEMA, then `REVOKE squad2_app FROM postgres;`), and say which path was taken.

Then check, SELECT only:

```sql
SELECT r.rolname, r.rolcanlogin, r.rolsuper, r.rolcreaterole,
       pg_has_role(r.rolname, 'squad_runtime', 'MEMBER') AS in_v1_runtime,
       has_schema_privilege(r.rolname, 'squad', 'USAGE') AS v1_schema_usage
FROM pg_roles r WHERE r.rolname IN ('squad2_app', 'squad2_web', 'squad2_runtime') ORDER BY 1;
SELECT pg_has_role('squad2_web', 'squad2_runtime', 'MEMBER') AS web_in_runtime, pg_has_role('squad2_web', 'squad2_app', 'MEMBER') AS web_is_owner;
```
Expected: three rows, only the two logins `rolcanlogin`, every `rolsuper`, `rolcreaterole`, `in_v1_runtime`, `v1_schema_usage` false; `web_in_runtime` true, `web_is_owner` false.

- [ ] **Step 5: Record**

Note in the session log (not the repo): project name, whether `credit-squad.vercel.app` or a suffixed alias was assigned (read in Task 10), the path taken in Step 4. Nothing to commit.

---

### Task 10: Deploy, load the book, and turn the setup routes off (controller session)

- [ ] **Step 1: First deploy and the production address**

```bash
./scripts/hosted/deploy-v2.sh --no-build
curl -s https://api.vercel.com/v9/projects/$V2_PROJECT | jq -r '.alias[]?.domain // empty, .targets.production.alias[]? // empty' | sort -u
```
Expected: the deploy prints a production URL for `$V2_PROJECT` (never `credit-agent-squad` or `csquad`); the alias list gives the production host. Set `V2=https://<that host>` for the rest of the phase.

- [ ] **Step 2: Load through the setup routes**

```bash
uv run python -I scripts/hosted/v2_setup.py run --base "$V2" --project-dir .vercel-build-v2
```
Expected: migrate 200, 20 seed lines 200, squad demo 200, final status `users 9, book_borrowers 20, target v2, schema squad2`, then `setup routes are off again (404)`. If `/api/_setup/status` reports `migrated: false` with a host reason ("tenant or user not found", a DNS error), the pooler host is wrong: rerun Task 9 Steps 3–4 with the corrected host using `--alter` (new passwords, `ALTER ROLE`), then this step. Never print or edit the URL by hand.

- [ ] **Step 3: Check the result in the database (SELECT only, MCP)**

```sql
SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = 'squad2';
SELECT (SELECT count(*) FROM squad2.borrowers) AS borrowers, (SELECT count(*) FROM squad2.users) AS users, (SELECT version_num FROM squad2.alembic_version) AS alembic;
SELECT has_table_privilege('squad2_runtime', 'squad2.ledger_events', 'UPDATE') AS may_update, has_table_privilege('squad2_runtime', 'squad2.ledger_events', 'INSERT') AS may_insert, has_schema_privilege('squad_runtime', 'squad2', 'USAGE') AS v1_runtime_sees_v2, has_schema_privilege('squad_web', 'squad2', 'USAGE') AS v1_web_sees_v2;
```
Expected: `squad2_app`; 20, 9, head revision (`0005` or later); `f, t, f, f`.

---

### Task 11: Hosted smoke test and the read-only journeys

- [ ] **Step 1: Smoke**

```bash
cd frontend && BASE_URL="$V2" EXPECT_MODEL=off pnpm e2e:smoke 2>&1 | tee /tmp/claude-0/p5-smoke.txt; echo "exit ${PIPESTATUS[0]}"
uv run python -I -c "import fitz,sys; t=''.join(p.get_text() for p in fitz.open('/tmp/claude-0/hosted-smoke/source.pdf')); print('marker', 'SYNTHETIC - FOR DEMONSTRATION' in t)"
```
Expected: exit 0, every line PASS (the Secure-cookie line included, since this is HTTPS); `marker True`. Keep the `TIMINGS` line for the report (Review Focus 5: warm calls over 3 s are a finding for Task 16's triage, not a stop).

- [ ] **Step 2: The 4b journeys that only read**

```bash
cd frontend && BASE_URL="$V2" ONLY='^(?!(Squad asks|drafts|hand-off|review room))' pnpm e2e:squad
```
Expected: every selected journey PASS (24 of the 28; the four excluded write). A timeout on a cold start is retried once alone (`ONLY='<name>'`); report both runs.

- [ ] **Step 3: Phone and tablet widths (measured, reported, not fixed)**

Using the analyst's screens list from `hosted-smoke.mjs`, measure `document.documentElement.scrollWidth - clientWidth` at 390 and 820 px with a short Playwright snippet run from the scratchpad (not committed), and list each screen with a non-zero value in the HANDOFF update (Task 14) as a known limit (`docs/lessons/look-at-it-on-the-owners-screen.md`).

---

### Task 12: The writing journeys, then a fresh book (gated on owner question 2)

- [ ] **Step 1 (only with owner question 2 answered "yes"): run what writes**

```bash
cd frontend && BASE_URL="$V2" HANDOFF=1 pnpm e2e:smoke && BASE_URL="$V2" ONLY='^(Squad asks|drafts|hand-off|review room)' pnpm e2e:squad
```
Expected: hand-off PASS; the four journeys PASS.

If the owner answered "no": skip this step; the writing journeys stay verified on local fresh seeds only (Phase 4b gates and Task 7); say so in the report.

- [ ] **Step 2: Keep the record, then rebuild `squad2` (controller, MCP; only with "yes")**

Export the ledger first (synthetic data; the record of what was done is kept):

```sql
SELECT json_agg(e ORDER BY e.seq) FROM squad2.ledger_events e;
```
Save the result as `docs/product/usability/ledger/2026-11-smoke.json` (commit it with Task 15's files). Then:

```sql
DROP SCHEMA squad2 CASCADE;
```
and rerun Task 10 Step 2 (`v2_setup.py run`). The roles, the project and its variables are unchanged.

- [ ] **Step 3: Confirm the book is fresh**

```bash
uv run python -I scripts/hosted/v2_setup.py check --base "$V2"
```
Expected: `ready: the book is unused, agents as expected, ledger append-only`.

---

### Task 13: After-check of the frozen sites and of `squad`

- [ ] **Step 1: Sites and projects**

```bash
uv run python -I scripts/hosted/frozen_check.py capture var/hosted/frozen-after.json && \
uv run python -I scripts/hosted/frozen_check.py compare var/hosted/frozen-before.json var/hosted/frozen-after.json
```
Expected: `unchanged`. Any difference: stop, do not "fix" either frozen project, report to the owner with the difference lines.

- [ ] **Step 2: Schema `squad` (MCP, SELECT only)**

Rerun the first five statements of Task 8 Step 3 and compare with `var/hosted/squad-before.json`: `columns`, `alembic`, `grants`, `triggers` equal; `members` equal except for the two new lines `squad2_runtime>squad2_web` (and `squad2_app>postgres` only if Task 9 Step 4 needed it and it was revoked: then it must be absent). For the ledger, v1 is live and its sign-ins append events, so check the old head instead:

```sql
SELECT hash FROM squad.ledger_events WHERE seq = <seq from squad-before.json>;
```
Expected: the stored hash; and `max(seq)` is greater than or equal to the stored one.

- [ ] **Step 3: Report** both checks with their outputs in the session report.

---

### Task 14: Documentation of the hosted v2

**Files:**
- Modify: `docs/DEPLOY.md` (new section "v2: Credit Squad on `squad2`" above "Frozen: the clickable demo")
- Modify: `docs/HANDOFF.md` (Phase 5 row and a "Phase 5 hosted" block)

- [ ] **Step 1: Write the DEPLOY section** with: the address; project name; schema `squad2`; the three roles and what each may do; "deploy only with `scripts/hosted/deploy-v2.sh`"; "load only with `scripts/hosted/v2_setup.py run`"; agents off (no key) and how they are turned on (Task 17); "before a session: `v2_setup.py check`"; reset (Task 12 Step 2) and that it needs the owner's yes; the free-tier pause (a paused Supabase project makes sign-in fail; the owner restores it from the dashboard); variables by name only; the measured seed time and briefing timings. Change "PostgreSQL 16" to the observed "PostgreSQL 17" where the Supabase project is described.

- [ ] **Step 2: Update HANDOFF** Phase 5 row (deployed, smoke results, journeys passed, frozen checks unchanged, what is not verified: phone/tablet widths, live agents).

- [ ] **Step 3: Commit**

```bash
git add docs/DEPLOY.md docs/HANDOFF.md && git commit -m "docs(p5): hosted v2 on its own project and schema; how to deploy, load, check and reset it" -- docs/DEPLOY.md docs/HANDOFF.md
```

---

### Task 15: The usability session kit

**Files:**
- Create: `docs/product/usability/consent-note.md`, `docs/product/usability/facilitator-script.md`, `docs/product/usability/observation-sheet.md`, `docs/product/usability/session-log.md`
- Create: `docs/product/v2-usability-findings.md`

- [ ] **Step 1: Consent and introduction note** (read aloud and handed over; one page). Content, in plain words:
  - What this is: a test of a prototype lending tool, Credit Squad, by its builder; it is the product being tested, not the participant.
  - **All data is synthetic**: the bank (Bank of Stoic), every client, person, figure and document is invented for demonstration; every document is stamped `SYNTHETIC - FOR DEMONSTRATION`. Do not type real client, bank or personal information anywhere in it.
  - The demo sign-in details are shared test accounts; nothing entered is private.
  - Agents are switched off on this copy unless the owner decides otherwise (Task 17): Squad's earlier work is already loaded; asking Squad a new question shows that questions are off. (Replace this line if agents are on.)
  - What is recorded: written notes by the note-taker; screen or audio recording only with a separate yes (owner question 5); the participant's name is not written in the notes (participant code P1–P5).
  - About 60 minutes; stop or skip any task at any time; no right answers; think aloud.
  - How notes are used: to find problems in the product; quotes are anonymous.
  - Signature or spoken yes, date, participant code.

- [ ] **Step 2: Facilitator script** with: before-session checklist (laptop or desktop, browser at least 1000 px wide, `v2_setup.py check` printed `ready` within the hour, both browsers signed out, facilitator's own window signed in as Helen Strand for the analyst sessions, timer); introduction (read the consent note); warm-up questions (role, years, tools used today for monitoring, what a morning looks like); tasks; debrief questions (what was easiest, hardest, what you expected and did not find, would you trust a figure here and why, one thing to change); after-session steps (save sheet, `session-log.md` line, then reset if approved).

  **Analyst tasks (P1–P4, signed in as `priya.raman@bankofstoic.example`, password `squad-demo`):** one line of scenario each, the success criterion the observer marks, and no hints on where to click. Client names come from Task 7's `priya-briefing.tsv` (the analyst's open covenant cases on a fresh book); write them into the script.

  | # | Area | Task as read to the participant | Success when |
  |---|---|---|---|
  | A1 | Briefing | "It is your morning. What does Squad say needs you, and which would you deal with first? Why?" | names the top item and a reason from the screen |
  | A2 | Thread | "Open Stripple Tech. What arrived this month, and is anything held back?" | finds the October documents and the held spreadsheet |
  | A3 | Squad asks | "Squad has a question for you about Stripple. Answer it, and make Squad remember your answer." | answers with Remember; sees it recorded with her name |
  | A4 | Ask Squad | "Ask Squad something you would want to know about this client." | asks; (agents off) reads why questions are off; note what they expected |
  | A5 | Evidence | "Dataflake's runway: where does that figure come from? Show me the page." | opens the source beside the thread and points at the figure |
  | A6 | Draft | "Lumora's package is late. Squad drafted a reminder. Change it as you like and send it." | edits and sends; says what "sent" means here |
  | A7 | Approvals, route | "<client from the TSV> has a covenant case. Decide what you think and send it to the credit officer with your view." | routes to Helen with a view |
  | A8 | Return with gathering | (facilitator, as Helen, returns A7 asking for the signed term sheet) "The officer sent it back. Do what she asks and send it back." | sees the return in the same thread, attaches what was asked, sends back |
  | A9 | Client file | "Find Corvane's covenant results and its documents for October." | reaches Covenants and Documents views |
  | A10 | Portfolio | "Which of your clients has the shortest runway? Open its conversation." | uses My Portfolio; opens the right thread |
  | A11 | Review room | "There is a portfolio review. Find what you are asked to prepare." | finds the review room and her sheet |
  | A12 | Packages | "Find the monitoring package for one client and check that its figures have sources." | opens Packages; reads the verification |

  **Facilitator as Helen during A7–A8:** in the second window, open Approvals, open the case, choose Return, reason "Please attach the signed term sheet before I decide.", add the needed item, send. Do not decide; the case stays for the next session only if the book is reset.

  **Officer tasks (P5, signed in as `helen.strand@bankofstoic.example`):** before the session the facilitator, signed in as Priya, routes two covenant cases from the TSV with views ("Breach confirmed on the certificate; recommend waiver with conditions.", "I would reserve rights until the November package.") and leaves one returned case waiting on Priya.

  | # | Area | Task | Success when |
  |---|---|---|---|
  | O1 | Approvals | "What is waiting for your decision, and which first?" | names both routed cases |
  | O2 | Decide | "Decide the first one. Use the analyst's view and the evidence." | records a decision with a reason; sees the two-person rule |
  | O3 | Return | "For the second, ask the analyst for something you need first." | returns with a reason and a needed item |
  | O4 | Evidence | "Before deciding, check the figure the case rests on." | opens the source page |
  | O5 | Thread | "Where does your decision show for the analyst?" | finds it in the client's thread |
  | O6 | Portfolio and review room | "Which clients would you raise at the next portfolio review?" | uses portfolio or review room |

- [ ] **Step 3: Observation sheet** (one per task per participant): participant code, task id, start/end time, outcome (done / done with help / not done / skipped), path taken (screens in order), hesitations over 10 s and where, words used for things (their names vs ours), errors seen (exact text), quote, severity proposal (blocker: could not finish or was misled about a figure or a decision; major: finished with help or a wrong belief corrected later; minor: slowed; cosmetic), trust question answered (would you rely on this figure: yes/no/why).

- [ ] **Step 4: Session log** (`session-log.md`): table: session, date, participant code, role, facilitator, note-taker, `v2_setup.py check` result before, reset after (yes/no, ledger export file), anything unusual (cold start, paused database).

- [ ] **Step 5: Findings file** (`docs/product/v2-usability-findings.md`), in the shape of `docs/product/v2-first-look-findings.md`: header (dates, sessions held, build commit, address); a table `ID | Session(s) | Task | What happened (observed, not interpreted) | Severity | Seen by (n of 5) | Proposed fix | Decision | Fix commit | Re-checked`; sections "Blockers and majors (fixed before v2 is done)", "Minors (owner decides)", "Not changing (with reason)", "Lessons" (each new lesson also goes to `docs/lessons/`). Triage rules written at the top: each blocker and major gets a fix with a test (an API test where a rule is involved, `docs/lessons/a-second-may-act-rule-drifts-from-the-engine.md`), a v2-only redeploy with `deploy-v2.sh`, and a re-run of `pnpm e2e:smoke` and the read-only journeys on the hosted v2; v2 is called done only when no blocker or major is open and the owner has read the file.

- [ ] **Step 6: Commit**

```bash
git add docs/product/usability docs/product/v2-usability-findings.md && \
git commit -m "docs(p5): usability session kit (consent note, facilitator script, observation sheet, log) and the findings file" -- docs/product/usability docs/product/v2-usability-findings.md
```
(Includes `docs/product/usability/ledger/2026-11-smoke.json` if Task 12 Step 2 ran.)

---

### Task 16: Sessions (run by people) and triage

Agents do not run sessions. This task is the owner's and the facilitator's, with the controller doing only the before/after commands and the triage.

- [ ] **Step 1: Owner gates** O-4 (names checked against real companies) and O-5 (participants recruited, dates set) are done; owner questions 2 and 5 answered.
- [ ] **Step 2: Before each session (controller, within the hour):** `uv run python -I scripts/hosted/v2_setup.py check --base "$V2"` prints `ready`. If not, and owner question 2 was "yes": export the ledger (Task 12 Step 2 SQL, file `docs/product/usability/ledger/<date>-P<n>.json`), drop and reload, check again. If sign-in fails, the free Supabase project may be paused: owner restores it in the dashboard (owner step O-6).
- [ ] **Step 3: Session** run by the facilitator from `facilitator-script.md`; observation sheets filled.
- [ ] **Step 4: After the five sessions:** the facilitator's sheets are transcribed into `v2-usability-findings.md` (by the facilitator or, from the sheets, by the controller with the facilitator checking). Commit `docs(p5): usability findings, sessions 1–5`.
- [ ] **Step 5: Triage and fix** per the file's rules; each fix in its own commit (`fix(p5): ...`) with its test; v2-only redeploy; smoke and read-only journeys re-run on the hosted v2; Task 13 after-check repeated after the last redeploy.
- [ ] **Step 6: Owner reads the findings file and says v2 is done** (or not). Update HANDOFF.

---

### Task 17 (later, only with the owner's go-ahead): turn agents on for the hosted v2

Not part of the default release. Runs only after owner question 1 is answered "live" and the estimate below is accepted.

- [ ] **Step 1: Estimate (labelled as an estimate)** from measured spend: the 21 November live record pass measured 8.31 US dollars for 164 recorded exchanges (about 0.05 per exchange, from recorded `usage`). Assumption: per session 5 free questions to Squad (about 1–2 exchanges each) and 2 stage runs ("Run … now", about 5–10 exchanges each): about 15–30 exchanges, so roughly 0.75–1.50 US dollars per session, about 4–8 US dollars for five sessions plus the smoke re-run. Propose a cap (for example 10 US dollars) and a spend limit on the key in the Anthropic console.
- [ ] **Step 2: Owner adds the key** themselves in the Vercel dashboard for the v2 project only (`ANTHROPIC_API_KEY`, production, sensitive) — never through this session, never on `csquad` or `credit-agent-squad` (owner step O-7). The controller then redeploys with `deploy-v2.sh --no-build` and runs `pnpm e2e:smoke` with `EXPECT_MODEL=on`, plus one Copilot question in a browser, and reads the answer's sources.
- [ ] **Step 3: Update** the consent note line about agents, DEPLOY.md and HANDOFF (billable, cap, measured spend after each session from the Anthropic console, reported as measured).

---

## Owner steps and credentials

| # | Step | Needed by | State |
|---|---|---|---|
| O-1 | Vercel access token | Tasks 8–10 | **Present** as this environment's network secret for `api.vercel.com` (checked: API answers 200, project list readable). Only if a call returns 401/403: refresh it in the environment's network secrets (credential card for `api.vercel.com`, bearer); no token in any command or file |
| O-2 | Answer owner question 3 (project name) | Task 9 | Open |
| O-3 | Give the Supabase **session pooler host** for project "Credit Agent Squad" (dashboard → Connect → Session pooler; host only, for example `aws-0-us-east-1.pooler.supabase.com`; not a secret) | Task 9 | Open: no available MCP tool returns it |
| O-4 | Check the client and person names against real companies before outside participants see them (`docs/owner-questions.md`, "Waiting for you" item 2) | Task 16 | Open ("Owner: to check") |
| O-5 | Recruit 4 analysts and 1 credit officer; choose a facilitator and a note-taker (people); set dates | Task 16 | Owner said they will start recruiting (standing approval 7) |
| O-6 | Restore the free Supabase project if it pauses before a session | Task 16 | As needed |
| O-7 | Only if agents go live: create a dedicated Anthropic key with a spend limit and add it to the v2 Vercel project yourself | Task 17 | Not requested by default |

Supabase access: the controller session's Supabase MCP tools (verified: `list_projects` shows "Credit Agent Squad", `us-east-1`, `ACTIVE_HEALTHY`, PostgreSQL 17). No new database credential is needed; the two v2 login passwords are made in Task 9 and exist only on Vercel and as verifiers.

## Owner questions (not decided by this plan)

1. **Agents on the hosted v2: live or off?** Live means `ANTHROPIC_API_KEY` on the v2 project; every question to Squad and every "Run … now" is billable (estimate in Task 17: about 4–8 US dollars for five sessions, an estimate). Off means no model calls: the seeded book shows Squad's earlier work, questions to Squad say they are off (Task 5), runs refuse. "Recorded" is not a working third option on a hosted copy (fact ids differ on every seed). **Default in this plan: off;** Task 17 turns live on only with your go-ahead.
2. **May `squad2` be rebuilt (schema dropped and reloaded) after the smoke test and between sessions?** It is v2's own test schema with synthetic data; each rebuild first exports that schema's ledger to `docs/product/usability/ledger/`. Without it, the writing journeys are not run on the hosted copy, and participants 2–5 would find the demo question answered, the draft sent and cases decided by participant 1. **Asked, not assumed;** the plan runs Task 12 and the between-session reset only on "yes".
3. **Name of the new Vercel project** (and so its address). Default `credit-squad` (address `credit-squad.vercel.app` if free on Vercel, otherwise Vercel adds a suffix).
4. **Names check (O-4)** before outside participants: do you want to check them yourself, or should a web search be run and the results shown to you?
5. **Recording in sessions:** notes only (default), or screen and audio with a separate yes from each participant?
6. **Free-tier terms:** the v2 project is on Vercel's free (Hobby) plan like v1, which is meant for non-commercial use; usability sessions with outside participants are a product test. Fine as is, or move v2 to a paid plan?

## Self-review notes

- Spec coverage: section 12 (new schema `squad2`, own Vercel project, v1 kept, csquad frozen) → Tasks 1, 2, 8–13; original plan Phase 5 (hosted smoke on `squad2`, usability script against the real product, findings fed back before v2 is done; c-squad unchanged by content hash) → Tasks 11, 13, 15, 16; standing approvals 6 and 7 → Global Constraints and O-5.
- Every SQL statement is written out; every secret is made inside one process; every deploy goes through `deploy-v2.sh`, which runs `check_link.py`.
- The executor reads `squad.mjs` lines 316-381 for the hand-off selectors and `backend/app/squad/` for the thread message fields before relying on them (Tasks 4 and 6 say so).

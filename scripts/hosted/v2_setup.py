"""Load v2's book through the setup routes, and check that a hosted book is ready for a session.

    python scripts/hosted/v2_setup.py run   --base https://<v2>.vercel.app --project-dir .vercel-build-v2
    python scripts/hosted/v2_setup.py load  --base http://localhost:8010      # token from $DEMO_SETUP_TOKEN
    python scripts/hosted/v2_setup.py check --base https://<v2>.vercel.app [--expect-model]

`run` makes the setup token in this process, puts it on Vercel, redeploys, loads, removes the token
and redeploys again, so the setup routes answer 404 whenever nobody is loading. Nothing secret is printed.

`check` signs in as the analyst who owns the demo clients (Priya Raman) and refuses a book whose demo
question (Cindrel Tech) is answered, whose demo draft (Calvere Health) is sent, or that has no open
covenant breach she may route to the credit officer (the hand-off task); it also checks agents are on or off as expected and the ledger is append-only.

Every command refuses a frozen site's host (frozen_hosts.py). `check` is not strictly read-only: its sign-in adds a
session and a ledger event, and a wrong SQUAD_DEMO_PASSWORD records a failed sign-in. `run` acts only on
.vercel-build-v2 once check_link.pinned_env has passed, with every vercel call pinned to that link."""
import argparse
import importlib.util
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
BUILD = ROOT / ".vercel-build-v2"


def _sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_link, frozen_hosts = _sibling("check_link"), _sibling("frozen_hosts")
VERCEL = ["npx", "--yes", "vercel@66.0.0"]
ANALYST, PASSWORD = "priya.raman@bankofstoic.example", os.environ.get("SQUAD_DEMO_PASSWORD", "squad-demo")
QUESTION_CLIENT, DRAFT_CLIENT = "cindrel-tech", "calvere-health"  # app.squad_demo on the innovation book


def _call(base, method, path, token=None, body=None, cookie=None, timeout=310):
    headers = {"Content-Type": "application/json", **({"X-Setup-Token": token} if token else {}),
               **({"Cookie": cookie} if cookie else {})}
    request = urllib.request.Request(base + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.build_opener().open(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}"), response.headers
    except urllib.error.HTTPError as error:
        return error.code, {"detail": error.read()[:300].decode(errors="replace")}, error.headers
    except (TimeoutError, urllib.error.URLError) as error:
        return 504, {"detail": str(error)[:300]}, {}


def load(base, token, post=None, get=None):
    frozen_hosts.refuse_frozen(base)
    post = post or (lambda path, t: _call(base, "POST", path, t)[:2])
    get = get or (lambda path, t: _call(base, "GET", path, t)[:2])
    code, status = get("/api/_setup/status", token)
    if code != 200 or status.get("target") != "v2" or status.get("schema") != "squad2":
        sys.exit(f"refused: {base} is not a v2 build on squad2 ({code}, {status.get('target')}, {status.get('schema')}, "
                 f"{status.get('reason', '')})")
    code, body = post("/api/_setup/migrate", token)
    if code != 200:
        sys.exit(f"migrate failed: {code} {body}")
    _, status = get("/api/_setup/status", token)
    if not status.get("migrated"):
        sys.exit(f"not migrated: {status.get('reason')}")
    for client in status["to_load"]:
        for attempt in (1, 2):
            started = time.monotonic()
            code, body = post(f"/api/_setup/seed/{client}", token)
            print(f"seed {client}: {code} {body.get('loaded')} {time.monotonic() - started:.1f}s (try {attempt})", flush=True)
            if code == 200:
                break
        else:
            sys.exit(f"seed {client} failed twice: {code} {body}")
    code, body = post("/api/_setup/squad-demo", token)
    if code != 200:
        sys.exit(f"squad demo failed: {code} {body}")
    print(f"squad demo: {code} question {body.get('question_borrower_code')}, draft {body.get('draft_borrower_code')}")
    _, status = get("/api/_setup/status", token)
    if status["to_load"]:
        sys.exit(f"still to load: {status['to_load']}")
    print(json.dumps({k: status.get(k) for k in ("users", "book_borrowers", "book_seed", "target", "schema")}))
    return status


def check_state(*, routable_breaches, question_open, draft_sent, model, ledger, expect_model):
    problems = []
    if not question_open:
        problems.append(f"Squad's demo question ({QUESTION_CLIENT}) is not open: the book has been used")
    if draft_sent:
        problems.append(f"the demo draft ({DRAFT_CLIENT}) has been sent: the book has been used")
    if not routable_breaches:
        problems.append("no open covenant breach is waiting for the analyst to route: the book has been used")
    if bool(model.get("model_connected")) != expect_model:
        problems.append(f"agents are {'on' if model.get('model_connected') else 'off'}; "
                        f"expected {'on' if expect_model else 'off'}")
    if not (ledger.get("ok") and ledger.get("append_only_for_this_role")):
        problems.append(f"ledger check failed: {ledger}")
    return problems


def _session_cookie(headers) -> str | None:
    """The session cookie's name=value, sent back by hand: the standard cookie jar keeps a Secure
    cookie off plain http, and the local rehearsal runs with deployment settings on http."""
    values = headers.get_all("Set-Cookie") if hasattr(headers, "get_all") else None
    return values[0].split(";", 1)[0] if values else None


def check(base, expect_model):
    frozen_hosts.refuse_frozen(base)
    code, _, headers = _call(base, "POST", "/api/v1/auth/login", body={"email": ANALYST, "password": PASSWORD})
    cookie = _session_cookie(headers) if code == 200 else None
    if not cookie:
        return [f"sign-in as the analyst failed: {code} (a paused free database answers this way too)"]

    def get(path):
        status, body, _ = _call(base, "GET", "/api/v1" + path, cookie=cookie)
        if status != 200:
            raise SystemExit(f"GET {path} answered {status}: {body}")
        return body

    # the hand-off task: a breach on one of her clients that she may still send to the credit officer
    breaches = [w for w in get("/work-items?item_type=covenant.breach") if w.get("status") == "open"]
    routable = [w for w in breaches if get(f"/cases/{w['id']}").get("may_route")]
    borrowers = {b["code"]: b["id"] for b in get("/borrowers")}
    question = get(f"/threads/{borrowers[QUESTION_CLIENT]}")
    drafts = get(f"/threads/{borrowers[DRAFT_CLIENT]}")
    question_open = any(m.get("type") == "ask" and m.get("status") == "open" for m in question["messages"])
    draft_sent = any(m.get("type") == "draft" and (m.get("sent_at") or m.get("status") == "sent")
                     for m in drafts["messages"])
    return check_state(routable_breaches=len(routable), question_open=question_open, draft_sent=draft_sent,
                       model=get("/agents/status"), ledger=get("/ledger/verify"), expect_model=expect_model)


def _run_vercel(args, cwd, env, value):
    done = subprocess.run([*VERCEL, *args, "--token", "proxyinjected"], cwd=cwd, env=env, text=True,
                          input=None if value is None else value + "\n", capture_output=True)
    output = (done.stderr or done.stdout)
    return done.returncode, (output.replace(value, "<value>") if value else output)[-300:]


REMOVE_BY_HAND = ("(cd .vercel-build-v2 && npx --yes vercel@66.0.0 env rm DEMO_SETUP_TOKEN --environment production "
                  "--confirm-name DEMO_SETUP_TOKEN --token proxyinjected) && ./scripts/hosted/deploy-v2.sh --no-build")


def run(base, project_dir, *, build_dir=None, frozen=None, expected_id=None, vercel=None, deploy=None,
        load_fn=None, call=None):
    """Token on, redeploy, load, token off, redeploy, then prove with the real token that the routes are gone.
    Only `.vercel-build-v2`, only when it is linked to the v2 project; every vercel call is pinned to that link."""
    frozen_hosts.refuse_frozen(base)
    build_dir = Path(build_dir or BUILD)
    if Path(project_dir).resolve() != build_dir.resolve():
        sys.exit(f"refused: run works only on {build_dir} (what deploy-v2.sh deploys), not {project_dir}")
    project = os.environ.get("V2_PROJECT") or "credit-squad"
    env = check_link.pinned_env(build_dir, project, frozen=frozen, expected_id=expected_id)
    vercel = vercel or _run_vercel
    deploy = deploy or (lambda e: subprocess.run([str(ROOT / "scripts" / "hosted" / "deploy-v2.sh"), "--no-build"],
                                                 check=True, env=e))
    load_fn, call = load_fn or load, call or _call
    token = secrets.token_urlsafe(32)
    code, said = vercel(["env", "add", "DEMO_SETUP_TOKEN", "--environment", "production", "--sensitive"],
                        build_dir, env, token)
    if code:
        sys.exit(f"vercel env add DEMO_SETUP_TOKEN failed: {said}")
    still_set = None
    try:
        deploy(env)
        load_fn(base, token)
    finally:
        code, said = vercel(["env", "rm", "DEMO_SETUP_TOKEN", "--environment", "production",
                             "--confirm-name", "DEMO_SETUP_TOKEN"], build_dir, env, None)
        if code:
            still_set = (f"DEMO_SETUP_TOKEN is still set on {project}: the setup routes stay open until it is "
                         f"removed. Run now: {REMOVE_BY_HAND}  (vercel said: {said.strip()})")
            print(still_set, file=sys.stderr)
        deploy(env)  # redeploy either way: without the variable, or so the next attempt starts from a known state
    if still_set:
        sys.exit(still_set)
    code, _, _ = call(base, "GET", "/api/_setup/status", token)  # the real token: 404 only if it is really gone
    if code != 404:
        sys.exit(f"the setup routes still answer ({code}) to the token that was just removed")
    print("setup routes are off again (404 to the removed token)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "load", "check"))
    parser.add_argument("--base", required=True)
    parser.add_argument("--project-dir", default=str(BUILD))
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

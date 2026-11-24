"""Loading v2 goes through the setup routes one client per call; a pre-session check refuses a book
that someone has already used. Tested against fakes: no network service is called."""
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "hosted" / "v2_setup.py"
spec = importlib.util.spec_from_file_location("v2_setup", SCRIPT)
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)


class FakeHost:
    """The setup routes as the function answers them, with one seed call that times out once."""

    def __init__(self):
        self.loaded, self.calls, self.flaky = [], [], {"calvere-health"}
        self.book = ["brackmere-medical", "calvere-health", "cindrel-tech"]

    def get(self, path, token):
        self.calls.append(("GET", path))
        return 200, {"migrated": True, "users": 9, "loaded": list(self.loaded),
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
    assert posts.count("/api/_setup/seed/calvere-health") == 2  # one retry after the timeout
    assert sum(p.startswith("/api/_setup/seed/") for p in posts) == 4
    assert status["to_load"] == [] and status["schema"] == "squad2"


def test_load_stops_when_a_client_fails_twice():
    host = FakeHost()
    host.post = lambda path, token: (504, {"detail": "timeout"}) if "seed" in path else (200, {})
    with pytest.raises(SystemExit, match="failed twice"):
        v2.load("https://x", "t", post=host.post, get=host.get)


def test_load_refuses_a_host_that_is_not_v2_on_squad2():
    host = FakeHost()
    host.get = lambda path, token: (200, {"migrated": True, "target": "v1", "schema": "squad", "to_load": []})
    with pytest.raises(SystemExit, match="squad2"):
        v2.load("https://x", "t", post=host.post, get=host.get)
    assert host.calls == []  # nothing was posted


FRESH = dict(routable_breaches=1, question_open=True, draft_sent=False, model={"model_connected": False}, expect_model=False)


def test_check_names_each_thing_a_used_book_has_lost():
    problems = v2.check_state(**{**FRESH, "question_open": False, "draft_sent": True, "routable_breaches": 0},
                              ledger={"ok": True, "append_only_for_this_role": True})
    assert any("question" in p for p in problems) and any("draft" in p for p in problems)
    assert any("covenant breach" in p for p in problems)


def test_check_passes_a_fresh_book_and_refuses_a_ledger_the_app_could_rewrite_or_agents_on():
    assert v2.check_state(**FRESH, ledger={"ok": True, "append_only_for_this_role": True}) == []
    assert v2.check_state(**FRESH, ledger={"ok": True, "append_only_for_this_role": False})
    assert v2.check_state(**{**FRESH, "model": {"model_connected": True}},
                          ledger={"ok": True, "append_only_for_this_role": True})


class Api(BaseHTTPRequestHandler):
    """The read routes `check` calls, answering in the shapes the real API returns."""
    sent = False
    routable = True

    def log_message(self, *args):
        pass

    def _send(self, status, body, cookie=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/v1/auth/login" and body.get("password") == "squad-demo":
            # Secure, as a deployment sends it: the check must still send it back over a local http rehearsal
            return self._send(200, {"email": body["email"]}, "squad_session=abc; HttpOnly; Secure; Path=/")
        self._send(401, {"detail": "no"})

    def do_GET(self):  # noqa: N802
        if "squad_session=abc" not in (self.headers.get("Cookie") or ""):
            return self._send(401, {"detail": "Not signed in."})
        routes = {
            "/api/v1/work-items?item_type=covenant.breach": [{"id": "w1", "status": "open"}, {"id": "w2", "status": "open"}],
            "/api/v1/cases/w1": {"status": "open", "may_route": Api.routable},  # Priya's client
            "/api/v1/cases/w2": {"status": "open", "may_route": False},  # a client of an analyst with no login
            "/api/v1/borrowers": [{"code": "cindrel-tech", "id": "c1"}, {"code": "calvere-health", "id": "c2"}],
            "/api/v1/threads/c1": {"messages": [{"type": "ask", "status": "open"}]},
            "/api/v1/threads/c2": {"messages": [{"type": "draft", "status": "sent" if Api.sent else "draft",
                                                 "sent_at": "2026-11-23T10:00:00Z" if Api.sent else None}]},
            "/api/v1/agents/status": {"model_connected": False, "reason": "No model key is set for this deployment."},
            "/api/v1/ledger/verify": {"ok": True, "append_only_for_this_role": True},
        }
        self._send(200, routes[self.path]) if self.path in routes else self._send(404, {"detail": "Not found."})


@pytest.fixture()
def fake_api():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Api)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    Api.sent, Api.routable = False, True


def test_check_reads_the_real_routes_and_passes_an_unused_book(fake_api):
    assert v2.check(fake_api, expect_model=False) == []


def test_check_finds_a_sent_draft_through_the_real_routes(fake_api):
    Api.sent = True
    assert any("draft" in p for p in v2.check(fake_api, expect_model=False))


def test_check_finds_a_routed_breach_through_the_real_routes(fake_api):
    Api.routable = False
    assert any("covenant breach" in p for p in v2.check(fake_api, expect_model=False))


def test_check_says_so_when_sign_in_fails(fake_api, monkeypatch):
    monkeypatch.setattr(v2, "PASSWORD", "wrong")
    assert "sign-in" in v2.check(fake_api, expect_model=False)[0]


# --- the project and host it may touch -------------------------------------------------------------------

FROZEN_IDS = ["prj_v1_frozen", "prj_csquad_frozen"]


def linked(folder, project_name="credit-squad", project_id="prj_new"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "api").mkdir(exist_ok=True)
    (folder / "api" / "target.json").write_text(json.dumps({"target": "v2", "schema": "squad2",
                                                            "runtime_role": "squad2_runtime"}))
    (folder / ".vercel").mkdir(exist_ok=True)
    (folder / ".vercel" / "project.json").write_text(json.dumps(
        {"projectId": project_id, "orgId": "team_x", "projectName": project_name}))
    return folder


class FakeVercel:
    """Records each vercel call with the project id it would act on; fails `env rm` when asked to."""

    def __init__(self, fail_rm=False):
        self.calls, self.fail_rm = [], fail_rm

    def __call__(self, args, cwd, env, value):
        self.calls.append((args[0], args[1], env.get("VERCEL_PROJECT_ID"), env.get("VERCEL_ORG_ID")))
        if self.fail_rm and args[:2] == ["env", "rm"]:
            return 1, "Error: something went wrong"
        return 0, ""


def run_with(tmp_path, build, *, vercel=None, answers_after=404, monkeypatch=None):
    vercel = vercel or FakeVercel()
    deploys, seen = [], {}

    def final_call(base, method, path, token=None, **_):
        seen["token"] = token
        return answers_after, {}, {}

    v2.run("https://credit-squad.vercel.app", str(build), build_dir=build, frozen=FROZEN_IDS, expected_id="prj_new",
           vercel=vercel, deploy=lambda env: deploys.append(env.get("VERCEL_PROJECT_ID")),
           load_fn=lambda base, token: seen.setdefault("loaded_with", token), call=final_call)
    return vercel, deploys, seen


def test_run_refuses_a_folder_linked_to_v1_before_any_vercel_call(tmp_path):
    for build in (linked(tmp_path / "a", "credit-agent-squad", "prj_x"), linked(tmp_path / "b", "credit-squad", "prj_v1_frozen")):
        vercel = FakeVercel()
        with pytest.raises(SystemExit, match="REFUSED"):
            run_with(tmp_path, build, vercel=vercel)
        assert vercel.calls == []


def test_run_refuses_any_folder_but_the_v2_build_folder(tmp_path):
    build, other = linked(tmp_path / "v2"), linked(tmp_path / "copy")
    vercel = FakeVercel()
    with pytest.raises(SystemExit, match="only"):
        v2.run("https://credit-squad.vercel.app", str(other), build_dir=build, frozen=FROZEN_IDS, expected_id="prj_new",
               vercel=vercel, deploy=lambda env: None, load_fn=lambda b, t: None, call=lambda *a, **k: (404, {}, {}))
    assert vercel.calls == []


def test_run_pins_every_vercel_call_to_the_checked_link_whatever_the_shell_exports(tmp_path, monkeypatch):
    monkeypatch.setenv("VERCEL_PROJECT_ID", "prj_v1_frozen")
    monkeypatch.setenv("VERCEL_ORG_ID", "team_v1")
    vercel, deploys, seen = run_with(tmp_path, linked(tmp_path / "v2"))
    assert [c[:2] for c in vercel.calls] == [("env", "add"), ("env", "rm")]
    assert all(c[2:] == ("prj_new", "team_x") for c in vercel.calls) and deploys == ["prj_new", "prj_new"]


def test_run_checks_the_routes_are_off_with_the_real_token_and_fails_if_they_answer(tmp_path):
    _, _, seen = run_with(tmp_path, linked(tmp_path / "v2"))
    assert seen["token"] == seen["loaded_with"] and seen["token"] != "anything"
    with pytest.raises(SystemExit, match="still answer"):
        run_with(tmp_path, linked(tmp_path / "v3"), answers_after=200)


def test_a_failed_token_removal_still_redeploys_and_says_exactly_what_to_run(tmp_path, capsys):
    vercel = FakeVercel(fail_rm=True)
    with pytest.raises(SystemExit) as stop:
        _, deploys, seen = run_with(tmp_path, linked(tmp_path / "v2"), vercel=vercel)
    message = str(stop.value)
    assert "DEMO_SETUP_TOKEN is still set" in message
    assert "env rm DEMO_SETUP_TOKEN --environment production --confirm-name DEMO_SETUP_TOKEN" in message
    assert len([c for c in vercel.calls if c[:2] == ("env", "rm")]) == 1


@pytest.mark.parametrize("base", ["https://credit-agent-squad.vercel.app", "https://c-squad.vercel.app/",
                                  "https://csquad-kappa.vercel.app", "https://credit-agent-squad-abc123-team.vercel.app",
                                  "https://csquad-git-main-team.vercel.app"])
def test_every_command_refuses_a_frozen_host_before_calling_it(base, monkeypatch):
    calls = []
    monkeypatch.setattr(v2, "_call", lambda *a, **k: calls.append(a) or (200, {}, {}))
    for command in (lambda: v2.check(base, expect_model=False), lambda: v2.load(base, "t"),
                    lambda: v2.run(base, "x", frozen=FROZEN_IDS, expected_id="prj_new")):
        with pytest.raises(SystemExit, match="frozen"):
            command()
    assert calls == []


def test_the_v2_host_and_a_local_rehearsal_are_allowed():
    for base in ("https://credit-squad.vercel.app", "http://localhost:8010", "https://credit-squad-abc-team.vercel.app"):
        v2.frozen_hosts.refuse_frozen(base)

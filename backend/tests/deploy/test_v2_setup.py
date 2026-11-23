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


FRESH = dict(briefing={"items": [{"kind": "breach", "needs_you": True, "borrower_code": "brackmere-medical"}]},
             question_open=True, draft_sent=False, model={"model_connected": False}, expect_model=False)


def test_check_names_each_thing_a_used_book_has_lost():
    problems = v2.check_state(**{**FRESH, "question_open": False, "draft_sent": True, "briefing": {"items": []}},
                              ledger={"ok": True, "append_only_for_this_role": True})
    assert any("question" in p for p in problems) and any("draft" in p for p in problems)
    assert any("covenant" in p for p in problems)


def test_check_passes_a_fresh_book_and_refuses_a_ledger_the_app_could_rewrite_or_agents_on():
    assert v2.check_state(**FRESH, ledger={"ok": True, "append_only_for_this_role": True}) == []
    assert v2.check_state(**FRESH, ledger={"ok": True, "append_only_for_this_role": False})
    assert v2.check_state(**{**FRESH, "model": {"model_connected": True}},
                          ledger={"ok": True, "append_only_for_this_role": True})


class Api(BaseHTTPRequestHandler):
    """The read routes `check` calls, answering in the shapes the real API returns."""
    sent = False

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
            "/api/v1/me/briefing": {"items": [{"kind": "breach", "needs_you": True, "borrower_code": "brackmere-medical"}]},
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
    Api.sent = False


def test_check_reads_the_real_routes_and_passes_an_unused_book(fake_api):
    assert v2.check(fake_api, expect_model=False) == []


def test_check_finds_a_sent_draft_through_the_real_routes(fake_api):
    Api.sent = True
    assert any("draft" in p for p in v2.check(fake_api, expect_model=False))


def test_check_says_so_when_sign_in_fails(fake_api, monkeypatch):
    monkeypatch.setattr(v2, "PASSWORD", "wrong")
    assert "sign-in" in v2.check(fake_api, expect_model=False)[0]

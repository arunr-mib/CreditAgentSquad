"""The Vercel entry point must serve the schema and runtime role its build was made for, and
nothing else: a v2 build that starts with v1's schema would write into v1's record."""
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ENTRY = Path(__file__).resolve().parents[3] / "deploy" / "vercel" / "api" / "index.py"
V2 = {"target": "v2", "schema": "squad2", "runtime_role": "squad2_runtime"}
KEYS = ("DB_SCHEMA", "DB_RUNTIME_ROLE", "DEMO_SETUP_TOKEN", "FILE_FALLBACK_DIR", "FILE_STORE_DIR", "DB_POOL")


@pytest.fixture()
def load(tmp_path, monkeypatch):
    """Import a copy of the entry point from a fake build folder. The entry point writes defaults
    into os.environ; monkeypatch puts every touched key back afterwards."""
    for key in KEYS:
        monkeypatch.setenv(key, "placeholder")  # registers the key for restoring
        monkeypatch.delenv(key)
    from app.core import db as db_module
    from app.core.config import get_settings

    monkeypatch.setattr(db_module, "_engine", None)  # an engine made here must not outlive the test
    monkeypatch.setattr(db_module, "_SessionLocal", None)

    def _load(target=None, **env):
        api = tmp_path / "api"
        api.mkdir()
        shutil.copy(ENTRY, api / "index.py")
        if target is not None:
            (api / "target.json").write_text(json.dumps(target))
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        spec = importlib.util.spec_from_file_location(f"entry_{tmp_path.name}", api / "index.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    yield _load
    get_settings.cache_clear()


def test_a_build_without_a_target_file_keeps_v1s_schema_and_role(load):
    module = load()
    assert module.TARGET["target"] == "v1"
    assert os.environ["DB_SCHEMA"] == "squad" and os.environ["DB_RUNTIME_ROLE"] == "squad_runtime"


def test_a_v2_build_takes_squad2_when_nothing_is_set(load):
    module = load(V2)
    assert module.TARGET == V2
    assert os.environ["DB_SCHEMA"] == "squad2" and os.environ["DB_RUNTIME_ROLE"] == "squad2_runtime"


@pytest.mark.parametrize("env", [{"DB_SCHEMA": "squad"}, {"DB_RUNTIME_ROLE": "squad_runtime"}])
def test_a_v2_build_refuses_to_start_on_v1s_schema_or_role(load, env):
    with pytest.raises(RuntimeError, match="built for"):
        load(V2, **env)


def test_every_setup_route_is_hidden_without_the_token(load):
    module = load(V2)
    client = TestClient(module.app)
    assert client.get("/api/_setup/status").status_code == 404
    for path in ("/api/_setup/migrate", "/api/_setup/seed/cindrel-tech", "/api/_setup/squad-demo"):
        assert client.post(path, headers={"X-Setup-Token": "anything"}).status_code == 404


def test_with_the_token_the_status_names_the_target_and_schema_even_before_migration(load):
    module = load(V2, DEMO_SETUP_TOKEN="t0ken-for-the-test",
                  DATABASE_URL="postgresql+psycopg://nobody:x@127.0.0.1:1/none")
    client = TestClient(module.app)
    body = client.get("/api/_setup/status", headers={"X-Setup-Token": "t0ken-for-the-test"}).json()
    assert body["target"] == "v2" and body["schema"] == "squad2" and body["migrated"] is False

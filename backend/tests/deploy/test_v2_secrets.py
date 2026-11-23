"""The passwords for v2's logins never leave one process except as verifiers (to the database)
and as connection strings on standard input (to Vercel)."""
import base64
import importlib.util
import json
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
    (PG_SUPERUSER_URL) because only a superuser may read pg_authid."""
    url = os.environ.get("PG_SUPERUSER_URL")
    if not url:
        pytest.skip("set PG_SUPERUSER_URL to compare with PostgreSQL's own verifier")
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("SET LOCAL password_encryption = 'scram-sha-256'"))
        db.execute(text("CREATE ROLE p5_scram_probe PASSWORD 'pencil-and-paper-12'"))
        stored = db.execute(text("SELECT rolpassword FROM pg_authid WHERE rolname = 'p5_scram_probe'")).scalar()
        db.execute(text("DROP ROLE p5_scram_probe"))
    engine.dispose()
    iterations, rest = stored.removeprefix("SCRAM-SHA-256$").split(":", 1)
    salt = base64.b64decode(rest.split("$", 1)[0])
    assert v2.scram_verifier("pencil-and-paper-12", salt=salt, iterations=int(iterations)) == stored


def test_role_sql_creates_three_roles_and_names_no_v1_role():
    sql = v2.role_sql("SCRAM-SHA-256$4096:a$b:c", "SCRAM-SHA-256$4096:d$e:f")
    assert len(sql.splitlines()) == 5
    assert "CREATE ROLE squad2_runtime NOLOGIN;" in sql
    assert "CREATE ROLE squad2_app LOGIN" in sql and "CREATE ROLE squad2_web LOGIN" in sql
    assert "GRANT squad2_runtime TO squad2_web;" in sql
    assert "GRANT CREATE ON DATABASE postgres TO squad2_app;" in sql
    for v1 in ("squad_runtime", "squad_app", "squad_web", " squad;", "squad."):
        assert v1 not in sql


def test_role_sql_for_a_retry_alters_the_two_logins_and_creates_nothing():
    sql = v2.role_sql("SCRAM-SHA-256$4096:a$b:c", "SCRAM-SHA-256$4096:d$e:f", alter=True)
    assert sql.splitlines() == [
        "ALTER ROLE squad2_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'SCRAM-SHA-256$4096:a$b:c';",
        "ALTER ROLE squad2_web LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'SCRAM-SHA-256$4096:d$e:f';"]


def test_the_url_uses_the_session_pooler_user_form_and_requires_tls():
    url = v2.connection_url("squad2_web", "ref123", "Abc123", "pooler.example")
    assert url == "postgresql+psycopg://squad2_web.ref123:Abc123@pooler.example:5432/postgres?sslmode=require"


def test_a_pooler_host_that_is_not_a_plain_host_name_is_refused_before_anything_is_made():
    for bad in ("pooler.example:6543", "user@pooler.example", "pooler.example/x", ""):
        with pytest.raises(ValueError):
            v2.connection_url("squad2_web", "ref123", "Abc123", bad)


FROZEN = ["prj_v1_frozen", "prj_csquad_frozen"]


def linked(folder, project_name="credit-squad", project_id="prj_new"):
    """A v2 build folder linked as `vercel link` leaves it."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "api").mkdir(exist_ok=True)
    (folder / "api" / "target.json").write_text(json.dumps({"target": "v2", "schema": "squad2",
                                                            "runtime_role": "squad2_runtime"}))
    (folder / ".vercel").mkdir(exist_ok=True)
    (folder / ".vercel" / "project.json").write_text(json.dumps(
        {"projectId": project_id, "orgId": "team_x", "projectName": project_name}))
    return folder


def fake_vercel(tmp_path, fail_on=None):
    """A fake vercel that records its arguments, the project it would act on and the length of its input,
    never the input itself."""
    fake = tmp_path / "vercel"
    log = tmp_path / "calls.txt"
    fail = f'case "$*" in *{fail_on}*) echo "boom $IN" >&2; exit 1;; esac\n' if fail_on else ""
    fake.write_text(f"#!/bin/sh\nIN=$(cat)\necho \"$* len=${{#IN}} project=$VERCEL_PROJECT_ID org=$VERCEL_ORG_ID\" >> {log}\n{fail}")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return fake, log


def run_cli(tmp_path, fake, *extra, build=None, env=None):
    build = build or linked(tmp_path / "build")
    return subprocess.run([sys.executable, "-I", str(SCRIPT), "--project-dir", str(build), "--ref", "ref123",
                           "--pooler-host", "aws-0-us-east-1.pooler.supabase.com", "--vercel", str(fake),
                           "--frozen-ids", *FROZEN, "--expected-id", "prj_new", *extra],
                          capture_output=True, text=True, env=env)


def test_a_folder_linked_to_v1_gets_nothing_by_name_or_by_id(tmp_path):
    fake, log = fake_vercel(tmp_path)
    for build in (linked(tmp_path / "a", "credit-agent-squad", "prj_other"),
                  linked(tmp_path / "b", "credit-squad", "prj_v1_frozen"),
                  linked(tmp_path / "c", "credit-squad", "prj_not_the_v2_id")):
        result = run_cli(tmp_path, fake, "--alter", build=build)
        assert result.returncode != 0 and "REFUSED" in result.stderr
    assert not log.exists() and "SCRAM" not in result.stdout


def test_v1_ids_in_the_shell_do_not_reach_the_cli(tmp_path):
    fake, log = fake_vercel(tmp_path)
    env = {**os.environ, "VERCEL_PROJECT_ID": "prj_v1_frozen", "VERCEL_ORG_ID": "team_v1"}
    assert run_cli(tmp_path, fake, env=env).returncode == 0
    calls = log.read_text().splitlines()
    assert len(calls) == 3 and all("project=prj_new org=team_x" in c for c in calls)


def test_the_cli_prints_only_sql_and_hands_each_value_to_vercel_on_stdin(tmp_path):
    fake, log = fake_vercel(tmp_path)
    result = run_cli(tmp_path, fake)
    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert [c.split()[2] for c in calls] == ["MIGRATION_DATABASE_URL", "DATABASE_URL", "SESSION_SECRET"]
    for call in calls:
        assert "--environment production --sensitive --token proxyinjected" in call and "--force" not in call
        assert int(call.rsplit("len=", 1)[1].split()[0]) > 30  # a value arrived on standard input
    assert "postgresql" not in result.stdout and "postgresql" not in result.stderr
    assert result.stdout.count("SCRAM-SHA-256$") == 2 and "CREATE ROLE squad2_runtime" in result.stdout


def test_a_retry_with_alter_overwrites_the_variables_and_alters_the_roles(tmp_path):
    fake, log = fake_vercel(tmp_path)
    result = run_cli(tmp_path, fake, "--alter")
    assert result.returncode == 0, result.stderr
    assert all("--force" in c for c in log.read_text().splitlines())
    assert "CREATE ROLE" not in result.stdout and "GRANT" not in result.stdout
    assert result.stdout.count("ALTER ROLE") == 2


def test_a_failed_vercel_call_prints_no_sql_and_no_value(tmp_path):
    fake, _ = fake_vercel(tmp_path, fail_on="DATABASE_URL")
    result = run_cli(tmp_path, fake)
    assert result.returncode != 0
    assert "SCRAM" not in result.stdout and "postgresql" not in result.stdout + result.stderr

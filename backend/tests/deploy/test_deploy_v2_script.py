"""deploy-v2.sh must stop when the pinning step fails, link with no v1 ids from the shell, and leave no
.env.local from the link in the folder it uploads. Run against fake `npx` and `uv` in a copied tree."""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "hosted" / "deploy-v2.sh"


def tree(tmp_path, export_fails=False):
    (tmp_path / "scripts" / "hosted").mkdir(parents=True)
    shutil.copy(SCRIPT, tmp_path / "scripts" / "hosted" / "deploy-v2.sh")
    build = tmp_path / ".vercel-build-v2"
    (build / "api").mkdir(parents=True)
    (build / "api" / "target.json").write_text(json.dumps({"target": "v2"}))
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    log = tmp_path / "log.txt"
    # npx: record what it was asked and which project the environment names; `link` writes .env.local as a TTY run would
    (bin_ / "npx").write_text(f'#!/bin/sh\necho "npx $* project=${{VERCEL_PROJECT_ID:-unset}}" >> {log}\n'
                              'case "$*" in *" link "*) echo "X=1" > .env.local;; esac\n')
    export = "exit 1" if export_fails else 'printf "export VERCEL_ORG_ID=team_x\\nexport VERCEL_PROJECT_ID=prj_new\\n"'
    (bin_ / "uv").write_text(f'#!/bin/sh\ncase "$*" in *--export*) {export};; *) echo "linked: ok";; esac\n')
    for f in bin_.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "VERCEL_PROJECT_ID": "prj_v1_frozen",
           "VERCEL_ORG_ID": "team_v1"}
    return tmp_path, build, log, env


def test_a_failed_pinning_step_stops_before_deploy(tmp_path):
    root, _, log, env = tree(tmp_path, export_fails=True)
    done = subprocess.run([str(root / "scripts/hosted/deploy-v2.sh"), "--no-build"], env=env, capture_output=True, text=True)
    assert done.returncode != 0
    assert " deploy " not in log.read_text()


def test_link_runs_without_the_shells_ids_and_deploy_with_the_checked_ones_and_no_env_local_is_left(tmp_path):
    root, build, log, env = tree(tmp_path)
    done = subprocess.run([str(root / "scripts/hosted/deploy-v2.sh"), "--no-build"], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    lines = log.read_text().splitlines()
    assert any(" link " in line and "project=unset" in line for line in lines)
    assert any(" deploy " in line and "project=prj_new" in line for line in lines)
    assert not (build / ".env.local").exists()

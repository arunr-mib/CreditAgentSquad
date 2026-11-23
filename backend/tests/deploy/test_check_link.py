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


def make(folder, project=None, target="v2"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "api").mkdir()
    (folder / "api" / "target.json").write_text(json.dumps({"target": target, "schema": "squad2",
                                                            "runtime_role": "squad2_runtime"}))
    if project is not None:
        (folder / ".vercel").mkdir()
        (folder / ".vercel" / "project.json").write_text(json.dumps(project))
    return folder


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


def test_no_frozen_ids_given_on_the_command_line_means_none_are_assumed(tmp_path):
    """--frozen-ids with no values must not silently skip the id check: it is refused."""
    build = make(tmp_path, {"projectId": "prj_new", "orgId": "team_x", "projectName": "credit-squad"})
    result = subprocess.run([sys.executable, "-I", str(SCRIPT), str(build), "credit-squad", "--frozen-ids"],
                            capture_output=True, text=True)
    assert result.returncode == 1 and "frozen" in result.stderr

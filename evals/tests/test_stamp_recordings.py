"""Stamping reads git history, never guesses."""
import hashlib
import json
import subprocess

from evals.stamp_recordings import stamp


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True, capture_output=True)


def test_an_unstamped_recording_takes_the_spec_of_the_commit_that_last_wrote_it(tmp_path):
    agents = tmp_path / "backend/app/agents"
    (agents / "specs").mkdir(parents=True)
    rec = tmp_path / "evals/recordings/intake/b/2026-09-30/01.json"
    rec.parent.mkdir(parents=True)
    _git(tmp_path, "init", "-q")
    (agents / "intake.py").write_text('SPEC = AgentSpec(name="intake", version="1", x=1)\n')
    (agents / "specs/intake.md").write_text("old prompt")
    rec.write_text(json.dumps({"content": [], "stop_reason": "end_turn"}))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "one")
    (agents / "intake.py").write_text('SPEC = AgentSpec(name="intake", version="2", x=1)\n')
    (agents / "specs/intake.md").write_text("new prompt")
    rec.write_text(json.dumps({"content": [], "stop_reason": "end_turn", "model": "m"}))  # re-recorded
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "two")
    (agents / "specs/intake.md").write_text("edited after, uncommitted into the recording")
    _git(tmp_path, "commit", "-qam", "three")
    lines = stamp(tmp_path / "evals/recordings", repo=tmp_path)
    assert len(lines) == 1
    assert json.loads(rec.read_text())["_spec"] == f"intake@2:{hashlib.sha256(b'new prompt').hexdigest()[:12]}"
    assert stamp(tmp_path / "evals/recordings", repo=tmp_path) == []  # already stamped: left alone

"""One-off: stamp the recordings made before specs were stamped, from git history, never by guess.

For each unstamped recording, find the last commit that wrote it (a recording re-recorded later was
made under the later spec), read the agent file and prompt as they were in that commit, and write
"<agent>@<version>:<prompt sha>" into the file, marked `_basis: "prompt-only"`.

BEST EFFORT: a recording does not store the request it answered, and git history only shows what the agent
file and prompt said in the commit that wrote it. Tool definitions, output schema, effort and model cannot be
recovered, so these stamps verify the prompt text and agent version only. Replay compares them on that basis
and the scorecard counts them."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from evals.book import REPO

# recordings directory -> (agent module, prompt file); the spec's own name is read from the module
AGENT_FILE = {"intake": ("intake.py", "intake.md"), "spreading": ("spreading.py", "spreading.md"),
              "certificate": ("certificate.py", "certificate.md"), "collateral": ("collateral.py", "collateral.md"),
              "covenant": ("covenant.py", "covenant.md"), "early_warning": ("early_warning.py", "early_warning.md"),
              "review": ("review.py", "review.md"), "terms": ("terms_agent.py", "terms.md"),
              "copilot": ("copilot.py", "copilot.md")}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def stamp(recordings: Path, repo: Path = REPO) -> list[str]:
    done = []
    for path in sorted(recordings.rglob("*.json")):
        data = json.loads(path.read_text())
        if "_spec" in data:
            continue
        agent = path.relative_to(recordings).parts[0]
        code_file, prompt_file = AGENT_FILE[agent]
        rel = str(path.resolve().relative_to(repo.resolve()))
        commits = _git(repo, "log", "--format=%H", "-1", "--", rel).split()
        if not commits:
            raise RuntimeError(f"{rel} has no commit: cannot say what spec it was made under")
        source = _git(repo, "show", f"{commits[0]}:backend/app/agents/{code_file}")
        found = re.search(r'name="(\w+)", version="(\d+)"', source)
        if not found:
            raise RuntimeError(f"{code_file} at {commits[0]} does not declare name=..., version=... in one place")
        prompt = _git(repo, "show", f"{commits[0]}:backend/app/agents/specs/{prompt_file}")
        data["_basis"] = "prompt-only"
        data["_spec"] = f"{found.group(1)}@{found.group(2)}:{hashlib.sha256(prompt.encode()).hexdigest()[:12]}"
        path.write_text(json.dumps(data, indent=1, sort_keys=True))
        done.append(f"{path.relative_to(recordings)} -> {data['_spec']} (commit {commits[0][:7]})")
    return done


if __name__ == "__main__":
    for line in stamp(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "evals" / "recordings"):
        print(line)

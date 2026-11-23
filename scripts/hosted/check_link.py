"""Refuse to deploy to, or put variables on, anything but the v2 project.

    python scripts/hosted/check_link.py .vercel-build-v2 credit-squad [--export]

The build folder must be a v2 build linked (`.vercel/project.json`) to the named project, and the link's id must be
the id the Vercel API gives for that name and differ from both frozen projects' ids. Both are read from the API
(GET only; the proxy adds the token); tests pass them with --frozen-ids and --expected-id. Prints nothing secret:
project and team ids only.

`pinned_env()` is what the scripts that write to Vercel (`v2_secrets.py`, `v2_setup.py run`) call before their
first `vercel` command: it refuses a wrong folder and returns an environment whose VERCEL_ORG_ID and
VERCEL_PROJECT_ID come from the checked link, so ids exported in the shell (say, v1's) cannot redirect the CLI."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

FROZEN_NAMES = ("csquad", "credit-agent-squad")


def _project(name: str) -> dict:
    with urllib.request.urlopen(f"https://api.vercel.com/v9/projects/{name}", timeout=30) as response:
        return json.load(response)


def frozen_ids() -> list[str]:
    return [_project(name)["id"] for name in FROZEN_NAMES]


def expected_project_id(name: str) -> str | None:
    """The id the API gives for the v2 project's name; None when the API says there is no such project."""
    try:
        return _project(name)["id"]
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def problems(build: Path, expected: str, frozen: list[str], expected_id: str | None = None) -> list[str]:
    found = []
    if not frozen:
        found.append("no frozen project ids to compare against")
    target = build / "api" / "target.json"
    if not target.exists() or json.loads(target.read_text()).get("target") != "v2":
        found.append("the folder is not a v2 build (api/target.json missing or not v2)")
    if expected in FROZEN_NAMES:
        found.append(f"{expected} is a frozen project and never a v2 target")
    link = build / ".vercel" / "project.json"
    if not link.exists():
        return found + ["the folder is not linked: run vercel link --yes --project <name> in it"]
    project = json.loads(link.read_text())
    if project.get("projectName") != expected:
        found.append(f"linked to {project.get('projectName')!r}, expected {expected!r}")
    if not project.get("projectId") or project.get("projectId") in frozen:
        found.append("linked to no project id or to the id of a frozen project")
    if not expected_id or project.get("projectId") != expected_id:
        found.append(f"the link's project id is not the id of {expected!r} ({expected_id or 'no such project'})")
    if not project.get("orgId"):
        found.append("the link names no team (orgId)")
    return found


def pinned_env(build: Path, expected: str, frozen: list[str] | None = None, expected_id: str | None = None) -> dict:
    """Check the link, then return os.environ with VERCEL_ORG_ID/VERCEL_PROJECT_ID taken from it. Exits on a problem."""
    build = Path(build)
    frozen = frozen if frozen is not None else frozen_ids()
    expected_id = expected_id if expected_id is not None else expected_project_id(expected)
    found = problems(build, expected, frozen, expected_id)
    if found:
        raise SystemExit("REFUSED: " + "; ".join(found))
    project = json.loads((build / ".vercel" / "project.json").read_text())
    return {**os.environ, "VERCEL_ORG_ID": project["orgId"], "VERCEL_PROJECT_ID": project["projectId"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("project")
    parser.add_argument("--frozen-ids", nargs="*")
    parser.add_argument("--expected-id")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    if (args.frozen_ids is None) != (args.expected_id is None):
        parser.error("--frozen-ids and --expected-id are given together (tests) or not at all (the API is asked)")
    frozen = args.frozen_ids if args.frozen_ids is not None else frozen_ids()
    expected_id = args.expected_id if args.expected_id is not None else expected_project_id(args.project)
    found = problems(args.build, args.project, frozen, expected_id)
    if found:
        print("REFUSED: " + "; ".join(found), file=sys.stderr)
        return 1
    project = json.loads((args.build / ".vercel" / "project.json").read_text())
    if args.export:
        print(f"export VERCEL_ORG_ID={project['orgId']}\nexport VERCEL_PROJECT_ID={project['projectId']}")
    else:
        print(f"linked to {project['projectName']} ({project['projectId']}): ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

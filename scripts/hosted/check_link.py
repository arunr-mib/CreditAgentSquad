"""Refuse to deploy a build folder that is not linked to the expected v2 project.

    python scripts/hosted/check_link.py .vercel-build-v2 credit-squad [--export]

The frozen projects' ids are read from the Vercel API (GET only; the proxy adds the token); tests
pass them with --frozen-ids. Prints nothing secret: project and team ids only."""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

FROZEN_NAMES = ("csquad", "credit-agent-squad")


def frozen_ids() -> list[str]:
    ids = []
    for name in FROZEN_NAMES:
        with urllib.request.urlopen(f"https://api.vercel.com/v9/projects/{name}", timeout=30) as response:
            ids.append(json.load(response)["id"])
    return ids


def problems(build: Path, expected: str, frozen: list[str]) -> list[str]:
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
    if not project.get("orgId"):
        found.append("the link names no team (orgId)")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("project")
    parser.add_argument("--frozen-ids", nargs="*")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    found = problems(args.build, args.project, args.frozen_ids if args.frozen_ids is not None else frozen_ids())
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

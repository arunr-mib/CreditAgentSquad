# scripts/hosted/frozen_check.py
"""Record and compare what the frozen sites serve and how their Vercel projects are set, without
calling anything billable (c-squad's /api is never called) and without reading any secret value."""
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request

SITES = ["https://c-squad.vercel.app", "https://csquad-kappa.vercel.app", "https://credit-agent-squad.vercel.app"]
PROBES = {"https://credit-agent-squad.vercel.app": ["/api/_setup/status", "/api/v1/me/briefing"]}
PROJECTS = ["csquad", "credit-agent-squad"]


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""


def site(base):
    status, body = fetch(base + "/")
    out = {"/": [status, hashlib.sha256(body).hexdigest()]}
    for asset in sorted(set(re.findall(rb'(?:src|href)="(/assets/[^"]+)"', body))):
        s, b = fetch(base + asset.decode())
        out[asset.decode()] = [s, hashlib.sha256(b).hexdigest()]
    for path in PROBES.get(base, []):
        out[path] = [fetch(base + path)[0]]
    return out


def project(name):
    with urllib.request.urlopen(f"https://api.vercel.com/v9/projects/{name}", timeout=30) as response:
        p = json.load(response)
    with urllib.request.urlopen(f"https://api.vercel.com/v10/projects/{name}/env", timeout=30) as response:
        envs = json.load(response).get("envs", [])
    return {"id": p["id"], "name": p["name"], "updatedAt": p.get("updatedAt"),
            "production": (p.get("targets") or {}).get("production", {}).get("id"),
            "env": sorted(({k: e.get(k) for k in ("key", "target", "type", "updatedAt")} for e in envs),
                          key=lambda e: (e["key"], str(e["target"])))}


def capture():
    return {"sites": {s: site(s) for s in SITES}, "projects": {p: project(p) for p in PROJECTS}}


def differences(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        found = []
        for key in sorted(set(before) | set(after)):
            found += differences(before.get(key), after.get(key), f"{path}/{key}")
        return found
    return [] if before == after else [f"{path}: {before!r} -> {after!r}"]


if __name__ == "__main__":
    if sys.argv[1] == "capture":
        open(sys.argv[2], "w").write(json.dumps(capture(), indent=1, sort_keys=True))
    else:
        found = differences(json.load(open(sys.argv[2])), json.load(open(sys.argv[3])))
        print("\n".join(found) or "unchanged")
        sys.exit(1 if found else 0)

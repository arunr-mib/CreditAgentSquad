"""The frozen sites' hosts, which no Phase 5 tool may call: one list for every Python script here.

A sign-in on a frozen site appends to its append-only ledger, and c-squad's /api/* is a billable live-answer
function. The JavaScript tools use frontend/e2e/frozen-hosts.mjs, which holds the same list."""
from urllib.parse import urlsplit

FROZEN_HOSTS = ("credit-agent-squad.vercel.app", "c-squad.vercel.app", "csquad-kappa.vercel.app")
# deployment and branch URLs of the two frozen projects: <project>-<hash>-<team>.vercel.app, <project>-git-...
FROZEN_PREFIXES = ("credit-agent-squad-", "csquad-", "c-squad-")


def is_frozen(base: str) -> bool:
    host = (urlsplit(base).hostname or "").lower().rstrip(".")
    return host in FROZEN_HOSTS or (host.endswith(".vercel.app") and host.startswith(FROZEN_PREFIXES))


def refuse_frozen(base: str) -> None:
    if is_frozen(base):
        raise SystemExit(f"refused: {base} is a frozen site; nothing in Phase 5 may call it")

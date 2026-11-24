// The frozen sites' hosts, which no e2e tool may call: one list for every JavaScript tool here
// (hosted-smoke.mjs, squad.mjs, repair.mjs). A sign-in on a frozen site appends to its append-only ledger, and
// c-squad's /api/* is a billable live-answer function. The Python scripts use scripts/hosted/frozen_hosts.py,
// which holds the same list.
export const FROZEN_HOSTS = ['credit-agent-squad.vercel.app', 'c-squad.vercel.app', 'csquad-kappa.vercel.app'];
// deployment and branch URLs of the two frozen projects: <project>-<hash>-<team>.vercel.app, <project>-git-...
export const FROZEN_PREFIXES = ['credit-agent-squad-', 'csquad-', 'c-squad-'];

export function isFrozen(base) {
  const host = new URL(base).hostname.toLowerCase().replace(/\.$/, '');
  return FROZEN_HOSTS.includes(host) || (host.endsWith('.vercel.app') && FROZEN_PREFIXES.some((p) => host.startsWith(p)));
}

export function refuseFrozenHost(base) {
  if (isFrozen(base)) throw new Error(`refused: ${base} is a frozen site; nothing in Phase 5 may call it`);
}

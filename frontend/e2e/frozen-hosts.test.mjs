import { describe, expect, it } from 'vitest';
import { isFrozen, refuseFrozenHost } from './frozen-hosts.mjs';

describe('the frozen sites no e2e tool may call', () => {
  it.each([
    'https://credit-agent-squad.vercel.app', 'https://c-squad.vercel.app/', 'https://csquad-kappa.vercel.app',
    'https://credit-agent-squad-abc123-team.vercel.app', 'https://csquad-git-main-team.vercel.app', 'https://CREDIT-AGENT-SQUAD.vercel.app',
  ])('refuses %s', (base) => {
    expect(isFrozen(base)).toBe(true);
    expect(() => refuseFrozenHost(base)).toThrow(/frozen/);
  });

  it.each(['https://credit-squad.vercel.app', 'https://credit-squad-abc-team.vercel.app', 'http://localhost:5173', 'http://localhost:5174'])('allows %s', (base) => {
    expect(isFrozen(base)).toBe(false);
    expect(() => refuseFrozenHost(base)).not.toThrow();
  });
});

import { describe, expect, it } from 'vitest';
import { ANSWER_KEYS, CASE_KEYS } from '../api/hooks';

const sources = import.meta.glob('/src/**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
const queryKeys = new Set(Object.values(sources).flatMap((text) => [...text.matchAll(/queryKey: \['([a-z-]+)'/g)].map((m) => m[1])));

describe('what a write refreshes (final review M13)', () => {
  it('names only query keys that exist: the portfolio is "my-portfolio"', () => {
    expect(CASE_KEYS).toContain('my-portfolio');
    expect(CASE_KEYS).not.toContain('portfolio');
    for (const key of CASE_KEYS) expect(queryKeys.has(key), key).toBe(true);
  });

  it('an answer to a match question refreshes the case and Approvals at once, not at the next heartbeat', () => {
    expect(ANSWER_KEYS).toEqual(expect.arrayContaining(['case', 'approvals', 'trail']));
  });
});

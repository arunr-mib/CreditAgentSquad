import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { contrast, LOOKS, LOOK_IDS } from '../looks';

const css = readFileSync(resolve(__dirname, '../squad.css'), 'utf8');
const rule = (selector: string) => {
  const m = css.split('\n').find((l) => l.startsWith(`${selector} {`));
  if (!m) throw new Error(`no rule for ${selector}`);
  return m;
};

describe('control borders', () => {
  it.each(['.sq-composer textarea', '.sq-why textarea', '.sq-option', '.sq-draftbox'])('%s uses the strong line, which is a visible control edge', (selector) => {
    expect(rule(selector)).toContain('border: 1px solid var(--sq-line-strong)');
    expect(rule(selector)).not.toMatch(/var\(--sq-line\)/);
  });

  it('the strong line is at least 3:1 against its surface in every look', () => {
    for (const id of LOOK_IDS) expect(contrast(LOOKS[id].vars.lineStrong, LOOKS[id].vars.surface), id).toBeGreaterThanOrEqual(3);
  });
});

import { describe, expect, it } from 'vitest';
import css from '../tokens.css?raw';

const rootBlock = css.slice(css.indexOf(':root {'), css.indexOf('@theme'));

function token(name: string): string {
  const match = new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`).exec(rootBlock);
  if (!match?.[1]) throw new Error(`Token --${name} is not a six-digit hex colour`);
  return match[1];
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * (channels[0] ?? 0) + 0.7152 * (channels[1] ?? 0) + 0.0722 * (channels[2] ?? 0);
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const SURFACES = ['canvas', 'surface', 'surface-sunken', 'surface-hover'];
const TEXT = ['ink-900', 'ink-700', 'ink-500', 'cobalt', 'cobalt-strong', 'iris', 'red', 'amber', 'green'];

describe('design tokens', () => {
  it.each(TEXT.flatMap((text) => SURFACES.map((surface) => [text, surface] as const)))('%s on %s passes WCAG AA for text (4.5:1)', (text, surface) => {
    expect(contrast(token(text), token(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it.each([
    ['cobalt-strong', 'cobalt-bg'],
    ['ink-900', 'cobalt-bg'],
    ['ink-700', 'cobalt-bg'],
    ['iris', 'iris-bg'],
    ['ink-900', 'iris-bg'],
    ['ink-700', 'iris-bg'],
    ['amber', 'iris-bg'],
    ['green', 'iris-bg'],
    ['red', 'red-bg'],
    ['amber', 'amber-bg'],
    ['green', 'green-bg'],
    ['red', 'cobalt-bg'],
  ] as const)('%s on its tinted ground %s passes AA for text', (text, ground) => {
    expect(contrast(token(text), token(ground))).toBeGreaterThanOrEqual(4.5);
  });

  it('white text on the primary button passes AA', () => {
    expect(contrast('#ffffff', token('cobalt'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', token('cobalt-strong'))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(
    ['red-mark', 'amber-mark', 'green-mark', 'iris-mark', 'ink-400', 'cobalt'].flatMap((mark) =>
      ['canvas', 'surface', 'surface-sunken'].map((s) => [mark, s] as const),
    ),
  )('%s on %s passes 3:1 for marks, control borders and focus rings', (mark, surface) => {
    expect(contrast(token(mark), token(surface))).toBeGreaterThanOrEqual(3);
  });

  it('defines exactly two shadow steps', () => {
    const shadows = [...rootBlock.matchAll(/--shadow-[a-z]+:/g)].map((m) => m[0]);
    expect(shadows).toEqual(['--shadow-raised:', '--shadow-overlay:']);
  });

  it('keeps every motion duration at or under 240 ms', () => {
    const durations = [...rootBlock.matchAll(/--motion-[a-z]+:\s*(\d+)ms/g)].map((m) => Number(m[1]));
    expect(durations.length).toBeGreaterThanOrEqual(4);
    expect(Math.max(...durations)).toBeLessThanOrEqual(240);
  });

  it('spaces on a 4 px scale', () => {
    const spaces = [...rootBlock.matchAll(/--space-\d+:\s*(\d+)px/g)].map((m) => Number(m[1]));
    expect(spaces.every((value) => value % 4 === 0)).toBe(true);
  });
});

import { describe, expect, it } from 'vitest';
import { legalFormLabel } from './labels';

describe('a legal form', () => {
  it('writes known abbreviations as they are written in an agreement', () => {
    expect(legalFormLabel('llc')).toBe('LLC');
    expect(legalFormLabel('LLP')).toBe('LLP');
    expect(legalFormLabel('corporation')).toBe('Corporation');
    expect(legalFormLabel('s_corporation')).toBe('S corporation');
    expect(legalFormLabel('limited_partnership')).toBe('Limited partnership');
    expect(legalFormLabel(null)).toBe('');
  });
});

import { describe, expect, it } from 'vitest';
import { clientFile } from '../links';
import { oldAddress } from '../redirects';

describe('old addresses', () => {
  it.each([
    ['/borrowers/QFL', '/clients/QFL/file'],
    ['/borrowers/QFL/covenants', '/clients/QFL/file/covenants'],
    ['/borrowers/QFL/spreads', '/clients/QFL/file/spreads'],
    ['/borrowers/QFL/timeline', '/clients/QFL/file/history'],
    ['/borrowers/QFL/borrowing-base', '/clients/QFL/file/loans'],
    ['/borrowers/QFL/signals', '/clients/QFL/file'],
    ['/borrowers/QFL/packages', '/clients/QFL/file/packages'],
    ['/borrowers', '/portfolio'],
    ['/agent-activity', '/oversight/activity'],
    ['/governance', '/oversight/governance'],
    ['/command-centre', '/'],
    ['/calendar', '/'],
    ['/design', '/'],
  ])('%s goes to %s', (from, to) => expect(oldAddress(from, {})).toBe(to));

  it('keeps the document and page of a document link', () => {
    expect(oldAddress('/borrowers/QFL/documents/d1', { page: 3 })).toBe('/clients/QFL/file/documents?document=d1&page=3');
  });

  it('sends a role without Oversight home, never to a refusal', () => {
    for (const path of ['/agent-activity', '/governance']) expect(oldAddress(path, {}, { oversight: false })).toBe('/');
    expect(oldAddress('/governance', {}, { oversight: true })).toBe('/oversight/governance');
    expect(oldAddress('/borrowers/QFL/covenants', {}, { oversight: false })).toBe('/clients/QFL/file/covenants');
  });

  it('keeps the part of Oversight an old query named', () => {
    expect(oldAddress('/governance', { tab: 'ledger' })).toBe('/oversight/ledger');
    expect(oldAddress('/governance', { tab: 'clock' })).toBe('/oversight/clock');
    expect(oldAddress('/governance', { tab: 'nonsense' })).toBe('/oversight/governance');
    expect(oldAddress('/agent-activity', { run: 'r1' })).toBe('/oversight/activity');
  });

  it('leaves every Squad address alone', () => {
    for (const path of ['/', '/clients/QFL', '/clients/QFL/file/spreads', '/approvals', '/review-room']) expect(oldAddress(path, {})).toBeNull();
  });

  it('builds client file addresses in one place', () => {
    expect(clientFile('QFL')).toBe('/clients/QFL/file');
    expect(clientFile('QFL', 'overview')).toBe('/clients/QFL/file');
    expect(clientFile('QFL', 'covenants')).toBe('/clients/QFL/file/covenants');
  });
});

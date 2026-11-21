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
  ])('%s goes to %s', (from, to) => expect(oldAddress(from, {})).toBe(to));

  it('keeps the document and page of a document link', () => {
    expect(oldAddress('/borrowers/QFL/documents/d1', { page: 3 })).toBe('/clients/QFL/file/documents?document=d1&page=3');
  });

  it('leaves every Squad address alone', () => {
    for (const path of ['/', '/clients/QFL', '/clients/QFL/file/spreads', '/approvals']) expect(oldAddress(path, {})).toBeNull();
  });

  it('builds client file addresses in one place', () => {
    expect(clientFile('QFL')).toBe('/clients/QFL/file');
    expect(clientFile('QFL', 'overview')).toBe('/clients/QFL/file');
    expect(clientFile('QFL', 'covenants')).toBe('/clients/QFL/file/covenants');
  });
});

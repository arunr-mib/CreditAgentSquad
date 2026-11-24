import { clientFile, type ClientFileView } from './links';

const OLD_VIEWS: Record<string, ClientFileView> = {
  '': 'overview', loans: 'loans', documents: 'documents', spreads: 'spreads', covenants: 'covenants',
  'borrowing-base': 'loans', signals: 'overview', reviews: 'reviews', packages: 'packages', timeline: 'history',
};

/** Where an address from the retired cockpit now lives, or null for an address that is not an old one. */
export function oldAddress(pathname: string, search: Record<string, unknown>, who: { oversight?: boolean } = {}): string | null {
  const oversight = who.oversight ?? true; // a role without Oversight is sent home: no address lands on a refusal
  if (pathname === '/agent-activity') return oversight ? '/oversight/activity' : '/';
  if (pathname === '/governance') {
    const tab = typeof search.tab === 'string' && ['ledger', 'clock'].includes(search.tab) ? search.tab : 'governance';
    return oversight ? `/oversight/${tab}` : '/';
  }
  const moved: Record<string, string> = { '/command-centre': '/', '/calendar': '/', '/design': '/' };
  if (moved[pathname]) return moved[pathname];
  if (pathname === '/borrowers' || pathname === '/borrowers/') return '/portfolio';
  const doc = /^\/borrowers\/([^/]+)\/documents\/([^/]+)\/?$/.exec(pathname);
  if (doc?.[1] && doc[2]) {
    const page = typeof search.page === 'number' || typeof search.page === 'string' ? `&page=${search.page}` : '';
    return `${clientFile(doc[1], 'documents')}?document=${encodeURIComponent(doc[2])}${page}`;
  }
  const match = /^\/borrowers\/([^/]+)(?:\/([^/]+))?\/?$/.exec(pathname);
  if (!match?.[1]) return null;
  return clientFile(match[1], OLD_VIEWS[match[2] ?? ''] ?? 'overview');
}

import { Link, Outlet, useParams, useRouterState } from '@tanstack/react-router';
import { useBorrower, useBorrowerByCode, useBorrowerOverview } from '@/api/hooks';
import type { BorrowerRow } from '@/api/schema';
import { Button, MetaItem, PageHeader, SkeletonRows, tabClass, tabListClass } from '@/design';
import { humanize } from '@/domain/labels';
import { FactFigure } from '@/source/figures';
import { EmptyCard, ErrorNotice } from '../parts';

const TABS: Array<{ label: string; path: string }> = [
  { label: 'Summary', path: '' },
  { label: 'Loans', path: '/loans' },
  { label: 'Documents', path: '/documents' },
  { label: 'Spreads', path: '/spreads' },
  { label: 'Covenants', path: '/covenants' },
  { label: 'Borrowing base', path: '/borrowing-base' },
  { label: 'Signals', path: '/signals' },
  { label: 'Reviews', path: '/reviews' },
  { label: 'Packages', path: '/packages' },
  { label: 'Timeline', path: '/timeline' },
];

/** The borrower in the address bar. Tabs render only once it is known, so they can rely on it. */
export function useCurrentBorrower(): BorrowerRow {
  const { code } = useParams({ strict: false }) as { code: string };
  const { borrower } = useBorrowerByCode(code);
  if (!borrower) throw new Error('Borrower tabs render inside the borrower layout');
  return borrower;
}

export function BorrowerLayout() {
  const { code } = useParams({ strict: false }) as { code: string };
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const lookup = useBorrowerByCode(code);
  const borrower = lookup.borrower;
  const detail = useBorrower(borrower?.id);
  const overview = useBorrowerOverview(borrower?.id);

  if (lookup.error) return <ErrorNotice error={lookup.error} what="The borrower" onRetry={() => void lookup.refetch()} />;
  if (lookup.notFound) {
    return (
      <EmptyCard
        title="No borrower has this record"
        description={`Nothing in the book is filed under “${code}”.`}
        action={
          <Button asChild>
            <Link to="/borrowers">Open the borrower directory</Link>
          </Button>
        }
      />
    );
  }
  if (!borrower) return <SkeletonRows rows={10} label="Loading the borrower" />;

  const base = `/borrowers/${borrower.code}`;
  const exposure = overview.data?.exposure;
  const place = [detail.data?.profile.city, detail.data?.profile.state].filter(Boolean).join(', ');

  return (
    <div className="space-y-5">
      <div>
        <PageHeader
          eyebrow={
            <>
              Borrower <span className="ident tracking-normal normal-case">{borrower.code}</span>
            </>
          }
          title={borrower.name}
          meta={
            <>
              <span>
                {humanize(borrower.industry)}
                {place ? ` · ${place}` : ''}
              </span>
              {exposure?.revolver_outstanding ? (
                <MetaItem label="Line of credit">
                  <FactFigure fact={exposure.revolver_outstanding} /> <span className="text-ink-500">drawn of</span> <FactFigure fact={exposure.commitment} />
                </MetaItem>
              ) : null}
              {exposure?.term_loan_outstanding ? (
                <MetaItem label="Term loan">
                  <FactFigure fact={exposure.term_loan_outstanding} />
                </MetaItem>
              ) : null}
              <MetaItem label="Risk rating">
                <span className="tnum">{borrower.risk_rating ?? 'Not rated'}</span>
              </MetaItem>
            </>
          }
          actions={
            <dl className="grid grid-cols-[auto_auto] gap-x-3 text-caption">
              <dt className="text-ink-500">Relationship manager</dt>
              <dd className="text-ink">{borrower.relationship_manager ?? 'Not assigned'}</dd>
              <dt className="text-ink-500">Credit analyst</dt>
              <dd className="text-ink">{borrower.analyst ?? 'Not assigned'}</dd>
            </dl>
          }
        />
        <nav aria-label="Borrower sections" className={`${tabListClass} mt-4`}>
          {TABS.map((tab) => {
            const to = `${base}${tab.path}`;
            const current = tab.path === '' ? pathname === base || pathname === `${base}/` : pathname.startsWith(to);
            return (
              <Link key={tab.label} to={to} activeOptions={{ exact: true }} activeProps={{}} aria-current={current ? 'page' : undefined} className={tabClass}>
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <Outlet />
    </div>
  );
}

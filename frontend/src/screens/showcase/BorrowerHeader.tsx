import { Link } from '@tanstack/react-router';
import type { FactMap } from '@/api/types';
import { Figure, MetaItem, PageHeader, tabClass, tabListClass, Tooltip } from '@/design';

interface BorrowerSummary {
  id: string;
  name: string;
  industry: string;
  location: string;
  relationshipManager: string;
  analyst: string;
  lineCommitmentFactId: string;
  lineDrawnFactId: string;
  termOutstandingFactId: string;
}

const SECTIONS: Array<{ label: string; to?: '/showcase/spread' | '/showcase/covenants' }> = [
  { label: 'Summary' },
  { label: 'Loans' },
  { label: 'Documents' },
  { label: 'Spreads', to: '/showcase/spread' },
  { label: 'Covenants', to: '/showcase/covenants' },
  { label: 'Borrowing base' },
  { label: 'Signals' },
  { label: 'Reviews' },
  { label: 'Timeline' },
];

export function BorrowerHeader({ borrower, facts, current }: { borrower: BorrowerSummary; facts: FactMap; current: 'Spreads' | 'Covenants' }) {
  const drawn = facts[borrower.lineDrawnFactId];
  const commitment = facts[borrower.lineCommitmentFactId];
  const term = facts[borrower.termOutstandingFactId];
  return (
    <div>
      <PageHeader
        eyebrow={
          <>
            Borrower <span className="ident tracking-normal normal-case">{borrower.id}</span>
          </>
        }
        title={borrower.name}
        meta={
          <>
            <span>
              {borrower.industry} · {borrower.location}
            </span>
            {drawn && commitment ? (
              <MetaItem label="Line of credit">
                <Figure fact={drawn} /> <span className="text-ink-500">drawn of</span> <Figure fact={commitment} />
              </MetaItem>
            ) : null}
            {term ? (
              <MetaItem label="Term loan">
                <Figure fact={term} />
              </MetaItem>
            ) : null}
          </>
        }
        actions={
          <dl className="grid grid-cols-[auto_auto] gap-x-3 text-caption">
            <dt className="text-ink-500">Relationship manager</dt>
            <dd className="text-ink">{borrower.relationshipManager}</dd>
            <dt className="text-ink-500">Credit analyst</dt>
            <dd className="text-ink">{borrower.analyst}</dd>
          </dl>
        }
      />
      <nav aria-label="Borrower sections" className={`${tabListClass} mt-4`}>
        {SECTIONS.map((section) =>
          section.to ? (
            <Link key={section.label} to={section.to} aria-current={section.label === current ? 'page' : undefined} className={tabClass}>
              {section.label}
            </Link>
          ) : (
            <Tooltip key={section.label} content="Arrives in a later milestone">
              <span tabIndex={0} role="link" aria-disabled="true" className={tabClass}>
                {section.label}
              </span>
            </Tooltip>
          ),
        )}
      </nav>
    </div>
  );
}

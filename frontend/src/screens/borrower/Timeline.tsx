import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTimeline } from '@/api/hooks';
import type { LedgerEvent } from '@/api/schema';
import { formatDate, Segmented, StatusDot } from '@/design';
import { actionLabel, humanize } from '@/domain/labels';
import { describeEvent } from '../Governance';
import { EmptyCard, Load, SectionHead } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';

function who(event: LedgerEvent) {
  if (event.actor_name) return <span className="text-ink">{event.actor_name}</span>;
  if (event.actor_type === 'agent') return <StatusDot tone="agent">{humanize(event.actor_id)} agent</StatusDot>;
  return <span className="text-ink-500">{event.actor_id === 'seed' ? 'Loaded with the book' : 'System'}</span>;
}

export function Timeline() {
  const borrower = useCurrentBorrower();
  const [routine, setRoutine] = useState('main');
  const timeline = useTimeline(borrower.id, routine === 'all');
  return (
    <section data-ready={timeline.data ? '' : undefined} aria-labelledby="timeline-heading">
      <SectionHead
        id="timeline-heading"
        title="Timeline"
        note="From the ledger, newest first. Times are when the event was recorded, in UTC."
        actions={
          <Segmented
            label="Events shown"
            value={routine}
            onValueChange={setRoutine}
            options={[
              { value: 'main', label: 'Decisions and results' },
              { value: 'all', label: 'With routine events' },
            ]}
          />
        }
      />
      <Load query={timeline} what="The timeline" rows={12}>
        {(events) => {
          if (events.length === 0) return <EmptyCard title="Nothing is recorded for this borrower yet" description="Documents, tests, signals and decisions appear here as they are written to the ledger." />;
          const days = new Map<string, LedgerEvent[]>();
          for (const event of events) days.set(event.ts.slice(0, 10), [...(days.get(event.ts.slice(0, 10)) ?? []), event]);
          return (
            <div className="rounded-md border border-hairline-strong bg-surface">
              {[...days.entries()].map(([day, entries]) => (
                <div key={day}>
                  <h3 className="eyebrow sticky top-(--topbar-h) z-10 border-b border-ink bg-surface px-4 pt-3 pb-1.5 first:rounded-t-md">
                    {formatDate(day)} <span className="font-medium tracking-normal normal-case">· {entries.length} events</span>
                  </h3>
                  <ol>
                    {entries.map((event) => (
                      <li key={event.seq} className="grid min-h-[34px] grid-cols-[52px_minmax(0,1fr)] items-baseline gap-x-4 border-b border-hairline px-4 py-1.5 text-body last:border-b-0 max-md:[&>*:nth-child(n+3)]:col-start-2 md:grid-cols-[52px_190px_minmax(0,1fr)_200px_auto]">
                        <span className="tnum text-ink-500">{event.ts.slice(11, 16)}</span>
                        <span className="font-medium text-ink">{actionLabel(event.action)}</span>
                        <span className="text-pretty text-ink-700">{describeEvent(event)}</span>
                        <span>{who(event)}</span>
                        <Link to="/governance" search={{ tab: 'ledger', entity: event.entity_id }} className="link text-caption">
                          No. <span className="tnum">{event.seq}</span>
                          <span className="sr-only"> in the ledger</span>
                        </Link>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          );
        }}
      </Load>
    </section>
  );
}

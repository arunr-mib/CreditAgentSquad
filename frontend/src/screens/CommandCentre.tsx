import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo, useRef, type ReactNode } from 'react';
import { usePortfolio, useWorkItems } from '@/api/hooks';
import type { WorkItemRow } from '@/api/schema';
import type { Severity } from '@/api/types';
import { useAuth } from '@/auth/context';
import { AgentMark, Button, DataTable, EmptyState, formatDate, formatDue, PageHeader, Segmented, Select, SkeletonRows, StatusDot, type DataColumn } from '@/design';
import { isBreachItem, ITEM_GROUP_LABEL, itemGroup, itemTypeLabel, OUTCOME, quarterLabel, SEVERITY_LABEL, SEVERITY_RANK, STAGE_ORDER, stageLabel, type ItemGroup } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { useAsOf } from '@/shell/AsOf';
import { EmptyCard, ErrorNotice, SeverityDot } from './parts';
import { WorkItemPanel } from './work/WorkItemPanel';

/** A headline count with its breakdown. Counts of records are not facts: each links to the list it counts. */
function SummaryBlock({ label, value, note, children }: { label: string; value: number; note: string; children: ReactNode }) {
  return (
    <div className="min-w-0 border-hairline-strong py-3.5 max-md:odd:pr-4 max-md:even:border-l max-md:even:pl-4 max-md:nth-[n+3]:border-t md:px-5 md:first:pl-0 md:last:pr-0">
      <h2 className="eyebrow md:whitespace-nowrap">{label}</h2>
      <p className="mt-0.5 flex items-baseline gap-x-2 max-md:flex-wrap">
        <span className="tnum text-display font-semibold tracking-[-0.02em] text-ink">{value}</span>
        <span className="text-caption whitespace-nowrap text-ink-500">{note}</span>
      </p>
      <ul className="mt-1.5 grid grid-cols-1 border-t border-hairline pt-1.5 text-body">{children}</ul>
    </div>
  );
}

const countRowClass =
  'group flex min-h-[22px] w-full items-baseline justify-between gap-3 rounded-xs text-left text-ink-700 t-colors hover:text-cobalt-strong aria-pressed:text-cobalt-strong md:h-[22px] md:whitespace-nowrap';
const countClass = 'tnum font-semibold text-ink group-hover:text-cobalt-strong group-aria-pressed:text-cobalt-strong';

/** The borrower's name leads every title; the table already has a borrower column. */
function shortTitle(item: WorkItemRow): string {
  const prefix = `${item.borrower_name}: `;
  const rest = item.borrower_name && item.title.startsWith(prefix) ? item.title.slice(prefix.length) : item.title;
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low'];

export function CommandCentre() {
  const queue = useWorkItems({ status: 'open' });
  const portfolio = usePortfolio();
  const { asOf } = useAsOf();
  const { can, user } = useAuth();
  const search = useSearch({ from: '/command-centre' });
  const navigate = useNavigate({ from: '/command-centre' });

  const items = useMemo(() => queue.data ?? [], [queue.data]);
  const severity = search.severity && SEVERITIES.includes(search.severity as Severity) ? search.severity : 'all';
  const group = search.type ?? 'all';
  const setSearch = (next: { item?: string; severity?: string; type?: string }) =>
    void navigate({ search: (previous) => ({ ...previous, ...next }), replace: true, resetScroll: false });

  const groupCounts = useMemo(() => {
    const counts = new Map<ItemGroup, number>();
    for (const item of items) counts.set(itemGroup(item.item_type), (counts.get(itemGroup(item.item_type)) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [items]);

  const filtered = useMemo(
    () =>
      items.filter(
        (item) =>
          (severity === 'all' || item.severity === severity) &&
          (group === 'all' || (group === 'mine' ? can(item.required_permission) : itemGroup(item.item_type) === group)),
      ),
    [items, severity, group, can],
  );

  const selected = filtered.find((item) => item.id === search.item) ?? filtered[0] ?? null;
  const panelRef = useRef<HTMLElement>(null);
  /** Below 1024 px the selected item sits under the queue, out of sight: choosing a row brings it into view. */
  const showPanel = () => {
    if (window.matchMedia?.('(max-width: 1023px)').matches) requestAnimationFrame(() => panelRef.current?.scrollIntoView({ block: 'start' }));
  };
  const mine = items.filter((item) => can(item.required_permission)).length;

  const columns = useMemo<Array<DataColumn<WorkItemRow>>>(
    () => [
      { id: 'severity', header: 'Severity', sortValue: (item) => SEVERITY_RANK[item.severity], cell: (item) => <SeverityDot severity={item.severity} /> },
      {
        id: 'borrower',
        header: 'Borrower',
        rowHeader: true,
        wrap: 'narrow',
        minWidth: '150px',
        sortValue: (item) => item.borrower_name,
        cell: (item) => <span className="font-medium text-ink">{item.borrower_name}</span>,
      },
      {
        id: 'summary',
        header: 'Question',
        wrap: true,
        width: '46%',
        sortValue: (item) => shortTitle(item),
        cell: (item) =>
          isBreachItem(item.item_type) ? (
            <StatusDot tone="breach" emphasis className="!whitespace-normal">
              {shortTitle(item)}
            </StatusDot>
          ) : (
            <span className="text-ink-700">{shortTitle(item)}</span>
          ),
      },
      {
        id: 'agent',
        header: 'Agent',
        sortValue: (item) => (item.agent_run_id ? 0 : 1),
        cell: (item) =>
          item.agent_run_id ? (
            <span className="inline-flex items-center gap-1.5 text-ink">
              <AgentMark size={8} />
              Note attached
            </span>
          ) : (
            <span className="text-ink-500">A person decides</span>
          ),
      },
      {
        id: 'due',
        header: 'Due',
        align: 'right',
        sortValue: (item) => item.due_date,
        cell: (item) => {
          if (!item.due_date || !asOf) return <span className="text-ink-500">Not set</span>;
          const due = formatDue(item.due_date, asOf);
          return <span className={cx('tnum', due.overdue ? 'font-medium text-amber' : due.today ? 'font-medium text-ink' : 'text-ink-700')}>{due.text}</span>;
        },
      },
    ],
    [asOf],
  );

  const summary = portfolio.data;
  const header = (
    <PageHeader
      eyebrow="Bank of Stoic · Commercial lending"
      title="Command centre"
      meta={
        summary ? (
          <span>
            {summary.period_end ? `Monitoring cycle for the quarter ended ${formatDate(summary.period_end)}` : 'No monitoring cycle is open'} · {summary.work_items.open} items need a
            person{user ? `, ${mine} of them open to your role` : ''}
          </span>
        ) : undefined
      }
    />
  );

  if (queue.error) {
    return (
      <div className="space-y-5">
        {header}
        <ErrorNotice error={queue.error} what="The work queue" onRetry={() => void queue.refetch()} />
      </div>
    );
  }
  if (!queue.data) {
    return (
      <div className="space-y-5">
        {header}
        <SkeletonRows rows={10} label="Loading the work queue" />
      </div>
    );
  }

  return (
    <div data-ready className="space-y-5">
      {header}

      {summary ? (
        <section aria-label="Portfolio summary" className="grid grid-cols-2 divide-hairline-strong border-t border-b border-t-ink border-b-hairline-strong md:grid-cols-4 md:divide-x">
          <SummaryBlock label="Cycles in progress" value={summary.cycles.open} note={`of ${summary.borrowers} borrowers`}>
            {[...summary.cycles.by_stage]
              .sort((a, b) => STAGE_ORDER.indexOf(a.stage) - STAGE_ORDER.indexOf(b.stage))
              .map((entry) => (
                <li key={entry.stage}>
                  <Link to="/portfolio" className={countRowClass}>
                    {stageLabel(entry.stage)} <span className={countClass}>{entry.count}</span>
                  </Link>
                </li>
              ))}
          </SummaryBlock>
          <SummaryBlock label="Open exceptions" value={items.length} note="by type">
            {groupCounts.map(([key, count]) => (
              <li key={key}>
                <button type="button" aria-pressed={group === key} onClick={() => setSearch({ type: group === key ? undefined : key, item: undefined })} className={countRowClass}>
                  <span className="group-aria-pressed:underline group-aria-pressed:decoration-cobalt group-aria-pressed:underline-offset-4">{ITEM_GROUP_LABEL[key]}</span>
                  <span className={countClass}>{count}</span>
                </button>
              </li>
            ))}
          </SummaryBlock>
          <SummaryBlock label="Covenant tests" value={summary.covenants.tests} note={summary.period_end ? quarterLabel(summary.period_end) : 'latest period'}>
            {[...summary.covenants.by_outcome]
              .sort((a, b) => OUTCOME[a.outcome].rank - OUTCOME[b.outcome].rank)
              .map((entry) => (
                <li key={entry.outcome}>
                  <Link to="/portfolio" className={countRowClass}>
                    <StatusDot tone={OUTCOME[entry.outcome].tone} emphasis={OUTCOME[entry.outcome].emphasis} className="max-md:whitespace-normal!">
                      {OUTCOME[entry.outcome].label}
                    </StatusDot>
                    <span className={countClass}>{entry.count}</span>
                  </Link>
                </li>
              ))}
          </SummaryBlock>
          <SummaryBlock label="Reporting due" value={summary.obligations.due_within_7_days} note="in the next 7 days">
            <li>
              <Link to="/calendar" className={countRowClass}>
                <StatusDot tone={summary.obligations.overdue > 0 ? 'attention' : 'muted'}>Overdue</StatusDot>
                <span className={countClass}>{summary.obligations.overdue}</span>
              </Link>
            </li>
            <li>
              <Link to="/calendar" className={countRowClass}>
                Received, last 30 days <span className={countClass}>{summary.obligations.received_in_last_30_days}</span>
              </Link>
            </li>
            <li>
              <Link to="/portfolio" className={countRowClass}>
                Open signals <span className={countClass}>{summary.signals.open}</span>
              </Link>
            </li>
          </SummaryBlock>
        </section>
      ) : portfolio.error ? (
        <ErrorNotice error={portfolio.error} what="The portfolio summary" onRetry={() => void portfolio.refetch()} />
      ) : (
        <SkeletonRows rows={3} label="Loading the portfolio summary" />
      )}

      {items.length === 0 ? (
        <EmptyCard
          title="Nothing needs a person"
          description="Every open cycle is either running or waiting for documents. New exceptions appear here as the agents and the calculations raise them."
          action={
            <Button asChild>
              <Link to="/portfolio">Open the portfolio</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
          <section aria-label="Work queue" className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <div className="relative -m-1 max-w-[calc(100%+8px)] overflow-x-auto p-1 max-sm:[&_button]:px-2">
                <Segmented
                  label="Severity"
                  value={severity}
                  onValueChange={(value) => setSearch({ severity: value === 'all' ? undefined : value, item: undefined })}
                  options={[
                    { value: 'all', label: 'All', count: items.length },
                    ...SEVERITIES.map((level) => ({ value: level, label: SEVERITY_LABEL[level], count: items.filter((item) => item.severity === level).length })),
                  ]}
                />
              </div>
              <Select
                label="Type"
                hideLabel
                className="w-full sm:w-52"
                value={group}
                onValueChange={(value) => setSearch({ type: value === 'all' ? undefined : value, item: undefined })}
                options={[
                  { value: 'all', label: 'All types' },
                  { value: 'mine', label: `My role can decide (${mine})` },
                  ...groupCounts.map(([key]) => ({ value: key, label: ITEM_GROUP_LABEL[key] })),
                ]}
              />
              <p className="ml-auto text-caption text-ink-500" aria-live="polite">
                {filtered.length} of {items.length} · by severity, then due date
              </p>
            </div>
            <DataTable
              caption="Work queue, ordered by severity and then due date"
              data={filtered}
              columns={columns}
              getRowId={(item) => item.id}
              selectedRowId={selected?.id ?? null}
              onRowActivate={(item) => {
                setSearch({ item: item.id });
                showPanel();
              }}
              stickyTop="var(--topbar-h)"
              narrow="stack"
              empty={
                <EmptyState
                  title="Nothing matches these filters"
                  description="No open item has this severity and type together."
                  action={<Button onClick={() => setSearch({ severity: undefined, type: undefined, item: undefined })}>Clear filters</Button>}
                />
              }
            />
            <p className="mt-2 text-caption text-ink-500">Up and Down move between rows. Enter opens the item. {selected ? `Showing: ${itemTypeLabel(selected.item_type)}.` : ''}</p>
          </section>

          <aside ref={panelRef} aria-label="Selected item" className="min-w-0 scroll-mt-16 max-md:min-h-[calc(100dvh-120px)] xl:sticky xl:top-[68px] xl:max-h-[calc(100vh-88px)] xl:overflow-y-auto xl:rounded-md">
            {selected ? <WorkItemPanel key={selected.id} itemId={selected.id} /> : <EmptyCard title="No item selected" description="Choose a row in the queue to see its question, evidence and decision." />}
          </aside>
        </div>
      )}
    </div>
  );
}

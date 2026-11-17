import { Link } from '@tanstack/react-router';
import { useMemo, useState, type ReactNode } from 'react';
import { useWorkQueue } from '@/api/queries';
import type { RecommendationKind, Severity, WorkItem, WorkItemGroup } from '@/api/types';
import {
  AgentMark,
  AgentNote,
  Button,
  Card,
  DataTable,
  EmptyState,
  FactsProvider,
  formatDate,
  formatDue,
  PageHeader,
  Segmented,
  Select,
  SkeletonRows,
  StatusDot,
  useToast,
  WorkItemCard,
  type DataColumn,
  type StatusTone,
} from '@/design';
import { workItemGroup, workItemGroupLabel, workItemTypeLabel } from '@/fixtures/workItems';
import { cx } from '@/lib/cx';
import { useAsOf } from '@/shell/AsOf';

const SEVERITY_LABEL: Record<Severity, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
const SEVERITY_RANK: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };

/**
 * One severity always looks the same, and never uses red: red is a covenant breach, and a breach
 * is marked on the question, not on the severity. Critical and high are amber (they need a person
 * now); medium is ink; low is hollow.
 */
const SEVERITY_TONE: Record<Severity, StatusTone> = { critical: 'attention', high: 'attention', medium: 'neutral', low: 'muted' };

const STAGE_LABEL: Record<string, string> = {
  awaiting_package: 'Awaiting package',
  intake: 'Intake',
  spreading: 'Spreading',
  covenant_testing: 'Covenant testing',
  borrowing_base: 'Borrowing base',
  signals: 'Signals',
  review_prep: 'Review prep',
};

const AGENT_LABEL: Record<RecommendationKind, string> = {
  escalate: 'Recommends escalate',
  request: 'Recommends request',
  resolve: 'Recommends resolve',
  abstain: 'Abstains',
  draft: 'Draft ready',
};

const isBreach = (item: WorkItem) => item.type === 'covenant.breach' || item.type === 'covenant.reported_mismatch';

function SeverityDot({ severity }: { severity: Severity }) {
  return (
    <StatusDot tone={SEVERITY_TONE[severity]}>
      <span className={severity === 'critical' ? 'font-semibold' : undefined}>{SEVERITY_LABEL[severity]}</span>
    </StatusDot>
  );
}

/** A headline count with its breakdown: label on the left, count right-aligned in tabular numerals. */
function SummaryBlock({ label, value, note, columns = 1, children }: { label: string; value: number; note: string; columns?: 1 | 2; children: ReactNode }) {
  return (
    <div className="min-w-0 items-start gap-x-8 px-5 py-3.5 first:pl-0 last:pr-0 xl:grid xl:grid-cols-[auto_minmax(0,1fr)] xl:px-6">
      <div>
        <h2 className="eyebrow whitespace-nowrap">{label}</h2>
        <p className="tnum mt-0.5 text-display font-semibold tracking-[-0.02em] text-ink">{value}</p>
        <p className="text-caption whitespace-nowrap text-ink-500">{note}</p>
      </div>
      {/* Below 1400 px the breakdown runs inline under the count; above, it is a column of right-aligned counts. */}
      <ul
        className={cx(
          'mt-2 flex flex-wrap gap-x-5 text-body xl:mt-0 xl:grid xl:gap-x-8 xl:pt-[18px]',
          columns === 2 ? 'xl:grid-flow-col xl:grid-cols-2 xl:grid-rows-4' : 'xl:grid-cols-1',
        )}
      >
        {children}
      </ul>
    </div>
  );
}

const countRowClass =
  'group inline-flex h-[22px] items-baseline gap-1.5 rounded-xs text-left whitespace-nowrap text-ink-700 t-colors hover:text-cobalt-strong aria-pressed:text-cobalt-strong xl:flex xl:w-full xl:justify-between xl:gap-4';
const countClass = 'tnum font-semibold text-ink group-hover:text-cobalt-strong group-aria-pressed:text-cobalt-strong';

export function CommandCentre() {
  const { data, isPending } = useWorkQueue();
  const { asOf } = useAsOf();
  const toast = useToast();
  const [severity, setSeverity] = useState('all');
  const [group, setGroup] = useState<'all' | WorkItemGroup>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const items = useMemo(() => data?.items ?? [], [data]);

  const groupCounts = useMemo(() => {
    const counts = new Map<WorkItemGroup, number>();
    for (const item of items) counts.set(workItemGroup[item.type], (counts.get(workItemGroup[item.type]) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const filtered = useMemo(
    () => items.filter((item) => (severity === 'all' || item.severity === severity) && (group === 'all' || workItemGroup[item.type] === group)),
    [items, severity, group],
  );

  const selected = filtered.find((item) => item.id === selectedId) ?? filtered[0] ?? null;

  const columns = useMemo<Array<DataColumn<WorkItem>>>(
    () => [
      { id: 'severity', header: 'Severity', sortValue: (item) => SEVERITY_RANK[item.severity], cell: (item) => <SeverityDot severity={item.severity} /> },
      {
        id: 'borrower',
        header: 'Borrower',
        rowHeader: true,
        sortValue: (item) => item.borrowerName,
        cell: (item) => <span className="font-medium text-ink">{item.borrowerName}</span>,
      },
      {
        id: 'summary',
        header: 'Question',
        wrap: true,
        sortValue: (item) => item.summary,
        cell: (item) =>
          isBreach(item) ? (
            <StatusDot tone="breach" emphasis className="!whitespace-normal">
              {item.summary}
            </StatusDot>
          ) : (
            <span className="text-ink-700">{item.summary}</span>
          ),
      },
      {
        id: 'agent',
        header: 'Agent',
        sortValue: (item) => (item.recommendation ? AGENT_LABEL[item.recommendation.kind] : null),
        cell: (item) =>
          item.recommendation ? (
            <span className="inline-flex items-center gap-1.5 text-ink">
              <AgentMark size={8} />
              {AGENT_LABEL[item.recommendation.kind]}
            </span>
          ) : (
            <span className="text-ink-500">A person decides</span>
          ),
      },
      {
        id: 'due',
        header: 'Due',
        align: 'right',
        sortValue: (item) => item.dueDate,
        cell: (item) => {
          const due = formatDue(item.dueDate, asOf);
          return <span className={cx('tnum', due.overdue ? 'font-medium text-amber' : due.today ? 'font-medium text-ink' : 'text-ink-700')}>{due.text}</span>;
        },
      },
    ],
    [asOf],
  );

  if (isPending || !data) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Bank of Stoic · Commercial lending" title="Command centre" />
        <SkeletonRows rows={10} label="Loading the work queue" />
      </div>
    );
  }

  const dueToday = items.filter((item) => formatDue(item.dueDate, asOf).today).length;
  const overdue = items.filter((item) => formatDue(item.dueDate, asOf).overdue).length;
  const { summary } = data;

  return (
    <FactsProvider facts={data.facts}>
      <div data-ready className="space-y-5">
        <PageHeader
          eyebrow="Bank of Stoic · Commercial lending"
          title="Command centre"
          meta={
            <span>
              Monitoring cycle for the quarter ended 30 Sep 2026 · {items.length} items need a person, {dueToday} due today, {overdue} overdue
            </span>
          }
        />

        <section
          aria-label="Portfolio summary"
          className="grid grid-cols-[minmax(0,5fr)_minmax(0,8fr)_minmax(0,5fr)] divide-x divide-hairline-strong border-t border-b border-t-ink border-b-hairline-strong"
        >
          <SummaryBlock label="Cycles in progress" value={summary.cycles.inProgress} note={`of ${summary.borrowers} borrowers`}>
            {summary.cycles.byState.map((state) => (
              <li key={state.label}>
                <Link to="/portfolio" className={countRowClass}>
                  {state.label} <span className={countClass}>{state.count}</span>
                </Link>
              </li>
            ))}
          </SummaryBlock>
          <SummaryBlock label="Open exceptions" value={items.length} note="by type" columns={2}>
            {groupCounts.map(([key, count]) => (
              <li key={key}>
                <button type="button" aria-pressed={group === key} onClick={() => setGroup(group === key ? 'all' : key)} className={countRowClass}>
                  <span className="group-aria-pressed:underline group-aria-pressed:decoration-cobalt group-aria-pressed:underline-offset-4">
                    {workItemGroupLabel[key]}
                  </span>
                  <span className={countClass}>{count}</span>
                </button>
              </li>
            ))}
          </SummaryBlock>
          <SummaryBlock label="Packages due this week" value={summary.packages.dueThisWeek} note={`week of ${formatDate('2026-11-09', { year: false })}`}>
            {summary.packages.byState.map((state) => (
              <li key={state.label}>
                <Link to="/calendar" className={countRowClass}>
                  {state.attention ? <StatusDot tone="attention">{state.label}</StatusDot> : state.label}
                  <span className={countClass}>{state.count}</span>
                </Link>
              </li>
            ))}
          </SummaryBlock>
        </section>

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <section aria-label="Work queue" className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <Segmented
                label="Severity"
                value={severity}
                onValueChange={setSeverity}
                options={[
                  { value: 'all', label: 'All', count: items.length },
                  ...(['critical', 'high', 'medium', 'low'] as const).map((level) => ({
                    value: level,
                    label: SEVERITY_LABEL[level],
                    count: items.filter((item) => item.severity === level).length,
                  })),
                ]}
              />
              <Select
                label="Type"
                hideLabel
                className="w-44"
                value={group}
                onValueChange={(value) => setGroup(value as 'all' | WorkItemGroup)}
                options={[{ value: 'all', label: 'All types' }, ...groupCounts.map(([key]) => ({ value: key, label: workItemGroupLabel[key] }))]}
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
              onRowActivate={(item) => setSelectedId(item.id)}
              stickyTop="var(--topbar-h)"
              empty={
                <EmptyState
                  title="Nothing matches these filters"
                  description="No open item has this severity and type together."
                  action={
                    <Button
                      onClick={() => {
                        setSeverity('all');
                        setGroup('all');
                      }}
                    >
                      Clear filters
                    </Button>
                  }
                />
              }
            />
            <p className="mt-2 text-caption text-ink-500">Up and Down move between rows. Enter opens the item.</p>
          </section>

          <aside aria-label="Selected item" className="xl:sticky xl:top-[68px]">
            {selected ? (
              <WorkItemCard
                key={selected.id}
                headingLevel="h2"
                typeLabel={workItemTypeLabel[selected.type]}
                itemId={selected.id}
                severity={{ tone: SEVERITY_TONE[selected.severity], label: SEVERITY_LABEL[selected.severity] }}
                breach={isBreach(selected)}
                subject={selected.borrowerName}
                context={`${selected.periodLabel} · ${STAGE_LABEL[selected.stage] ?? selected.stage}`}
                due={(() => {
                  const due = formatDue(selected.dueDate, asOf);
                  return { text: due.sentence, attention: due.overdue };
                })()}
                question={selected.question}
                evidence={selected.evidence}
                decisions={selected.decisions}
                requiresSecondPerson={selected.requiresSecondPerson}
                onDecide={(decision) =>
                  toast({ title: `${decision.label}: not recorded`, description: 'The showcase runs on fixture data. No decision was written to the ledger.' })
                }
              >
                {selected.recommendation ? (
                  <AgentNote
                    agent={selected.recommendation.agent}
                    headline={selected.recommendation.headline}
                    body={selected.recommendation.body}
                    state={selected.recommendation.approved ? 'approved' : 'draft'}
                    runId={selected.recommendation.runId}
                    writtenAt={selected.recommendation.writtenAt}
                    collapseAfter={1}
                  />
                ) : (
                  <p className="rounded-md border border-hairline bg-canvas px-4 py-3 text-body text-ink-700">
                    No agent recommendation. Releasing a package is always decided by a person.
                  </p>
                )}
              </WorkItemCard>
            ) : (
              <Card>
                <EmptyState title="No item selected" description="Choose a row in the queue to see its question, evidence and decisions." />
              </Card>
            )}
          </aside>
        </div>
      </div>
    </FactsProvider>
  );
}

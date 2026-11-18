import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { Banknote, FileStack, FileText, Inbox, Radar, Scale, ShieldCheck, Table2, X, type LucideIcon } from 'lucide-react';
import { useEffect, useMemo, type ReactNode } from 'react';
import { usePortfolio, useUsers, useWorkItems } from '@/api/hooks';
import type { WorkItemRow } from '@/api/schema';
import type { Severity, StageId } from '@/api/types';
import { useAuth } from '@/auth/context';
import {
  AgentMark,
  Button,
  DataTable,
  EmptyState,
  formatDate,
  formatDue,
  Kbd,
  PageHeader,
  Segmented,
  SkeletonRows,
  StackedBar,
  StatusDot,
  Tag,
  type BarFill,
  type DataColumn,
} from '@/design';
import {
  isBreachItem,
  ITEM_GROUP_LABEL,
  itemGroup,
  OUTCOME,
  quarterLabel,
  roleLabel,
  ROLES_WITH,
  SEVERITY_LABEL,
  SEVERITY_RANK,
  STAGE_ORDER,
  stageLabel,
  type ItemGroup,
} from '@/domain/labels';
import { useWorkspaceDrawer } from '@/drawer/context';
import { cx } from '@/lib/cx';
import { useAsOf } from '@/shell/AsOf';
import { EmptyCard, ErrorNotice, SeverityTag } from './parts';

/* ── Summary cards ────────────────────────────────────────────────────── */

/** A headline count, a bar that shows its make-up, and the rows behind the bar. Counts of records are not facts: each row leads to the list it counts. */
function SummaryCard({
  label,
  value,
  note,
  bar,
  compact,
  children,
}: {
  label: string;
  value: number;
  note: string;
  bar?: ReactNode;
  compact?: boolean;
  children: ReactNode;
}) {
  return (
    <section aria-label={label} className="flex min-w-0 flex-col rounded-md border border-hairline-strong bg-surface px-4 pt-3 pb-3">
      <h2 className="eyebrow">{label}</h2>
      <p className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
        <span className={cx('tnum font-semibold tracking-[-0.02em] text-ink', compact ? 'text-heading' : 'text-display')}>{value}</span>
        <span className="text-caption text-ink-700">{note}</span>
      </p>
      {bar ? <div className="mt-2">{bar}</div> : null}
      {/* Beside the open drawer the cards keep their headline and bar and give the rows' room to the queue. */}
      {compact ? null : <ul className="mt-2 grid grid-cols-1 gap-px text-body">{children}</ul>}
    </section>
  );
}

const rowClass =
  'group flex min-h-[26px] w-full items-center justify-between gap-3 rounded-sm px-1.5 -mx-1.5 text-left text-ink-700 t-colors hover:bg-hover hover:text-ink aria-pressed:bg-cobalt-bg aria-pressed:text-ink';
const countClass = 'tnum font-semibold text-ink';

/** A swatch that ties a row to its segment of the bar above it. */
function Swatch({ fill }: { fill: string }) {
  return <span aria-hidden className="inline-block size-2 shrink-0 rounded-xs" style={{ background: fill }} />;
}

/** One icon per kind of exception: categories have no good or bad, so they carry no colour. */
const GROUP_ICON: Record<ItemGroup, LucideIcon> = {
  covenant: Scale,
  spreading: Table2,
  terms: FileText,
  borrowing_base: Banknote,
  intake: Inbox,
  signals: Radar,
  review: FileStack,
};

const OUTCOME_FILL: Record<string, BarFill> = { breach: 'breach', attention: 'attention', pass: 'pass' };
const RAMP = ['var(--ramp-1)', 'var(--ramp-2)', 'var(--ramp-3)', 'var(--ramp-4)', 'var(--ramp-5)', 'var(--ramp-6)'];

/* ── Queue ────────────────────────────────────────────────────────────── */

/** The borrower's name leads every title; the table already has a borrower column. */
function shortTitle(item: WorkItemRow): string {
  const prefix = `${item.borrower_name}: `;
  const rest = item.borrower_name && item.title.startsWith(prefix) ? item.title.slice(prefix.length) : item.title;
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low'];

/** Who an item goes to: the roles that hold the permission it needs, in words. */
function rolesFor(item: WorkItemRow): string {
  return (ROLES_WITH[item.required_permission] ?? []).map(roleLabel).join(' or ');
}

export function CommandCentre() {
  const queue = useWorkItems({ status: 'open' });
  const portfolio = usePortfolio();
  const users = useUsers();
  const { asOf } = useAsOf();
  const { can, user } = useAuth();
  const drawer = useWorkspaceDrawer();
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

  // A link that names an item opens it. After that the drawer owns the selection.
  const linked = search.item;
  const { openItem } = drawer;
  useEffect(() => {
    if (linked && items.some((item) => item.id === linked)) openItem(linked);
  }, [linked, items, openItem]);

  const openId = drawer.open ? drawer.itemId : null;
  useEffect(() => {
    if (!openId) return;
    const frame = requestAnimationFrame(() => document.querySelector('tr[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }));
    return () => cancelAnimationFrame(frame);
  }, [openId]);

  const selectedId = drawer.open && !drawer.borrowerCode && drawer.itemId && filtered.some((item) => item.id === drawer.itemId) ? drawer.itemId : null;
  const mine = items.filter((item) => can(item.required_permission)).length;

  /** The items outside the reader's authority, counted by the role that may decide them. */
  const others = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items)
      if (!can(item.required_permission)) counts.set(rolesFor(item) || 'another role', (counts.get(rolesFor(item) || 'another role') ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [items, can]);

  const columns = useMemo<Array<DataColumn<WorkItemRow>>>(
    () => [
      { id: 'severity', header: 'Severity', sortValue: (item) => SEVERITY_RANK[item.severity], cell: (item) => <SeverityTag severity={item.severity} /> },
      {
        id: 'borrower',
        header: 'Borrower',
        rowHeader: true,
        wrap: true,
        minWidth: '150px',
        sortValue: (item) => item.borrower_name,
        cell: (item) => <span className="font-medium text-ink">{item.borrower_name}</span>,
      },
      {
        id: 'summary',
        header: 'Exception / finding',
        wrap: true,
        width: '40%',
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
        id: 'routing',
        header: 'Routing',
        wrap: true,
        sortValue: (item) => (can(item.required_permission) ? 0 : 1),
        cell: (item) => {
          const assignee = item.assigned_to ? users.data?.find((person) => person.id === item.assigned_to) : undefined;
          return (
            <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
              {can(item.required_permission) ? (
                <span className="text-ink-700">Within your authority</span>
              ) : (
                <Tag tone="gate" icon={<ShieldCheck size={12} strokeWidth={2} />}>
                  {rolesFor(item) || 'Another role'} sign-off
                </Tag>
              )}
              {assignee ? <span className="text-caption text-ink-700">routed to {assignee.name}</span> : null}
              {item.agent_run_id ? (
                <span className="inline-flex items-center gap-1 text-caption text-iris">
                  <AgentMark size={8} />
                  agent note
                </span>
              ) : null}
            </span>
          );
        },
      },
      {
        id: 'due',
        header: 'Due / SLA',
        align: 'right',
        sortValue: (item) => item.due_date,
        cell: (item) => {
          if (!item.due_date || !asOf) return <span className="text-ink-500">Not set</span>;
          const due = formatDue(item.due_date, asOf);
          return due.overdue ? (
            <Tag tone="attention">{due.text}</Tag>
          ) : (
            <span className={cx('tnum', due.today ? 'font-medium text-ink' : 'text-ink-700')}>{due.text}</span>
          );
        },
      },
    ],
    [asOf, can, users.data],
  );

  const summary = portfolio.data;
  const header = (
    <PageHeader
      eyebrow="Bank of Stoic · Commercial lending"
      title="Command centre"
      meta={
        summary ? (
          <span data-subtitle>
            {summary.period_end
              ? `${quarterLabel(summary.period_end)} monitoring cycle (ended ${formatDate(summary.period_end)})`
              : 'No monitoring cycle is open'}{' '}
            · {items.length} {items.length === 1 ? 'exception' : 'exceptions'} awaiting sign-off
            {user && items.length > 0
              ? `: ${mine} within your ${roleLabel(user.role)} authority${others.length > 0 ? `, ${others.map(([role, count]) => `${count} for ${role}`).join(', ')}` : ''}.`
              : '.'}{' '}
            <span className="text-ink-500">Totals cover the whole portfolio.</span>
          </span>
        ) : undefined
      }
    />
  );

  if (queue.error) {
    return (
      <div className="space-y-5">
        {header}
        <ErrorNotice error={queue.error} what="The exception queue" onRetry={() => void queue.refetch()} />
      </div>
    );
  }
  if (!queue.data) {
    return (
      <div className="space-y-5">
        {header}
        <SkeletonRows rows={10} label="Loading the exception queue" />
      </div>
    );
  }

  const stages = summary ? [...summary.cycles.by_stage].sort((a, b) => STAGE_ORDER.indexOf(a.stage) - STAGE_ORDER.indexOf(b.stage)) : [];
  // further along the cycle is darker: one ink ramp, because a stage is not good or bad
  const stageFill = (stage: StageId): number =>
    Math.min(6, Math.max(1, Math.round(1 + (STAGE_ORDER.indexOf(stage) / Math.max(1, STAGE_ORDER.length - 1)) * 5)));
  const outcomes = summary ? [...summary.covenants.by_outcome].sort((a, b) => OUTCOME[a.outcome].rank - OUTCOME[b.outcome].rank) : [];
  const filterLabel = group === 'all' ? null : group === 'mine' ? 'Within my authority' : (ITEM_GROUP_LABEL[group as ItemGroup] ?? group);
  const filtersOn = group !== 'all' || severity !== 'all';
  const compact = drawer.open;

  return (
    <div data-ready className="@container space-y-5">
      {header}

      {summary ? (
        <div
          data-summary={compact ? 'compact' : 'full'}
          className={cx('grid gap-3', compact ? 'grid-cols-2 @min-[720px]:grid-cols-4' : 'grid-cols-1 @min-[560px]:grid-cols-2 @min-[1080px]:grid-cols-4')}
        >
          <SummaryCard
            compact={compact}
            label="Active review cycles"
            value={summary.cycles.open}
            note={`of ${summary.borrowers} borrowers`}
            bar={
              <StackedBar
                label="Cycles by stage"
                segments={stages.map((entry) => ({
                  id: entry.stage,
                  label: stageLabel(entry.stage),
                  count: entry.count,
                  fill: stageFill(entry.stage) as BarFill,
                }))}
              />
            }
          >
            {stages.map((entry) => (
              <li key={entry.stage}>
                <Link to="/portfolio" className={rowClass}>
                  <span className="flex min-w-0 items-center gap-2">
                    <Swatch fill={RAMP[stageFill(entry.stage) - 1] ?? RAMP[0]!} />
                    {stageLabel(entry.stage)}
                  </span>
                  <span className={countClass}>{entry.count}</span>
                </Link>
              </li>
            ))}
          </SummaryCard>

          <SummaryCard compact={compact} label="Exception breakdown" value={items.length} note="open, by kind">
            {groupCounts.map(([key, count]) => {
              const Icon = GROUP_ICON[key];
              return (
                <li key={key}>
                  <button
                    type="button"
                    aria-pressed={group === key}
                    onClick={() => setSearch({ type: group === key ? undefined : key, item: undefined })}
                    className={rowClass}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <Icon size={14} strokeWidth={1.75} aria-hidden className="shrink-0 text-ink-500 group-aria-pressed:text-cobalt" />
                      {ITEM_GROUP_LABEL[key]}
                    </span>
                    <span className={countClass}>{count}</span>
                  </button>
                </li>
              );
            })}
            <li>
              <button
                type="button"
                aria-pressed={group === 'mine'}
                onClick={() => setSearch({ type: group === 'mine' ? undefined : 'mine', item: undefined })}
                className={cx(rowClass, 'mt-1 border-t border-hairline pt-1')}
              >
                <span>Within my authority</span>
                <span className={countClass}>{mine}</span>
              </button>
            </li>
          </SummaryCard>

          <SummaryCard
            compact={compact}
            label={`${summary.period_end ? quarterLabel(summary.period_end).split(' ')[0] : 'Latest'} covenant compliance`}
            value={summary.covenants.tests}
            note="tests, calculated by code"
            bar={
              <StackedBar
                label="Covenant tests by outcome"
                segments={outcomes.map((entry) => ({
                  id: entry.outcome,
                  label: OUTCOME[entry.outcome].label,
                  count: entry.count,
                  fill: OUTCOME_FILL[OUTCOME[entry.outcome].tone] ?? 'muted',
                }))}
              />
            }
          >
            {outcomes.map((entry) => (
              <li key={entry.outcome}>
                <Link to="/portfolio" className={rowClass}>
                  <StatusDot tone={OUTCOME[entry.outcome].tone} emphasis={OUTCOME[entry.outcome].emphasis} className="whitespace-normal!">
                    {OUTCOME[entry.outcome].label}
                  </StatusDot>
                  <span className={countClass}>{entry.count}</span>
                </Link>
              </li>
            ))}
          </SummaryCard>

          <SummaryCard compact={compact} label="Deliverables & signals" value={summary.obligations.due_within_7_days} note="due in the next 7 days">
            <li>
              <Link to="/calendar" className={rowClass}>
                {summary.obligations.overdue > 0 ? <Tag tone="attention">Overdue</Tag> : <span>Overdue</span>}
                <span className={countClass}>{summary.obligations.overdue}</span>
              </Link>
            </li>
            <li>
              <Link to="/calendar" className={rowClass}>
                <StatusDot tone="pass">Received, last 30 days</StatusDot>
                <span className={countClass}>{summary.obligations.received_in_last_30_days}</span>
              </Link>
            </li>
            <li>
              <Link to="/portfolio" className={rowClass}>
                <span>Open signals</span>
                <span className={countClass}>{summary.signals.open}</span>
              </Link>
            </li>
          </SummaryCard>
        </div>
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
        <section aria-label="Exception queue" className="min-w-0">
          <div className="mb-2 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
            <div className="min-w-0">
              <h2 className="text-title font-semibold text-ink">Exception queue</h2>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-caption text-ink-700">
                Prioritised by severity, then due date.
                <span className="inline-flex items-center gap-1 max-sm:hidden">
                  <Kbd>J</Kbd>
                  <Kbd>K</Kbd> or <Kbd>↑</Kbd>
                  <Kbd>↓</Kbd> to move, <Kbd>Enter</Kbd> to inspect.
                </span>
              </p>
            </div>
            <p className="text-caption text-ink-700" aria-live="polite">
              {filtered.length} of {items.length}
            </p>
          </div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="flex max-sm:relative max-sm:-m-1 max-sm:max-w-[calc(100%+8px)] max-sm:overflow-x-auto max-sm:p-1 max-sm:[&_button]:px-2">
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
            {filterLabel ? (
              <button
                type="button"
                data-active-filter
                onClick={() => setSearch({ type: undefined, item: undefined })}
                className="inline-flex h-8 items-center gap-1.5 rounded-sm border border-cobalt-border bg-cobalt-bg px-2.5 text-body font-medium text-ink t-colors hover:border-cobalt"
              >
                {filterLabel}
                <X size={13} aria-hidden className="text-ink-700" />
                <span className="sr-only">: remove this filter</span>
              </button>
            ) : null}
            {filtersOn ? (
              <Button variant="ghost" size="sm" onClick={() => setSearch({ severity: undefined, type: undefined, item: undefined })}>
                Clear filters
              </Button>
            ) : null}
          </div>
          <DataTable
            caption="Exception queue, ordered by severity and then due date"
            data={filtered}
            columns={columns}
            getRowId={(item) => item.id}
            selectedRowId={selectedId}
            onRowActivate={(item) => drawer.openItem(item.id)}
            pageKeys
            stickyTop="var(--topbar-h)"
            narrow="stack"
            empty={
              <EmptyState
                title="Nothing matches these filters"
                description="No open exception has this severity and kind together."
                action={<Button onClick={() => setSearch({ severity: undefined, type: undefined, item: undefined })}>Clear filters</Button>}
              />
            }
          />
        </section>
      )}
    </div>
  );
}

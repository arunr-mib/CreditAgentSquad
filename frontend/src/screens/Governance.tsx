import { useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo, useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAgents, useLedger, useLedgerVerification, useSetClock, useUsers } from '@/api/hooks';
import type { AgentSpec, LedgerEvent } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { Button, Card, DataTable, EmptyState, formatDate, Input, PageHeader, Select, StatusDot, tabClass, tabListClass, useToast, type DataColumn } from '@/design';
import { actionLabel, decisionLabel, docTypeLabel, formatTimestamp, humanize, roleLabel, signalLabel, STAGE_STATUS_LABEL, stageLabel } from '@/domain/labels';
import { useAsOf } from '@/shell/AsOf';
import { Load, Notice } from './parts';

const ACTION_FILTERS: Array<[string, string]> = [
  ['all', 'All actions'],
  ['work_item.decided', 'Decisions recorded'],
  ['work_item.', 'Work items'],
  ['covenant.', 'Covenant tests'],
  ['borrowing_base.', 'Borrowing base reviews'],
  ['signal.', 'Signals'],
  ['document.', 'Documents'],
  ['cycle.', 'Monitoring cycles'],
  ['terms.', 'Terms'],
  ['fact.', 'Facts'],
  ['obligation.', 'Reporting requirements'],
  ['review', 'Reviews'],
  ['action.', 'Actions'],
  ['agent', 'Agent runs'],
  ['auth.', 'Sign-ins'],
  ['clock.', 'Clock'],
];

/** The payload in a few plain words: the decision and its reason first, then whatever else is there. */
export function describeEvent(event: LedgerEvent): string {
  const payload = event.payload ?? {};
  const text = (key: string) => (typeof payload[key] === 'string' && payload[key] ? (payload[key] as string) : null);
  const parts: string[] = [];
  if (text('decision')) parts.push(decisionLabel(text('decision')));
  if (text('reason')) parts.push(`“${text('reason')}”`);
  if (text('title')) parts.push(text('title') as string);
  if (text('key')) parts.push(text('key') as string);
  const covenant = text('covenant') ?? text('covenant_id');
  if (covenant) parts.push(humanize(covenant));
  const rule = text('rule') ?? text('rule_id');
  if (rule) parts.push(`${signalLabel(rule)}${text('subject') ? ` (${humanize(text('subject')).toLowerCase()})` : ''}`);
  if (text('outcome')) parts.push(humanize(text('outcome')).toLowerCase());
  if (text('stage')) {
    const status = (value: unknown) => STAGE_STATUS_LABEL[String(value) as keyof typeof STAGE_STATUS_LABEL]?.toLowerCase() ?? String(value ?? '');
    parts.push(`${stageLabel(text('stage'))}: ${status(payload.from)} to ${status(payload.to)}`);
  }
  if (text('document_type')) parts.push(docTypeLabel(text('document_type')));
  if (text('period_end')) parts.push(`period ended ${formatDate(text('period_end') as string)}`);
  if (event.action === 'clock.set' && text('to')) parts.push(`to ${formatDate(text('to') as string)}`);
  if (text('received_date')) parts.push(`received ${formatDate(text('received_date') as string)}`);
  if (text('email')) parts.push(`${text('email')}${text('role') ? `, ${roleLabel(text('role')).toLowerCase()}` : ''}`);
  if (event.document_title) parts.push(event.document_title);
  else if (text('file_name')) parts.push(text('file_name') as string);
  if (parts.length === 0) {
    for (const [key, value] of Object.entries(payload).slice(0, 3)) {
      if (value !== null && typeof value !== 'object') parts.push(`${humanize(key).toLowerCase()} ${String(value)}`);
    }
  }
  return parts.join(' · ');
}

function Ledger() {
  const search = useSearch({ from: '/governance' });
  const navigate = useNavigate({ from: '/governance' });
  const users = useUsers();
  const [before, setBefore] = useState<number[]>([]);
  const [verify, setVerify] = useState(false);
  const verification = useLedgerVerification(verify);
  const action = search.action ?? 'all';
  const entity = search.entity ?? '';
  const filter = { action: action === 'all' ? undefined : action, entity_id: entity || undefined, before_seq: before[before.length - 1], limit: 100 };
  const ledger = useLedger(filter);
  const names = useMemo(() => new Map((users.data ?? []).map((user) => [user.id, user])), [users.data]);
  const setFilter = (next: { action?: string; entity?: string }) => {
    setBefore([]);
    void navigate({ search: (previous) => ({ ...previous, ...next }), replace: true, resetScroll: false });
  };

  const columns = useMemo<Array<DataColumn<LedgerEvent>>>(
    () => [
      { id: 'seq', header: 'No.', align: 'right', cell: (event) => <span className="tnum text-ink-700">{event.seq}</span> },
      { id: 'ts', header: 'Recorded, UTC', cell: (event) => <span className="tnum text-ink-700">{formatTimestamp(event.ts)}</span> },
      {
        id: 'actor',
        header: 'By',
        wrap: 'narrow',
        cell: (event) => {
          const user = names.get(event.actor_id);
          if (user) return <span className="text-ink">{user.name}</span>;
          return event.actor_type === 'agent' ? (
            <StatusDot tone="agent">{humanize(event.actor_id)} agent</StatusDot>
          ) : (
            <span className="text-ink-500">
              {event.actor_type === 'system' ? 'System' : 'Person'} · <span className="ident">{event.actor_id.slice(0, 12)}</span>
            </span>
          );
        },
      },
      { id: 'action', header: 'Action', rowHeader: true, wrap: 'narrow', cell: (event) => <span className="font-medium text-ink">{actionLabel(event.action)}</span> },
      { id: 'detail', header: 'Detail', wrap: true, width: '30%', cell: (event) => <span className="text-ink-700 [overflow-wrap:anywhere]">{describeEvent(event)}</span> },
      {
        id: 'entity',
        header: 'Record',
        wrap: 'narrow',
        cell: (event) => (
          <button type="button" className="link text-left text-caption" onClick={() => setFilter({ entity: event.entity_id })} aria-label={`Show every event for ${humanize(event.entity_type)} ${event.entity_id.slice(0, 8)}`}>
            {humanize(event.entity_type)} <span className="ident">{event.entity_id.slice(0, 8)}</span>
          </button>
        ),
      },
      { id: 'hash', header: 'Hash', cell: (event) => <span className="ident text-caption text-ink-500">{event.hash.slice(0, 10)}</span> },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [names],
  );

  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap items-center justify-between gap-4 px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-title font-semibold text-ink">Chain verification</h2>
          <p className="text-body text-pretty text-ink-700">
            Each event stores the hash of the one before it, so an edit or a removal breaks the chain. The database also refuses updates and deletes on the ledger.
          </p>
          <div className="mt-1.5 text-body" aria-live="polite" data-chain-result>
            {verification.isFetching ? (
              <StatusDot tone="neutral">Checking every event</StatusDot>
            ) : verification.error ? (
              <span className="font-medium text-amber">{errorMessage(verification.error)}</span>
            ) : verification.data ? (
              verification.data.ok ? (
                <StatusDot tone="pass" emphasis>
                  Chain intact: <span className="tnum">{verification.data.events_checked.toLocaleString('en-US')}</span> events checked
                </StatusDot>
              ) : (
                <StatusDot tone="attention" emphasis>
                  Chain broken after <span className="tnum">{verification.data.events_checked.toLocaleString('en-US')}</span> events: {verification.data.problem}
                </StatusDot>
              )
            ) : (
              <span className="text-ink-500">Not checked in this session.</span>
            )}
          </div>
        </div>
        <Button variant="primary" disabled={verification.isFetching} onClick={() => (verify ? void verification.refetch() : setVerify(true))}>
          Verify the chain
        </Button>
      </Card>

      <section aria-labelledby="ledger-heading">
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <h2 id="ledger-heading" className="sr-only">
            Ledger events
          </h2>
          <Select label="Action" hideLabel className="w-full sm:w-60" value={action} onValueChange={(value) => setFilter({ action: value === 'all' ? undefined : value })} options={ACTION_FILTERS.map(([value, label]) => ({ value, label }))} />
          <Input
            label="Record identifier"
            hideLabel
            placeholder="Record identifier"
            className="w-full sm:w-[340px]"
            value={entity}
            onChange={(event) => setFilter({ entity: event.target.value.trim() || undefined })}
          />
          {entity || action !== 'all' ? (
            <Button variant="ghost" onClick={() => setFilter({ entity: undefined, action: undefined })}>
              Clear filters
            </Button>
          ) : null}
          <p className="ml-auto text-caption text-ink-500" aria-live="polite">
            {ledger.data ? `${ledger.data.length} events, newest first${before.length > 0 ? ` · page ${before.length + 1}` : ''}` : ''}
          </p>
        </div>
        <Load query={ledger} what="The ledger" rows={12}>
          {(events) => (
            <>
              <DataTable
                caption="Ledger events, newest first"
                data={events}
                columns={columns}
                getRowId={(event) => String(event.seq)}
                stickyTop="var(--topbar-h)"
                narrow="stack"
                empty={<EmptyState title="No event matches" description="Nothing in the ledger fits this action and record." action={<Button onClick={() => setFilter({ entity: undefined, action: undefined })}>Clear filters</Button>} />}
              />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <p className="text-caption text-ink-500">The ledger is append-only. Choose a record to see everything that happened to it.</p>
                <div className="flex gap-2">
                  <Button disabled={before.length === 0} onClick={() => setBefore((stack) => stack.slice(0, -1))}>
                    Newer
                  </Button>
                  <Button
                    disabled={events.length < 100}
                    onClick={() => {
                      const last = events[events.length - 1];
                      if (last) setBefore((stack) => [...stack, last.seq]);
                    }}
                  >
                    Older
                  </Button>
                </div>
              </div>
            </>
          )}
        </Load>
      </section>
    </div>
  );
}

function AgentInventory() {
  const agents = useAgents();
  const columns = useMemo<Array<DataColumn<AgentSpec>>>(
    () => [
      { id: 'name', header: 'Agent', rowHeader: true, sortValue: (spec) => spec.name, cell: (spec) => <StatusDot tone="agent">{humanize(spec.name)}</StatusDot> },
      { id: 'version', header: 'Version', cell: (spec) => <span className="ident">{spec.version}</span> },
      { id: 'model', header: 'Model', cell: (spec) => <span className="ident">{spec.model}</span> },
      { id: 'effort', header: 'Effort', cell: (spec) => <span className="text-ink-700">{humanize(spec.effort)}</span> },
      { id: 'steps', header: 'Step cap', align: 'right', cell: (spec) => <span className="tnum">{spec.max_steps}</span> },
      { id: 'tools', header: 'Tools', wrap: true, cell: (spec) => <span className="text-ink-700">{spec.tools.length > 0 ? spec.tools.join(', ') : 'None'}</span> },
      { id: 'prompt', header: 'Prompt hash', cell: (spec) => <span className="ident text-caption text-ink-500">{spec.prompt_sha256.slice(0, 12)}</span> },
      { id: 'runs', header: 'Runs', align: 'right', sortValue: (spec) => spec.runs, cell: (spec) => <span className="tnum">{spec.runs}</span> },
      { id: 'active', header: 'State', cell: (spec) => <StatusDot tone={spec.active ? 'neutral' : 'muted'}>{spec.active ? 'Registered' : 'Retired'}</StatusDot> },
    ],
    [],
  );
  return (
    <Load query={agents} what="The agent inventory" rows={6}>
      {(specs) =>
        specs.length === 0 ? (
          <Card>
            <EmptyState
              title="No agent version is registered"
              description="An agent version is registered the first time it runs. The demonstration book was loaded from ground truth and replayed through the calculation code, so no agent has run in this workspace yet."
            />
          </Card>
        ) : (
          <DataTable caption="Registered agent versions: the model inventory" data={specs} columns={columns} getRowId={(spec) => spec.id} stickyTop="var(--topbar-h)" narrow="stack" />
        )
      }
    </Load>
  );
}

function Clock() {
  const { asOf } = useAsOf();
  const { can, user } = useAuth();
  const setClock = useSetClock();
  const toast = useToast();
  const [value, setValue] = useState('');
  const date = value || asOf || '';

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!date) return;
    setClock.mutate(date, {
      onSuccess: (result) =>
        toast({ tone: 'pass', title: `Date set to ${formatDate(result.today)}`, description: `${result.obligations_now_overdue} reporting requirements changed status. The change is in the ledger.` }),
    });
  }

  return (
    <Card className="max-w-[560px] px-4 py-3.5">
      <h2 className="text-title font-semibold text-ink">Simulated clock</h2>
      <p className="tnum mt-1 text-heading font-semibold text-ink">{asOf ? formatDate(asOf) : 'Reading the clock'}</p>
      <p className="mt-1 text-body text-pretty text-ink-700">
        The demonstration runs on a date that a person sets. Due dates, overdue reporting and cycle stages follow it. Setting the date is recorded in the ledger.
      </p>
      {can('advance_clock') ? (
        <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
          <Input label="New date" type="date" className="w-48" value={date} onChange={(event) => setValue(event.target.value)} />
          <Button type="submit" variant="primary" disabled={setClock.isPending || !date || date === asOf}>
            {setClock.isPending ? 'Setting' : 'Set the date'}
          </Button>
        </form>
      ) : (
        <Notice title="Only an administrator sets the date" className="mt-3">
          You are signed in as {user ? roleLabel(user.role).toLowerCase() : 'a reader'}. Sign in as the platform administrator to change it.
        </Notice>
      )}
      {setClock.error ? (
        <Notice tone="attention" title="The date was not changed" className="mt-3">
          The server said: “{errorMessage(setClock.error)}”
        </Notice>
      ) : null}
    </Card>
  );
}

const TABS = [
  { id: 'ledger', label: 'Ledger' },
  { id: 'agents', label: 'Agent inventory' },
  { id: 'clock', label: 'Clock' },
] as const;

export function Governance() {
  const search = useSearch({ from: '/governance' });
  const navigate = useNavigate({ from: '/governance' });
  const tab = TABS.some((entry) => entry.id === search.tab) ? search.tab : 'ledger';
  return (
    <div data-ready className="space-y-5">
      <div>
        <PageHeader eyebrow="Bank of Stoic · Commercial lending" title="Governance" meta={<span>What was done, by whom and when; which agent versions exist; and the date the demonstration runs on</span>} />
        <div role="tablist" aria-label="Governance sections" className={`${tabListClass} mt-4 flex-wrap gap-y-0`}>
          {TABS.map((entry) => (
            <button
              key={entry.id}
              type="button"
              role="tab"
              id={`governance-tab-${entry.id}`}
              aria-selected={tab === entry.id}
              aria-controls="governance-panel"
              data-state={tab === entry.id ? 'active' : 'inactive'}
              onClick={() => void navigate({ search: { tab: entry.id }, replace: true })}
              className={tabClass}
            >
              {entry.label}
            </button>
          ))}
        </div>
      </div>
      <div role="tabpanel" id="governance-panel" aria-labelledby={`governance-tab-${tab}`}>
        {tab === 'ledger' ? <Ledger /> : tab === 'agents' ? <AgentInventory /> : <Clock />}
      </div>
    </div>
  );
}

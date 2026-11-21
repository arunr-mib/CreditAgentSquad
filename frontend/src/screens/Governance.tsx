import { useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo, useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAgents, useLedger, useLedgerVerification, usePolicyRegister, useRolesAndPermissions, useSetClock, useUsers } from '@/api/hooks';
import type { AgentSpec, LedgerEvent, PolicyAgent, PolicyRegister, PolicyRule, PolicySignalRule, RolesAndPermissions } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { AgentMark, Button, Card, DataTable, EmptyState, formatDate, Input, PageHeader, Select, StatusDot, tabClass, tabListClass, Tag, useToast, type DataColumn } from '@/design';
import { actionLabel, formatTimestamp, humanize, roleLabel } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { describeEvent } from '@/squad/oversight/describeEvent';
import { useAsOf } from '@/shell/AsOf';
import { Load, Notice, SectionHead, SeverityDot, ShortId } from './parts';

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

/** An agent is recorded as "review" or "review@1"; it is the same agent, so it gets one name. */
export function ledgerAgentName(actorId: string): string {
  const name = actorId.split('@')[0] ?? actorId;
  return name === 'copilot' ? 'Copilot' : `${humanize(name)} agent`;
}

/** Sign-ins and sign-outs: many, and rarely what a reader of the ledger is looking for. */
export const isSignIn = (event: Pick<LedgerEvent, 'action'>) => event.action.startsWith('auth.');

/** One page of the ledger, with sign-ins left out when asked. */
export function ledgerPage(events: LedgerEvent[], hideSignIns: boolean, size: number): { shown: LedgerEvent[]; hidden: number; more: boolean } {
  if (!hideSignIns) return { shown: events.slice(0, size), hidden: 0, more: events.length >= size };
  const kept = events.filter((event) => !isSignIn(event));
  const shown = kept.slice(0, size);
  const last = shown[shown.length - 1];
  const hidden = events.filter((event) => isSignIn(event) && (!last || event.seq > last.seq)).length;
  return { shown, hidden, more: kept.length > size || events.length >= LEDGER_FETCH };
}

const LEDGER_PAGE = 100;
/** With sign-ins hidden, more is read than is shown, so that a page is still a page. */
const LEDGER_FETCH = 500;

export { describeEvent };

function Ledger() {
  const search = useSearch({ from: '/governance' });
  const navigate = useNavigate({ from: '/governance' });
  const users = useUsers();
  const [before, setBefore] = useState<number[]>([]);
  const [verify, setVerify] = useState(false);
  const verification = useLedgerVerification(verify);
  const action = search.action ?? 'all';
  const entity = search.entity ?? '';
  // Sign-ins are hidden unless asked for, or unless the reader filtered to them.
  const [showSignIns, setShowSignIns] = useState(false);
  const hideSignIns = !showSignIns && action !== 'auth.';
  const filter = {
    action: action === 'all' ? undefined : action,
    entity_id: entity || undefined,
    before_seq: before[before.length - 1],
    limit: hideSignIns ? LEDGER_FETCH : LEDGER_PAGE,
  };
  const ledger = useLedger(filter);
  const page = ledger.data ? ledgerPage(ledger.data, hideSignIns, LEDGER_PAGE) : null;
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
            <span title={event.actor_id}>
              <StatusDot tone="agent">{ledgerAgentName(event.actor_id)}</StatusDot>
            </span>
          ) : (
            <span className="text-ink-500">
              {event.actor_type === 'system' ? 'System' : 'Person'} · <ShortId id={event.actor_id} />
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
            {humanize(event.entity_type)} <ShortId id={event.entity_id} />
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
          {action !== 'auth.' ? (
            <label className="inline-flex h-8 items-center gap-2 text-body text-ink-700">
              <input
                type="checkbox"
                checked={!showSignIns}
                onChange={(event) => {
                  setBefore([]);
                  setShowSignIns(!event.target.checked);
                }}
                className="size-4 accent-[var(--cobalt)]"
              />
              Hide sign-ins
            </label>
          ) : null}
          {entity || action !== 'all' ? (
            <Button variant="ghost" onClick={() => setFilter({ entity: undefined, action: undefined })}>
              Clear filters
            </Button>
          ) : null}
          <p className="ml-auto text-caption text-ink-500" aria-live="polite">
            {page
              ? `${page.shown.length} events, newest first${page.hidden > 0 ? `, ${page.hidden} sign-ins hidden` : ''}${before.length > 0 ? ` · page ${before.length + 1}` : ''}`
              : ''}
          </p>
        </div>
        <Load query={ledger} what="The ledger" rows={12}>
          {(fetched) => {
            const { shown: events, more } = ledgerPage(fetched, hideSignIns, LEDGER_PAGE);
            return (
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
                    disabled={!more}
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
            );
          }}
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

/* ── Roles and permissions ────────────────────────────────────────────── */

const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
const people = (n: number) => `${n.toLocaleString('en-US')} ${n === 1 ? 'person' : 'people'}`;

type Grant = 'yes' | 'second' | 'no';
const GRANT_WORDS: Record<Grant, string> = { yes: 'May', second: 'May, but never on their own work', no: 'May not' };

/** Not a check mark: a grant is a fact about the table, not something code verified. */
function GrantMark({ grant }: { grant: Grant }) {
  if (grant === 'no') return <span aria-hidden className="inline-block h-px w-2.5 bg-hairline-strong align-middle" />;
  if (grant === 'second') {
    return (
      <span aria-hidden className="inline-flex size-[15px] items-center justify-center rounded-full border-[1.5px] border-ink align-middle">
        <span className="size-[5px] rounded-full bg-ink" />
      </span>
    );
  }
  return <span aria-hidden className="inline-block size-[9px] rounded-full bg-ink align-middle" />;
}

function groupsOf(table: RolesAndPermissions) {
  const groups: Array<{ name: string; permissions: RolesAndPermissions['permissions'] }> = [];
  for (const permission of table.permissions) {
    const last = groups[groups.length - 1];
    if (last && last.name === permission.group) last.permissions.push(permission);
    else groups.push({ name: permission.group, permissions: [permission] });
  }
  return groups;
}

/**
 * The six roles against every permission, exactly as `/governance/roles` returns them. From 1024 px a matrix;
 * below that, each permission with the roles that hold it, so nothing has to scroll sideways.
 */
export function RolesMatrix({ table, ownRole }: { table: RolesAndPermissions; ownRole?: string | null }) {
  const groups = groupsOf(table);
  const grant = (role: string, permission: RolesAndPermissions['permissions'][number]): Grant =>
    (table.grants[role] ?? []).includes(permission.id) ? (permission.second_person ? 'second' : 'yes') : 'no';
  const second = table.permissions.some((permission) => permission.second_person);
  const tint = (role: string) => (role === ownRole ? 'bg-hover' : undefined);

  return (
    <div>
      <Card className="overflow-hidden max-md:hidden">
        <table data-roles-matrix className="w-full table-fixed border-separate border-spacing-0 text-body">
          <caption className="sr-only">Roles and what each may do</caption>
          <thead>
            <tr>
              <th scope="col" className="eyebrow w-[30%] border-b border-ink px-4 pb-2 text-left align-bottom">
                Permission
              </th>
              {table.roles.map((role) => (
                <th key={role.id} scope="col" data-role={role.id} className={cx('border-b border-ink px-2 pt-3 pb-2 text-center align-bottom font-regular', tint(role.id))}>
                  {role.id === ownRole ? <span className="eyebrow block">Your role</span> : null}
                  <span className="block text-caption font-semibold text-pretty text-ink">{role.label}</span>
                  <span className="tnum block text-caption text-ink-500">{people(role.people)}</span>
                </th>
              ))}
            </tr>
          </thead>
          {groups.map((group) => (
            <tbody key={group.name}>
              <tr>
                <th scope="rowgroup" colSpan={table.roles.length + 1} className="eyebrow border-b border-hairline bg-canvas px-4 pt-3 pb-1 text-left">
                  {group.name}
                </th>
              </tr>
              {group.permissions.map((permission) => (
                <tr key={permission.id} data-permission={permission.id} className="group/row">
                  <th scope="row" className="border-b border-hairline px-4 py-1.5 text-left font-regular text-ink group-hover/row:bg-hover">
                    {sentence(permission.label)}
                    {permission.second_person ? <span className="block text-caption text-ink-500">A second person is required</span> : null}
                  </th>
                  {table.roles.map((role) => {
                    const value = grant(role.id, permission);
                    return (
                      <td
                        key={role.id}
                        data-role={role.id}
                        data-grant={value}
                        className={cx('border-b border-hairline px-2 py-1.5 text-center group-hover/row:bg-hover', tint(role.id))}
                      >
                        <GrantMark grant={value} />
                        <span className="sr-only">{GRANT_WORDS[value]}</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </Card>

      <div data-roles-list className="space-y-4 md:hidden">
        {groups.map((group) => (
          <section key={group.name} aria-label={group.name}>
            <h3 className="eyebrow mb-1 px-1">{group.name}</h3>
            <Card>
              <ul>
                {group.permissions.map((permission) => {
                  const holders = table.roles.filter((role) => grant(role.id, permission) !== 'no');
                  return (
                    <li key={permission.id} className="border-b border-hairline px-4 py-2.5 last:border-b-0">
                      <p className="flex items-center gap-2 text-body font-medium text-ink">
                        <GrantMark grant={permission.second_person ? 'second' : 'yes'} />
                        {sentence(permission.label)}
                      </p>
                      <p className="mt-0.5 pl-[23px] text-body text-pretty text-ink-700">
                        {holders.length === 0
                          ? 'No role holds this.'
                          : holders.map((role, index) => (
                              <span key={role.id}>
                                {index > 0 ? ' · ' : ''}
                                <span className={role.id === ownRole ? 'font-medium text-ink' : undefined}>
                                  {role.label}
                                  {role.id === ownRole ? ' (your role)' : ''}
                                </span>
                              </span>
                            ))}
                      </p>
                      {permission.second_person ? <p className="mt-0.5 pl-[23px] text-caption text-ink-500">A second person is required</p> : null}
                    </li>
                  );
                })}
              </ul>
            </Card>
          </section>
        ))}
      </div>

      <ul aria-label="Key" className="mt-3 flex flex-wrap gap-x-6 gap-y-1.5 px-1 text-caption text-ink-700">
        <li className="inline-flex items-center gap-2">
          <GrantMark grant="yes" /> {GRANT_WORDS.yes}
        </li>
        {second ? (
          <li className="inline-flex items-center gap-2">
            <GrantMark grant="second" /> {GRANT_WORDS.second}
          </li>
        ) : null}
        <li className="inline-flex items-center gap-2 max-md:hidden">
          <GrantMark grant="no" /> {GRANT_WORDS.no}
        </li>
      </ul>
    </div>
  );
}

function Roles() {
  const table = useRolesAndPermissions();
  const { user } = useAuth();
  return (
    <Load query={table} what="The roles and permissions" rows={12}>
      {(data) => (
        <div className="space-y-6">
          <section aria-labelledby="roles-heading">
            <SectionHead
              id="roles-heading"
              title="Who may do what"
              note={`${data.roles.length} roles, ${data.permissions.length} permissions, read from the permission table every check goes through`}
            />
            <RolesMatrix table={data} ownRole={user?.role} />
          </section>

          <section aria-labelledby="second-person-heading">
            <SectionHead id="second-person-heading" title="A person cannot approve their own work" />
            <Card>
              <p className="flex items-start gap-2.5 px-4 pt-3.5 pb-3 text-prose text-pretty text-ink">
                <span className="mt-1 shrink-0">
                  <GrantMark grant="second" />
                </span>
                <span className="max-w-[78ch]">{data.second_person.rule}</span>
              </p>
              <ul className="border-t border-hairline">
                {data.second_person.applies_to.map((entry) => (
                  <li key={entry.permission} className="grid gap-x-6 gap-y-0.5 border-b border-hairline px-4 py-2.5 text-body last:border-b-0 md:grid-cols-[200px_minmax(0,1fr)_auto]">
                    <span className="font-medium text-ink">{entry.what}</span>
                    <span className="text-pretty text-ink-700">{entry.detail}</span>
                    <span className="ident text-caption text-ink-500 md:text-right">{entry.source}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </section>
        </div>
      )}
    </Load>
  );
}

/* ── Policy rules ─────────────────────────────────────────────────────── */

function Setting({ rule }: { rule: PolicyRule }) {
  if (rule.state === 'attention') return <Tag tone="attention">{rule.setting}</Tag>;
  if (rule.state === 'verified') {
    return (
      <StatusDot tone="pass" emphasis className="whitespace-normal!">
        {rule.setting}
      </StatusDot>
    );
  }
  return <span className={rule.kind === 'ident' ? 'ident text-ink' : 'tnum font-medium text-ink'}>{rule.setting}</span>;
}

const RULE_COLUMNS: Array<DataColumn<PolicyRule>> = [
  { id: 'rule', header: 'Rule', rowHeader: true, wrap: true, width: '24%', cell: (rule) => <span className="font-medium text-ink">{rule.rule}</span> },
  { id: 'setting', header: 'In force', wrap: true, width: '18%', cell: (rule) => <Setting rule={rule} /> },
  { id: 'effect', header: 'What code does', wrap: true, cell: (rule) => <span className="text-ink-700">{rule.effect}</span> },
  { id: 'source', header: 'Enforced in', wrap: true, width: '236px', cell: (rule) => <span className="ident text-caption text-ink-500 [overflow-wrap:anywhere]">{rule.source}</span> },
];

const SIGNAL_COLUMNS: Array<DataColumn<PolicySignalRule>> = [
  { id: 'name', header: 'Rule', rowHeader: true, wrap: true, width: '24%', cell: (rule) => <span className="font-medium text-ink">{rule.name}</span> },
  { id: 'severity', header: 'Severity', width: '18%', cell: (rule) => <SeverityDot severity={rule.severity} /> },
  { id: 'trigger', header: 'Fires when', wrap: true, cell: (rule) => <span className="tnum text-ink-700">{rule.trigger}</span> },
];

const AGENT_COLUMNS: Array<DataColumn<PolicyAgent>> = [
  {
    id: 'name',
    header: 'Agent',
    rowHeader: true,
    cell: (agent) => (
      <span className="inline-flex items-center gap-1.5 font-medium text-iris">
        <AgentMark />
        {humanize(agent.name)}
      </span>
    ),
  },
  { id: 'version', header: 'Version', cell: (agent) => <span className="ident">{agent.version}</span> },
  { id: 'purpose', header: 'What it is for', wrap: true, cell: (agent) => <span className="text-ink-700">{agent.purpose}</span> },
  { id: 'model', header: 'Model', cell: (agent) => <span className="ident">{agent.model}</span> },
  { id: 'effort', header: 'Effort', cell: (agent) => <span className="text-ink-700">{humanize(agent.effort)}</span> },
  { id: 'steps', header: 'Step cap', align: 'right', cell: (agent) => <span className="tnum">{agent.max_steps}</span> },
  { id: 'tools', header: 'Tools', align: 'right', cell: (agent) => <span className="tnum">{agent.tools.length}</span> },
  { id: 'prompt', header: 'Prompt hash', cell: (agent) => <span className="ident text-caption text-ink-500">{agent.prompt_sha256.slice(0, 12)}</span> },
];

/** The rules code applies without a model, as scannable tables. Every setting is the API's; nothing is typed here. */
export function PolicyTables({ register }: { register: PolicyRegister }) {
  return (
    <div className="space-y-7">
      {register.sections.map((section) => (
        <section key={section.id} aria-labelledby={`policy-${section.id}`} data-policy-section={section.id}>
          <SectionHead id={`policy-${section.id}`} title={section.title} note={section.summary} />
          <DataTable caption={section.title} data={section.rules} columns={RULE_COLUMNS} getRowId={(rule) => rule.id} narrow="stack" />
        </section>
      ))}
      <section aria-labelledby="policy-signals" data-policy-section="signals">
        <SectionHead
          id="policy-signals"
          title="Early warning rules"
          note={
            <>
              Rule table <span className="ident">{register.signal_rules.version}</span>. A rule never fires on a missing value.
            </>
          }
        />
        <DataTable caption="Early warning rules" data={register.signal_rules.rules} columns={SIGNAL_COLUMNS} getRowId={(rule) => rule.id} narrow="stack" />
      </section>
      <section aria-labelledby="policy-agents" data-policy-section="agents">
        <SectionHead id="policy-agents" title="Agent versions in this build" note="What would run if an agent were asked now. The inventory tab lists the versions a run has registered." />
        <DataTable caption="Agent versions in this build" data={register.agents} columns={AGENT_COLUMNS} getRowId={(agent) => `${agent.name}@${agent.version}`} narrow="stack" />
      </section>
    </div>
  );
}

function Policy() {
  const register = usePolicyRegister();
  return (
    <Load query={register} what="The policy rules" rows={12}>
      {(data) => (
        <div className="space-y-5">
          <p className="max-w-[86ch] text-prose text-pretty text-ink-700">
            These rules are applied by code, not by a model. Each setting is read from the constant or setting the enforcing code uses, and the last column
            names the module to read to check it.
          </p>
          <PolicyTables register={data} />
        </div>
      )}
    </Load>
  );
}

const TABS = [
  { id: 'roles', label: 'Roles and permissions' },
  { id: 'policy', label: 'Policy rules' },
  { id: 'ledger', label: 'Ledger' },
  { id: 'agents', label: 'Agent inventory' },
  { id: 'clock', label: 'Clock' },
] as const;

export function Governance() {
  const search = useSearch({ from: '/governance' });
  const navigate = useNavigate({ from: '/governance' });
  const tab = TABS.find((entry) => entry.id === search.tab)?.id ?? 'roles';
  return (
    <div data-ready className="space-y-5">
      <div>
        <PageHeader
          eyebrow="Bank of Stoic · Commercial lending"
          title="Governance"
          meta={<span>Who may do what; the rules code applies; what was done, by whom and when; which agent versions exist; and the date the demonstration runs on</span>}
        />
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
        {tab === 'roles' ? <Roles /> : tab === 'policy' ? <Policy /> : tab === 'ledger' ? <Ledger /> : tab === 'agents' ? <AgentInventory /> : <Clock />}
      </div>
    </div>
  );
}

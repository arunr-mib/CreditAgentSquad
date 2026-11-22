import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import { AuthContext } from '@/auth/context';
import { oldAddress } from '../redirects';
import { Oversight } from '../oversight/Oversight';

const h = vi.hoisted(() => ({
  ledgerCalls: [] as unknown[], runCalls: [] as unknown[], offered: true, verifyRefetch: vi.fn(), verifyError: null as Error | null,
  verifyData: undefined as unknown, runs: null as unknown[] | null, agents: null as unknown[] | null, steps: null as unknown[] | null,
  ledger: null as unknown[] | null, evaluation: null as unknown,
}));
const RUN = { id: 'r1', agent_name: 'covenant', task: 'investigate', agent_label: 'Covenant agent', task_label: 'Investigate', status_label: 'Abstained', borrower_name: 'Quillfeather Labs, Inc.', borrower_code: 'QFL', status: 'abstained', created_at: '2026-11-21T08:00:00Z', duration_ms: 1200, steps_count: 2, tool_calls: 5, input_tokens: 1234567, output_tokens: 20, error: null, guardrail_notes: [{ layer: 'narrative', check: 'figure_untraceable', action: 'dropped', detail: 'a typed figure', words: 'figure untraceable · dropped' }] };
const STEPS = [{ id: 's1', n: 1, kind: 'tool', name: 'read_page', input_summary: 'page 4', output_summary: 'read', detail: {}, refused: false, duration_ms: 10 }];
const EVENT = { seq: 7, id: 'e7', ts: '2026-11-21T08:00:00Z', actor_type: 'user', actor_id: 'u1', actor_name: 'Priya Raman', actor_label: 'Priya Raman', action: 'work_item.routed', entity_type: 'work_item', entity_id: 'w1', payload: {}, summary: '“Recommend reserving rights.”', hash: 'h', note: null };
const page = (n: number) => Array.from({ length: n }, (_, i) => ({ ...EVENT, seq: 7 + (n - 1 - i), id: `e${i}` }));
const EVAL = { source: 'file', id: null, suite: 'book', commit: 'c94f23b', borrowers: 20, mode: 'standin', standin: true, notice: 'Stand-in run: not model performance.', gate_passed: true, created_at: '2026-11-21T07:00:00Z', rows: [{ key: 'covenant_outcome_accuracy', label: 'Covenant outcome accuracy', value: '94.92', unit: 'pct' }, { key: 'exception_recall', label: 'Exception recall', value: null, unit: 'pct' }] };

vi.mock('@/api/hooks', () => ({
  useAgentRun: (id?: string | null) => ({ data: id ? { ...RUN, steps: h.steps ?? STEPS } : undefined }),
  useLedgerVerification: () => ({ data: h.verifyData, error: h.verifyError, isFetching: false, refetch: h.verifyRefetch }),
  useRolesAndPermissions: () => ({ data: { roles: [{ id: 'credit_officer', label: 'Credit officer', people: 1 }], permissions: [{ id: 'decide_breach', label: 'Decide the response to a breach', group: 'Exceptions', second_person: false }], grants: { credit_officer: ['decide_breach'] }, second_person: { rule: 'Two people.', applies_to: [] } }, isPending: false, error: null }),
  usePolicyRegister: () => ({ data: { sections: [], signal_rules: { version: '3', rules: [{ id: 'runway_below_watch', name: 'Runway below the watch level', severity: 'high', severity_label: 'High', trigger: 'Runway below 12 months; high severity below 9 months' }] }, agents: [] }, isPending: false, error: null }),
  useClock: () => ({ data: { today: '2026-11-21' } }),
  useSetClock: () => ({ mutate: vi.fn(), isPending: false, error: null }),
}));
vi.mock('../api/hooks', () => ({
  RUNS_PAGE: 100,
  useBriefing: () => ({ data: { oversight: { offered: h.offered } }, isPending: false }),
  useOversightRuns: (offset: number) => { h.runCalls.push(offset); return { data: h.runs ?? [RUN], isPending: false, error: null }; },
  useOversightAgents: () => ({ data: h.agents ?? [{ id: 'a1', label: 'Covenant agent', name: 'covenant', version: '2', model: 'm', effort: 'high', max_steps: 12, tools: ['read_page'], prompt_sha256: 'abc', spec_sha256: 'def', purpose: 'Investigates a covenant result', active: true, runs: 4 }], isPending: false, error: null }),
  useOversightLedger: (filter: unknown) => { h.ledgerCalls.push(filter); return { data: h.ledger ?? [EVENT], isPending: false, error: null }; },
  useLedgerActions: () => ({ data: [{ key: 'work_item', words: 'Cases' }, { key: 'borrowing_base', words: 'Borrowing base' }, { key: 'auth', words: 'Sign-ins' }] }),
  useEvaluation: () => h.evaluation ?? { data: EVAL, isPending: false, error: null },
}));
vi.mock('../DocType', () => ({ useDocWords: () => (t: string | null) => t ?? '' }));

function mount(path: string, role = 'credit_review', permissions: string[] = ['view', 'record_qa_finding']) {
  const root = createRootRoute();
  const base = createRoute({ getParentRoute: () => root, path: '/oversight', component: Oversight });
  const tab = createRoute({ getParentRoute: () => root, path: '/oversight/$tab', component: Oversight });
  const thread = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([base, tab, thread]), history: createMemoryHistory({ initialEntries: [path] }) });
  const user = { id: 'u9', email: 'r@x', name: 'Ruth Calloway', title: '', role, permissions };
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthContext.Provider value={{ user, status: 'signed-in', can: (p: string) => permissions.includes(p), signIn: async () => user, signOut: async () => {}, retry: () => {} }}>
        <RouterProvider router={router} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  Object.assign(h, { ledgerCalls: [], runCalls: [], offered: true, verifyError: null, verifyData: undefined, runs: null, agents: null, steps: null, ledger: null, evaluation: null });
  h.verifyRefetch.mockReset();
});
afterEach(() => cleanup());

describe('Oversight', () => {
  it('lists agent runs with their outcome, the client, the guardrail notes, tool calls and, on request, the steps', async () => {
    mount('/oversight/activity');
    const table = await screen.findByRole('table', { name: 'Agent activity' });
    expect(within(table).getByText('Abstained')).toBeInTheDocument();
    expect(within(table).getByRole('link', { name: 'Quillfeather Labs, Inc.' })).toHaveAttribute('href', '/clients/QFL');
    expect(within(table).getByText(/figure untraceable · dropped/)).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: '5' })).toBeInTheDocument(); // tool calls, not the two stored steps
    expect(within(table).getByText('1,234,567 / 20')).toBeInTheDocument();
    await userEvent.click(within(table).getByRole('button', { name: 'Steps of covenant investigate' }));
    expect(await screen.findByText(/read_page · page 4/)).toBeInTheDocument();
  });

  it('says so when no agent has run, when a run has no steps, and shows a failed run’s error', async () => {
    h.runs = [];
    mount('/oversight/activity');
    expect(await screen.findByText('No agent has run in this database yet.')).toBeInTheDocument();
    cleanup();
    h.runs = [{ ...RUN, status: 'failed', status_label: 'Failed', error: 'The model did not answer.' }];
    h.steps = [];
    mount('/oversight/activity');
    await userEvent.click(await screen.findByRole('button', { name: 'Steps of covenant investigate' }));
    expect(await screen.findByText('No steps were recorded for this run.')).toBeInTheDocument();
    expect(screen.getByText(/The model did not answer\./)).toBeInTheDocument();
  });

  it('pages back through runs past the first page', async () => {
    h.runs = Array.from({ length: 100 }, (_, i) => ({ ...RUN, id: `r${i}` }));
    mount('/oversight/activity');
    await userEvent.click(await screen.findByRole('button', { name: 'Older runs' }));
    expect(h.runCalls.at(-1)).toBe(100);
  });

  it('describes ledger events in words, filters by the served families, hides sign-ins on the server and pages back', async () => {
    h.ledger = page(100);
    mount('/oversight/ledger');
    expect(await screen.findAllByText(/Recommend reserving rights/)).not.toHaveLength(0);
    expect(h.ledgerCalls.at(-1)).toMatchObject({ hide_sign_ins: true });
    const select = screen.getByLabelText('Action');
    expect(within(select).getByRole('option', { name: 'Borrowing base' })).toBeInTheDocument();
    await userEvent.selectOptions(select, 'borrowing_base');
    expect(h.ledgerCalls.at(-1)).toMatchObject({ action: 'borrowing_base' });
    await userEvent.selectOptions(select, 'auth');
    expect(screen.getByRole('checkbox', { name: 'Hide sign-ins' })).toBeDisabled();
    await userEvent.selectOptions(select, 'borrowing_base');
    await userEvent.click(screen.getByRole('checkbox', { name: 'Hide sign-ins' }));
    expect(h.ledgerCalls.at(-1)).toMatchObject({ hide_sign_ins: false });
    await userEvent.click(screen.getByRole('button', { name: 'Older events' }));
    expect(h.ledgerCalls.at(-1)).toMatchObject({ before_seq: 7 });
  });

  it('names who acted from the server’s words, says when nothing matches, and offers no older page after a short one', async () => {
    mount('/oversight/ledger');
    expect(await screen.findByText('Priya Raman')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Older events' })).not.toBeInTheDocument();
    cleanup();
    h.ledger = [];
    mount('/oversight/ledger');
    expect(await screen.findByText('No events match.')).toBeInTheDocument();
  });

  it('verifies the chain again on every press and shows a verification error', async () => {
    mount('/oversight/ledger');
    const button = await screen.findByRole('button', { name: 'Verify the chain' });
    await userEvent.click(button);
    await userEvent.click(button);
    expect(h.verifyRefetch).toHaveBeenCalledTimes(1); // the first press starts the check, the second asks again
    cleanup();
    h.verifyError = new ApiError(500, 'The ledger could not be read.');
    mount('/oversight/ledger');
    await userEvent.click(await screen.findByRole('button', { name: 'Verify the chain' }));
    expect(await screen.findByText(/The ledger could not be read\./)).toBeInTheDocument();
  });

  it('shows the agent inventory and the signal rules beside the permission matrix, in plain severity words', async () => {
    mount('/oversight/governance');
    expect(await screen.findByRole('table', { name: 'Agents' })).toHaveTextContent('Investigates a covenant result');
    const rules = screen.getByRole('table', { name: 'Signal rules' });
    expect(rules).toHaveTextContent('Runway below the watch level');
    expect(rules).toHaveTextContent('High');
    expect(rules).toHaveTextContent('Runway below 12 months; high severity below 9 months');
  });

  it('says so when no agent is registered', async () => {
    h.agents = [];
    mount('/oversight/governance');
    expect(await screen.findByText('No agent is registered yet.')).toBeInTheDocument();
  });

  it('labels a stand-in evaluation, says where it came from, prints shares as the server’s percentages and unmeasured as such', async () => {
    mount('/oversight/evaluations');
    expect(await screen.findByText('Stand-in run: not model performance.')).toBeInTheDocument();
    expect(screen.getByText(/From the repository file, commit c94f23b, 20 clients/)).toBeInTheDocument();
    expect(screen.getByText('94.92%')).toBeInTheDocument();
    expect(screen.getByText('Not measured')).toBeInTheDocument();
    cleanup();
    h.evaluation = { data: { ...EVAL, source: 'database', id: 'abcdef12-0000', commit: 'def5678' }, isPending: false, error: null };
    mount('/oversight/evaluations');
    expect(await screen.findByText(/A run in this database, commit def5678/)).toBeInTheDocument();
  });

  it('reads a missing evaluation as missing and any other failure as a failure', async () => {
    h.evaluation = { data: undefined, isPending: false, error: new ApiError(404, 'No evaluation has been run yet.') };
    mount('/oversight/evaluations');
    expect(await screen.findByText('No evaluation has been run yet.')).toBeInTheDocument();
    cleanup();
    h.evaluation = { data: undefined, isPending: false, error: new ApiError(500, 'The scorecard could not be read.') };
    mount('/oversight/evaluations');
    expect(await screen.findByRole('alert')).toHaveTextContent('The scorecard could not be read.');
  });

  it('marks exactly one tab as current', async () => {
    mount('/oversight/ledger');
    const nav = await screen.findByRole('navigation', { name: 'Oversight' });
    const current = within(nav).getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page');
    expect(current.map((a) => a.textContent)).toEqual(['Ledger']);
    cleanup();
    mount('/oversight');
    const nav2 = await screen.findByRole('navigation', { name: 'Oversight' });
    expect(within(nav2).getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page').map((a) => a.textContent)).toEqual(['Agent activity']);
  });

  it('offers the clock only to a role that may move it, and never a credit decision', async () => {
    mount('/oversight', 'credit_review');
    expect(await screen.findByRole('navigation', { name: 'Oversight' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Clock' })).not.toBeInTheDocument();
    cleanup();
    mount('/oversight/clock', 'credit_review');
    expect(await screen.findByText('The clock is for the administrator.')).toBeInTheDocument();
    cleanup();
    mount('/oversight/clock', 'admin', ['view', 'change_policy', 'manage_users', 'advance_clock']);
    expect(await screen.findByText(/The working date is 21 Nov 2026/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /record decision|send to|return to|attach/i })).not.toBeInTheDocument();
  });

  it('lets the server decide who has oversight', async () => {
    h.offered = false;
    mount('/oversight', 'credit_review');
    expect(await screen.findByText('Oversight is for administrators, credit administration and credit review.')).toBeInTheDocument();
  });

  it('moves the old oversight addresses', () => {
    expect(oldAddress('/agent-activity', {})).toBe('/oversight/activity');
    expect(oldAddress('/governance', {})).toBe('/oversight/governance');
    expect(oldAddress('/command-centre', {})).toBe('/');
  });
});

describe('no credit decision in Oversight', () => {
  it.each(['activity', 'ledger', 'governance', 'evaluations', 'clock'])('offers none on %s to an administrator', async (tab) => {
    mount(`/oversight/${tab}`, 'admin', ['view', 'change_policy', 'manage_users', 'advance_clock']);
    await screen.findByRole('navigation', { name: 'Oversight' });
    expect(screen.queryByRole('button', { name: /decide|route|return|attach|send to|record decision/i })).not.toBeInTheDocument();
  });
});

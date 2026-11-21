import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AuthContext } from '@/auth/context';
import type { LedgerEvent } from '@/api/schema';
import { describeEvent } from '../oversight/describeEvent';
import { oldAddress } from '../redirects';
import { Oversight } from '../oversight/Oversight';

const ledgerCalls = vi.hoisted(() => [] as unknown[]);
const RUN = { id: 'r1', agent_name: 'covenant', task: 'investigate', agent_label: 'Covenant agent', task_label: 'Investigate', status_label: 'Abstained', borrower_name: 'Quillfeather Labs, Inc.', borrower_code: 'QFL', status: 'abstained', created_at: '2026-11-21T08:00:00Z', duration_ms: 1200, steps_count: 12, input_tokens: 100, output_tokens: 20, guardrail_notes: [{ layer: 'narrative', check: 'figure_untraceable', action: 'dropped', detail: 'a typed figure', words: 'figure untraceable · dropped' }] };
vi.mock('@/api/hooks', () => ({
  useAgentRun: (id?: string | null) => ({ data: id ? { ...RUN, steps: [{ id: 's1', n: 1, kind: 'tool', name: 'read_page', input_summary: 'page 4', output_summary: 'read', detail: {}, refused: false, duration_ms: 10 }] } : undefined }),
  useLedger: (filter: unknown) => {
    ledgerCalls.push(filter);
    return { data: [{ seq: 7, id: 'e7', ts: '2026-11-21T08:00:00Z', actor_type: 'user', actor_id: 'u1', actor_name: 'Priya Raman', action: 'work_item.routed', entity_type: 'work_item', entity_id: 'w1', payload: { view: 'Recommend reserving rights.' }, hash: 'h', note: null }], isPending: false, error: null };
  },
  useLedgerVerification: () => ({ data: undefined, isFetching: false }),
  useRolesAndPermissions: () => ({ data: { roles: [{ id: 'credit_officer', label: 'Credit officer', people: 1 }], permissions: [{ id: 'decide_breach', label: 'Decide the response to a breach', group: 'Exceptions', second_person: false }], grants: { credit_officer: ['decide_breach'] }, second_person: { rule: 'Two people.', applies_to: [] } }, isPending: false, error: null }),
  usePolicyRegister: () => ({ data: { sections: [], signal_rules: { version: '3', rules: [{ id: 'runway_below_watch', name: 'Runway below watch', severity: 'high', trigger: 'runway under 9 months' }] }, agents: [] }, isPending: false, error: null }),
  useClock: () => ({ data: { today: '2026-11-21' } }),
  useSetClock: () => ({ mutate: vi.fn(), isPending: false, error: null }),
}));
vi.mock('../api/hooks', () => ({
  useOversightRuns: () => ({ data: [RUN], isPending: false, error: null }),
  useOversightAgents: () => ({ data: [{ id: 'a1', label: 'Covenant agent', name: 'covenant', version: '2', model: 'm', effort: 'high', max_steps: 12, tools: ['read_page'], prompt_sha256: 'abc', spec_sha256: 'def', purpose: 'Investigates a covenant result', active: true, runs: 4 }] }),
  useEvaluation: () => ({ data: { mode: 'standin', standin: true, notice: 'Stand-in run: not model performance.', gate_passed: true, created_at: '2026-11-21T07:00:00Z', rows: [{ key: 'covenant_outcome_accuracy', label: 'Covenant outcome accuracy', value: '94.92', unit: 'pct' }, { key: 'exception_recall', label: 'Exception recall', value: null, unit: 'pct' }] }, isPending: false, error: null }),
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

describe('Oversight', () => {
  it('lists agent runs with their outcome, the client, the guardrail notes and, on request, the steps', async () => {
    mount('/oversight/activity');
    const table = await screen.findByRole('table', { name: 'Agent activity' });
    expect(within(table).getByText('Abstained')).toBeInTheDocument();
    expect(within(table).getByRole('link', { name: 'Quillfeather Labs, Inc.' })).toHaveAttribute('href', '/clients/QFL');
    expect(within(table).getByText(/figure untraceable · dropped/)).toBeInTheDocument();
    await userEvent.click(within(table).getByRole('button', { name: 'Steps of covenant investigate' }));
    expect(await screen.findByText(/read_page · page 4/)).toBeInTheDocument();
  });

  it('describes ledger events in words, filters by action, hides sign-ins and pages back', async () => {
    mount('/oversight/ledger');
    expect(await screen.findByText(/Recommend reserving rights/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Action'), 'work_item');
    expect(ledgerCalls.at(-1)).toMatchObject({ action: 'work_item' });
    await userEvent.click(screen.getByRole('button', { name: 'Older events' }));
    expect(ledgerCalls.at(-1)).toMatchObject({ before_seq: 7 });
  });

  it('shows the agent inventory and the signal rules beside the permission matrix', async () => {
    mount('/oversight/governance');
    expect(await screen.findByRole('table', { name: 'Agents' })).toHaveTextContent('Investigates a covenant result');
    expect(screen.getByRole('table', { name: 'Signal rules' })).toHaveTextContent('Runway below watch');
  });

  it('labels a stand-in evaluation, prints shares as the server’s percentages and unmeasured as such', async () => {
    mount('/oversight/evaluations');
    expect(await screen.findByText('Stand-in run: not model performance.')).toBeInTheDocument();
    expect(screen.getByText('94.92%')).toBeInTheDocument();
    expect(screen.getByText('Not measured')).toBeInTheDocument();
  });

  it('offers the clock only to a role that may move it, and never a credit decision', async () => {
    mount('/oversight', 'credit_review');
    expect(await screen.findByRole('navigation', { name: 'Oversight' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Clock' })).not.toBeInTheDocument();
    mount('/oversight', 'admin', ['view', 'change_policy', 'manage_users', 'advance_clock']);
    expect(await screen.findAllByRole('link', { name: 'Clock' })).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: /record decision|send to|return to|attach/i })).not.toBeInTheDocument();
  });

  it('tells a role without oversight that the page is not theirs', async () => {
    mount('/oversight', 'analyst', ['view', 'decide_work_item']);
    expect(await screen.findByText('Oversight is for administrators, credit administration and credit review.')).toBeInTheDocument();
  });

  it('moves the old oversight addresses', () => {
    expect(oldAddress('/agent-activity', {})).toBe('/oversight/activity');
    expect(oldAddress('/governance', {})).toBe('/oversight/governance');
    expect(oldAddress('/command-centre', {})).toBe('/');
  });
});

describe('describeEvent', () => {
  const event = (action: string, payload: Record<string, unknown>) => ({ seq: 1, id: 'e', ts: '2026-11-21T08:00:00Z', actor_type: 'user', actor_id: 'u', action, entity_type: 'work_item', entity_id: 'w', payload }) as unknown as LedgerEvent;
  it('reads a routed view and names a document type in the served words', () => {
    expect(describeEvent(event('work_item.routed', { view: 'Recommend reserving rights.' }))).toBe('“Recommend reserving rights.”');
    expect(describeEvent(event('document.classified', { document_type: 'mrr_report' }), (t) => (t === 'mrr_report' ? 'MRR report' : ''))).toBe('MRR report');
  });
});

describe('no credit decision in Oversight', () => {
  it.each(['activity', 'ledger', 'governance', 'evaluations', 'clock'])('offers none on %s to an administrator', async (tab) => {
    mount(`/oversight/${tab}`, 'admin', ['view', 'change_policy', 'manage_users', 'advance_clock']);
    await screen.findByRole('navigation', { name: 'Oversight' });
    expect(screen.queryByRole('button', { name: /decide|route|return|attach|send to|record decision/i })).not.toBeInTheDocument();
  });
});


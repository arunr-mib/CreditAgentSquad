import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser, WorkItemDetail } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { SeverityTag } from '../parts';
import { DecisionForm } from './WorkItemPanel';

const item = (over: Partial<WorkItemDetail> = {}): WorkItemDetail =>
  ({
    id: 'w-1',
    borrower_id: 'b-1',
    borrower_name: 'Kestrel Bay Packaging Corp.',
    item_type: 'covenant.reported_mismatch',
    severity: 'critical',
    title: 'Total Leverage Ratio fails but the certificate reports compliance',
    question: 'How should the bank respond?',
    allowed_decisions: ['waiver_requested', 'escalate_to_committee'],
    required_permission: 'decide_breach',
    requires_second_person: false,
    assigned_to: null,
    due_date: null,
    status: 'open',
    evidence: {},
    guardrail_notes: [],
    recommendation: null,
    ...over,
  }) as unknown as WorkItemDetail;

const analyst: ApiUser = {
  id: 'u-1',
  email: 'priya@bankofstoic.example',
  name: 'Priya Raman',
  title: 'Senior Credit Analyst',
  role: 'analyst',
  permissions: ['view', 'decide_work_item', 'manage_actions'],
};
const officer: ApiUser = {
  id: 'u-2',
  email: 'helen@bankofstoic.example',
  name: 'Helen Strand',
  title: 'Senior Credit Officer',
  role: 'credit_officer',
  permissions: ['view', 'decide_breach', 'manage_actions'],
};
const PEOPLE = [
  { id: 'u-1', name: 'Priya Raman', title: 'Senior Credit Analyst', role: 'analyst' },
  { id: 'u-2', name: 'Helen Strand', title: 'Senior Credit Officer', role: 'credit_officer' },
];

function mockApi() {
  const calls: Array<{ method: string; url: string; body: unknown }> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET';
      calls.push({ method, url, body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined });
      const body = url.startsWith('/api/v1/ui/users') ? PEOPLE : item();
      return { ok: true, status: 200, text: async () => JSON.stringify(body) } as Response;
    }),
  );
  return calls;
}

function show(work: WorkItemDetail, user: ApiUser) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = {
    user,
    status: 'signed-in' as const,
    can: (permission: string) => user.permissions.includes(permission),
    signIn: async () => user,
    signOut: async () => {},
    retry: () => {},
  };
  return render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <DecisionForm item={work} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('a decision outside the reader’s authority', () => {
  it('cannot be recorded, names who may decide, and routes to that person in one press', async () => {
    const calls = mockApi();
    show(item(), analyst);
    expect(screen.getByRole('button', { name: 'Record decision' })).toBeDisabled();
    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled();
    const gate = document.querySelector('[data-authority-gate]') as HTMLElement;
    expect(gate).toHaveTextContent('Credit officer sign-off');
    expect(gate).toHaveTextContent('Your role, Credit analyst, does not have it');
    await userEvent.click(await screen.findByRole('button', { name: 'Route to Helen Strand for sign-off' }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    expect(calls.filter((call) => call.method === 'POST')).toEqual([
      { method: 'POST', url: '/api/v1/work-items/w-1/assign', body: { assigned_to: 'u-2', due_date: null } },
    ]);
  });

  it('shows who it was routed to instead of offering to route it again', async () => {
    mockApi();
    show(item({ assigned_to: 'u-2' }), analyst);
    expect(await screen.findByText('Routed to Helen Strand, Senior Credit Officer')).toBeVisible();
    expect(screen.queryByRole('button', { name: /Route to/ })).toBeNull();
  });
});

describe('a decision within the reader’s authority', () => {
  it('has no gate, and records the chosen card with its reason', async () => {
    const calls = mockApi();
    show(item(), officer);
    expect(document.querySelector('[data-authority-gate]')).toBeNull();
    await userEvent.click(screen.getByRole('radio', { name: /Escalate to committee/ }));
    await userEvent.type(screen.getByLabelText('Reason (required)'), 'Second breach in two quarters.');
    await userEvent.click(screen.getByRole('button', { name: 'Record decision' }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    expect(calls.find((call) => call.method === 'POST')).toEqual({
      method: 'POST',
      url: '/api/v1/work-items/w-1/decide',
      body: { decision: 'escalate_to_committee', reason: 'Second breach in two quarters.' },
    });
  });

  it('asks for a reason before recording a decision that needs one', async () => {
    const calls = mockApi();
    show(item(), officer);
    await userEvent.click(screen.getByRole('radio', { name: /Escalate to committee/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Record decision' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This decision needs a reason');
    expect(calls.filter((call) => call.method === 'POST')).toEqual([]);
  });
});

describe('severity', () => {
  it('is a tag where it calls for action and plain text where it does not', () => {
    const { container, rerender } = render(<SeverityTag severity="critical" />);
    expect(container.querySelector('[data-tag="breach"]')).toHaveTextContent('Critical');
    rerender(<SeverityTag severity="high" />);
    expect(container.querySelector('[data-tag="attention"]')).toHaveTextContent('High');
    rerender(<SeverityTag severity="low" />);
    expect(container.querySelector('[data-tag]')).toBeNull();
    expect(container).toHaveTextContent('Low');
  });
});

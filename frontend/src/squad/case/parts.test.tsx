import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser, WorkItemDetail } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { WorkspaceDrawerContext, type WorkspaceDrawerValue } from '@/drawer/context';
import { SeverityTag } from '../parts';
import { DecisionForm, WorkItemPanel } from './WorkItemPanel';

window.scrollTo = () => {};
const noop = () => {};
const drawerValue: WorkspaceDrawerValue = {
  open: true,
  tab: 'item',
  itemId: 'w-1',
  borrowerCode: null,
  copilotScope: { kind: 'portfolio' },
  reasonDraft: null,
  openItem: noop,
  openBorrower: noop,
  openCopilot: noop,
  setTab: noop,
  setCopilotScope: noop,
  draftReason: noop,
  close: noop,
};

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
      { method: 'POST', url: '/api/v1/work-items/w-1/assign', body: { assigned_to: 'u-2' } },
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

describe('open questions that may change the result', () => {
  const RELATED = [
    {
      id: 'w-amend-1234',
      item_type: 'terms.amendment_unapproved',
      title: 'Second amendment is on file but not approved into terms',
      severity: 'high' as const,
      status: 'open' as const,
      relation: 'An unapproved amendment may change the threshold',
    },
    { id: 'w-held-5678', item_type: 'spread.value_unverified', title: 'Two figures are held', severity: 'medium' as const, status: 'open' as const, relation: 'Held figures feed this ratio' },
  ];

  function panel(work: WorkItemDetail) {
    const openItem = vi.fn();
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const body = url.startsWith('/api/v1/work-items/') ? work : url.startsWith('/api/v1/ui/users') ? PEOPLE : [];
        return { ok: true, status: 200, text: async () => JSON.stringify(body) } as Response;
      }),
    );
    const root = createRootRoute();
    const page = createRoute({ getParentRoute: () => root, path: '/', component: () => <WorkItemPanel itemId={work.id} variant="drawer" /> });
    const router = createRouter({ routeTree: root.addChildren([page]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const auth = {
      user: officer,
      status: 'signed-in' as const,
      can: (permission: string) => officer.permissions.includes(permission),
      signIn: async () => officer,
      signOut: async () => {},
      retry: () => {},
    };
    render(
      <QueryClientProvider client={client}>
        <AuthContext.Provider value={auth}>
          <WorkspaceDrawerContext.Provider value={{ ...drawerValue, openItem }}>
            <RouterProvider router={router as never} />
          </WorkspaceDrawerContext.Provider>
        </AuthContext.Provider>
      </QueryClientProvider>,
    );
    return openItem;
  }

  it('lists each related open item above the decision, each opening in the drawer, without blocking the decision', async () => {
    const openItem = panel(item({ related_items: RELATED }));
    const notice = await screen.findByRole('region', { name: 'Open questions that may change this result' });
    const form = screen.getByRole('form', { name: 'Record a decision' });
    expect(notice.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(notice).toHaveTextContent('An unapproved amendment may change the threshold');
    await userEvent.click(screen.getByRole('button', { name: 'Second amendment is on file but not approved into terms' }));
    expect(openItem).toHaveBeenCalledWith('w-amend-1234');
    await userEvent.click(screen.getByRole('radio', { name: /Escalate to committee/ }));
    expect(screen.getByRole('button', { name: 'Record decision' })).toBeEnabled();
  });

  it('shows nothing when there are none, or when the API does not send them', async () => {
    panel(item({ related_items: [] }));
    await screen.findByRole('form', { name: 'Record a decision' });
    expect(screen.queryByRole('region', { name: 'Open questions that may change this result' })).toBeNull();
  });

  it('names each review section the checks withheld and the check that withheld it', async () => {
    panel(
      item({
        item_type: 'review.commentary_approval',
        evidence: {
          withheld_sections: [
            { section: 'covenants', withheld_by: 'number check', reason: 'a figure was typed, not referenced' },
            { section: 'outlook', withheld_by: 'policy check', reason: 'the wording was refused' },
          ],
        },
      }),
    );
    const block = await waitFor(() => {
      const found = document.querySelector('[data-withheld-sections]');
      expect(found).not.toBeNull();
      return found as HTMLElement;
    });
    expect(block).toHaveTextContent('2 sections were withheld');
    expect(block).toHaveTextContent('Covenants · withheld by the number check');
    expect(block).toHaveTextContent('Outlook · withheld by the policy check');
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

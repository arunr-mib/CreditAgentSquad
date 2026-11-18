import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { SourceContext } from '@/source/context';
import { CopilotConversationProvider, CopilotPanel } from './CopilotPanel';
import { WorkspaceDrawerContext, type WorkspaceDrawerValue } from './context';

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
  useRouterState: () => '/command-centre',
}));

const analyst: ApiUser = {
  id: 'u-1',
  email: 'priya@bankofstoic.example',
  name: 'Priya Raman',
  title: 'Senior Credit Analyst',
  role: 'analyst',
  permissions: ['view', 'decide_work_item'],
};
const ITEM = {
  id: 'w-1234567890',
  borrower_id: 'b-1',
  borrower_name: 'Briarstone Beverage Company',
  item_type: 'bb.over_advance',
  severity: 'critical',
  status: 'open',
  required_permission: 'decide_breach',
  evidence: {},
  guardrail_notes: [],
};
const REPLY = {
  status: 'answered',
  answer: 'Leverage is 2.60x.',
  answer_with_references: 'Leverage is {{fact:f-1}}.',
  fact_ids: ['f-1'],
  citations: [{ document_id: 'd-1', page: 14, quote: 'shall not exceed 2.50 to 1.00', document_title: 'Credit Agreement' }],
  follow_ups: [],
  guardrail_notes: [],
  agent_run_id: 'run-abcdef123456',
};

const FACT = {
  id: 'f-1abcdefgh',
  key: 'cov.total_leverage.value',
  label: 'Total leverage',
  value: '2.60',
  unit: 'ratio',
  kind: 'calculated',
  status: 'verified',
  period_end: '2026-09-30',
  months: 0,
  borrower_id: 'b-1',
  document_id: null,
  page: null,
  calc_run_id: 'c-1',
};

function mockApi(connected: boolean) {
  const calls: Array<{ method: string; url: string; body: unknown }> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET';
      calls.push({ method, url, body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined });
      let body: unknown = [];
      if (url.startsWith('/api/v1/agents/status'))
        body = { model_connected: connected, mode: 'live', model: 'claude-opus-5-5', reason: connected ? '' : 'No model key is set for this deployment.' };
      else if (url.startsWith('/api/v1/ui/portfolio'))
        body = { borrowers: 21, covenants: { tests: 46, by_outcome: [{ outcome: 'breach_reported_compliant', count: 3 }] } };
      else if (url.startsWith('/api/v1/work-items/')) body = ITEM;
      else if (url.startsWith('/api/v1/work-items')) body = [ITEM, { ...ITEM, id: 'w-2', required_permission: 'decide_work_item' }];
      else if (url.startsWith('/api/v1/ui/facts')) body = { 'f-1': FACT };
      else if (url.startsWith('/api/v1/copilot/ask')) body = REPLY;
      return { ok: true, status: 200, text: async () => JSON.stringify(body) } as Response;
    }),
  );
  return calls;
}

function show(over: Partial<WorkspaceDrawerValue> = {}) {
  const noop = () => {};
  const drawer: WorkspaceDrawerValue = {
    open: true,
    tab: 'copilot',
    itemId: 'w-1234567890',
    borrowerCode: null,
    copilotScope: { kind: 'item', itemId: 'w-1234567890' },
    reasonDraft: null,
    openItem: noop,
    openBorrower: noop,
    openCopilot: noop,
    setTab: noop,
    setCopilotScope: noop,
    draftReason: vi.fn(),
    close: noop,
    ...over,
  };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const auth = {
    user: analyst,
    status: 'signed-in' as const,
    can: (permission: string) => analyst.permissions.includes(permission),
    signIn: async () => analyst,
    signOut: async () => {},
    retry: () => {},
  };
  render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <SourceContext.Provider value={{ open: () => {}, close: () => {}, current: null }}>
          <WorkspaceDrawerContext.Provider value={drawer}>
            <CopilotConversationProvider>
              <CopilotPanel />
            </CopilotConversationProvider>
          </WorkspaceDrawerContext.Provider>
        </SourceContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return drawer;
}

afterEach(() => vi.unstubAllGlobals());

describe('the Copilot’s starting points', () => {
  it('are written from what is on file: the reader, the real counts and the open exception', async () => {
    mockApi(true);
    show();
    expect(await screen.findByText('Which of the 2 open exceptions can Priya Raman (Credit analyst) decide right now?')).toBeVisible();
    expect(screen.getByText(/Audit the 3 covenant tests marked “Breach, reported compliant”/)).toBeVisible();
    expect(screen.getByText(/Summarise Briarstone Beverage Company’s over-advance \(w-123456\)/)).toBeVisible();
    await waitFor(() => expect(screen.getAllByRole('button', { name: /Audit|Which of|Summarise|List the overdue/ })[0]).toBeEnabled());
  });

  it('are switched off, with the reason, where no model is connected', async () => {
    mockApi(false);
    show();
    expect(await screen.findByText('No model key is set for this deployment.')).toBeVisible();
    for (const starter of document.querySelectorAll('[data-starter]')) expect(starter).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
  });
});

describe('a Copilot answer', () => {
  it('sends the scope the reader chose, shows figures as fact chips and quotes as verified, and copies to the decision with its run', async () => {
    const calls = mockApi(true);
    const drawer = show();
    await userEvent.type(screen.getByRole('textbox'), 'What is leverage?{Enter}');
    const answer = await screen.findByLabelText('Written by the Copilot: answered');
    const sent = calls.find((call) => call.url.startsWith('/api/v1/copilot/ask'));
    expect(sent?.body).toMatchObject({ question: 'What is leverage?', work_item_id: 'w-1234567890' });
    await waitFor(() => expect(answer.querySelector('[data-fact-chip]')).toHaveTextContent('f-1abcde'));
    expect(answer.querySelector('[data-verified-quote]')).toHaveTextContent('Quote verified by code · p. 14');
    await userEvent.click(screen.getByRole('button', { name: 'Copy to decision reason' }));
    expect(drawer.draftReason).toHaveBeenCalledWith('w-1234567890', 'Leverage is 2.60x. (from the Copilot, run run-abcd)');
  });
});

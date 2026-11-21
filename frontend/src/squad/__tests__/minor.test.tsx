// Final-review minor fixes: wording and states in the Squad thread.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import { SignIn } from '@/screens/SignIn';
import type { ThreadMessage, Trail as TrailData } from '../api/types';
import { PresenceProvider } from '../presence/Presence';
import { AskMessage } from '../thread/AskMessage';
import { caseState } from '../thread/messages';
import { Time } from '../thread/Time';
import { Trail } from '../thread/Trail';

const hooks = vi.hoisted(() => ({ trail: undefined as unknown }));
vi.mock('../api/hooks', () => ({
  useAnswer: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useTrail: () => ({ data: hooks.trail, isPending: false, error: null, refetch: vi.fn() }),
}));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p data-testid="body">{text}</p> }));

const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: ['decide_work_item'] };
const asPriya = (ui: React.ReactNode) => (
  <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => true, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
    <PresenceProvider needs={0}>{ui}</PresenceProvider>
  </AuthContext.Provider>
);

describe('sign in', () => {
  it('says Credit Squad', () => {
    render(
      <AuthContext.Provider value={{ user: null, status: 'signed-out', can: () => false, signIn: async () => priya, signOut: async () => {}, retry: () => {} } as never}>
        <SignIn />
      </AuthContext.Provider>,
    );
    expect(screen.getByText('Credit Squad')).toBeInTheDocument();
    expect(screen.queryByText('Credit Agent Squad')).not.toBeInTheDocument();
  });
});

describe('Time', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 20, 15, 30));
  });
  afterEach(() => vi.useRealTimers());

  it('shows only the time for today', () => {
    render(<Time ts={new Date(2026, 10, 20, 14, 2).toISOString()} />);
    expect(screen.getByText(/2:02/)).toBeInTheDocument();
    expect(screen.queryByText(/Nov/)).not.toBeInTheDocument();
  });

  it('shows the date, then the time, for another day', () => {
    render(<Time ts={new Date(2026, 10, 18, 14, 2).toISOString()} />);
    expect(screen.getByText(/18 Nov.*2:02/)).toBeInTheDocument();
  });

  it('adds the year for another year', () => {
    render(<Time ts={new Date(2025, 10, 18, 14, 2).toISOString()} />);
    expect(screen.getByText(/18 Nov 2025/)).toBeInTheDocument();
  });
});

const ask = (over: Partial<Extract<ThreadMessage, { type: 'ask' }>> = {}): Extract<ThreadMessage, { type: 'ask' }> => ({
  id: 'ask:1', ts: 't', type: 'ask', work_item_id: 'w1', title: 'T', question: 'Which?', options: [{ id: 'a', label: 'A', evidence: '' }, { id: 'b', label: 'B', evidence: '' }],
  status: 'open', choice: null, chosen_by: null, needs_you: true, state_words: '', habits: [], ...over,
});

describe('AskMessage when it is no longer open', () => {
  it('says "Closed without an answer" when nobody chose, never "null chose null"', () => {
    render(asPriya(<AskMessage message={ask({ status: 'closed' })} focused={false} />));
    expect(screen.getByText('Closed without an answer')).toBeInTheDocument();
    expect(screen.queryByText(/null/)).not.toBeInTheDocument();
  });

  it('names who chose what once answered', () => {
    render(asPriya(<AskMessage message={ask({ status: 'decided', choice: 'Map to ARR', chosen_by: 'Priya Raman' })} focused={false} />));
    expect(screen.getByText('Priya Raman chose Map to ARR')).toBeInTheDocument();
  });
});

describe('decision words', () => {
  const base = { ts: 't' };
  const kase: Extract<ThreadMessage, { type: 'case' }> = { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'C', question: 'q', severity: 'high', status: 'decided', allowed_decisions: [], needs_you: false, state_words: '' };

  it('reads a decided case in the backend\'s past tense', () => {
    const decision: ThreadMessage = { ...base, id: 'decision:1', type: 'decision', work_item_id: 'w1', decision: 'approve', decision_words: 'approved', reason: '', by: 'Helen Strand', by_id: 'u2' };
    expect(caseState(kase, [kase, decision]).text).toBe('approved by Helen Strand');
  });

  it('falls back to the stored words when the server sent none', () => {
    const decision = { ...base, id: 'decision:1', type: 'decision', work_item_id: 'w1', decision: 'not_a_breach', reason: '', by: 'Helen Strand', by_id: 'u2' } as ThreadMessage;
    expect(caseState(kase, [kase, decision]).text).toBe('not a breach by Helen Strand');
  });
});

describe('Trail', () => {
  const data = (over: Partial<TrailData>): TrailData => ({ work_item_id: 'w1', steps: [], calculation: null, checks: [], ...over });
  const mount = () => render(<QueryClientProvider client={new QueryClient()}><Trail workItemId="w1" /></QueryClientProvider>);
  const open = async () => userEvent.click(screen.getByRole('button', { name: /how i got here/i }));

  it('marks a failed run as failed, not as a tick', async () => {
    hooks.trail = data({ steps: [{ n: 1, who: 'Spreading agent', role_line: 'reads', text: 'Ran read statements.', check: 'failed', run_id: 'r1' }, { n: 2, who: 'Code', role_line: 'c', text: 'Applied.', check: 'exact arithmetic', run_id: null }] });
    mount();
    await open();
    expect(screen.getByText('✗ failed')).toBeInTheDocument();
    expect(screen.getByText('✓ exact arithmetic')).toBeInTheDocument();
    expect(screen.queryByText('✓ failed')).not.toBeInTheDocument();
  });

  it('shows the calculation with its inputs by fact id, and its outputs', async () => {
    hooks.trail = data({
      steps: [{ n: 1, who: 'Code', role_line: 'c', text: 'Applied cov.min_cash to 2 stored figures.', check: 'exact arithmetic', run_id: null }],
      calculation: { id: 'c1', formula_key: 'cov.min_cash', inputs: [{ name: 'Unrestricted cash', key: 'cash', fact_id: 'f-123' }, { name: 'Floor', key: 'floor', value: 'n/a' }], outputs: { headroom: '12' } },
    });
    mount();
    await open();
    const calc = screen.getByRole('group', { name: /calculation/i });
    expect(within(calc).getByText('cov.min_cash')).toBeInTheDocument();
    expect(within(calc).getByText(/Unrestricted cash/)).toBeInTheDocument();
    expect(within(calc).getByTestId('body')).toHaveTextContent('{{fact:f-123}}');
    expect(within(calc).getByText(/headroom/)).toBeInTheDocument();
  });

  it('lists the checks that ran', async () => {
    hooks.trail = data({ steps: [{ n: 1, who: 'A', role_line: 'r', text: 't', check: 'completed', run_id: null }], checks: [{ layer: 'numbers', check: 'figures_trace', action: 'passed', detail: 'All figures traced' }] });
    mount();
    await open();
    const checks = screen.getByRole('list', { name: /checks/i });
    expect(within(checks).getByText(/numbers/)).toBeInTheDocument();
    expect(within(checks).getByText(/All figures traced/)).toBeInTheDocument();
  });

  it('still says nothing is recorded when there is nothing at all', async () => {
    hooks.trail = data({});
    mount();
    await open();
    expect(screen.getByText(/no agent work is recorded/i)).toBeInTheDocument();
  });
});

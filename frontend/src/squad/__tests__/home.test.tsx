import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import type { Briefing, BriefingItem } from '../api/types';
import { SquadHome } from '../home/SquadHome';

const mockBriefing = vi.hoisted(() => ({ data: undefined as unknown, isPending: false, error: null as unknown, refetch: vi.fn() }));
vi.mock('../api/hooks', () => ({ useBriefing: () => mockBriefing }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));

const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: [] };
const item = (over: Partial<BriefingItem>): BriefingItem => ({
  key: 'k', kind: 'review', borrower_id: 'b1', borrower_code: 'QFL', borrower_name: 'Quillfeather Labs, Inc.', title: 'Confirm revenue',
  state: 'waiting for you', severity: 'medium', needs_you: true, work_item_id: 'w1', ...over,
});
const briefing = (items: BriefingItem[], overnight: Briefing['overnight'] = []): Briefing => ({
  as_of: '2026-11-20', needs_you: items.filter((i) => i.needs_you).length, items, overnight, open_clients: [], approvals: { offered: false, waiting: 0 }, oversight: { offered: false },
});

function mount(b: Briefing) {
  mockBriefing.data = b;
  const root = createRootRoute({ component: SquadHome });
  const client = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([client]), history: createMemoryHistory({ initialEntries: ['/'] }) });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => true, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
        <RouterProvider router={router} />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe('SquadHome', () => {
  it('scopes the ember dot to needs-you rows and makes the count a heading', async () => {
    mount(briefing([
      item({ key: 'a', severity: 'high' }),
      item({ key: 'b', work_item_id: 'w2', severity: 'high', kind: 'decided', needs_you: false, state: 'reviewed by Priya Raman', title: 'Done thing' }),
    ]));
    expect(await screen.findByRole('heading', { name: '1 needs you' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /confirm revenue/i })).toHaveClass('sq-row-needs');
    expect(screen.getByRole('link', { name: /done thing/i })).not.toHaveClass('sq-row-needs');
  });

  it('offers Try again on error, which refetches', async () => {
    mockBriefing.data = undefined;
    mockBriefing.error = new Error('x');
    const root = createRootRoute({ component: SquadHome });
    const router = createRouter({ routeTree: root.addChildren([]), history: createMemoryHistory({ initialEntries: ['/'] }) });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => true, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
          <RouterProvider router={router} />
        </AuthContext.Provider>
      </QueryClientProvider>,
    );
    (await screen.findByRole('button', { name: 'Try again' })).click();
    expect(mockBriefing.refetch).toHaveBeenCalled();
    mockBriefing.error = null;
  });

  it('says plainly that nothing needs her, and does not paint zero as an alarm', async () => {
    mount(briefing([]));
    expect(await screen.findByText('Nothing needs you.')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: /needs you/i })).not.toBeInTheDocument();
  });

  it('counts exactly the needs-you items it lists', async () => {
    mount(briefing([
      item({ key: 'a', work_item_id: 'w1' }),
      item({ key: 'b', work_item_id: 'w2', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.', kind: 'question', state: 'Squad asks' }),
      item({ key: 'c', work_item_id: 'w3', kind: 'decided', state: 'reviewed by Priya Raman', needs_you: false }),
    ]));
    expect(await screen.findByText('2 need you')).toBeInTheDocument();
    const list = screen.getByRole('list', { name: /needs you/i });
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('reviewed by Priya Raman')).toBeInTheDocument();
  });

  it('opens the client thread at the case, not the first screen of someone else', async () => {
    mount(briefing([item({ work_item_id: 'w9', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.' })]));
    const link = await screen.findByRole('link', { name: /zephyr zinc works.*confirm revenue/i });
    expect(link).toHaveAttribute('href', '/clients/ZZZ?case=w9');
  });

  it('opens an item without a case (a signal) at the client thread alone', async () => {
    mount(briefing([item({ kind: 'signal', work_item_id: null, title: 'A signal needs a look' })]));
    expect(await screen.findByRole('link', { name: /signal/i })).toHaveAttribute('href', '/clients/QFL');
  });

  it('lists signals under Watching, grouped by client, and never counts them', async () => {
    mount(briefing([
      item({ key: 'a', needs_you: true }),
      item({ key: 's1', kind: 'signal', needs_you: false, state: 'watching', title: 'Signals: runway falling, burn rising', work_item_id: null }),
      item({ key: 'f1', kind: 'funding', needs_you: false, state: 'expected', title: 'Expected equity round closes 30 November', work_item_id: null }),
      item({ key: 's2', kind: 'signal', needs_you: false, state: 'watching', title: 'Signal: revenue below plan', work_item_id: null, borrower_id: 'b2', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.' }),
    ]));
    expect(await screen.findByText('1 needs you')).toBeInTheDocument();
    const watching = screen.getByRole('region', { name: 'Watching' });
    const groups = within(watching).getAllByRole('group');
    expect(groups.map((g) => within(g).getAllByText(/Inc\./)[0]!.textContent)).toEqual(['Quillfeather Labs, Inc.', 'Zephyr Zinc Works, Inc.']);
    expect(within(groups[0]!).getByText(/runway falling, burn rising/)).toBeInTheDocument();
  });

  it('shows a one-row group\u2019s state in its summary, and repeats no client name inside an expanded group', async () => {
    mount(briefing([
      item({ key: 's2', kind: 'signal', needs_you: false, state: 'watching \u00b7 October 2026', title: 'Signal: Revenue below plan', work_item_id: null, borrower_id: 'b2', borrower_code: 'ZZZ', borrower_name: 'Zephyr Zinc Works, Inc.' }),
      item({ key: 'o1', kind: 'overdue_report', needs_you: false, state: '5 days overdue', title: 'MRR report for October 2026 is overdue', work_item_id: null }),
      item({ key: 'f1', kind: 'funding', needs_you: false, state: 'expected', title: 'Expected equity round closes 30 November', work_item_id: null }),
    ]));
    const watching = await screen.findByRole('region', { name: 'Watching' });
    const single = within(watching).getByRole('group', { name: 'Zephyr Zinc Works, Inc.' });
    expect(within(single.querySelector('summary')!).getByText(/watching \u00b7 October 2026/)).toBeInTheDocument();
    const several = within(watching).getByRole('group', { name: 'Quillfeather Labs, Inc.' });
    expect(within(several).getAllByText(/Quillfeather Labs, Inc\./)).toHaveLength(1); // the summary only, not each row
    expect(within(several).getByText('5 days overdue')).toBeInTheDocument();
  });

  it('lists what agents did overnight with the client named', async () => {
    mount(briefing([], [{ agent_name: 'spreading', text: 'Read the October package.', borrower_id: 'b1', borrower_code: 'QFL', borrower_name: 'Quillfeather Labs, Inc.', finished_at: '2026-11-20T02:00:00Z' }]));
    await userEvent.click(await screen.findByText(/what squad did overnight/i));
    expect(await screen.findByText('Read the October package.')).toBeInTheDocument();
    expect(screen.getByText(/spreading agent/i)).toBeInTheDocument();
  });
});

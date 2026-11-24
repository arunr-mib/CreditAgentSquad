import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AuthContext } from '@/auth/context';
import { ToastProvider, TooltipProvider } from '@/design';
import { ReviewRoom } from '../review/ReviewRoom';

const MEETING = { id: 'm1', title: 'Quarterly portfolio review', meeting_date: '2026-11-25', period_end: '2026-09-30', phase: 'before', chair_id: null, notes: '', sheets: [{ id: 's1', borrower_name: 'Larkspur Environmental Services', status: 'draft' }] };
const SHEET = { id: 's1', borrower_id: 'b1', borrower_name: 'Larkspur Environmental Services', cycle_id: 'c1', meeting_id: 'm1', status: 'draft', period_end: '2026-09-30', approved_by: null, approved_by_name: null, content: { metrics: [], covenants: [], signals: [] }, commentary: [] };
const { q, m } = vi.hoisted(() => ({
  q: (data: unknown) => ({ data, isPending: false, error: null, refetch: () => {} }),
  m: () => ({ mutate: () => {}, mutateAsync: async () => {}, isPending: false, error: null, reset: () => {} }),
}));
vi.mock('@/api/hooks', () => ({
  useMeetings: () => q([MEETING]),
  useReviewSheets: () => q([SHEET]),
  useReviewSheet: (id?: string) => q(id ? SHEET : undefined),
  useCycles: () => q([{ id: 'c1', period_end: '2026-09-30' }]),
  useFactsById: () => q({}),
  useWorkItems: () => q([
    { id: 'w-other', item_type: 'review.commentary_approval', title: 'Commentary for another period', question: 'Another sheet’s question.', status: 'open', review_sheet_id: 's2' },
    { id: 'w-approve', item_type: 'review.commentary_approval', title: 'Commentary awaiting approval', question: 'Two sections were withheld: outlook, liquidity.', status: 'open', review_sheet_id: 's1' },
  ]),
  useBorrowers: () => q([{ id: 'b1', code: 'LES', name: 'Larkspur Environmental Services' }]),
  useActions: () => q([]),
  useUsers: () => q([]),
  useCreateMeeting: m, useSetMeetingPhase: m, useCreateAction: m, useSetActionStatus: m,
}));
vi.mock('../case/CasePanel', () => ({ CasePanel: ({ workItemId }: { workItemId: string }) => <p>case {workItemId}</p> }));
vi.mock('@/squad/clientfile/review/Commentary', () => ({ Commentary: () => <p>commentary</p> }));
vi.mock('../presence/Presence', () => ({ usePresence: () => ({ say: vi.fn() }) }));

function mount(permissions: string[], path = '/review-room?sheet=s1') {
  const root = createRootRoute();
  const room = createRoute({ getParentRoute: () => root, path: '/review-room', component: ReviewRoom, validateSearch: (s: Record<string, unknown>) => ({ meeting: typeof s.meeting === 'string' ? s.meeting : undefined, sheet: typeof s.sheet === 'string' ? s.sheet : undefined }) });
  const file = createRoute({ getParentRoute: () => root, path: '/clients/$code/file', component: () => null });
  const router = createRouter({ routeTree: root.addChildren([room, file]), history: createMemoryHistory({ initialEntries: [path] }) });
  const user = { id: 'u1', email: 'd@x', name: 'Dana Whitfield', title: '', role: 'portfolio_manager', permissions };
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthContext.Provider value={{ user, status: 'signed-in', can: (p: string) => permissions.includes(p), signIn: async () => user, signOut: async () => {}, retry: () => {} }}>
        <TooltipProvider><ToastProvider><RouterProvider router={router} /></ToastProvider></TooltipProvider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe('ReviewRoom in Squad', () => {
  it('keeps the meeting with its phases, its sheets and the commentary approval as a Squad case', async () => {
    mount(['view', 'manage_actions', 'approve_commentary']);
    expect(await screen.findByText('Quarterly portfolio review')).toBeInTheDocument();
    for (const phase of ['Before', 'During', 'After']) expect(screen.getAllByText(phase).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Move to during' })).toBeInTheDocument();
    const approval = screen.getByRole('complementary', { name: 'Approval of this commentary' });
    expect(within(approval).getByText('Commentary awaiting approval')).toBeInTheDocument();
    expect(within(approval).getByText('case w-approve')).toBeInTheDocument();
    // the item's own question, and only this sheet's approval, not the client's first open one
    expect(within(approval).getByText('Two sections were withheld: outlook, liquidity.')).toBeInTheDocument();
    expect(screen.queryByText('case w-other')).not.toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Client' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open the client file' })).toHaveAttribute('href', '/clients/LES/file');
  });

  it('offers no meeting control to a person whose served permissions lack it, and names no role', async () => {
    const { container } = mount(['view']);
    expect(await screen.findByText('Quarterly portfolio review')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /move to/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create the meeting' })).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/portfolio manager|credit officer|credit analyst/i);
  });
});

describe('the words after a meeting is created', () => {
  it('say how many sheets were attached, and say none when none were', async () => {
    const { meetingCreatedWords } = await import('../review/ReviewRoom');
    expect(meetingCreatedWords(0)).toBe('Meeting created · no review sheet was waiting for this period, so none is attached · recorded');
    expect(meetingCreatedWords(1)).toBe('Meeting created · 1 review sheet for the period attached · recorded');
    expect(meetingCreatedWords(3)).toBe('Meeting created · 3 review sheets for the period attached · recorded');
    expect(meetingCreatedWords(undefined)).toBe('Meeting created · recorded'); // an older server sends no count
  });
});

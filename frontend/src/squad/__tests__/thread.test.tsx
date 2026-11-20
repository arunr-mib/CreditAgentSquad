// frontend/src/squad/__tests__/thread.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Thread, ThreadMessage } from '../api/types';
import { ClientThread } from '../thread/ClientThread';

const state = vi.hoisted(() => ({ thread: undefined as unknown, notFound: false, open: vi.fn(), trail: undefined as unknown }));
vi.mock('@/api/hooks', () => ({
  useBorrowerByCode: (code: string) => ({ borrower: state.notFound ? undefined : { id: 'b1', code, name: 'Quillfeather Labs, Inc.' }, notFound: state.notFound, isPending: false }),
}));
vi.mock('../api/hooks', () => ({
  useThread: () => ({ data: state.thread, isPending: false, error: null }),
  useTrail: () => ({ data: state.trail, isPending: false }),
}));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));
vi.mock('../thread/Composer', () => ({ Composer: () => null }));
vi.mock('../thread/AskMessage', () => ({ AskMessage: () => null }));
vi.mock('../thread/QaMessage', () => ({ QaMessage: () => null }));
vi.mock('../thread/DraftMessage', () => ({ DraftMessage: () => null }));

const base = { ts: '2026-11-20T08:00:00Z' };
const messages: ThreadMessage[] = [
  { ...base, id: 'doc:1', type: 'document', document_id: 'd1', title: 'October compliance certificate', doc_type: 'compliance_certificate', pages: 2, period_end: '2026-10-31' },
  { ...base, id: 'held:1', type: 'held', document_id: 'd2', title: 'Unknown scan', reason: "Not this client's file" },
  { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'covenant.breach', title: 'Cash below minimum', question: 'Is this a breach?', severity: 'critical', status: 'open', allowed_decisions: [] },
  { ...base, id: 'case:2', type: 'case', work_item_id: 'w2', item_type: 'funding_slipped', title: 'Funding slipped', question: 'Review the outlook?', severity: 'high', status: 'open', allowed_decisions: [] },
  { ...base, id: 'decision:1', type: 'decision', work_item_id: 'w2', decision: 'reviewed', reason: 'Close is signed.', by: 'Priya Raman', by_id: 'u1' },
  { ...base, id: 'handoff:1', type: 'handoff', work_item_id: 'w1', assigned_to: 'Helen Strand', assigned_to_id: 'u2', by: 'Priya Raman' },
  { ...base, id: 'run:1', type: 'report', agent_name: 'spreading', task: 'read_statements', text: 'Read the October package.', run_id: 'r1' },
];
const thread = (m: ThreadMessage[]): Thread => ({ borrower: { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', template_id: 'vc-1' }, head_seq: 9, messages: m });

function mount(search = '') {
  const root = createRootRoute();
  const route = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: ClientThread, validateSearch: (s: Record<string, unknown>) => ({ case: typeof s.case === 'string' ? s.case : undefined }) });
  const router = createRouter({ routeTree: root.addChildren([route]), history: createMemoryHistory({ initialEntries: [`/clients/QFL${search}`] }) });
  return render(<QueryClientProvider client={new QueryClient()}><RouterProvider router={router} /></QueryClientProvider>);
}

beforeEach(() => {
  state.notFound = false;
  state.thread = thread(messages);
  state.trail = undefined;
  state.open.mockClear();
});

describe('ClientThread', () => {
  it('names the client and offers the client file', async () => {
    mount();
    expect(await screen.findByRole('heading', { name: 'Quillfeather Labs, Inc.' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open in client file/i })).toHaveAttribute('href', '/borrowers/QFL');
  });

  it('renders each message type in words a person can act on', async () => {
    mount();
    expect(await screen.findByText('October compliance certificate')).toBeInTheDocument();
    expect(screen.getByText(/Not this client's file/)).toBeInTheDocument();
    expect(screen.getByText('Cash below minimum')).toBeInTheDocument();
    expect(screen.getByText(/Priya Raman handed this to Helen Strand/)).toBeInTheDocument();
    expect(screen.getByText(/Priya Raman: reviewed/)).toBeInTheDocument();
    expect(screen.getByText('Close is signed.')).toBeInTheDocument();
    expect(screen.getByText('Read the October package.')).toBeInTheDocument();
  });

  it('opens a document in the evidence drawer from the thread', async () => {
    mount();
    await userEvent.click(await screen.findByRole('button', { name: /open october compliance certificate/i }));
    expect(state.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1', page: 1 }));
  });

  it('focuses the case named in the address and no other', async () => {
    mount('?case=w1');
    const focused = await screen.findByText('Cash below minimum');
    expect(focused.closest('[data-work-item]')).toHaveAttribute('data-focused', 'true');
    expect(screen.getByText('Funding slipped').closest('[data-work-item]')).not.toHaveAttribute('data-focused');
  });

  it('shows the whole thread, without an error, for a case id that is not there', async () => {
    mount('?case=does-not-exist');
    expect(await screen.findByText('Cash below minimum')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(document.querySelector('[data-focused]')).toBeNull();
  });

  it('is honest about an empty thread', async () => {
    state.thread = thread([]);
    mount();
    expect(await screen.findByText(/nothing here yet/i)).toBeInTheDocument();
  });

  it('says so, and offers the way home, for a client that does not exist', async () => {
    state.notFound = true;
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent(/no client with that code/i);
    expect(screen.getByRole('link', { name: /back to squad/i })).toHaveAttribute('href', '/');
  });

  it('loads "How I got here" only when it is opened', async () => {
    state.trail = { work_item_id: 'w1', steps: [{ n: 1, who: 'Spreading agent', role_line: 'reads figures from documents', text: 'Ran read statements.', check: 'completed', run_id: 'r1' }, { n: 2, who: 'Code', role_line: 'calculation, no AI', text: 'Applied cov.min_unrestricted_cash.', check: 'exact arithmetic', run_id: null }], calculation: null, checks: [] };
    mount();
    const card = (await screen.findByText('Cash below minimum')).closest('[data-work-item]') as HTMLElement;
    expect(within(card).queryByText('Spreading agent')).not.toBeInTheDocument();
    await userEvent.click(within(card).getByRole('button', { name: /how i got here/i }));
    expect(within(card).getByText('Spreading agent')).toBeInTheDocument();
    expect(within(card).getByText(/calculation, no AI/)).toBeInTheDocument();
  });
});

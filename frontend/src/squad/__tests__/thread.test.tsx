// frontend/src/squad/__tests__/thread.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryHistory, createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Thread, ThreadMessage } from '../api/types';
import { ClientThread } from '../thread/ClientThread';

const state = vi.hoisted(() => ({ thread: undefined as unknown, notFound: false, borrowersError: false, refetchBorrowers: vi.fn(), open: vi.fn(), trail: undefined as unknown, trailError: false, subs: new Set<() => void>(), refetch: vi.fn() }));
vi.mock('@/api/hooks', () => ({
  useBorrowerByCode: (code: string) => ({ borrower: state.notFound || state.borrowersError ? undefined : { id: 'b1', code, name: 'Quillfeather Labs, Inc.' }, notFound: state.notFound, isPending: false, error: state.borrowersError ? new Error('down') : null, refetch: state.refetchBorrowers }),
}));
vi.mock('../api/hooks', async () => {
  const { useEffect, useState } = await import('react');
  return {
  useThread: () => {
    const [, bump] = useState(0);
    useEffect(() => {
      const f = () => bump((n) => n + 1);
      state.subs.add(f);
      return () => void state.subs.delete(f);
    }, []);
    return { data: state.thread, isPending: false, error: null };
  },
  useTrail: () => ({ data: state.trail, isPending: false, error: state.trailError ? new Error('x') : null, refetch: state.refetch }),
  };
});
vi.mock('../case/CasePanel', () => ({ CasePanel: ({ workItemId }: { workItemId: string }) => <p>case panel {workItemId}</p> }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));
vi.mock('../thread/Composer', () => ({ Composer: () => null }));
vi.mock('../thread/AskMessage', () => ({ AskMessage: () => null }));
vi.mock('../thread/QaMessage', () => ({ QaMessage: () => null }));
vi.mock('../thread/DraftMessage', () => ({ DraftMessage: () => null }));

const base = { ts: '2026-11-20T08:00:00Z' };
const messages: ThreadMessage[] = [
  { ...base, id: 'doc:1', type: 'document', document_id: 'd1', title: 'October compliance certificate', doc_type: 'compliance_certificate', doc_type_words: 'Compliance certificate', pages: 2, period_end: '2026-10-31' },
  { ...base, id: 'held:1', type: 'held', document_id: 'd2', title: 'Unknown scan', reason: "Not this client's file" },
  { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'covenant.breach', title: 'Cash below minimum', question: 'Is this a breach?', severity: 'critical', status: 'open', allowed_decisions: [], needs_you: false, state_words: 'With the credit officer' },
  { ...base, id: 'case:2', type: 'case', work_item_id: 'w2', item_type: 'funding_slipped', title: 'Funding slipped', question: 'Review the outlook?', severity: 'high', status: 'open', allowed_decisions: [], needs_you: false, state_words: 'Open' },
  { ...base, id: 'decision:1', type: 'decision', work_item_id: 'w2', decision: 'reviewed', reason: 'Close is signed.', by: 'Priya Raman', by_id: 'u1' },
  { ...base, id: 'handoff:1', type: 'handoff', work_item_id: 'w1', assigned_to: 'Helen Strand', assigned_to_id: 'u2', by: 'Priya Raman' },
  { ...base, id: 'run:1', type: 'report', agent_name: 'spreading', agent_label: 'Statement reader agent', task: 'read_statements', text: 'Read the October package.', run_id: 'r1' },
];
const thread = (m: ThreadMessage[]): Thread => ({ borrower: { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.', template_id: 'vc-1' }, head_seq: 9, opening_id: null, messages: m });

function mount(search = '') {
  const root = createRootRoute();
  const route = createRoute({ getParentRoute: () => root, path: '/clients/$code', component: ClientThread, validateSearch: (s: Record<string, unknown>) => ({ case: typeof s.case === 'string' ? s.case : undefined }) });
  const router = createRouter({ routeTree: root.addChildren([route]), history: createMemoryHistory({ initialEntries: [`/clients/QFL${search}`] }) });
  const client = new QueryClient();
  const ui = () => <QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>;
  const result = render(ui());
  return { ...result, update: () => act(() => state.subs.forEach((f) => f())) };
}

beforeEach(() => {
  state.notFound = false;
  state.borrowersError = false;
  state.refetchBorrowers.mockClear();
  state.thread = thread(messages);
  state.trail = undefined;
  state.open.mockClear();
});

describe('ClientThread', () => {
  it('names the client and offers the client file', async () => {
    mount();
    expect(await screen.findByRole('heading', { name: 'Quillfeather Labs, Inc.' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open in client file' })).toHaveAttribute('href', '/clients/QFL/file');
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
    expect(screen.getByText('Statement reader agent')).toBeInTheDocument();
  });

  it('says in Squad\u2019s own sentence what Squad attached, and still opens the document', async () => {
    state.thread = thread([...messages, { ...base, id: 'attached:1', type: 'attached', work_item_id: 'w1', document_id: 'd9', title: 'Account statement September 2026', note: 'Attached the Bank statement for September 2026 that Helen Strand asked for.', by: 'Squad', by_kind: 'squad' }]);
    mount();
    expect(await screen.findByText(/^Attached the Bank statement for September 2026 that Helen Strand asked for\./)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Open Account statement September 2026' }));
    expect(state.open).toHaveBeenCalledWith(expect.objectContaining({ documentId: 'd9' }));
  });

  it('does not take a person called Squad for Squad: the kind decides', async () => {
    state.thread = thread([...messages, { ...base, id: 'attached:2', type: 'attached', work_item_id: 'w1', document_id: 'd8', title: 'Statement X', note: 'As asked.', by: 'Squad', by_kind: 'user' }]);
    mount();
    expect(await screen.findByText(/Squad attached/)).toBeInTheDocument();
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

  it('says the client list could not be loaded, with Try again, instead of waiting for ever', async () => {
    state.borrowersError = true;
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded/i);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(state.refetchBorrowers).toHaveBeenCalled();
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

  it('says where each case stands in words, from the thread', async () => {
    state.thread = thread([
      { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'Mine', question: 'q', severity: 'critical', status: 'open', allowed_decisions: ['breach'], needs_you: true, state_words: '' },
      { ...base, id: 'case:2', type: 'case', work_item_id: 'w2', item_type: 'x', title: 'Handed', question: 'q', severity: 'high', status: 'open', allowed_decisions: [], needs_you: false, state_words: 'Open' },
      { ...base, id: 'handoff:2', type: 'handoff', work_item_id: 'w2', assigned_to: 'Helen Strand', assigned_to_id: 'u2', by: 'Priya Raman' },
      { ...base, id: 'case:3', type: 'case', work_item_id: 'w3', item_type: 'x', title: 'Done', question: 'q', severity: 'medium', status: 'closed', allowed_decisions: [], needs_you: false, state_words: '' },
      { ...base, id: 'decision:3', type: 'decision', work_item_id: 'w3', decision: 'not_a_breach', reason: '', by: 'Priya Raman', by_id: 'u1' },
    ]);
    mount();
    const card = async (t: string) => (await screen.findByText(t)).closest('[data-work-item]') as HTMLElement;
    expect(within(await card('Mine')).getByText('Needs your call')).toBeInTheDocument();
    expect(within(await card('Mine')).getByText('Critical')).toBeInTheDocument();
    expect(within(await card('Handed')).getByText('With Helen Strand')).toBeInTheDocument();
    expect(within(await card('Handed')).getByText('High')).toBeInTheDocument();
    expect(within(await card('Done')).getByText('not a breach by Priya Raman')).toBeInTheDocument();
    expect(screen.queryByText('open')).not.toBeInTheDocument();
    expect(screen.queryByText('closed')).not.toBeInTheDocument();
  });

  it('opens the case inline on the thread a person can act on, through the address', async () => {
    state.thread = thread([{ ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'Mine', question: 'q', severity: 'critical', status: 'open', allowed_decisions: ['breach'], needs_you: true, state_words: '' }]);
    mount();
    const mine = (await screen.findByText('Mine')).closest('[data-work-item]') as HTMLElement;
    expect(within(mine).getByRole('link', { name: 'Open the case: Mine' })).toHaveAttribute('href', '/clients/QFL?case=w1');
    mount('?case=w1');
    expect(await screen.findByText('case panel w1')).toBeInTheDocument();
  });

  it('says a returned case is back with the person it came back to', async () => {
    state.thread = thread([
      { ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'Back', question: 'q', severity: 'high', status: 'open', allowed_decisions: [], needs_you: true, state_words: 'With Priya Raman' },
      { ...base, id: 'handoff:1', type: 'handoff', work_item_id: 'w1', assigned_to: 'Helen Strand', assigned_to_id: 'u2', by: 'Priya Raman', view: 'Recommend reserving rights.' },
      { ...base, id: 'returned:2', type: 'returned', work_item_id: 'w1', reason: 'Attach the term sheet.', by: 'Helen Strand', to: 'Priya Raman' },
    ]);
    mount();
    const card = (await screen.findByText('Back')).closest('[data-work-item]') as HTMLElement;
    expect(within(card).getByText('Returned to you')).toBeInTheDocument();
    expect(screen.getByText(/Helen Strand returned this to Priya Raman/)).toBeInTheDocument();
    expect(screen.getByText('Attach the term sheet.')).toBeInTheDocument();
    expect(screen.getByText('Recommend reserving rights.')).toBeInTheDocument();
  });

  it('reads a case the viewer cannot act on in the backend words, not as their call', async () => {
    state.thread = thread([{ ...base, id: 'case:1', type: 'case', work_item_id: 'w1', item_type: 'x', title: 'Not mine', question: 'q', severity: 'critical', status: 'open', allowed_decisions: ['breach'], needs_you: false, state_words: 'With the credit officer' }]);
    mount();
    const card = (await screen.findByText('Not mine')).closest('[data-work-item]') as HTMLElement;
    expect(within(card).getByText('With the credit officer')).toBeInTheDocument();
    expect(screen.queryByText('Needs your call')).not.toBeInTheDocument();
  });

  it('gives each case its own client-file link with a distinct name', async () => {
    mount();
    const link = await screen.findByRole('link', { name: 'Open in client file: Cash below minimum' });
    expect(link).toHaveAttribute('href', '/clients/QFL/file');
    expect(screen.getByRole('link', { name: 'Open in client file: Funding slipped' })).toBeInTheDocument();
  });

  it('scrolls to the focused case once, not on every update', async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    state.thread = thread([messages[0]!]);
    const view = mount('?case=w1');
    await screen.findByText('October compliance certificate');
    expect(scroll).not.toHaveBeenCalled();
    state.thread = thread(messages);
    view.update();
    await screen.findByText('Cash below minimum');
    expect(scroll).toHaveBeenCalledTimes(1);
    state.thread = thread([...messages, { ...base, id: 'held:9', type: 'held', document_id: 'd9', title: 'Another scan', reason: 'x' }]);
    view.update();
    await screen.findByText('Another scan');
    expect(scroll).toHaveBeenCalledTimes(1);
  });

  it('offers Try again when the trail request fails', async () => {
    state.trailError = true;
    mount();
    const card = (await screen.findByText('Cash below minimum')).closest('[data-work-item]') as HTMLElement;
    await userEvent.click(within(card).getByRole('button', { name: /how i got here/i }));
    expect(within(card).getByRole('alert')).toHaveTextContent(/could not be loaded/i);
    await userEvent.click(within(card).getByRole('button', { name: /try again/i }));
    expect(state.refetch).toHaveBeenCalled();
    state.trailError = false;
  });

  it('shows a time on messages and an error with Try again for a failed trail', async () => {
    state.trail = undefined;
    mount();
    const card = (await screen.findByText('Cash below minimum')).closest('[data-work-item]') as HTMLElement;
    expect(card.querySelector('time')).not.toBeNull();
    expect(within(card).getByRole('button', { name: /how i got here/i })).toHaveAttribute('aria-controls', 'trail-w1');
  });

  describe('opening position', () => {
    const original = Element.prototype.scrollIntoView;
    afterEach(() => { Element.prototype.scrollIntoView = original; });
    const arrivals: ThreadMessage = { ...base, id: 'arrivals:2026-10', type: 'arrivals', title: '2 documents arrived for October 2026', period_end: '2026-10-31', documents: [
      { ...base, id: 'doc:1', type: 'document', document_id: 'd1', title: 'MRR report, October 2026', doc_type: 'mrr_report', doc_type_words: 'MRR report', pages: 1, period_end: '2026-10-31' },
      { ...base, id: 'doc:2', type: 'document', document_id: 'd2', title: 'Account statement, October 2026', doc_type: 'bank_statement', doc_type_words: 'Bank statement', pages: 1, period_end: '2026-10-31' },
    ] };
    const older: ThreadMessage = { ...base, id: 'doc:0', type: 'document', document_id: 'd0', title: 'MRR report, September 2026', doc_type: 'mrr_report', doc_type_words: 'MRR report', pages: 1, period_end: '2026-09-30' };
    const later: ThreadMessage = { ...base, id: 'run:9', type: 'report', agent_name: 'spreading', agent_label: 'Spreading agent', task: 't', text: 'Read it.', run_id: 'r9' };
    const newCase: ThreadMessage = { ...base, id: 'case:9', type: 'case', work_item_id: 'w9', item_type: 'x', title: 'New line', question: 'q', severity: 'medium', status: 'open', allowed_decisions: [], needs_you: true, state_words: '' };
    const record = () => {
      const scrolled: string[] = [];
      Element.prototype.scrollIntoView = function (this: Element) { scrolled.push(this.closest('[data-message-id]')?.getAttribute('data-message-id') ?? ''); };
      return scrolled;
    };

    it('opens at the message the server names, not the last one, and groups arrivals', async () => {
      const scrolled = record();
      state.thread = { ...thread([older, arrivals, later]), opening_id: 'arrivals:2026-10' };
      mount();
      expect(await screen.findByText('2 documents arrived for October 2026')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Open MRR report, October 2026' })).toBeInTheDocument();
      expect(scrolled).toEqual(['arrivals:2026-10']);
    });

    it('lets ?case= win over the opening position', async () => {
      const scrolled = record();
      state.thread = { ...thread([older, arrivals, newCase, later]), opening_id: 'arrivals:2026-10' };
      mount('?case=w9');
      await screen.findByText('2 documents arrived for October 2026');
      expect(scrolled).toEqual(['case:9']);
    });
  });
});

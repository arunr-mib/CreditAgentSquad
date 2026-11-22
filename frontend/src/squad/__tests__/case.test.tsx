import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import type { CaseView } from '../api/types';
import { CasePanel, refusal } from '../case/CasePanel';

const state = vi.hoisted(() => ({ view: undefined as unknown, detail: undefined as unknown, decide: vi.fn(), route: vi.fn(), ret: vi.fn(), attach: vi.fn(), say: vi.fn(), open: vi.fn(), openCase: vi.fn(), error: null as unknown }));
const write = (fn: (i: unknown) => void) => ({ mutateAsync: async (i: unknown) => { fn(i); if (state.error) throw state.error; }, isPending: false, error: state.error, reset: () => {} });
vi.mock('../api/hooks', () => ({
  useCase: () => ({ data: state.view, isPending: false, error: null, refetch: vi.fn() }),
  useDecideCase: () => write(state.decide),
  useRouteCase: () => write(state.route),
  useReturnCase: () => write(state.ret),
  useAttachEvidence: () => write(state.attach),
}));
vi.mock('@/api/hooks', () => ({ useWorkItem: () => ({ data: state.detail }) }));
vi.mock('../presence/Presence', () => ({ usePresence: () => ({ say: state.say }) }));
// The real evidence rows, recommendation and related items are tested where they live (src/squad/case/parts.test.tsx);
// here only that the case panel shows them, in order.
vi.mock('@/squad/case/parts', () => ({
  Evidence: () => <p>evidence rows</p>,
  Recommendation: () => <p>agent recommendation</p>,
  RelatedItems: ({ items, onOpen }: { items: Array<{ id: string; title: string }>; onOpen: (id: string) => void }) =>
    items.length ? <button type="button" onClick={() => onOpen(items[0]!.id)}>{items[0]!.title}</button> : null,
}));
const reply = vi.hoisted(() => ({ next: { status: 'answered', answer: 'Because X.', answer_with_references: 'Because X.', fact_ids: [], citations: [] } as Record<string, unknown> }));
vi.mock('../thread/Composer', () => ({ Composer: (p: { borrowerId: string; workItemId?: string; onReply?: (r: never) => void }) => <button type="button" onClick={() => p.onReply?.(reply.next as never)}>case composer {p.borrowerId} {p.workItemId}</button> }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p>{text}</p> }));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: state.open, close: () => {}, current: null }) }));
vi.mock('@/squad/case/KeyFigures', () => ({ KeyFigures: () => null }));
vi.mock('@/squad/case/HeldFigures', () => ({ HeldFigures: () => <p>held figures</p> }));

const base: CaseView = {
  work_item_id: 'w1', borrower: { id: 'b1', code: 'QFL', name: 'Quillfeather Labs, Inc.' }, item_type: 'covenant.breach',
  title: 'Cash below minimum', question: 'How should the bank respond?', severity: 'high', status: 'open', due_date: null,
  decision: null, decision_words: null, decision_reason: '', decided_by: null, requires_second_person: false, with: null,
  state_words: 'With the credit officer', needs_you: false, view: null, history: [], attached: [], candidates: [],
  decisions: [{ id: 'reservation_of_rights', label: 'Reserve rights', hint: 'Send a reservation of rights letter.', needs_reason: true, permitted: false }, { id: 'not_a_breach', label: 'Not a breach', hint: '', needs_reason: true, permitted: false }],
  route_to: [{ id: 'u2', name: 'Helen Strand', title: 'Senior Credit Officer' }], may_route: true, may_return: false, may_attach: true,
};

beforeEach(() => {
  state.view = base;
  state.detail = undefined;
  state.error = null;
  [state.decide, state.route, state.ret, state.attach, state.say, state.openCase].forEach((f) => f.mockClear());
});

const panel = () => render(<CasePanel workItemId="w1" onOpenCase={state.openCase} />);

describe('CasePanel', () => {
  it('lets anyone ask Squad about this open case: the client and the case travel together', () => {
    panel();
    expect(screen.getByText('case composer b1 w1')).toBeInTheDocument();
  });

  it('shows the answer to a question about the case right there, and a refusal as a refusal', async () => {
    panel();
    await userEvent.click(screen.getByRole('button', { name: 'case composer b1 w1' }));
    expect(screen.getByText('Because X.')).toBeInTheDocument();
    reply.next = { status: 'refused', answer: 'I cannot ground that.', answer_with_references: '', fact_ids: [], citations: [] };
    await userEvent.click(screen.getByRole('button', { name: 'case composer b1 w1' }));
    expect(screen.getByRole('group', { name: 'Squad could not answer' })).toHaveTextContent('I cannot ground that.');
  });

  it('shows a case that is with someone else as theirs, with no way to send or decide it', () => {
    state.view = { ...base, may_route: false, with: 'Helen Strand', state_words: 'With Helen Strand', route_to: [] };
    panel();
    expect(screen.getByText(/With Helen Strand\. This case is not yours to decide/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Send/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Record decision' })).not.toBeInTheDocument();
  });

  it('lets the analyst route with her view, and only once the view is written', async () => {
    panel();
    const send = screen.getByRole('button', { name: 'Send to Helen Strand' });
    expect(send).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/your view/i), 'Cash fell under the floor.');
    await userEvent.click(send);
    expect(state.route).toHaveBeenCalledWith({ to: 'u2', view: 'Cash fell under the floor.' });
    expect(state.say).toHaveBeenCalledWith('Sent to Helen Strand with your view · recorded');
    expect(screen.queryByRole('button', { name: /record decision/i })).not.toBeInTheDocument();
  });

  it('with several people who may decide, preselects nobody and sends only to the one chosen', async () => {
    state.view = { ...base, route_to: [{ id: 'u3', name: 'Graham Sedgwick', title: 'Credit Officer' }, { id: 'u2', name: 'Helen Strand', title: 'Senior Credit Officer' }] };
    panel();
    await userEvent.type(screen.getByLabelText(/your view/i), 'Cash fell under the floor.');
    const send = screen.getByRole('button', { name: 'Choose who decides' });
    expect(send).toBeDisabled();
    expect(screen.getByLabelText('Send to')).toHaveValue('');
    await userEvent.selectOptions(screen.getByLabelText('Send to'), 'u2');
    await userEvent.click(screen.getByRole('button', { name: 'Send to Helen Strand' }));
    expect(state.route).toHaveBeenCalledWith({ to: 'u2', view: 'Cash fell under the floor.' });
  });

  it('shows the officer the view, a reason box the server says is required, and Return', async () => {
    state.view = { ...base, needs_you: true, may_route: false, may_return: true, may_attach: true, view: { text: 'Recommend reserving rights.', by: 'Priya Raman', at: '2026-11-21T09:00:00Z' },
      decisions: base.decisions.map((d) => ({ ...d, permitted: true })) };
    panel();
    expect(screen.getByText('Recommend reserving rights.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: /reserve rights/i }));
    const record = screen.getByRole('button', { name: 'Record decision' });
    expect(record).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Reason (required)'), 'Pending the close.');
    await userEvent.click(record);
    expect(state.decide).toHaveBeenCalledWith({ decision: 'reservation_of_rights', reason: 'Pending the close.' });
    await userEvent.type(screen.getByLabelText(/what is missing/i), 'Attach the signed term sheet.');
    await userEvent.click(screen.getByRole('button', { name: 'Return to Priya Raman' }));
    expect(state.ret).toHaveBeenCalledWith({ reason: 'Attach the signed term sheet.' });
  });

  it('shows a second-person refusal in the server’s words, never pre-empted', async () => {
    state.view = { ...base, decisions: [{ id: 'not_a_breach', label: 'Not a breach', hint: '', needs_reason: false, permitted: true }], may_route: false };
    state.error = new ApiError(409, 'This approval must come from a different person than the preparer.');
    panel();
    await userEvent.click(screen.getByRole('radio', { name: /not a breach/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Record decision' }));
    const alert = await screen.findByRole('alert');
    expect(within(alert).getByText('Not recorded: a second person must decide this')).toBeInTheDocument();
    expect(within(alert).getByText(/different person than the preparer/)).toBeInTheDocument();
  });

  it('offers an administrator nothing to do', () => {
    state.view = { ...base, may_route: false, may_return: false, may_attach: false, candidates: [] };
    panel();
    // asking Squad is a question, not a credit action: every viewer may; no send, return, attach or decide control
    expect(screen.queryAllByRole('button').filter((b) => !/case composer/.test(b.textContent ?? ''))).toHaveLength(0);
    expect(screen.getByText(/With the credit officer/)).toBeInTheDocument();
  });

  it('attaches a document the analyst picks; it never attaches one by itself', async () => {
    state.view = { ...base, candidates: [{ document_id: 'd9', title: 'Signed term sheet', doc_type: 'term_sheet', pages: 2 }] };
    panel();
    expect(state.attach).not.toHaveBeenCalled();
    await userEvent.click(screen.getByText(/on file you can attach/));
    await userEvent.click(screen.getByRole('button', { name: 'Attach Signed term sheet' }));
    expect(state.attach).toHaveBeenCalledWith({ document_id: 'd9' });
  });

  it('shows the evidence, says when no agent recommendation is attached, and lists related open questions before the decision', async () => {
    state.view = { ...base, needs_you: true, may_route: false, decisions: base.decisions.map((d) => ({ ...d, permitted: true })) };
    state.detail = { id: 'w1', item_type: 'covenant.breach', status: 'open', evidence: {}, recommendation: null, guardrail_notes: [], related_items: [{ id: 'w2', title: 'Second amendment is not approved', status: 'open' }] };
    panel();
    const evidence = screen.getByText('evidence rows');
    const form = screen.getByRole('form', { name: 'Record a decision' });
    expect(evidence.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/No agent recommendation is attached/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Second amendment is not approved' }));
    expect(state.openCase).toHaveBeenCalledWith('w2');
  });

  it('says the decision is theirs only to a person who may take it', () => {
    state.detail = { id: 'w1', item_type: 'covenant.breach', status: 'open', evidence: {}, recommendation: null, guardrail_notes: [], related_items: [] };
    const { unmount } = panel();
    expect(screen.getByText(/No agent recommendation is attached/)).toBeInTheDocument();
    expect(screen.queryByText(/decision is yours/)).not.toBeInTheDocument();
    unmount();
    state.view = { ...base, needs_you: true, may_route: false, decisions: base.decisions.map((d) => ({ ...d, permitted: true })) };
    panel();
    expect(screen.getByText(/decision is yours/)).toBeInTheDocument();
  });

  it('shows the agent’s recommendation when there is one, and each decision’s hint', () => {
    state.view = { ...base, needs_you: true, may_route: false, decisions: base.decisions.map((d) => ({ ...d, permitted: true })) };
    state.detail = { id: 'w1', item_type: 'covenant.breach', status: 'open', evidence: {}, recommendation: { headline: 'Recommends escalate' }, guardrail_notes: [], related_items: [] };
    panel();
    expect(screen.getByText('agent recommendation')).toBeInTheDocument();
    expect(screen.queryByText(/No agent recommendation is attached/)).not.toBeInTheDocument();
    expect(screen.getByText('Send a reservation of rights letter.')).toBeInTheDocument();
  });

  it('names each refusal by what it means', () => {
    expect(refusal(new ApiError(403, 'no')).title).toBe('Not recorded: your role cannot do this');
    expect(refusal(new ApiError(422, 'needs a reason')).text).toBe('needs a reason');
  });
});

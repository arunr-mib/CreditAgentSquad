// frontend/src/squad/__tests__/questions.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { ApiError } from '@/api/client';
import { AuthContext } from '@/auth/context';
import type { ThreadMessage } from '../api/types';
import { PresenceProvider, usePresence } from '../presence/Presence';
import { AskMessage } from '../thread/AskMessage';
import { Composer } from '../thread/Composer';
import { QaMessage } from '../thread/QaMessage';

const calls = vi.hoisted(() => ({ ask: vi.fn(), answer: vi.fn(), open: vi.fn() }));
vi.mock('../api/hooks', () => ({
  useAskCopilot: () => ({ mutateAsync: calls.ask, isPending: false }),
  useAnswer: () => ({ mutateAsync: calls.answer, isPending: false }),
}));
vi.mock('@/source/context', () => ({ useSource: () => ({ open: calls.open, close: () => {}, current: null }) }));
vi.mock('../thread/Trail', () => ({ Trail: () => null }));
vi.mock('@tanstack/react-router', () => ({ Link: ({ to, children, ...rest }: { to: string; children: React.ReactNode }) => <a href={to} {...rest}>{children}</a> }));
vi.mock('@/source/AgentBody', () => ({ AgentBody: ({ text }: { text: string }) => <p data-testid="body">{text}</p> }));

const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: ['decide_work_item'] };
function Say() {
  return <span data-testid="said">{usePresence().said}</span>;
}
const mount = (ui: React.ReactNode, can = true) =>
  render(
    <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => can, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
      <PresenceProvider needs={0}>
        {ui}
        <Say />
      </PresenceProvider>
    </AuthContext.Provider>,
  );
beforeEach(() => Object.values(calls).forEach((c) => c.mockReset()));

describe('Composer', () => {
  it('sends the question scoped to the client and clears the box', async () => {
    calls.ask.mockResolvedValue({ status: 'answered', answer: 'x' });
    mount(<Composer borrowerId="b1" borrowerName="Quillfeather Labs, Inc." />);
    await userEvent.type(screen.getByLabelText(/ask squad about quillfeather/i), 'What is cash?');
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }));
    expect(calls.ask).toHaveBeenCalledWith({ question: 'What is cash?', borrower_id: 'b1' });
    await waitFor(() => expect(screen.getByLabelText(/ask squad about/i)).toHaveValue(''));
  });

  it('sends with Ctrl+Enter, and plain Enter only makes a new line', async () => {
    calls.ask.mockResolvedValue({ status: 'answered', answer: 'x' });
    mount(<Composer borrowerId="b1" borrowerName="Q" />);
    await userEvent.type(screen.getByLabelText(/ask squad about/i), 'Line one{Enter}two');
    expect(calls.ask).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText(/ask squad about/i), '{Control>}{Enter}{/Control}');
    expect(calls.ask).toHaveBeenCalledWith({ question: 'Line one\ntwo', borrower_id: 'b1' });
  });

  it('does not send an empty question', async () => {
    mount(<Composer borrowerId="b1" borrowerName="Q" />);
    expect(screen.getByRole('button', { name: /^ask$/i })).toBeDisabled();
  });

  it('shows the server\'s own words when Squad cannot be reached, and keeps the question', async () => {
    calls.ask.mockRejectedValue(new ApiError(503, "The Copilot's model is not available."));
    mount(<Composer borrowerId="b1" borrowerName="Q" />);
    await userEvent.type(screen.getByLabelText(/ask squad about/i), 'What is cash?');
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent("The Copilot's model is not available.");
    expect(screen.getByLabelText(/ask squad about/i)).toHaveValue('What is cash?');
  });
});

const qa = (over: Partial<Extract<ThreadMessage, { type: 'qa' }>> = {}): Extract<ThreadMessage, { type: 'qa' }> => ({
  id: 'qa:1', ts: 't', type: 'qa', question: 'What is cash?', answer: 'Cash was {{fact:f1}}.', fact_ids: ['f1', 'f1', 'f2'],
  citations: [{ document_id: 'd1', page: 3 }], status: 'answered', run_id: 'r1', asked_by: 'Priya Raman', ...over,
});

describe('QaMessage', () => {
  it('shows the question, the answer with its sources, and how many figures code checked', () => {
    mount(<QaMessage message={qa()} borrowerCode="QFL" />);
    expect(screen.getByText('What is cash?')).toBeInTheDocument();
    expect(screen.getByTestId('body')).toHaveTextContent('Cash was {{fact:f1}}.');
    expect(screen.getByText(/checked by code: 2 stored figures/i)).toBeInTheDocument();
  });

  it('opens the cited page in the evidence drawer', async () => {
    mount(<QaMessage message={qa()} borrowerCode="QFL" />);
    await userEvent.click(screen.getByRole('button', { name: /source: page 3/i }));
    expect(calls.open).toHaveBeenCalledWith(expect.objectContaining({ type: 'document', documentId: 'd1', page: 3 }));
  });

  it('shows a refusal as a refusal, with the way to the evidence', () => {
    mount(<QaMessage message={qa({ status: 'refused', answer: 'I cannot answer that from what is on file. No grounding.', fact_ids: [], citations: [] })} borrowerCode="QFL" />);
    expect(screen.getByRole('group', { name: /squad could not answer/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open the client file/i })).toHaveAttribute('href', '/borrowers/QFL');
    expect(screen.queryByText(/checked by code/i)).not.toBeInTheDocument();
  });
});

const ask = (over: Partial<Extract<ThreadMessage, { type: 'ask' }>> = {}): Extract<ThreadMessage, { type: 'ask' }> => ({
  id: 'ask:1', ts: 't', type: 'ask', work_item_id: 'w1', title: 'How should I map this line?', question: "Is 'Recurring revenue' ARR or MRR?",
  options: [{ id: 'map_to_arr', label: 'Map it to ARR', evidence: 'Page 3 says ARR.' }, { id: 'map_to_mrr', label: 'Map it to MRR', evidence: 'Page 3 also shows monthly.' }],
  status: 'open', choice: null, chosen_by: null, needs_you: true, state_words: '', ...over,
});

describe('AskMessage', () => {
  it('disables the options for a viewer the server says is not the one to answer, and says whose it is', async () => {
    render(<AskMessage message={ask({ needs_you: false, state_words: 'With Priya Raman' })} focused={false} />);
    expect(screen.getByText('With Priya Raman')).toBeInTheDocument();
    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled();
  });

  it('renders agent-written option text through AgentBody, so a fact reference becomes a stored figure', () => {
    mount(<AskMessage message={ask({ options: [{ id: 'a', label: 'Use {{fact:f1}}', evidence: 'Cash was {{fact:f2}}.' }, { id: 'b', label: 'Ignore it', evidence: '' }] })} focused={false} />);
    const bodies = screen.getAllByTestId('body').map((n) => n.textContent);
    expect(bodies).toEqual(expect.arrayContaining(['Use {{fact:f1}}', 'Cash was {{fact:f2}}.']));
  });

  it('cannot be confirmed until an option is chosen', async () => {
    mount(<AskMessage message={ask()} focused={false} />);
    const confirm = screen.getByRole('button', { name: /confirm/i });
    expect(confirm).toBeDisabled();
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    expect(confirm).toBeEnabled();
  });

  it('records the choice without remembering unless asked to', async () => {
    calls.answer.mockResolvedValue({ lesson_id: null });
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to mrr/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(calls.answer).toHaveBeenCalledWith({ option_id: 'map_to_mrr', remember: false });
    expect(await screen.findByText('Recorded as Priya')).toBeInTheDocument();
    expect(screen.queryByLabelText(/why\? squad will remember/i)).not.toBeInTheDocument();
  });

  it('remembers only in the person\'s own words: ticking asks why, and Confirm waits for it', async () => {
    calls.answer.mockResolvedValue({ lesson_id: 'l1' });
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    await userEvent.click(screen.getByRole('checkbox', { name: /remember/i }));
    const confirm = screen.getByRole('button', { name: /confirm/i });
    expect(confirm).toBeDisabled();
    await userEvent.click(confirm);
    expect(calls.answer).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText(/why\? squad will remember this in your words/i), '  Their contracts are annual.  ');
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(calls.answer).toHaveBeenCalledWith({ option_id: 'map_to_arr', remember: true, note: 'Their contracts are annual.' });
    expect(await screen.findByText('Recorded as Priya · remembered')).toBeInTheDocument();
  });

  it('cannot submit a remembered choice with a blank note', async () => {
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    await userEvent.click(screen.getByRole('checkbox', { name: /remember/i }));
    await userEvent.type(screen.getByLabelText(/why\? squad will remember/i), '   ');
    expect(screen.getByRole('button', { name: /confirm/i })).toBeDisabled();
    expect(calls.answer).not.toHaveBeenCalled();
  });

  it('shows the engine\'s refusal and leaves the question open', async () => {
    calls.answer.mockRejectedValue(new ApiError(422, 'this item has already been decided'));
    mount(<AskMessage message={ask()} focused={false} />);
    await userEvent.click(screen.getByRole('radio', { name: /map it to arr/i }));
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('already been decided');
    expect(screen.getByRole('button', { name: /confirm/i })).toBeEnabled();
  });

  it('is read-only once answered, with who chose what', () => {
    mount(<AskMessage message={ask({ status: 'decided', choice: 'Map it to ARR', chosen_by: 'Priya Raman' })} focused={false} />);
    expect(screen.getByText(/Priya Raman chose Map it to ARR/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
  });

  it('is read-only for a person who cannot decide it', () => {
    mount(<AskMessage message={ask({ needs_you: false, state_words: 'With the client’s analyst' })} focused={false} />, false);
    expect(screen.getByText(/with the client’s analyst/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
  });
});

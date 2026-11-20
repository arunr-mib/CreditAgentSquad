// frontend/src/squad/__tests__/drafts.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/client';
import type { ApiUser } from '@/api/schema';
import { AuthContext } from '@/auth/context';
import type { ThreadMessage } from '../api/types';
import { PresenceProvider, usePresence } from '../presence/Presence';
import { DraftMessage } from '../thread/DraftMessage';

const calls = vi.hoisted(() => ({ edit: vi.fn(), send: vi.fn() }));
vi.mock('../api/hooks', () => ({
  useEditDraft: () => ({ mutateAsync: calls.edit, isPending: false }),
  useSendDraft: () => ({ mutateAsync: calls.send, isPending: false }),
}));
const priya: ApiUser = { id: 'u1', email: 'p@x', name: 'Priya Raman', title: '', role: 'analyst', permissions: [] };
const Say = () => <span data-testid="said">{usePresence().said}</span>;
const mount = (m: Extract<ThreadMessage, { type: 'draft' }>, can = true) =>
  render(
    <AuthContext.Provider value={{ user: priya, status: 'signed-in', can: () => can, signIn: async () => priya, signOut: async () => {}, retry: () => {} }}>
      <PresenceProvider needs={0}><DraftMessage message={m} /><Say /></PresenceProvider>
    </AuthContext.Provider>,
  );
const draft = (over: Partial<Extract<ThreadMessage, { type: 'draft' }>> = {}): Extract<ThreadMessage, { type: 'draft' }> => ({
  id: 'draft:d1', ts: 't', type: 'draft', draft_id: 'd1', borrower_id: 'b1', created_at: 't', to: 'cfo@quillfeather.example', subject: 'October MRR', body: 'Hi, could you send the October MRR?',
  kind: 'reminder', status: 'draft', created_by: 'Squad', edited_by: null, sent_by: null, sent_at: null, work_item_id: null, ...over,
});
beforeEach(() => Object.values(calls).forEach((c) => c.mockReset()));

describe('DraftMessage', () => {
  it('shows who drafted it and offers to send as the signed-in person', () => {
    mount(draft());
    expect(screen.getByText(/drafted by squad/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send as Priya' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /save changes/i })).not.toBeInTheDocument();
  });

  it('offers to save only once the text has changed', async () => {
    mount(draft());
    await userEvent.type(screen.getByLabelText('Message'), ' Thanks.');
    expect(screen.getByRole('button', { name: /save changes/i })).toBeInTheDocument();
  });

  it('sends as the person and says it was recorded, not emailed', async () => {
    calls.send.mockResolvedValue({ status: 'sent', delivered: false });
    mount(draft());
    await userEvent.click(screen.getByRole('button', { name: 'Send as Priya' }));
    expect(calls.send).toHaveBeenCalledWith({ draft_id: 'd1' });
    expect(calls.edit).not.toHaveBeenCalled();
    expect(await screen.findByText('Send recorded as Priya · not emailed (no mail connector yet)')).toBeInTheDocument();
  });

  it('saves her edit first and sends only when the save worked', async () => {
    calls.edit.mockResolvedValue({ status: 'draft' });
    calls.send.mockResolvedValue({ status: 'sent', delivered: false });
    mount(draft());
    const box = screen.getByLabelText('Message');
    await userEvent.clear(box);
    await userEvent.type(box, 'Shorter.');
    await userEvent.click(screen.getByRole('button', { name: 'Send as Priya' }));
    expect(calls.edit).toHaveBeenCalledWith({ draft_id: 'd1', body: 'Shorter.' });
    expect(calls.send).toHaveBeenCalled();
  });

  it('does not send when the save is refused', async () => {
    calls.edit.mockRejectedValue(new ApiError(422, 'this draft has been sent and cannot be changed'));
    mount(draft());
    await userEvent.type(screen.getByLabelText('Message'), ' more');
    await userEvent.click(screen.getByRole('button', { name: 'Send as Priya' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('cannot be changed');
    expect(calls.send).not.toHaveBeenCalled();
  });

  it('is read-only once sent, with who sent it, and cannot be sent again', () => {
    mount(draft({ status: 'sent', sent_by: 'Priya Raman', sent_at: '2026-11-20T09:00:00Z' }));
    expect(screen.getByText('Sent')).toBeInTheDocument();
    expect(screen.getByText(/sent by Priya Raman/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toHaveAttribute('readonly');
    expect(screen.queryByRole('button', { name: /send as/i })).not.toBeInTheDocument();
  });

  it('is read-only for a person who may not send', () => {
    mount(draft(), false);
    expect(screen.getByText(/only an analyst can send this/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /send as/i })).not.toBeInTheDocument();
  });
});

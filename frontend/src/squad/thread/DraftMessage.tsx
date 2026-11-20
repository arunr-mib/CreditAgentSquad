// frontend/src/squad/thread/DraftMessage.tsx
import { useState } from 'react';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { useEditDraft, useSendDraft } from '../api/hooks';
import type { ThreadMessage } from '../api/types';
import { SquadMark } from '../mark/SquadMark';
import { usePresence } from '../presence/Presence';
import { Time } from './Time';

type Draft = Extract<ThreadMessage, { type: 'draft' }>;

/** Squad drafts; only a person sends. "Send" records the send on the ledger; nothing is emailed in v2. */
export function DraftMessage({ message }: { message: Draft }) {
  const { user, can } = useAuth();
  const edit = useEditDraft();
  const send = useSendDraft();
  const { say, pulse } = usePresence();
  const [body, setBody] = useState(message.body);
  const [error, setError] = useState<string | null>(null);
  const [justSent, setJustSent] = useState(false);
  const sent = message.status === 'sent' || justSent;
  const mayWrite = can('edit_commentary');
  const dirty = body !== message.body;
  const first = user?.name.split(' ')[0] ?? 'you';

  async function save(): Promise<boolean> {
    try {
      await edit.mutateAsync({ draft_id: message.draft_id, body });
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    }
  }
  async function sendIt() {
    setError(null);
    if (dirty && !(await save())) return;
    try {
      await send.mutateAsync({ draft_id: message.draft_id });
      setJustSent(true);
      say(`Send recorded as ${first} · not emailed (no mail connector yet)`);
      pulse();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <article className="sq-msg sq-card sq-email">
      <header className="sq-msghead">
        <SquadMark size={22} /> <b>Draft to {message.to}</b>
        <span className="sq-faint">drafted by {message.created_by}</span>
        {message.edited_by ? <span className="sq-faint">edited by {message.edited_by}</span> : null}
        {sent ? <span className="sq-tag">Sent</span> : null}
      </header>
      <p className="sq-muted">Subject: {message.subject}</p>
      <textarea aria-label="Message" value={sent ? message.body : body} readOnly={sent || !mayWrite} onChange={(e) => setBody(e.target.value)} rows={6} className="sq-paper sq-draftbox" />
      {sent ? <p className="sq-faint">Sent by {message.sent_by ?? (justSent ? user?.name : null)}{message.sent_at ? <> <Time ts={message.sent_at} /></> : null}. Recorded on the ledger, not emailed.</p> : null}
      {!sent && mayWrite ? (
        <div className="sq-actions">
          <button type="button" className="sq-btn sq-btn-primary" disabled={!body.trim() || send.isPending || edit.isPending} onClick={() => void sendIt()}>
            Send as {first}
          </button>
          {dirty ? <button type="button" className="sq-btn" disabled={edit.isPending} onClick={() => void save().then((ok) => ok && say('Draft saved'))}>Save changes</button> : null}
        </div>
      ) : null}
      {!sent && !mayWrite ? <p className="sq-muted">Only an analyst can send this.</p> : null}
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
    </article>
  );
}

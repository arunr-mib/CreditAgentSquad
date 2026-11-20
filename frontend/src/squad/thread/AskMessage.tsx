import { useId, useState } from 'react';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { AgentBody } from '@/source/AgentBody';
import { useAnswer } from '../api/hooks';
import type { ThreadMessage } from '../api/types';
import { SquadMark } from '../mark/SquadMark';
import { usePresence } from '../presence/Presence';
import { Time } from './Time';
import { Trail } from './Trail';

type Ask = Extract<ThreadMessage, { type: 'ask' }>;

/** Squad asks: options with their evidence, one choice. "Remember" needs the person's own words; the engine records it with her name. */
export function AskMessage({ message, focused }: { message: Ask; focused: boolean }) {
  const { user, can } = useAuth();
  const answer = useAnswer(message.work_item_id);
  const { say, pulse } = usePresence();
  const group = useId();
  const noteId = useId();
  const [choice, setChoice] = useState<string | null>(null);
  const [remember, setRemember] = useState(false);
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const open = message.status === 'open';
  const mayAnswer = can('decide_work_item');
  const reason = note.trim();
  const ready = choice !== null && (!remember || reason !== '');

  async function confirm() {
    if (!choice || !ready) return;
    setError(null);
    try {
      await answer.mutateAsync(remember ? { option_id: choice, remember: true, note: reason } : { option_id: choice, remember: false });
      say(`Recorded as ${user?.name.split(' ')[0] ?? 'you'}${remember ? ' · remembered' : ''}`);
      pulse();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <article className="sq-msg sq-card sq-squad" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
      <header className="sq-msghead"><SquadMark size={22} /> <b>Squad asks</b> <Time ts={message.ts} /></header>
      <p>{message.question}</p>
      {open ? (
        <fieldset className="sq-options" disabled={!mayAnswer}>
          <legend className="sq-sr">{message.question}</legend>
          {message.options.map((o) => (
            <label key={o.id} className="sq-option">
              <input type="radio" name={group} value={o.id} checked={choice === o.id} onChange={() => setChoice(o.id)} />
              <AgentBody text={o.label} className="sq-optlabel" />
              {o.evidence ? <AgentBody text={o.evidence} className="sq-muted sq-optevidence" /> : null}
            </label>
          ))}
        </fieldset>
      ) : (
        <p><b>{message.choice ? `${message.chosen_by ?? 'Someone'} chose ${message.choice}` : 'Closed without an answer'}</b></p>
      )}
      {open && mayAnswer ? (
        <>
          <label className="sq-check-label"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember this for next time</label>
          {remember ? (
            <div className="sq-why">
              <label htmlFor={noteId}>Why? Squad will remember this in your words</label>
              <textarea id={noteId} value={note} onChange={(e) => setNote(e.target.value)} rows={2} required />
            </div>
          ) : null}
          <div className="sq-actions">
            <button type="button" className="sq-btn sq-btn-primary" disabled={!ready || answer.isPending} onClick={() => void confirm()}>Confirm</button>
          </div>
        </>
      ) : null}
      {open && !mayAnswer ? <p className="sq-muted">Waiting for an analyst.</p> : null}
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
      <Trail workItemId={message.work_item_id} />
    </article>
  );
}

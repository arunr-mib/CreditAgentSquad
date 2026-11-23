import { useId, useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAgentsStatus } from '@/api/hooks';
import { useAskCopilot, type CopilotReply } from '../api/hooks';
import { usePresence } from '../presence/Presence';

/** A free question, answered by the engine's Copilot under its own guarantees (spec 7). */
export function Composer({ borrowerId, borrowerName, workItemId, label, onReply }: {
  /** The client the question is about; null asks about the whole portfolio. */
  borrowerId: string | null;
  borrowerName?: string;
  /** The case open beside the question: the server reads it with the client's scope. */
  workItemId?: string;
  label?: string;
  onReply?: (reply: CopilotReply) => void;
}) {
  const name = label ?? `Ask Squad about ${borrowerId === null ? 'the whole portfolio' : (borrowerName ?? 'this client')}`;
  const id = useId();
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const ask = useAskCopilot();
  // A deployment with no model says so before anyone types, in the server's own words.
  const model = useAgentsStatus().data;
  const off = model?.model_connected === false; // unknown while loading: do not block
  const { beginWork, pulse } = usePresence();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = text.trim();
    if (!question || off) return;
    setError(null);
    const done = beginWork();
    try {
      const reply = await ask.mutateAsync({ question, borrower_id: borrowerId, ...(workItemId ? { work_item_id: workItemId } : {}) });
      onReply?.(reply);
      setText('');
      pulse();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      done();
    }
  }
  return (
    <form onSubmit={(e) => void submit(e)} className="sq-composer">
      <label htmlFor={id} className="sq-sr">{name}</label>
      <textarea id={id} value={text} onChange={(e) => setText(e.target.value)} aria-describedby={`${id}-hint`} onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} rows={2} placeholder={name} readOnly={off} aria-disabled={off || undefined} />
      <small id={`${id}-hint`} className="sq-faint">{(off && model?.reason) || 'Ctrl or Cmd + Enter to send'}</small>
      <button type="submit" className="sq-btn sq-btn-primary" disabled={off || !text.trim() || ask.isPending}>Ask</button>
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
    </form>
  );
}

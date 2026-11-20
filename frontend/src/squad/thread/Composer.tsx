import { useId, useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAskCopilot } from '../api/hooks';
import { usePresence } from '../presence/Presence';

/** A free question, answered by the engine's Copilot under its own guarantees (spec 7). */
export function Composer({ borrowerId, borrowerName }: { borrowerId: string; borrowerName: string }) {
  const id = useId();
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const ask = useAskCopilot();
  const { beginWork, pulse } = usePresence();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = text.trim();
    if (!question) return;
    setError(null);
    const done = beginWork();
    try {
      await ask.mutateAsync({ question, borrower_id: borrowerId });
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
      <label htmlFor={id} className="sq-sr">Ask Squad about {borrowerName}</label>
      <textarea id={id} value={text} onChange={(e) => setText(e.target.value)} aria-describedby={`${id}-hint`} onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} rows={2} placeholder={`Ask Squad about ${borrowerName}`} />
      <small id={`${id}-hint`} className="sq-faint">Ctrl or Cmd + Enter to send</small>
      <button type="submit" className="sq-btn sq-btn-primary" disabled={!text.trim() || ask.isPending}>Ask</button>
      {error ? <p role="alert" className="sq-error">{error}</p> : null}
    </form>
  );
}

// frontend/src/squad/thread/ClientThread.tsx
import { Link, useParams, useSearch } from '@tanstack/react-router';
import { useEffect, useRef } from 'react';
import { useBorrowerByCode } from '@/api/hooks';
import { useThread } from '../api/hooks';
import { clientFile } from '../links';
import { Composer } from './Composer';
import { MessageView } from './messages';

export function ClientThread() {
  const { code } = useParams({ strict: false }) as { code: string };
  const { case: focusId } = useSearch({ strict: false }) as { case?: string };
  const { borrower, notFound, error: borrowersError, refetch: refetchBorrowers } = useBorrowerByCode(code);
  const thread = useThread(borrower?.id);

  const scrolled = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (!focusId || scrolled.current === focusId || !thread.data) return;
    const el = document.querySelector('[data-focused="true"]');
    if (!el) return;
    scrolled.current = focusId;
    // To the start of what is new for this case, not the bottom of the thread; once per case, so a poll never re-scrolls.
    el.scrollIntoView?.({ block: 'start' });
  }, [focusId, thread.data]);

  const opened = useRef<string | undefined>(undefined);
  useEffect(() => {
    const data = thread.data;
    if (focusId || !data?.opening_id || opened.current === data.borrower.id) return;
    const el = document.querySelector(`[data-message-id="${data.opening_id}"]`);
    if (!el) return;
    opened.current = data.borrower.id;
    el.scrollIntoView?.({ block: 'start' });
  }, [focusId, thread.data]);

  if (notFound) {
    return (
      <div role="alert" className="sq-card">
        <p>There is no client with that code.</p>
        <Link to="/" className="sq-link">Back to Squad</Link>
      </div>
    );
  }
  if (!borrower && borrowersError) {
    return (
      <div role="alert" className="sq-card">
        <p>The client list could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void refetchBorrowers()}>Try again</button>
      </div>
    );
  }
  if (!borrower || thread.isPending) return <p role="status" className="sq-muted">Opening the thread.</p>;
  if (thread.error || !thread.data) return <p role="alert">The thread could not be loaded. Try again in a moment.</p>;
  const messages = thread.data.messages;
  return (
    <section className="sq-thread" aria-label={`${borrower.name} thread`}>
      <header className="sq-threadhead">
        <h1 className="sq-h1">{borrower.name}</h1>
        <Link to={clientFile(borrower.code)} className="sq-link">Open in client file</Link>
      </header>
      {messages.length === 0 ? <p className="sq-muted">Nothing here yet. Squad will write here as documents arrive and work is done.</p> : null}
      <div className="sq-messages">
        {messages.map((m) => (
          <div key={m.id} data-message-id={m.id}>
            <MessageView message={m} thread={messages} borrowerCode={borrower.code}
              focused={Boolean(focusId) && 'work_item_id' in m && m.work_item_id === focusId && (m.type === 'case' || m.type === 'ask')} />
          </div>
        ))}
      </div>
      <Composer borrowerId={borrower.id} borrowerName={borrower.name} />
    </section>
  );
}

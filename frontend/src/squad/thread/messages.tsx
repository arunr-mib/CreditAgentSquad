// frontend/src/squad/thread/messages.tsx
import { Link, useNavigate } from '@tanstack/react-router';
import { word } from '@/api/words';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { ThreadMessage } from '../api/types';
import { CasePanel } from '../case/CasePanel';
import { clientFile, threadHref } from '../links';
import { SquadMark } from '../mark/SquadMark';
import { AskMessage } from './AskMessage';
import { DraftMessage } from './DraftMessage';
import { QaMessage } from './QaMessage';
import { Time } from './Time';
import { Trail } from './Trail';

/** A decision the server did not word for this message, in the server's table of decision words. */
const decided = (s: string | null) => (s ? word('decisions', s).toLowerCase() : 'decided');

/** Where a case stands, in words: its decision, whether the server says it is yours (the briefing's own rule), a handoff or return, or who holds it. */
export function caseState(message: Extract<ThreadMessage, { type: 'case' }>, all: ThreadMessage[]): { text: string; needsYou: boolean } {
  const mine = all.filter((m) => 'work_item_id' in m && m.work_item_id === message.work_item_id);
  const decision = mine.find((m): m is Extract<ThreadMessage, { type: 'decision' }> => m.type === 'decision');
  if (decision) return { text: `${decision.decision_words ?? decided(decision.decision)} by ${decision.by}`, needsYou: false };
  if (message.status !== 'open') return { text: word('case_statuses', message.status), needsYou: false };
  const last = [...mine].reverse().find((m) => m.type === 'handoff' || m.type === 'returned');
  if (message.needs_you) return { text: last?.type === 'returned' ? 'Returned to you' : 'Needs your call', needsYou: true };
  if (last?.type === 'returned') return { text: `Returned to ${last.to ?? 'the analyst'}`, needsYou: false };
  if (last?.type === 'handoff') return { text: `With ${last.assigned_to ?? 'no one in particular'}`, needsYou: false };
  return { text: message.state_words || 'Open', needsYou: false };
}

export function MessageView({ message, focused, borrowerCode, thread = [] }: { message: ThreadMessage; focused: boolean; borrowerCode: string; thread?: ThreadMessage[] }) {
  const source = useSource();
  const navigate = useNavigate();
  switch (message.type) {
    case 'report':
      return (
        <article className="sq-msg sq-card sq-squad">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b> <span className="sq-faint">{message.agent_label}</span> <Time ts={message.ts} /></header>
          <AgentBody text={message.text} />
        </article>
      );
    case 'case': {
      const state = caseState(message, thread);
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
          <header className="sq-msghead"><b>{message.title}</b> <span className="sq-tag">{word('severities', message.severity)}</span> <span className={state.needsYou ? 'sq-tag sq-tag-needs' : 'sq-tag'}>{state.text}</span> <Time ts={message.ts} /></header>
          <p>{message.question}</p>
          <div className="sq-actions">
            {focused ? null : (
              <Link {...threadHref(borrowerCode, message.work_item_id)} className={state.needsYou ? 'sq-btn sq-btn-primary' : 'sq-btn'} aria-label={`${state.needsYou ? 'Open the case' : 'See the case'}: ${message.title}`}>
                {state.needsYou ? 'Open the case' : 'See the case'}
              </Link>
            )}
            <Link to={clientFile(borrowerCode)} className="sq-link" aria-label={`Open in client file: ${message.title}`}>Open in client file</Link>
          </div>
          {focused ? <CasePanel workItemId={message.work_item_id} onOpenCase={(id) => void navigate(threadHref(borrowerCode, id))} /> : null}
          <Trail workItemId={message.work_item_id} />
        </article>
      );
    }
    case 'document':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>Document arrived</b> <Time ts={message.ts} /></header>
          <button type="button" className="sq-link" aria-label={`Open ${message.title}`} onClick={() => source.open({ type: 'document', documentId: message.document_id, page: 1, title: message.title, borrowerCode })}>
            {message.title}
          </button>
          <p className="sq-muted">{message.doc_type_words} · {message.pages} {message.pages === 1 ? 'page' : 'pages'}</p>
        </article>
      );
    case 'arrivals':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>{message.title}</b> <Time ts={message.ts} /></header>
          <ul className="sq-plainlist">
            {message.documents.map((d) => (
              <li key={d.document_id}>
                <button type="button" className="sq-link" aria-label={`Open ${d.title}`} onClick={() => source.open({ type: 'document', documentId: d.document_id, page: 1, title: d.title, borrowerCode })}>{d.title}</button>
                <span className="sq-faint"> · {d.doc_type_words} · {d.pages} {d.pages === 1 ? 'page' : 'pages'}</span>
              </li>
            ))}
          </ul>
        </article>
      );
    case 'held':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>Held</b> <Time ts={message.ts} /></header>
          <p>{message.title}</p>
          <p className="sq-muted">{message.reason || 'No reason was written.'}</p>
        </article>
      );
    case 'decision':
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id}>
          <p><b>{message.by}: {message.decision_words ?? decided(message.decision)}</b> <Time ts={message.ts} /></p>
          {message.reason ? <blockquote className="sq-quote">{message.reason}</blockquote> : null}
        </article>
      );
    case 'handoff':
      return (
        <div className="sq-msg" data-work-item={message.work_item_id}>
          <p className="sq-faint">{message.by} {message.view ? 'sent this to' : 'handed this to'} {message.assigned_to ?? 'no one in particular'}{message.view ? ' with this view:' : '.'} <Time ts={message.ts} /></p>
          {message.view ? <blockquote className="sq-quote">{message.view}</blockquote> : null}
        </div>
      );
    case 'returned':
      return (
        <div className="sq-msg" data-work-item={message.work_item_id}>
          <p className="sq-faint">{message.by} returned this to {message.to ?? 'the analyst'}: <Time ts={message.ts} /></p>
          <blockquote className="sq-quote">{message.reason}</blockquote>
        </div>
      );
    case 'attached':
      return (
        <p className="sq-msg sq-faint" data-work-item={message.work_item_id}>
          {message.by_kind === 'squad' && message.note ? `${message.note} ` : `${message.by} attached `}
          <button type="button" className="sq-link" aria-label={`Open ${message.title}`} onClick={() => source.open({ type: 'document', documentId: message.document_id, page: 1, title: message.title, borrowerCode })}>{message.title}</button>
          {message.by_kind !== 'squad' && message.note ? ` · ${message.note}` : ''} <Time ts={message.ts} />
        </p>
      );
    case 'ask':
      return <AskMessage message={message} focused={focused} />;
    case 'qa':
      return <QaMessage message={message} borrowerCode={borrowerCode} />;
    case 'draft':
      return <DraftMessage message={message} />;
  }
}

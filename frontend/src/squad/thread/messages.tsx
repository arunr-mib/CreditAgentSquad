// frontend/src/squad/thread/messages.tsx
import { Link } from '@tanstack/react-router';
import { useWorkspaceDrawer } from '@/drawer/context';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { ThreadMessage } from '../api/types';
import { clientFile } from '../links';
import { SquadMark } from '../mark/SquadMark';
import { AskMessage } from './AskMessage';
import { DraftMessage } from './DraftMessage';
import { QaMessage } from './QaMessage';
import { Time } from './Time';
import { Trail } from './Trail';

const words = (s: string | null) => (s ?? 'decided').replace(/_/g, ' ');
const agent = (name: string) => `${name.charAt(0).toUpperCase()}${name.slice(1)} agent`;

const SEVERITY: Record<string, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };

/** Where a case stands, in words: its decision, whether the server says it is yours (the briefing's own rule), a handoff, or who holds it. */
export function caseState(message: Extract<ThreadMessage, { type: 'case' }>, all: ThreadMessage[]): { text: string; needsYou: boolean } {
  const mine = all.filter((m) => 'work_item_id' in m && m.work_item_id === message.work_item_id);
  const decision = mine.find((m): m is Extract<ThreadMessage, { type: 'decision' }> => m.type === 'decision');
  if (decision) return { text: `${words(decision.decision)} by ${decision.by}`, needsYou: false };
  if (message.status !== 'open') return { text: words(message.status).replace(/^./, (c) => c.toUpperCase()), needsYou: false };
  if (message.needs_you) return { text: 'Needs your call', needsYou: true };
  const handoff = [...mine].reverse().find((m): m is Extract<ThreadMessage, { type: 'handoff' }> => m.type === 'handoff');
  if (handoff) return { text: `With ${handoff.assigned_to ?? 'no one in particular'}`, needsYou: false };
  return { text: message.state_words || 'Open', needsYou: false };
}

export function MessageView({ message, focused, borrowerCode, thread = [] }: { message: ThreadMessage; focused: boolean; borrowerCode: string; thread?: ThreadMessage[] }) {
  const source = useSource();
  const drawer = useWorkspaceDrawer();
  switch (message.type) {
    case 'report':
      return (
        <article className="sq-msg sq-card sq-squad">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b> <span className="sq-faint">{agent(message.agent_name)}</span> <Time ts={message.ts} /></header>
          <AgentBody text={message.text} />
        </article>
      );
    case 'case': {
      const state = caseState(message, thread);
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
          <header className="sq-msghead"><b>{message.title}</b> <span className="sq-tag">{SEVERITY[message.severity] ?? words(message.severity)}</span> <span className={state.needsYou ? 'sq-tag sq-tag-needs' : 'sq-tag'}>{state.text}</span> <Time ts={message.ts} /></header>
          <p>{message.question}</p>
          <div className="sq-actions">
            {state.needsYou ? (
              <button type="button" className="sq-btn sq-btn-primary" aria-label={`Decide ${message.title}`} onClick={() => drawer.openItem(message.work_item_id)}>Decide</button>
            ) : null}
            <Link to={clientFile(borrowerCode)} className="sq-link" aria-label={`Open ${message.title} in the client file`}>Open in client file</Link>
          </div>
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
          <p className="sq-muted">{message.doc_type ? words(message.doc_type) : 'Not yet classified'} · {message.pages} {message.pages === 1 ? 'page' : 'pages'}</p>
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
          <p><b>{message.by}: {words(message.decision)}</b> <Time ts={message.ts} /></p>
          {message.reason ? <blockquote className="sq-quote">{message.reason}</blockquote> : null}
        </article>
      );
    case 'handoff':
      return <p className="sq-msg sq-faint" data-work-item={message.work_item_id}>{message.by} handed this to {message.assigned_to ?? 'no one in particular'}. <Time ts={message.ts} /></p>;
    case 'ask':
      return <AskMessage message={message} focused={focused} />;
    case 'qa':
      return <QaMessage message={message} borrowerCode={borrowerCode} />;
    case 'draft':
      return <DraftMessage message={message} />;
  }
}

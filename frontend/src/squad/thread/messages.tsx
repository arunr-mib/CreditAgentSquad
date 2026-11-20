// frontend/src/squad/thread/messages.tsx
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { ThreadMessage } from '../api/types';
import { SquadMark } from '../mark/SquadMark';
import { AskMessage } from './AskMessage';
import { DraftMessage } from './DraftMessage';
import { QaMessage } from './QaMessage';
import { Trail } from './Trail';

const words = (s: string | null) => (s ?? 'decided').replace(/_/g, ' ');
const agent = (name: string) => `${name.charAt(0).toUpperCase()}${name.slice(1)} agent`;

const SEVERITY: Record<string, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };

/** Where a case stands, in words, computed from the thread: its decision, a later handoff, or whether you can act. */
export function caseState(message: Extract<ThreadMessage, { type: 'case' }>, all: ThreadMessage[]): { text: string; needsYou: boolean } {
  const mine = all.filter((m) => 'work_item_id' in m && m.work_item_id === message.work_item_id);
  const decision = mine.find((m): m is Extract<ThreadMessage, { type: 'decision' }> => m.type === 'decision');
  if (decision) return { text: `${words(decision.decision)} by ${decision.by}`, needsYou: false };
  if (message.status !== 'open') return { text: words(message.status).replace(/^./, (c) => c.toUpperCase()), needsYou: false };
  const handoff = [...mine].reverse().find((m): m is Extract<ThreadMessage, { type: 'handoff' }> => m.type === 'handoff');
  if (handoff) return { text: `With ${handoff.assigned_to ?? 'no one in particular'}`, needsYou: false };
  if (message.allowed_decisions.length > 0) return { text: 'Needs your call', needsYou: true };
  return { text: 'Open', needsYou: false };
}

function Time({ ts }: { ts: string }) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return null;
  return <time className="sq-faint sq-time" dateTime={ts} title={d.toLocaleString()}>{d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</time>;
}

export function MessageView({ message, focused, borrowerCode, thread = [] }: { message: ThreadMessage; focused: boolean; borrowerCode: string; thread?: ThreadMessage[] }) {
  const source = useSource();
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

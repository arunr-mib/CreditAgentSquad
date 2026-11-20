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

export function MessageView({ message, focused, borrowerCode }: { message: ThreadMessage; focused: boolean; borrowerCode: string }) {
  const source = useSource();
  switch (message.type) {
    case 'report':
      return (
        <article className="sq-msg sq-card sq-squad">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b> <span className="sq-faint">{agent(message.agent_name)}</span></header>
          <AgentBody text={message.text} />
        </article>
      );
    case 'case':
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id} data-focused={focused ? 'true' : undefined} aria-current={focused ? 'true' : undefined}>
          <header className="sq-msghead"><b>{message.title}</b> <span className="sq-tag">{message.status}</span></header>
          <p>{message.question}</p>
          <Trail workItemId={message.work_item_id} />
        </article>
      );
    case 'document':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>Document arrived</b></header>
          <button type="button" className="sq-link" aria-label={`Open ${message.title}`} onClick={() => source.open({ type: 'document', documentId: message.document_id, page: 1, title: message.title, borrowerCode })}>
            {message.title}
          </button>
          <p className="sq-muted">{message.doc_type ? words(message.doc_type) : 'Not yet classified'} · {message.pages} {message.pages === 1 ? 'page' : 'pages'}</p>
        </article>
      );
    case 'held':
      return (
        <article className="sq-msg sq-card">
          <header className="sq-msghead"><b>Held</b></header>
          <p>{message.title}</p>
          <p className="sq-muted">{message.reason || 'No reason was written.'}</p>
        </article>
      );
    case 'decision':
      return (
        <article className="sq-msg sq-card" data-work-item={message.work_item_id}>
          <p><b>{message.by}: {words(message.decision)}</b></p>
          {message.reason ? <blockquote className="sq-quote">{message.reason}</blockquote> : null}
        </article>
      );
    case 'handoff':
      return <p className="sq-msg sq-faint" data-work-item={message.work_item_id}>{message.by} handed this to {message.assigned_to ?? 'no one in particular'}.</p>;
    case 'ask':
      return <AskMessage message={message} focused={focused} />;
    case 'qa':
      return <QaMessage message={message} borrowerCode={borrowerCode} />;
    case 'draft':
      return <DraftMessage message={message} />;
  }
}

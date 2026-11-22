import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { CopilotReply } from '../api/hooks';

/** Squad's answer to a question that no thread holds: figures are stored facts rendered by code, a refusal is shown as a refusal. */
export function AskReply({ reply }: { reply: CopilotReply }) {
  const source = useSource();
  const checked = new Set(reply.fact_ids).size;
  if (reply.status !== 'answered') {
    return <div role="group" aria-label="Squad could not answer" className="sq-msg sq-card sq-refusal"><p>{reply.answer}</p></div>;
  }
  return (
    <div className="sq-msg sq-card sq-squad">
      <AgentBody text={reply.answer_with_references} />
      {checked > 0 ? <p className="sq-faint">Checked by code: {checked} stored {checked === 1 ? 'figure' : 'figures'}</p> : null}
      <div className="sq-actions">
        {reply.citations.map((c, i) => <button key={i} type="button" className="sq-link" onClick={() => source.open({ type: 'document', documentId: c.document_id, page: c.page })}>Source: page {c.page}</button>)}
      </div>
    </div>
  );
}

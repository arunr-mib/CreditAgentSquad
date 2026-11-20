import { Link } from '@tanstack/react-router';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import type { ThreadMessage } from '../api/types';
import { clientFile } from '../links';
import { SquadMark } from '../mark/SquadMark';
import { Time } from './Time';

type Qa = Extract<ThreadMessage, { type: 'qa' }>;

/** A question and Squad's answer. Figures are stored facts rendered by code; a refusal is shown as a refusal. */
export function QaMessage({ message, borrowerCode }: { message: Qa; borrowerCode: string }) {
  const source = useSource();
  const checked = new Set(message.fact_ids).size;
  const refused = message.status !== 'answered';
  const open = (c: { document_id: string; page: number }) => source.open({ type: 'document', documentId: c.document_id, page: c.page, borrowerCode });
  const first = message.citations[0];
  return (
    <div className="sq-qa">
      <p className="sq-me"><b>{message.asked_by}</b> {message.question} <Time ts={message.ts} /></p>
      {refused ? (
        <div role="group" aria-label="Squad could not answer" className="sq-msg sq-card sq-refusal">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b></header>
          <p>{message.answer}</p>
          <div className="sq-actions">
            {first ? <button type="button" className="sq-link" onClick={() => open(first)}>Show the source</button> : null}
            <Link to={clientFile(borrowerCode)} className="sq-link">Open the client file</Link>
          </div>
        </div>
      ) : (
        <div className="sq-msg sq-card sq-squad">
          <header className="sq-msghead"><SquadMark size={22} /> <b>Squad</b></header>
          <AgentBody text={message.answer} />
          {checked > 0 ? <p className="sq-faint">Checked by code: {checked} stored {checked === 1 ? 'figure' : 'figures'}</p> : null}
          <div className="sq-actions">
            {message.citations.map((c, i) => (
              <button key={i} type="button" className="sq-link" onClick={() => open(c)}>Source: page {c.page}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

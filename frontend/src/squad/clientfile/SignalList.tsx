import type { SignalRow } from '@/api/schema';
import { formatDate } from '@/design';
import { AgentBody } from '@/source/AgentBody';
import { useSignalWords } from '../DocType';

type Row = Pick<SignalRow, 'id' | 'rule_id' | 'severity' | 'period_end' | 'explanation'> & { basis?: Record<string, unknown> };

const plain = (id: string) => id.replace(/[_-]/g, ' ');

/** Open signals, one line per rule and the covenant or requirement it is about, however many periods fired it: the
 * latest period's words are shown, and every period is one click away. Counts are of the rows the server returned. */
export function SignalList({ signals }: { signals: Row[] }) {
  const words = useSignalWords();
  const groups = new Map<string, Row[]>();
  for (const s of signals) {
    const subject = typeof s.basis?.subject === 'string' ? s.basis.subject : '';
    const key = `${s.rule_id}|${subject}`;
    groups.set(key, [...(groups.get(key) ?? []), s]);
  }
  return (
    <ul className="sq-plainlist">
      {[...groups.entries()].map(([key, unsorted]) => {
        const rows = [...unsorted].sort((a, b) => b.period_end.localeCompare(a.period_end));
        const latest = rows[0];
        const oldest = rows[rows.length - 1];
        if (!latest || !oldest) return null;
        const subject = key.slice(key.indexOf('|') + 1);
        return (
          <li key={key}>
            <span className={`sq-dotmark sq-sev-${latest.severity}`} aria-hidden /> <span>{words(latest.rule_id)}</span>
            {subject ? <span className="sq-muted"> · {plain(subject)}</span> : null}
            {' · '}
            <span className="sq-faint">
              {rows.length === 1 ? formatDate(latest.period_end) : `${rows.length} periods, ${formatDate(oldest.period_end)} to ${formatDate(latest.period_end)}`}
            </span>
            {latest.explanation?.text ? <AgentBody text={latest.explanation.text} /> : null}
            {rows.length > 1 ? (
              <details className="sq-group">
                <summary>Each period</summary>
                <ul className="sq-plainlist">
                  {rows.map((s) => (
                    <li key={s.id}><span className="sq-faint">{formatDate(s.period_end)}</span>{s.explanation?.text ? <AgentBody text={s.explanation.text} /> : null}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

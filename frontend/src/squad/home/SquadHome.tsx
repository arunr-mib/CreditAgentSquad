import { Link } from '@tanstack/react-router';
import { useAuth } from '@/auth/context';
import { AgentBody } from '@/source/AgentBody';
import { useBriefing } from '../api/hooks';
import type { BriefingItem } from '../api/types';
import { threadHref } from '../links';

const word = (n: number) => (n === 1 ? '1 needs you' : `${n} need you`);

function Row({ item }: { item: BriefingItem }) {
  const href = threadHref(item.borrower_code, item.work_item_id ?? undefined);
  return (
    <li>
      <Link {...href} className={item.needs_you ? 'sq-row sq-row-needs' : 'sq-row'} aria-label={`${item.borrower_name}: ${item.title}. ${item.state}`}>
        <span className={`sq-dotmark sq-sev-${item.severity}`} aria-hidden />
        <span className="sq-grow">
          <b>{item.borrower_name}</b>
          <span className="sq-muted"> · {item.title}</span>
        </span>
        <span className={item.needs_you ? 'sq-state sq-state-needs' : 'sq-state'}>{item.state}</span>
      </Link>
    </li>
  );
}

export function SquadHome() {
  const { user } = useAuth();
  const briefing = useBriefing();
  if (briefing.isPending) return <p role="status" className="sq-muted">Squad is reading the overnight record.</p>;
  if (briefing.error || !briefing.data)
    return (
      <div role="alert">
        <p>The briefing could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void briefing.refetch()}>Try again</button>
      </div>
    );
  const { items, overnight } = briefing.data;
  const needs = items.filter((i) => i.needs_you);
  const rest = items.filter((i) => !i.needs_you);
  return (
    <div className="sq-home">
      <h1 className="sq-h1">Hello, {user?.name.split(' ')[0] ?? 'there'}.</h1>
      <h2 className="sq-lede">{needs.length ? word(needs.length) : 'Nothing needs you.'}</h2>
      {needs.length > 0 ? (
        <ul className="sq-list" aria-label="Needs you">
          {needs.map((i) => <Row key={i.key} item={i} />)}
        </ul>
      ) : null}
      {rest.length > 0 ? (
        <>
          <h2 className="sq-h2">Also on the record</h2>
          <ul className="sq-list" aria-label="Also on the record">
            {rest.map((i) => <Row key={i.key} item={i} />)}
          </ul>
        </>
      ) : null}
      {overnight.length > 0 ? (
        <>
          <h2 className="sq-h2">What Squad did overnight</h2>
          <ul className="sq-list" aria-label="Overnight">
            {overnight.map((o) => (
              <li key={`${o.agent_name}|${o.finished_at}|${o.borrower_id}`} className="sq-card sq-squad">
                <p className="sq-faint"><b>{o.agent_name.charAt(0).toUpperCase() + o.agent_name.slice(1)} agent</b> · {o.borrower_name}</p>
                <AgentBody text={o.text} />
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}

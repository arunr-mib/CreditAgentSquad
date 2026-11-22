import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { useApprovals } from '../api/hooks';
import { CasePanel } from '../case/CasePanel';
import { threadHref } from '../links';
import { Trail } from '../thread/Trail';

const waits = (n: number) => (n === 1 ? '1 decision waits for you' : `${n} decisions wait for you`);

/** The credit officer's decisions: each with the case, its evidence and the analyst's view; the case opens beside the list. */
export function Approvals() {
  const { case: selected } = useSearch({ strict: false }) as { case?: string };
  const approvals = useApprovals();
  const navigate = useNavigate();
  if (approvals.isPending) return <p role="status" className="sq-muted">Gathering the decisions that wait for you.</p>;
  if (approvals.error || !approvals.data)
    return (
      <div role="alert">
        <p>The decisions could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void approvals.refetch()}>Try again</button>
      </div>
    );
  const rows = approvals.data;
  const current = rows.find((r) => r.work_item_id === selected);
  return (
    <div className="sq-approvals" data-ready="">
      <h1 className="sq-h1">Approvals</h1>
      <h2 className="sq-lede">{rows.length ? waits(rows.length) : 'Nothing waits for your decision.'}</h2>
      <div className="sq-split">
        <ul className="sq-list" aria-label="Decisions waiting">
          {rows.map((r) => (
            <li key={r.work_item_id}>
              <Link to="/approvals" search={{ case: r.work_item_id }} className="sq-row" aria-current={r.work_item_id === selected ? 'true' : undefined}>
                <span className={`sq-dotmark sq-sev-${r.severity}`} aria-hidden />
                <span className="sq-grow">
                  <b>{r.borrower_name}</b>
                  <span className="sq-muted"> · {r.title}</span>
                  {r.view ? <span className="sq-faint sq-block">{r.routed_by}: {r.view}</span> : null}
                </span>
                {r.returns > 0 ? <span className="sq-faint">returned {r.returns === 1 ? 'once' : `${r.returns} times`}</span> : null}
              </Link>
            </li>
          ))}
        </ul>
        <div>
          {selected ? (
            <>
              <CasePanel workItemId={selected} onOpenCase={(id) => void navigate({ to: '/approvals', search: { case: id } })} />
              <Trail workItemId={selected} />
              {current ? (
                <Link {...threadHref(current.borrower_code, selected)} className="sq-link">Open in {current.borrower_name}’s thread</Link>
              ) : null}
            </>
          ) : rows.length ? (
            <p className="sq-muted">Choose a decision to see its case, the evidence and the analyst’s view.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

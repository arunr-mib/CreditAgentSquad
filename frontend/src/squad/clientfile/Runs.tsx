import { useSearch } from '@tanstack/react-router';
import { useState } from 'react';
import type { BorrowerRow } from '@/api/schema';
import { useClientRuns, useRunDetail } from '../api/hooks';
import { Time } from '../thread/Time';

function Steps({ id, errorWords }: { id: string; errorWords: string | null }) {
  const run = useRunDetail(id);
  if (run.error) return <p role="alert">The steps could not be loaded. Try again in a moment.</p>;
  if (!run.data) return <p role="status" className="sq-muted">Reading the steps.</p>;
  return (
    <div>
      {errorWords ? <p role="alert" className="sq-block">{errorWords}</p> : null}
      {run.data.steps.length === 0 ? <p className="sq-muted">No steps were recorded for this run.</p> : (
        <ol className="sq-plainlist" aria-label="Steps">
          {run.data.steps.map((s) => <li key={s.id}><span className="sq-mono">{s.n}</span> {s.words}</li>)}
        </ol>
      )}
    </div>
  );
}

/** What the agents did for this client: read only, for anyone who may see the client (Oversight holds every run, for its roles). */
export function Runs({ borrower }: { borrower: BorrowerRow }) {
  const runs = useClientRuns(borrower.id);
  const named = (useSearch({ strict: false }) as { run?: string }).run ?? null;
  const [open, setOpen] = useState<string | null>(null);
  if (runs.isPending) return <p role="status" className="sq-muted">Reading what the agents did.</p>;
  if (runs.error || !runs.data) return <p role="alert">What the agents did could not be loaded. Try again in a moment.</p>;
  if (runs.data.length === 0) return <p className="sq-muted">No agent has run for this client yet.</p>;
  const shown = open ?? named;
  const older = named && !runs.data.some((r) => r.id === named) ? named : null;
  return (
    <>
      {older ? <NamedRun id={older} /> : null}
    <div className="sq-tablewrap">
      <table className="sq-table" aria-label="Agent runs">
        <thead><tr><th scope="col">When</th><th scope="col">Agent</th><th scope="col">Outcome</th><th scope="col">Checks</th></tr></thead>
        <tbody>
          {runs.data.map((r) => (
            <tr key={r.id}>
              <td><Time ts={r.created_at} /></td>
              <td>
                {r.agent_label} · <span className="sq-faint">{r.task_label}</span>{' '}
                <button type="button" className="sq-link" aria-expanded={shown === r.id} aria-label={`Steps of ${r.agent_label} ${r.task_label}`} onClick={() => setOpen(shown === r.id ? '' : r.id)}>Steps</button>
                {shown === r.id ? <Steps id={r.id} errorWords={r.error_words} /> : null}
              </td>
              <td>{r.status_label}</td>
              <td>{r.guardrail_notes.length === 0 ? <span className="sq-faint">None named</span> : r.guardrail_notes.map((n, i) => <span key={i} className="sq-block">{n.words}</span>)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </>
  );
}

/** A run a link names that is older than the newest page of runs: read on its own and shown above the table, so a
 * link from a thread to an old run never opens nothing. */
function NamedRun({ id }: { id: string }) {
  const run = useRunDetail(id);
  if (run.error) return <p role="alert">The run this link names could not be loaded.</p>;
  if (!run.data) return <p role="status" className="sq-muted">Reading the run this link names.</p>;
  const r = run.data;
  return (
    <section className="sq-card" aria-label="The run the link names">
      <p><b>{r.agent_label}</b> · <span className="sq-faint">{r.task_label}</span> · {r.status_label} · <Time ts={r.created_at} /></p>
      {r.guardrail_notes.map((n, i) => <span key={i} className="sq-block sq-faint">{n.words}</span>)}
      <Steps id={r.id} errorWords={r.error_words} />
    </section>
  );
}

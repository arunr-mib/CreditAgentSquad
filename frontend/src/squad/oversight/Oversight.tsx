// frontend/src/squad/oversight/Oversight.tsx
import { Link, useParams } from '@tanstack/react-router';
import { useState } from 'react';
import { ApiError, errorMessage } from '@/api/client';
import { useAgentRun, useClock, useLedgerVerification, usePolicyRegister, useRolesAndPermissions, useSetClock } from '@/api/hooks';
import { useAuth } from '@/auth/context';
import { formatDate, formatFigure } from '@/design';
import { RUNS_PAGE, useBriefing, useEvaluation, useLedgerActions, useOversightAgents, useOversightLedger, useOversightRuns } from '../api/hooks';
import { useDocWords } from '../DocType';
import { threadHref } from '../links';
import { Time } from '../thread/Time';
import { describeEvent } from './describeEvent';

type Tab = 'activity' | 'ledger' | 'governance' | 'evaluations' | 'clock';
const TABS: Array<[Tab, string]> = [['activity', 'Agent activity'], ['ledger', 'Ledger'], ['governance', 'Governance'], ['evaluations', 'Evaluations'], ['clock', 'Clock']];
const PAGE = 100;
const count = (n: number | string) => formatFigure(String(n), 'count', { dp: 0 }).text;

function Steps({ id, error }: { id: string; error: string | null }) {
  const run = useAgentRun(id);
  if (!run.data) return <p role="status" className="sq-muted">Reading the steps.</p>;
  return (
    <div>
      {error ? <p role="alert" className="sq-block">The run failed: {error}</p> : null}
      {run.data.steps.length === 0 ? <p className="sq-muted">No steps were recorded for this run.</p> : (
        <ol className="sq-plainlist">
          {run.data.steps.map((s) => <li key={s.id}><span className="sq-mono">{s.n}</span> {s.kind} · {s.name}{s.input_summary ? ` · ${s.input_summary}` : ''}{s.refused ? ' · refused' : ''}</li>)}
        </ol>
      )}
    </div>
  );
}

function Activity() {
  const [offset, setOffset] = useState(0);
  const runs = useOversightRuns(offset);
  const [open, setOpen] = useState<string | null>(null);
  if (runs.isPending) return <p role="status" className="sq-muted">Reading agent activity.</p>;
  if (runs.error || !runs.data) return <p role="alert">Agent activity could not be loaded.</p>;
  if (runs.data.length === 0) return <p className="sq-muted">{offset === 0 ? 'No agent has run in this database yet.' : 'No older runs.'}</p>;
  return (
    <div>
      <div className="sq-tablewrap">
        <table className="sq-table" aria-label="Agent activity">
          <thead><tr><th scope="col">When</th><th scope="col">Agent</th><th scope="col">Client</th><th scope="col">Outcome</th><th scope="col">Checks</th><th scope="col" className="sq-num">Tool calls</th><th scope="col" className="sq-num">Tokens in / out</th></tr></thead>
          <tbody>
            {runs.data.map((r) => (
              <tr key={r.id}>
                <td><Time ts={r.created_at} /></td>
                <td>
                  {r.agent_label} · <span className="sq-faint">{r.task_label}</span>{' '}
                  <button type="button" className="sq-link" aria-expanded={open === r.id} aria-label={`Steps of ${r.agent_name} ${r.task}`} onClick={() => setOpen(open === r.id ? null : r.id)}>Steps</button>
                  {open === r.id ? <Steps id={r.id} error={r.error} /> : null}
                </td>
                <td>{r.borrower_code && r.borrower_name ? <Link {...threadHref(r.borrower_code)} className="sq-link">{r.borrower_name}</Link> : <span className="sq-faint">No client</span>}</td>
                <td>{r.status_label}</td>
                <td>{r.guardrail_notes.length === 0 ? <span className="sq-faint">None named</span> : r.guardrail_notes.map((n, i) => <span key={i} className="sq-block">{n.words}</span>)}</td>
                <td className="sq-num">{count(r.tool_calls)}</td>
                <td className="sq-num">{count(r.input_tokens)} / {count(r.output_tokens)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="sq-actions">
        {offset > 0 ? <button type="button" className="sq-btn" onClick={() => { setOffset(Math.max(0, offset - RUNS_PAGE)); setOpen(null); }}>Newer runs</button> : null}
        {runs.data.length >= RUNS_PAGE ? <button type="button" className="sq-btn" onClick={() => { setOffset(offset + RUNS_PAGE); setOpen(null); }}>Older runs</button> : null}
      </div>
    </div>
  );
}

function Ledger() {
  const words = useDocWords();
  const families = useLedgerActions();
  const [verify, setVerify] = useState(false);
  const [action, setAction] = useState('all');
  const [hideSignIns, setHideSignIns] = useState(true);
  const [before, setBefore] = useState<number | undefined>(undefined);
  const events = useOversightLedger({ limit: PAGE, hide_sign_ins: hideSignIns, ...(action !== 'all' ? { action } : {}), ...(before ? { before_seq: before } : {}) });
  const verification = useLedgerVerification(verify);
  const rows = events.data ?? [];
  const oldest = rows.at(-1)?.seq;
  const check = () => (verify ? void verification.refetch() : setVerify(true));
  return (
    <div>
      <div className="sq-actions">
        <label className="sq-field"><span aria-hidden>Action</span>
          <select className="sq-input" aria-label="Action" value={action} onChange={(e) => { setAction(e.target.value); setBefore(undefined); }}>
            <option value="all">Every action</option>
            {(families.data ?? []).map((f) => <option key={f.key} value={f.key}>{f.words}</option>)}
          </select>
        </label>
        <label className="sq-check-label"><input type="checkbox" checked={hideSignIns && action !== 'auth'} disabled={action === 'auth'} onChange={(e) => { setHideSignIns(e.target.checked); setBefore(undefined); }} /> Hide sign-ins</label>
        <button type="button" className="sq-btn" onClick={check} disabled={verification.isFetching}>Verify the chain</button>
      </div>
      {verification.isFetching ? <p role="status" className="sq-muted">Checking the chain.</p> : null}
      {!verification.isFetching && verification.error ? <p role="alert">The chain could not be checked. The server said: “{errorMessage(verification.error)}”</p> : null}
      {!verification.isFetching && !verification.error && verification.data ? <p role="status">{verification.data.ok ? `The chain verifies: ${count(verification.data.events_checked)} events checked.` : `The chain does not verify: ${verification.data.problem}`}</p> : null}
      {events.isPending ? <p role="status" className="sq-muted">Reading the ledger.</p> : events.error ? <p role="alert">The ledger could not be loaded.</p> : rows.length === 0 ? (
        <p className="sq-muted">{before ? 'No older events.' : 'No events match.'}</p>
      ) : (
        <ol className="sq-plainlist" aria-label="Ledger">
          {rows.map((e) => (
            <li key={e.seq}><span className="sq-mono">#{e.seq}</span> · <Time ts={e.ts} /> · <b>{e.actor_label}</b> · {e.action.replace(/[._]/g, ' ')}{describeEvent(e, words) ? ` · ${describeEvent(e, words)}` : ''}</li>
          ))}
        </ol>
      )}
      <div className="sq-actions">
        {before ? <button type="button" className="sq-btn" onClick={() => setBefore(undefined)}>Newest events</button> : null}
        {oldest && rows.length >= PAGE ? <button type="button" className="sq-btn" onClick={() => setBefore(oldest)}>Older events</button> : null}
      </div>
    </div>
  );
}

function Governance() {
  const roles = useRolesAndPermissions();
  const policy = usePolicyRegister();
  const agents = useOversightAgents();
  if (roles.isPending || policy.isPending) return <p role="status" className="sq-muted">Reading the rules.</p>;
  if (!roles.data || !policy.data) return <p role="alert">The rules could not be loaded.</p>;
  const { roles: list, permissions, grants, second_person } = roles.data;
  return (
    <div>
      <div className="sq-tablewrap">
        <table className="sq-table" aria-label="Who may do what">
          <thead><tr><th scope="col">Permission</th>{list.map((r) => <th key={r.id} scope="col">{r.label}</th>)}</tr></thead>
          <tbody>
            {permissions.map((p) => (
              <tr key={p.id}>
                <th scope="row">{p.label}{p.second_person ? <span className="sq-faint"> · second person</span> : null}</th>
                {list.map((r) => <td key={r.id}>{grants[r.id]?.includes(p.id) ? 'Yes' : <span className="sq-faint">No</span>}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>{second_person.rule}</p>
      {policy.data.sections.map((s) => (
        <section key={s.id} aria-label={s.title}>
          <h2 className="sq-h2">{s.title}</h2>
          <ul className="sq-plainlist">{s.rules.map((r) => <li key={r.id}><b>{r.rule}</b>: {r.setting} · <span className="sq-faint">{r.effect} ({r.source})</span></li>)}</ul>
        </section>
      ))}
      <h2 className="sq-h2">Signal rules · version {policy.data.signal_rules.version}</h2>
      <div className="sq-tablewrap">
        <table className="sq-table" aria-label="Signal rules">
          <thead><tr><th scope="col">Rule</th><th scope="col">Severity</th><th scope="col">Fires when</th></tr></thead>
          <tbody>{policy.data.signal_rules.rules.map((r) => <tr key={r.id}><th scope="row">{r.name}</th><td>{r.severity_label ?? r.severity}</td><td>{r.trigger}</td></tr>)}</tbody>
        </table>
      </div>
      <h2 className="sq-h2">Agents</h2>
      <div className="sq-tablewrap">
        <table className="sq-table" aria-label="Agents">
          <thead><tr><th scope="col">Agent</th><th scope="col">Purpose</th><th scope="col">Model</th><th scope="col" className="sq-num">Step cap</th><th scope="col" className="sq-num">Runs</th><th scope="col">Prompt</th></tr></thead>
          <tbody>
            {(agents.data ?? []).length === 0 ? <tr><td colSpan={6} className="sq-muted">No agent is registered yet.</td></tr> : null}
            {(agents.data ?? []).map((a) => (
              <tr key={a.id}><th scope="row">{a.label} v{a.version}</th><td>{a.purpose}</td><td className="sq-mono">{a.model}</td><td className="sq-num">{a.max_steps}</td><td className="sq-num">{a.runs}</td><td className="sq-mono">{a.prompt_sha256.slice(0, 12)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Evaluations() {
  const latest = useEvaluation();
  if (latest.isPending) return <p role="status" className="sq-muted">Reading the latest evaluation.</p>;
  if (latest.error) {
    return latest.error instanceof ApiError && latest.error.status === 404
      ? <p className="sq-muted">{errorMessage(latest.error)}</p>
      : <p role="alert">The evaluation could not be loaded. The server said: “{errorMessage(latest.error)}”</p>;
  }
  if (!latest.data) return <p className="sq-muted">No evaluation has been run in this database yet.</p>;
  const e = latest.data;
  const where = e.source === 'database' ? 'A run in this database' : 'From the repository file';
  const scope = [e.commit ? `commit ${e.commit}` : null, e.borrowers !== null ? `${e.borrowers} clients` : null].filter(Boolean).join(', ');
  return (
    <div>
      {e.notice ? <p className="sq-card">{e.notice}</p> : null}
      <p>{where}{scope ? `, ${scope}` : ''}{e.suite ? ` · suite ${e.suite}` : ''}</p>
      <p>Mode: {e.mode ?? 'unknown'} · gate {e.gate_passed === null ? 'not recorded' : e.gate_passed ? 'passed' : 'failed'}{e.created_at ? <> · <Time ts={e.created_at} /></> : null}</p>
      <table className="sq-table" aria-label="Evaluation measures">
        <tbody>
          {e.rows.map((r) => (
            <tr key={r.key}><th scope="row">{r.label}</th><td className="sq-num">{r.value === null ? <span className="sq-faint">Not measured</span> : formatFigure(r.value, r.unit === 'pct' ? 'pct' : 'count', { dp: r.unit === 'pct' ? 2 : 0 }).text}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Clock() {
  const clock = useClock(true);
  const set = useSetClock();
  const [day, setDay] = useState('');
  return (
    <form aria-label="The demonstration clock" onSubmit={(ev) => { ev.preventDefault(); if (day) set.mutate(day); }}>
      <p>The working date is {clock.data?.today ? formatDate(clock.data.today) : 'not known'}.</p>
      <label className="sq-field">Set the working date<input className="sq-input" type="date" value={day} onChange={(ev) => setDay(ev.target.value)} /></label>
      <button type="submit" className="sq-btn" disabled={!day || set.isPending}>Set the date</button>
      {set.error ? <p role="alert">The server said: “{errorMessage(set.error)}”</p> : null}
    </form>
  );
}

const NOT_YOURS = 'Oversight is for administrators, credit administration and credit review.';

/** Oversight for administrators, credit administration and credit review: what agents did, the ledger, the rules, the
 * evaluation. No credit decision is offered here. The server says who is offered Oversight (`briefing.oversight`) and
 * refuses the API to everyone else; this page keeps no list of roles. */
export function Oversight() {
  const { tab = 'activity' } = useParams({ strict: false }) as { tab?: string };
  const { can } = useAuth();
  const briefing = useBriefing();
  if (briefing.isPending) return <p role="status" className="sq-muted">Reading Oversight.</p>;
  if (!briefing.data?.oversight?.offered) return <p role="alert">{NOT_YOURS}</p>;
  const tabs = TABS.filter(([id]) => id !== 'clock' || can('advance_clock'));
  const current = tabs.find(([id]) => id === tab)?.[0];
  const body = { activity: <Activity />, ledger: <Ledger />, governance: <Governance />, evaluations: <Evaluations />, clock: <Clock /> };
  return (
    <div className="sq-oversight" data-ready="">
      <h1 className="sq-h1">Oversight</h1>
      <nav aria-label="Oversight" className="sq-tabs">
        {tabs.map(([id, label]) => id === 'activity'
          ? <Link key={id} to="/oversight" activeOptions={{ exact: true }} className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>
          : <Link key={id} to="/oversight/$tab" params={{ tab: id }} className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>)}
      </nav>
      {current ? body[current] : tab === 'clock' ? <p role="alert">The clock is for the administrator.</p> : <p role="alert">There is no such part of Oversight.</p>}
    </div>
  );
}

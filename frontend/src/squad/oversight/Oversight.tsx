// frontend/src/squad/oversight/Oversight.tsx
import { Link, useParams } from '@tanstack/react-router';
import { useState } from 'react';
import { errorMessage } from '@/api/client';
import { useAgentRun, useClock, useLedger, useLedgerVerification, usePolicyRegister, useRolesAndPermissions, useSetClock } from '@/api/hooks';
import { useAuth } from '@/auth/context';
import { formatFigure } from '@/design';
import { useEvaluation, useOversightAgents, useOversightRuns } from '../api/hooks';
import { useDocWords } from '../DocType';
import { threadHref } from '../links';
import { OVERSIGHT_ROLES } from '../shell/commands';
import { Time } from '../thread/Time';
import { describeEvent } from './describeEvent';

type Tab = 'activity' | 'ledger' | 'governance' | 'evaluations' | 'clock';
const TABS: Array<[Tab, string]> = [['activity', 'Agent activity'], ['ledger', 'Ledger'], ['governance', 'Governance'], ['evaluations', 'Evaluations'], ['clock', 'Clock']];
const ACTIONS = ['all', 'work_item', 'document', 'fact', 'cycle', 'copilot', 'draft', 'lesson', 'terms', 'clock', 'user'];
const PAGE = 100;

function Steps({ id }: { id: string }) {
  const run = useAgentRun(id);
  if (!run.data) return <p role="status" className="sq-muted">Reading the steps.</p>;
  return (
    <ol className="sq-plainlist">
      {run.data.steps.map((s) => <li key={s.id}><span className="sq-mono">{s.n}</span> {s.kind} · {s.name}{s.input_summary ? ` · ${s.input_summary}` : ''}{s.refused ? ' · refused' : ''}</li>)}
    </ol>
  );
}

function Activity() {
  const runs = useOversightRuns();
  const [open, setOpen] = useState<string | null>(null);
  if (runs.isPending) return <p role="status" className="sq-muted">Reading agent activity.</p>;
  if (runs.error || !runs.data) return <p role="alert">Agent activity could not be loaded.</p>;
  return (
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
                {open === r.id ? <Steps id={r.id} /> : null}
              </td>
              <td>{r.borrower_code && r.borrower_name ? <Link {...threadHref(r.borrower_code)} className="sq-link">{r.borrower_name}</Link> : <span className="sq-faint">No client</span>}</td>
              <td>{r.status_label}</td>
              <td>{r.guardrail_notes.length === 0 ? <span className="sq-faint">None named</span> : r.guardrail_notes.map((n, i) => <span key={i} className="sq-block">{n.words}</span>)}</td>
              <td className="sq-num">{r.steps_count}</td>
              <td className="sq-num">{r.input_tokens} / {r.output_tokens}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Ledger() {
  const words = useDocWords();
  const [verify, setVerify] = useState(false);
  const [action, setAction] = useState('all');
  const [hideSignIns, setHideSignIns] = useState(true);
  const [before, setBefore] = useState<number | undefined>(undefined);
  const events = useLedger({ limit: PAGE, ...(action !== 'all' ? { action } : {}), ...(before ? { before_seq: before } : {}) });
  const verification = useLedgerVerification(verify);
  const rows = (events.data ?? []).filter((e) => !(hideSignIns && e.action.startsWith('auth.')));
  const oldest = events.data?.at(-1)?.seq;
  return (
    <div>
      <div className="sq-actions">
        <label className="sq-field"><span aria-hidden>Action</span>
          <select className="sq-input" aria-label="Action" value={action} onChange={(e) => { setAction(e.target.value); setBefore(undefined); }}>
            {ACTIONS.map((a) => <option key={a} value={a}>{a === 'all' ? 'Every action' : a.replace(/_/g, ' ')}</option>)}
          </select>
        </label>
        <label className="sq-check-label"><input type="checkbox" checked={hideSignIns} onChange={(e) => setHideSignIns(e.target.checked)} /> Hide sign-ins</label>
        <button type="button" className="sq-btn" onClick={() => setVerify(true)} disabled={verification.isFetching}>Verify the chain</button>
      </div>
      {verification.data ? <p role="status">{verification.data.ok ? `The chain verifies: ${verification.data.events_checked} events checked.` : `The chain does not verify: ${verification.data.problem}`}</p> : null}
      {events.isPending ? <p role="status" className="sq-muted">Reading the ledger.</p> : (
        <ol className="sq-plainlist" aria-label="Ledger">
          {rows.map((e) => (
            <li key={e.seq}><span className="sq-mono">#{e.seq}</span> · <Time ts={e.ts} /> · <b>{e.actor_name ?? e.actor_type}</b> · {e.action.replace(/[._]/g, ' ')}{describeEvent(e, words) ? ` · ${describeEvent(e, words)}` : ''}</li>
          ))}
        </ol>
      )}
      <div className="sq-actions">
        {before ? <button type="button" className="sq-btn" onClick={() => setBefore(undefined)}>Newest events</button> : null}
        {oldest && (events.data?.length ?? 0) >= 1 ? <button type="button" className="sq-btn" onClick={() => setBefore(oldest)}>Older events</button> : null}
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
          <tbody>{policy.data.signal_rules.rules.map((r) => <tr key={r.id}><th scope="row">{r.name}</th><td>{r.severity}</td><td>{r.trigger}</td></tr>)}</tbody>
        </table>
      </div>
      <h2 className="sq-h2">Agents</h2>
      <div className="sq-tablewrap">
        <table className="sq-table" aria-label="Agents">
          <thead><tr><th scope="col">Agent</th><th scope="col">Purpose</th><th scope="col">Model</th><th scope="col" className="sq-num">Step cap</th><th scope="col" className="sq-num">Runs</th><th scope="col">Prompt</th></tr></thead>
          <tbody>
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
  if (latest.error || !latest.data) return <p className="sq-muted">No evaluation has been run in this database yet.</p>;
  const e = latest.data;
  return (
    <div>
      {e.notice ? <p className="sq-card">{e.notice}</p> : null}
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
      <p>The working date is {clock.data?.today ?? 'not known'}.</p>
      <label className="sq-field">Set the working date<input className="sq-input" type="date" value={day} onChange={(ev) => setDay(ev.target.value)} /></label>
      <button type="submit" className="sq-btn" disabled={!day || set.isPending}>Set the date</button>
      {set.error ? <p role="alert">The server said: “{errorMessage(set.error)}”</p> : null}
    </form>
  );
}

/** Oversight for administrators, credit administration and credit review: what agents did, the ledger, the rules, the
 * evaluation. No credit decision is offered here. The API refuses what a role may not read; this page also says so. */
export function Oversight() {
  const { tab = 'activity' } = useParams({ strict: false }) as { tab?: string };
  const { user, can } = useAuth();
  if (!OVERSIGHT_ROLES.includes(user?.role ?? '')) return <p role="alert">Oversight is for administrators, credit administration and credit review.</p>;
  const tabs = TABS.filter(([id]) => id !== 'clock' || can('advance_clock'));
  const current = tabs.find(([id]) => id === tab)?.[0];
  const body = { activity: <Activity />, ledger: <Ledger />, governance: <Governance />, evaluations: <Evaluations />, clock: <Clock /> };
  return (
    <div className="sq-oversight" data-ready="">
      <h1 className="sq-h1">Oversight</h1>
      <nav aria-label="Oversight" className="sq-tabs">
        {tabs.map(([id, label]) => id === 'activity'
          ? <Link key={id} to="/oversight" className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>
          : <Link key={id} to="/oversight/$tab" params={{ tab: id }} className="sq-tab" aria-current={id === current ? 'page' : undefined}>{label}</Link>)}
      </nav>
      {current ? body[current] : <p role="alert">There is no such part of Oversight.</p>}
    </div>
  );
}

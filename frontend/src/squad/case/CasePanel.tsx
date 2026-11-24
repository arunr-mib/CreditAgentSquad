import { useId, useState } from 'react';
import { ApiError, errorMessage } from '@/api/client';
import { word } from '@/api/words';
import { useWorkItem } from '@/api/hooks';
import { HeldFigures } from '@/squad/case/HeldFigures';
import { KeyFigures } from '@/squad/case/KeyFigures';
import { Evidence as ItemEvidence, Recommendation, RelatedItems } from '@/squad/case/parts';
import { useSource } from '@/source/context';
import { useAttachEvidence, useCase, useDecideCase, useDocumentTypeWords, useReturnCase, useRouteCase, type CopilotReply } from '../api/hooks';
import type { CaseNeed, CaseView, NeedInput } from '../api/types';
import { usePresence } from '../presence/Presence';
import { AskReply } from '../thread/AskReply';
import { Composer } from '../thread/Composer';
import { Time } from '../thread/Time';

const HELD = new Set(['spread.value_unverified', 'spread.does_not_foot']);

/** The server's refusal in its own words, titled by what it means. A second-person refusal is shown, never pre-empted.
 * A 409 is a second-person rule, a case that cannot be sent yet or an assignment, so it is titled neutrally and the
 * server's words say which; a 403 is the engine saying this person may not (their role, or a client that is not theirs). */
export function refusal(error: unknown): { title: string; text: string } {
  const text = errorMessage(error);
  if (error instanceof ApiError && error.status === 403) return { title: 'Not recorded: this is not yours to do', text };
  return { title: 'Not recorded', text };
}

function Refused({ error }: { error: unknown }) {
  if (!error) return null;
  const r = refusal(error);
  return (
    <div role="alert" className="sq-refusal">
      <b>{r.title}</b>
      <p>The server said: “{r.text}”</p>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const id = useId();
  return (
    <div className="sq-field">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} rows={3} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

const MAX_NEEDS = 5;
/** "2026-09" (a month picker's value) to the last day of that month, the period a need names. */
const monthEnd = (month: string): string => {
  const [y, m] = month.split('-').map(Number);
  return new Date(Date.UTC(y!, m!, 0)).toISOString().slice(0, 10);
};
const needLine = (n: CaseNeed) => (n.state === 'attached' ? n.state_words : `${n.words}: ${n.state_words}`);

function NeedsList({ needs, label, only }: { needs: CaseNeed[]; label: string; only?: (n: CaseNeed) => boolean }) {
  const shown = only ? needs.filter(only) : needs;
  if (shown.length === 0) return null;
  return (
    <ul className="sq-plainlist" aria-label={label}>
      {shown.map((n) => <li key={n.index}>{needLine(n)}</li>)}
    </ul>
  );
}

function DecideForm({ c }: { c: CaseView }) {
  const decide = useDecideCase(c.work_item_id);
  const { say } = usePresence();
  const [choice, setChoice] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState<unknown>(null);
  const picked = c.decisions.find((d) => d.id === choice);
  const ready = Boolean(picked) && (!picked?.needs_reason || reason.trim().length > 0);
  async function submit() {
    setError(null);
    try {
      await decide.mutateAsync({ decision: choice, reason: reason.trim() });
      say(`${picked?.label ?? 'Decision'} · recorded`);
    } catch (e) {
      setError(e);
    }
  }
  return (
    <form className="sq-caseform" aria-label="Record a decision" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <fieldset className="sq-options">
        <legend>Your decision</legend>
        {c.decisions.filter((d) => d.permitted).map((d) => (
          <label key={d.id} className="sq-option">
            <input type="radio" name={`decision-${c.work_item_id}`} value={d.id} checked={choice === d.id} onChange={() => setChoice(d.id)} />
            <span>{d.label}{d.hint ? <span className="sq-faint sq-block">{d.hint}</span> : null}</span>
          </label>
        ))}
      </fieldset>
      <Field label={picked?.needs_reason ? 'Reason (required)' : 'Reason'} value={reason} onChange={setReason} />
      <Refused error={error} />
      <button type="submit" className="sq-btn sq-btn-primary" disabled={!ready || decide.isPending}>Record decision</button>
      {c.requires_second_person ? <p className="sq-faint">Two people: whoever prepared or routed this case cannot decide it.</p> : null}
    </form>
  );
}

function RouteForm({ c }: { c: CaseView }) {
  const route = useRouteCase(c.work_item_id);
  const { say } = usePresence();
  const [picked, setTo] = useState('');
  const [view, setView] = useState('');
  const [error, setError] = useState<unknown>(null);
  // with several people who may decide nobody is preselected: the analyst chooses; with exactly one it is that person
  const to = c.route_to.length === 1 ? (c.route_to[0]?.id ?? '') : picked;
  const person = c.route_to.find((p) => p.id === to);
  async function submit() {
    setError(null);
    try {
      await route.mutateAsync({ to, view: view.trim() });
      say(`Sent to ${person?.name ?? 'them'} with your view · recorded`);
      setView('');
    } catch (e) {
      setError(e);
    }
  }
  return (
    <form className="sq-caseform" aria-label="Send for a decision" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      {c.route_to.length > 1 ? (
        <label className="sq-field">
          Send to
          <select className="sq-input" value={to} onChange={(e) => setTo(e.target.value)}>
            <option value="" disabled>Choose who decides</option>
            {c.route_to.map((p) => <option key={p.id} value={p.id}>{p.name}, {p.title}</option>)}
          </select>
        </label>
      ) : null}
      <NeedsList needs={c.needs} label="Still asked of the client" only={(n) => n.state !== 'attached'} />
      <Field label="Your view (required): what you found and what you recommend" value={view} onChange={setView} />
      <Refused error={error} />
      <button type="submit" className="sq-btn" disabled={!view.trim() || !person || route.isPending}>{person ? `Send to ${person.name}` : 'Choose who decides'}</button>
    </form>
  );
}

function ReturnForm({ c }: { c: CaseView }) {
  const ret = useReturnCase(c.work_item_id);
  const { say } = usePresence();
  const words = useDocumentTypeWords().data;
  const [reason, setReason] = useState('');
  const [rows, setRows] = useState<Array<{ doc_type: string; month: string }>>([]);
  const [error, setError] = useState<unknown>(null);
  const who = c.view?.by ?? 'the person who sent it';
  // only the types a document can have, as the server serves them, in the server's words
  const choices = (words?.needable ?? []).map((key) => [key, words?.types[key] ?? key] as const);
  const change = (i: number, part: Partial<{ doc_type: string; month: string }>) => setRows((r) => r.map((row, j) => (j === i ? { ...row, ...part } : row)));
  const complete = rows.every((r) => r.doc_type && /^\d{4}-\d{2}$/.test(r.month));
  async function submit() {
    setError(null);
    try {
      const needs: NeedInput[] = rows.map((r) => ({ doc_type: r.doc_type, period_end: monthEnd(r.month) }));
      await ret.mutateAsync(needs.length > 0 ? { reason: reason.trim(), needs } : { reason: reason.trim() });
      say(`Returned to ${who} · recorded`);
    } catch (e) {
      setError(e);
    }
  }
  return (
    <form className="sq-caseform" aria-label="Return the case" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <Field label="What is missing, or what you want done (required)" value={reason} onChange={setReason} />
      <fieldset className="sq-needs">
        <legend>What is needed (optional): Squad gathers these and asks you only if it is not sure</legend>
        {rows.map((r, i) => (
          <div key={i} className="sq-need-row">
            <select className="sq-input" aria-label={`Document type ${i + 1}`} value={r.doc_type} onChange={(e) => change(i, { doc_type: e.target.value })}>
              <option value="" disabled>Document type</option>
              {choices.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
            <input className="sq-input" type="month" aria-label={`Month ${i + 1}`} value={r.month} onChange={(e) => change(i, { month: e.target.value })} />
            <button type="button" className="sq-btn" aria-label={`Remove need ${i + 1}`} onClick={() => setRows((all) => all.filter((_, j) => j !== i))}>Remove</button>
          </div>
        ))}
        <button type="button" className="sq-btn" disabled={rows.length >= MAX_NEEDS} onClick={() => setRows((all) => [...all, { doc_type: '', month: '' }])}>Add something that is needed</button>
      </fieldset>
      <Refused error={error} />
      <button type="submit" className="sq-btn" disabled={!reason.trim() || !complete || ret.isPending}>Return to {who}</button>
    </form>
  );
}

function Attachments({ c }: { c: CaseView }) {
  const source = useSource();
  const attach = useAttachEvidence(c.work_item_id);
  const { say } = usePresence();
  const [error, setError] = useState<unknown>(null);
  const open = (documentId: string, title: string) => source.open({ type: 'document', documentId, page: 1, title, borrowerCode: c.borrower.code });
  return (
    <>
      {c.attached.length > 0 ? (
        <ul className="sq-plainlist" aria-label="Attached to this case">
          {c.attached.map((a) => (
            <li key={a.document_id}>
              <button type="button" className="sq-link" aria-label={`Open ${a.title}`} onClick={() => open(a.document_id, a.title)}>{a.title}</button>
              {a.note ? <span className="sq-faint"> · {a.note}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {c.may_attach && c.status === 'open' && c.candidates.length > 0 ? (
        <details className="sq-candidates">
          <summary>Squad found {c.candidates.length === 1 ? '1 document' : `${c.candidates.length} documents`} on file you can attach</summary>
          <ul className="sq-plainlist">
            {c.candidates.map((d) => (
              <li key={d.document_id}>
                <button type="button" className="sq-link" aria-label={`Open ${d.title}`} onClick={() => open(d.document_id, d.title)}>{d.title}</button>{' '}
                <button type="button" className="sq-btn" aria-label={`Attach ${d.title}`} disabled={attach.isPending}
                  onClick={() => void attach.mutateAsync({ document_id: d.document_id }).then(() => say(`${d.title} attached · recorded`), setError)}>Attach</button>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <Refused error={error} />
    </>
  );
}

function History({ c }: { c: CaseView }) {
  if (c.history.length === 0) return null;
  return (
    <ol className="sq-plainlist sq-faint" aria-label="What happened to this case">
      {c.history.map((h) => (
        <li key={h.seq}>{h.by} {word('case_history', h.kind).toLowerCase()}{h.kind === 'evidence_attached' ? '' : ` ${h.to ?? ''}`} · <Time ts={h.at} /></li>
      ))}
    </ol>
  );
}

/** One case, in place in the thread or beside the Approvals list: the router's view, the evidence (each row opens its
 * source), what the agent recommended or that it recommended nothing, open questions that may change the result, and
 * only the actions the server allows this person. `onOpenCase` opens a related case where the panel is shown. */
export function CasePanel({ workItemId, onOpenCase }: { workItemId: string; onOpenCase: (id: string) => void }) {
  const q = useCase(workItemId);
  const detail = useWorkItem(workItemId);
  const [answer, setAnswer] = useState<CopilotReply | null>(null);
  if (q.isPending) return <p role="status" className="sq-muted">Opening the case.</p>;
  if (q.error || !q.data)
    return (
      <div role="alert">
        <p>The case could not be loaded.</p>
        <button type="button" className="sq-btn" onClick={() => void q.refetch()}>Try again</button>
      </div>
    );
  const c = q.data;
  const decides = c.status === 'open' && c.decisions.some((d) => d.permitted);
  return (
    <section className="sq-case" aria-label={`Case: ${c.title}`} data-case={c.work_item_id} data-item-status={c.status}>
      {c.view ? (
        <figure className="sq-view">
          <figcaption className="sq-faint">{c.view.by}’s view · <Time ts={c.view.at} /></figcaption>
          <blockquote className="sq-quote">{c.view.text}</blockquote>
        </figure>
      ) : null}
      <History c={c} />
      <NeedsList needs={c.needs} label="What was asked for" />
      {detail.data ? <KeyFigures item={detail.data} /> : null}
      {detail.data ? <ItemEvidence item={detail.data} code={c.borrower.code} headingLevel="h4" /> : null}
      {detail.data && HELD.has(c.item_type) ? <HeldFigures item={detail.data} code={c.borrower.code} headingLevel="h4" mayRepair={c.may_repair} /> : null}
      {detail.data?.recommendation ? (
        <Recommendation recommendation={detail.data.recommendation} item={detail.data} headingLevel="h4" code={c.borrower.code} />
      ) : c.status === 'open' && detail.data ? (
        <p className="sq-muted">No agent recommendation is attached. The evidence above was produced by code.{decides ? ' The decision is yours.' : ''}</p>
      ) : null}
      {detail.data && c.status === 'open' ? (
        <RelatedItems items={(detail.data.related_items ?? []).filter((r) => r.id !== c.work_item_id && r.status === 'open')} headingLevel="h4" onOpen={onOpenCase} />
      ) : null}
      <Attachments c={c} />
      {c.status !== 'open' ? (
        <p><b>{c.decided_by ?? 'A person'}: {c.decision_words}</b>{c.decision_reason ? ` · “${c.decision_reason}”` : ''}</p>
      ) : (
        <>
          {decides ? <DecideForm c={c} /> : null}
          {c.may_return ? <ReturnForm c={c} /> : null}
          {c.may_route ? <RouteForm c={c} /> : null}
          {!c.may_route && c.route_blocked_words ? <p className="sq-muted">{c.route_blocked_words} before the case is sent.</p> : null}
          {!decides && !c.may_route && !c.may_return ? <p className="sq-muted">{c.state_words}. This case is not yours to decide.</p> : null}
          <details className="sq-group">
            <summary>Ask Squad about this case</summary>
            <Composer borrowerId={c.borrower.id} workItemId={c.work_item_id} label="Ask Squad about this case" onReply={setAnswer} />
            {answer ? <AskReply reply={answer} /> : null}
          </details>
        </>
      )}
    </section>
  );
}

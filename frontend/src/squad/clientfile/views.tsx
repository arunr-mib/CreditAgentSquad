// frontend/src/squad/clientfile/views.tsx
import { Link, useRouterState, useSearch } from '@tanstack/react-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  useActions, useBorrowerCovenants, useBorrowerOverview, useBorrowerTerms, useDocuments, useFactsById,
  useReviewSheet, useReviewSheets, useSignals, useSpread, useTimeline,
} from '@/api/hooks';
import type { BorrowerRow, FactSummary } from '@/api/schema';
import { word } from '@/api/words';
import { useAuth } from '@/auth/context';
import { formatDate } from '@/design';
import { outcomeOf } from '@/domain/labels';
import { RunStage } from '@/squad/clientfile/RunStage';
import { UploadDocument } from '@/squad/clientfile/UploadDocument';
import { Commentary } from '@/squad/clientfile/review/Commentary';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import { Absent, FactFigure, SourcedFigure } from '@/source/figures';
import { useDocumentTypeWords, useFundingEvents, useLessons, useMeasure, useTrackRecord } from '../api/hooks';
import { DocType, useSignalWords } from '../DocType';
import { Time } from '../thread/Time';
import { BorrowingBase } from './BorrowingBase';
import { MeasureNow, TrendBars } from './Measure';

type Props = { borrower: BorrowerRow };

function Loading({ what }: { what: string }) {
  return <p role="status" className="sq-muted">Reading {what}.</p>;
}
function Failed({ what }: { what: string }) {
  return <p role="alert">{what} could not be loaded. Try again in a moment.</p>;
}

export function Overview({ borrower }: Props) {
  const overview = useBorrowerOverview(borrower.id);
  const measure = useMeasure(borrower.id);
  const signals = useSignals({ borrower_id: borrower.id });
  const signalWords = useSignalWords();
  const track = useTrackRecord(borrower.id);
  const lessons = useLessons(borrower.id);
  if (overview.isPending) return <Loading what="the overview" />;
  if (overview.error || !overview.data) return <Failed what="The overview" />;
  const { exposure, cycle } = overview.data;
  return (
    <div className="sq-filegrid">
      <section className="sq-card" aria-label="Exposure">
        <h2 className="sq-h2">Exposure</h2>
        {Object.keys(exposure).length === 0 ? <p className="sq-muted">No exposure figure is stored for this client.</p> : (
          <dl className="sq-defs">
            {Object.entries(exposure).map(([key, fact]) => (
              <div key={key}><dt>{fact?.label ?? key}</dt><dd>{fact ? <FactFigure fact={fact} /> : <Absent />}</dd></div>
            ))}
          </dl>
        )}
      </section>
      <section className="sq-card" aria-label={measure.data?.label ?? 'Measure'} data-measure>
        <h2 className="sq-h2">{measure.data?.label ?? 'Measure'}</h2>
        {measure.data ? (
          <>
            <span data-measure-now><MeasureNow series={measure.data} /></span>
            <TrendBars points={measure.data.points} label={measure.data.label} />
          </>
        ) : <Loading what="the measure" />}
      </section>
      <section className="sq-card" aria-label="This cycle">
        <h2 className="sq-h2">This cycle</h2>
        {cycle ? (
          <>
            <p>Period ended {formatDate(cycle.period_end)} · {cycle.status === 'closed' ? 'closed' : `at ${(cycle.stage_label ?? cycle.stage).toLowerCase()}`}</p>
            {cycle.status !== 'closed' ? <RunStage cycle={cycle} code={borrower.code} /> : null}
          </>
        ) : <p className="sq-muted">No cycle has been opened for this client yet.</p>}
      </section>
      <section className="sq-card" aria-label="Signals">
        <h2 className="sq-h2">Signals</h2>
        {(signals.data ?? []).length === 0 ? <p className="sq-muted">No open signal.</p> : (
          <ul className="sq-plainlist">
            {(signals.data ?? []).map((s) => <li key={s.id}><span className={`sq-dotmark sq-sev-${s.severity}`} aria-hidden /> {signalWords(s.rule_id)} · <span className="sq-faint">{formatDate(s.period_end)}</span>{s.explanation?.text ? <AgentBody text={s.explanation.text} /> : null}</li>)}
          </ul>
        )}
      </section>
      <section className="sq-card" aria-label="Track record">
        <h2 className="sq-h2">Track record</h2>
        {(track.data ?? []).length === 0 ? <p className="sq-muted">No figure has been read for this client yet.</p> : (
          <table className="sq-table">
            <thead><tr><th scope="col">Task</th><th scope="col" className="sq-num">Checked</th><th scope="col" className="sq-num">Right</th><th scope="col" className="sq-num">Corrected</th><th scope="col" className="sq-num">Not yet reviewed</th><th scope="col">Last correction</th></tr></thead>
            <tbody>
              {(track.data ?? []).map((t) => (
                <tr key={`${t.agent_name}|${t.task}`}>
                  <th scope="row">{t.agent_label} · {t.task_label} <span className="sq-faint">since {formatDate(t.since)}</span></th>
                  <td className="sq-num">{t.checked}</td><td className="sq-num">{t.right}</td><td className="sq-num">{t.corrected}</td><td className="sq-num">{t.unreviewed}</td>
                  <td>{t.last_correction_at ? formatDate(t.last_correction_at) : <span className="sq-faint">None</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section className="sq-card" aria-label="What Squad remembers">
        <h2 className="sq-h2">What Squad remembers</h2>
        {(lessons.data ?? []).length === 0 ? <p className="sq-muted">Nothing has been taught for this client yet.</p> : (
          <ul className="sq-plainlist">{(lessons.data ?? []).map((l) => <li key={l.id}>{l.text} <span className="sq-faint">· {l.by}, <Time ts={l.at} /></span></li>)}</ul>
        )}
      </section>
    </div>
  );
}

export function Spreads({ borrower }: Props) {
  const spread = useSpread(borrower.id);
  const periods = useMemo(() => (spread.data?.periods ?? []).slice(-6), [spread.data]);
  const ids = useMemo(() => (spread.data?.lines ?? []).flatMap((l) => periods.map((p) => l.cells[p.period_end]?.fact_id)), [spread.data, periods]);
  const facts = useFactsById(ids);
  if (spread.isPending) return <Loading what="the spread" />;
  if (spread.error || !spread.data) return <Failed what="The spread" />;
  const lines = spread.data.lines.filter((l) => periods.some((p) => l.cells[p.period_end]));
  if (lines.length === 0) return <p className="sq-muted">Nothing has been spread for this client yet.</p>;
  return (
    <div className="sq-tablewrap">
      <table className="sq-table" aria-label="Spread">
        <thead><tr><th scope="col">Line</th>{periods.map((p) => <th key={p.period_end} scope="col" className="sq-num">{formatDate(p.period_end)}{p.months ? ` · ${p.months} mo` : ''}</th>)}</tr></thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.key}>
              <th scope="row">{l.label}</th>
              {periods.map((p) => {
                const cell = l.cells[p.period_end];
                const fact: FactSummary | undefined = cell ? facts.data?.[cell.fact_id] : undefined;
                return <td key={p.period_end} className="sq-num">{cell ? (fact ? <FactFigure fact={fact} align="column" /> : <span className="sq-faint">Reading</span>) : <Absent align="column" />}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Covenants({ borrower }: Props) {
  const covenants = useBorrowerCovenants(borrower.id);
  const noteWords = useDocumentTypeWords().data?.notes ?? {};
  if (covenants.isPending) return <Loading what="the covenants" />;
  if (covenants.error || !covenants.data) return <Failed what="The covenants" />;
  const { tests, facts } = covenants.data;
  const latest = tests[0]?.period_end ?? null;
  const current = tests.filter((t) => t.period_end === latest);
  if (current.length === 0) return <p className="sq-muted">No covenant has been tested for this client yet.</p>;
  return (
    <div className="sq-tablewrap">
      <p className="sq-faint">Tested for the period ended {formatDate(latest as string)}</p>
      <table className="sq-table" aria-label="Covenants">
        <thead><tr><th scope="col">Covenant</th><th scope="col" className="sq-num">Value</th><th scope="col" className="sq-num">Reported</th><th scope="col" className="sq-num">Limit</th><th scope="col" className="sq-num">Headroom</th><th scope="col">Outcome</th></tr></thead>
        <tbody>
          {current.map((t) => {
            const note = t.note ? (noteWords[t.note] ?? t.note.replace(/_/g, ' ')) : null;
            return (
              <tr key={t.id}>
                <th scope="row">{t.covenant_name}{t.terms_version ? <span className="sq-faint"> · terms v{t.terms_version.version}</span> : null}</th>
                <td className="sq-num">{t.value_fact_id && facts[t.value_fact_id] ? <FactFigure fact={facts[t.value_fact_id]} align="column" /> : <Absent align="column" reason={note ?? 'Not measured'} />}</td>
                <td className="sq-num">{t.reported_fact_id && facts[t.reported_fact_id] ? <FactFigure fact={facts[t.reported_fact_id]} align="column" /> : <Absent align="column" reason="Not reported" />}</td>
                <td className="sq-num">{t.threshold_fact_id && facts[t.threshold_fact_id] ? <FactFigure fact={facts[t.threshold_fact_id]} align="column" /> : <Absent align="column" />}</td>
                <td className="sq-num">{t.headroom_fact_id && facts[t.headroom_fact_id] ? <FactFigure fact={facts[t.headroom_fact_id]} align="column" /> : <Absent align="column" />}</td>
                <td>{['breach', 'breach_reported_compliant'].includes(t.outcome) ? <span className="sq-tag sq-tag-breach">{outcomeOf(t.outcome).label}</span> : outcomeOf(t.outcome).label}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {(() => {
        const periods = [...new Set(tests.map((t) => t.period_end))].filter((p) => p !== latest).sort().reverse().slice(0, 6);
        if (periods.length === 0) return null;
        const names = [...new Set(tests.map((t) => t.covenant_name))];
        return (
          <>
            <h2 className="sq-h2">Earlier periods</h2>
            <table className="sq-table" aria-label="Earlier periods">
              <thead><tr><th scope="col">Covenant</th>{periods.map((p) => <th key={p} scope="col">{formatDate(p)}</th>)}</tr></thead>
              <tbody>
                {names.map((name) => (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    {periods.map((p) => {
                      const t = tests.find((x) => x.covenant_name === name && x.period_end === p);
                      return <td key={p}>{t ? outcomeOf(t.outcome).label : <span className="sq-faint">Not tested</span>}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        );
      })()}
    </div>
  );
}

export function Documents({ borrower }: Props) {
  const documents = useDocuments(borrower.id);
  const { can } = useAuth();
  const source = useSource();
  const search = useSearch({ strict: false }) as { document?: string; page?: number; quote?: string };
  const opened = useRef<string | undefined>(undefined);
  const nav = useRouterState({ select: (s) => (s.location.state as { visit?: number }).visit }); // the drawer's link stamps each visit, so a second click on the same address opens it again
  const [uploading, setUploading] = useState(false);
  const rows = useMemo(() => documents.data ?? [], [documents.data]);
  useEffect(() => {
    const doc = rows.find((d) => d.id === search.document);
    const visit = `${doc?.id}|${nav}`;
    if (!doc || opened.current === visit) return;
    opened.current = visit;
    source.open({ type: 'document', documentId: doc.id, page: search.page ?? 1, quote: search.quote ?? null, title: doc.title, borrowerCode: borrower.code });
  }, [rows, search.document, search.page, search.quote, source, borrower.code, nav]);
  if (documents.isPending) return <Loading what="the documents" />;
  if (documents.error) return <Failed what="The documents" />;
  const missing = Boolean(search.document) && !rows.some((d) => d.id === search.document);
  return (
    <div>
      {missing ? <p role="alert">That document is not on file for this client.</p> : null}
      {can('upload_document') ? <button type="button" className="sq-btn" onClick={() => setUploading((u) => !u)} aria-expanded={uploading}>File a document</button> : null}
      {uploading && can('upload_document') ? <UploadDocument borrowerId={borrower.id} code={borrower.code} onClose={() => setUploading(false)} /> : null}
      {rows.length === 0 ? <p className="sq-muted">No document is on file for this client.</p> : (
        <div className="sq-tablewrap"><table className="sq-table" aria-label="Documents">
          <thead><tr><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Period</th><th scope="col">Received</th></tr></thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <th scope="row"><button type="button" className="sq-link" aria-label={`Open ${d.title}`} onClick={() => source.open({ type: 'document', documentId: d.id, page: 1, title: d.title, borrowerCode: borrower.code })}>{d.title}</button>{d.status === 'rejected' ? <span className="sq-faint"> · set aside</span> : null}</th>
                <td><DocType type={d.doc_type} /></td>
                <td>{d.period_end ? formatDate(d.period_end) : <span className="sq-faint">None</span>}</td>
                <td>{d.received_date ? formatDate(d.received_date) : <span className="sq-faint">Not recorded</span>}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </div>
  );
}

const fundingKind = (kind: string) => word('funding_kinds', kind);

export function Funding({ borrower }: Props) {
  const events = useFundingEvents(borrower.id);
  if (events.isPending) return <Loading what="the funding events" />;
  if (events.error || !events.data) return <Failed what="The funding events" />;
  if (events.data.length === 0) return <p className="sq-muted">No funding event is recorded for this client.</p>;
  return (
    <div className="sq-tablewrap"><table className="sq-table" aria-label="Funding events">
      <thead><tr><th scope="col">Event</th><th scope="col" className="sq-num">Amount</th><th scope="col">Expected close</th><th scope="col">Status</th></tr></thead>
      <tbody>
        {events.data.map((e) => (
          <tr key={e.id}>
            <th scope="row">{fundingKind(e.kind)}</th>
            <td className="sq-num">
              <SourcedFigure value={e.amount} unit="usd" kind="manual" label={`${fundingKind(e.kind)} amount`} align="column"
                source={{ type: 'record', kind: 'manual', title: 'Funding event', value: e.amount, rows: [['Kind', fundingKind(e.kind)], ['Expected close', formatDate(e.expected_close)], ['Status', e.status]], note: 'Recorded by a person on the funding event; not read from a document.' }} />
            </td>
            <td>{formatDate(e.expected_close)}</td>
            <td>{e.status === 'slipped' ? <span className="sq-tag sq-tag-attention">Slipped</span> : e.status}</td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}

export function Loans({ borrower }: Props) {
  const terms = useBorrowerTerms(borrower.id);
  if (terms.isPending) return <Loading what="the loans" />;
  if (terms.error || !terms.data) return <Failed what="The loans" />;
  return (
    <div className="sq-filegrid">
      {terms.data.map((loan) => (
        <section key={loan.id} className="sq-card" aria-label={loan.name}>
          <h2 className="sq-h2">{loan.name}</h2>
          <p>
            Commitment{' '}
            <SourcedFigure value={loan.commitment} unit="usd" kind="system" label={`${loan.name} commitment`}
              source={{ type: 'record', kind: 'system', title: loan.name, value: loan.commitment, rows: [['Loan', loan.code], ['Type', loan.facility_type.replace('_', ' ')]], note: 'From the loan record.' }} />
          </p>
          <ul className="sq-plainlist">
            {loan.terms_versions.map((v) => (
              <li key={v.id}>Terms v{v.version} · {v.in_force ? 'in force' : v.status}{v.approved_by_name ? ` · approved by ${v.approved_by_name}` : ''} · {v.covenants.map((c) => c.name).join(', ')}</li>
            ))}
          </ul>
        </section>
      ))}
      <BorrowingBase borrower={borrower} />
    </div>
  );
}

export function Reviews({ borrower }: Props) {
  const sheets = useReviewSheets({ borrower_id: borrower.id });
  const actions = useActions({ status: 'all', borrower_id: borrower.id });
  const [open, setOpen] = useState<string | null>(null);
  const sheet = useReviewSheet(open);
  if (sheets.isPending) return <Loading what="the reviews" />;
  if (sheets.error || !sheets.data) return <Failed what="The reviews" />;
  return (
    <div>
      {sheets.data.length === 0 ? <p className="sq-muted">No review sheet has been prepared. One is built when the cycle reaches review preparation.</p> : (
        <ul className="sq-plainlist" aria-label="Review sheets">
          {sheets.data.map((s) => (
            <li key={s.id}><button type="button" className="sq-link" aria-expanded={open === s.id} onClick={() => setOpen(open === s.id ? null : s.id)}>Review for the period ended {formatDate(s.period_end)}</button> · <span className="sq-faint">{s.status === 'draft' ? 'draft, not yet approved' : s.status}</span> · <Link to="/review-room" search={{ sheet: s.id }} className="sq-link">Open in the review room</Link></li>
          ))}
        </ul>
      )}
      {open && sheet.data ? <Commentary sheet={sheet.data} /> : null}
      <h2 className="sq-h2">Actions</h2>
      {(actions.data ?? []).length === 0 ? <p className="sq-muted">No action has been raised for this client.</p> : (
        <ul className="sq-plainlist">{(actions.data ?? []).map((a) => <li key={a.id}>{a.title} · <span className="sq-faint">{a.owner_name ?? 'No owner'}{a.due_date ? ` · due ${formatDate(a.due_date)}` : ''}</span></li>)}</ul>
      )}
    </div>
  );
}

export function History({ borrower }: Props) {
  const [routine, setRoutine] = useState(false);
  const timeline = useTimeline(borrower.id, routine);
  return (
    <>
      <label className="sq-option"><input type="checkbox" checked={routine} onChange={(e) => setRoutine(e.target.checked)} /> <span>Include routine events (received, overdue, stage changes)</span></label>
      {timeline.isPending ? <Loading what="the history" /> : timeline.error || !timeline.data ? <Failed what="The history" /> : timeline.data.length === 0 ? (
        <p className="sq-muted">Nothing has been recorded for this client yet.</p>
      ) : (
        <ol className="sq-plainlist" aria-label="History">
          {timeline.data.map((e) => (
            <li key={e.seq}><Time ts={e.ts} /> · <b>{e.actor_label ?? e.actor_name ?? e.actor_type}</b> · {e.action_label ?? e.action}{e.summary ? ` · ${e.summary}` : ''}</li>
          ))}
        </ol>
      )}
    </>
  );
}


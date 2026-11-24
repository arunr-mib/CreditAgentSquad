import { Link } from '@tanstack/react-router';
import { ArrowUpRight } from 'lucide-react';
import { useId, type ReactNode } from 'react';
import { useDocuments, useFactsById } from '@/api/hooks';
import type { ApiRecommendation, RelatedItem, WorkItemDetail } from '@/api/schema';
import { word } from '@/api/words';
import type { ProvenanceKind } from '@/api/types';
import { AgentNote, formatDate, GuardrailNotes, ProvenanceGlyph, Quote, Skeleton, StatusDot } from '@/design';
import { humanize } from '@/domain/labels';
import { AgentBody } from '@/source/AgentBody';
import { useSource } from '@/source/context';
import { FactFigure, SourcedFigure } from '@/source/figures';
import { useDocWords, useSignalWords } from '../DocType';
import { clientFile } from '../links';

const text = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);

/* ── Evidence ─────────────────────────────────────────────────────────── */

function EvidenceRow({
  kind,
  label,
  detail,
  reference,
  name,
  children,
}: {
  kind: ProvenanceKind;
  label: string;
  detail?: string | null;
  reference?: string | null;
  name?: string;
  children: ReactNode;
}) {
  return (
    <li className="flex min-h-8 items-center gap-2 border-b border-hairline py-1 text-body" data-evidence={name}>
      <ProvenanceGlyph kind={kind} />
      <span className="min-w-0 flex-1 text-ink">
        <span className="font-medium">{label}</span>
        {detail ? <span className="text-ink-500">, {detail}</span> : null}
      </span>
      {reference ? <span className="ident shrink-0 text-caption text-ink-500">{reference}</span> : null}
      <span className="shrink-0">{children}</span>
    </li>
  );
}

const openClass = 'link inline-flex items-center gap-0.5 font-medium';

export function Evidence({ item, code, headingLevel: Heading }: { item: WorkItemDetail; code: string | undefined; headingLevel: 'h3' | 'h4' }) {
  const source = useSource();
  const words = useDocWords();
  const signals = useSignalWords();
  const evidence = item.evidence;
  const valueId = text(evidence.value_fact_id);
  const reportedId = text(evidence.reported_fact_id);
  const calcId = text(evidence.calc_run_id);
  const testId = text(evidence.covenant_test_id);
  const reviewId = text(evidence.borrowing_base_review_id);
  const documentId = text(evidence.document_id);
  const subject = text(evidence.subject);
  const subjectDocument = subject?.startsWith('document:') ? subject.slice('document:'.length) : null;
  const signalId = text(evidence.signal_id);
  const missing = Array.isArray(evidence.missing) ? (evidence.missing as Array<{ document_type?: string; due_date?: string }>) : [];
  const lines = Array.isArray(evidence.lines)
    ? (evidence.lines as Array<{ line: string; computed: string | null; certificate: string | null; difference: string | null }>)
    : [];
  const basis = evidence.basis && typeof evidence.basis === 'object' ? (evidence.basis as Record<string, unknown>) : null;

  const facts = useFactsById([valueId, reportedId]);
  const documents = useDocuments(documentId || subjectDocument ? item.borrower_id : undefined);
  const filed = documents.data?.find((doc) => doc.id === documentId || (subjectDocument && doc.meta?.external_id === subjectDocument));

  const rows: ReactNode[] = [];
  if (valueId) {
    rows.push(
      <EvidenceRow key="value" kind="calculated" label="Calculated by code" detail={facts.data?.[valueId]?.label}>
        {facts.data ? <FactFigure fact={facts.data[valueId]} weight="semibold" /> : <Skeleton className="h-3 w-12" />}
      </EvidenceRow>,
    );
  }
  if (reportedId) {
    rows.push(
      <EvidenceRow key="reported" kind={facts.data?.[reportedId]?.kind ?? 'extracted'} label="Reported on the certificate">
        {facts.data ? <FactFigure fact={facts.data[reportedId]} /> : <Skeleton className="h-3 w-12" />}
      </EvidenceRow>,
    );
  }
  if (calcId) {
    rows.push(
      <EvidenceRow key="calc" kind="calculated" label="The calculation" detail="inputs and steps" reference={calcId.slice(0, 8)}>
        <button type="button" className={openClass} onClick={() => source.open({ type: 'calculation', id: calcId })}>
          Open
        </button>
      </EvidenceRow>,
    );
  }
  if (testId && code) {
    rows.push(
      <EvidenceRow key="test" kind="calculated" label="Covenant test" detail="the figures behind the test, what the certificate reported and earlier periods">
        <Link to={clientFile(code, 'covenants')} className={openClass}>
          Open <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }
  if (reviewId && code) {
    rows.push(
      <EvidenceRow key="review" kind="calculated" label="Borrowing base review" detail="each line beside the certificate">
        <Link to={clientFile(code, 'loans')} className={openClass}>
          Open <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }
  if (documentId || subjectDocument) {
    const effective = text(evidence.effective_date);
    rows.push(
      <EvidenceRow
        key="document"
        kind="extracted"
        label={filed ? filed.title : 'Document on file'}
        detail={effective ? `effective ${formatDate(effective)}` : filed ? words(filed.doc_type).toLowerCase() : null}
      >
        {filed ? (
          <button
            type="button"
            className={openClass}
            onClick={() => source.open({ type: 'document', documentId: filed.id, page: 1, title: filed.title, borrowerCode: code })}
          >
            Open
          </button>
        ) : documents.isPending ? (
          <Skeleton className="h-3 w-10" />
        ) : (
          <span className="text-caption text-ink-500">Not found on file</span>
        )}
      </EvidenceRow>,
    );
  }
  for (const [index, entry] of missing.entries()) {
    rows.push(
      <EvidenceRow
        key={`missing-${index}`}
        kind="system"
        label={words(entry.document_type)}
        detail={entry.due_date ? `was due ${formatDate(entry.due_date)}` : 'not received'}
      >
        {code ? (
          <Link to={clientFile(code, 'documents')} className={openClass}>
            Documents <ArrowUpRight size={12} aria-hidden />
          </Link>
        ) : null}
      </EvidenceRow>,
    );
  }
  const fundingId = text(evidence.funding_event_id);
  const fundingAmount = text(evidence.amount);
  if (fundingId && fundingAmount) {
    // the amount a person recorded on the funding event: shown here with its source, never typed into the title
    const kind = word('funding_kinds', text(evidence.kind) ?? 'funding_event');
    const close = text(evidence.expected_close);
    rows.push(
      <EvidenceRow key="funding" name="funding" kind="manual" label={kind} detail={close ? `expected to close ${formatDate(close)}` : null}>
        <SourcedFigure value={fundingAmount} unit="usd" kind="manual" label={`${kind} amount`}
          source={{ type: 'record', kind: 'manual', title: 'Funding event', value: fundingAmount, rows: [['Kind', kind], ...(close ? [['Expected close', formatDate(close)] as [string, string]] : [])], note: 'Recorded by a person on the funding event; not read from a document.' }} />
      </EvidenceRow>,
    );
  }
  if (signalId && code) {
    const rule = text(evidence.rule_id);
    rows.push(
      <EvidenceRow key="signal" kind="calculated" label={rule ? signals(rule) : 'Signal'} detail={basis ? basisSentence(basis) : null}>
        <Link to={clientFile(code)} className={openClass}>
          Signals <ArrowUpRight size={12} aria-hidden />
        </Link>
      </EvidenceRow>,
    );
  }

  const note = text(evidence.note);
  const error = text(evidence.error);
  const draft = text(evidence.draft_email);
  const withheld = Array.isArray(evidence.withheld_sections)
    ? (evidence.withheld_sections as Array<{ section?: string; withheld_by?: string; reason?: string }>)
    : [];

  return (
    <div>
      <Heading className="eyebrow mb-1">Evidence</Heading>
      {rows.length > 0 ? <ul className="border-t border-ink">{rows}</ul> : null}
      {withheld.length > 0 ? (
        <div data-withheld-sections className="mt-3">
          <p className="text-body text-ink-700">
            {withheld.length === 1 ? 'One section was' : `${withheld.length} sections were`} withheld from the sheet. The agent&rsquo;s text failed a
            check, so it is not shown; write the section or approve the sheet without it.
          </p>
          <ul className="mt-1.5 border-t border-hairline">
            {withheld.map((entry, index) => (
              <li key={`${entry.section ?? 'section'}-${index}`} className="border-b border-hairline py-1.5 text-body">
                <span className="font-medium text-ink">{humanize(entry.section ?? 'Section')}</span>
                {entry.withheld_by ? <span className="text-ink-600"> · withheld by the {entry.withheld_by}</span> : null}
                {entry.reason ? <span className="block text-ink-600">{entry.reason}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {lines.length > 0 && calcId ? (
        <table className="mt-2 w-full text-body">
          <caption className="eyebrow pb-1 text-left">Lines that differ, USD thousands</caption>
          <thead>
            <tr className="text-left">
              <th scope="col" className="eyebrow border-b border-ink py-1 font-semibold">
                Line
              </th>
              <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                Recalculated
              </th>
              <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                Certificate
              </th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.line} className="border-b border-hairline last:border-b-0">
                <th scope="row" className="py-1 text-left font-regular text-ink-700">
                  {humanize(line.line)}
                </th>
                <td className="py-1 text-right">
                  <SourcedFigure
                    value={line.computed}
                    unit="usd"
                    kind="calculated"
                    label={`${humanize(line.line)}, recalculated`}
                    source={{ type: 'calculation', id: calcId }}
                    scale={1000}
                    unitMark={false}
                    align="column"
                  />
                </td>
                <td className="py-1 text-right">
                  <SourcedFigure
                    value={line.certificate}
                    unit="usd"
                    kind="extracted"
                    label={`${humanize(line.line)}, on the certificate`}
                    source={{ type: 'calculation', id: calcId }}
                    scale={1000}
                    unitMark={false}
                    align="column"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {error ? <p className="mt-2 text-body text-amber">{error}</p> : null}
      {note ? <p className="mt-2 text-caption text-pretty text-ink-500">{note}</p> : null}
      {rows.length === 0 && lines.length === 0 && !note && !draft ? (
        <p className="border-t border-ink pt-2 text-body text-ink-500">No evidence is attached to this item.</p>
      ) : null}
      {draft ? (
        <AgentNote agent="Intake Agent" headline="Drafted a reminder email. Squad sends nothing: copy it and send it yourself" state="draft" className="mt-3">
          <p className="text-body whitespace-pre-line text-ink">{draft}</p>
        </AgentNote>
      ) : null}
    </div>
  );
}

/** A signal's basis in a few plain words. Counts of days are not money; figures with facts are shown on the Signals tab. */
function basisSentence(basis: Record<string, unknown>): string | null {
  if (typeof basis.days_late === 'number') return `${basis.days_late} days late against a limit of ${String(basis.threshold)}`;
  if (typeof basis.past_due_days === 'number') return `${basis.past_due_days} days past due against a limit of ${String(basis.threshold)}`;
  const subject = text(basis.subject) ?? text(basis.metric);
  return subject ? humanize(subject).toLowerCase() : null;
}

/* ── Recommendation ───────────────────────────────────────────────────── */


export function Recommendation({
  recommendation,
  item,
  headingLevel,
  code,
}: {
  recommendation: ApiRecommendation;
  item: WorkItemDetail;
  headingLevel: 'h3' | 'h4';
  code: string | undefined;
}) {
  const kind = text(recommendation.recommendation) ?? text(recommendation.kind) ?? '';
  const body = text(recommendation.explanation) ?? text(recommendation.body) ?? text(recommendation.text) ?? '';
  const agent = text(recommendation.agent) ?? text(recommendation.agent_name) ?? 'Covenant Agent';
  const runId = text(recommendation.run_id) ?? item.agent_run_id;
  const source = useSource();
  const claims = Array.isArray(recommendation.claims) ? recommendation.claims : [];
  const missing = Array.isArray(recommendation.missing_evidence)
    ? recommendation.missing_evidence.filter((entry): entry is string => typeof entry === 'string')
    : [];
  return (
    <>
      <AgentNote
        agent={agent}
        headline={text(recommendation.headline) ?? word('recommendations', kind)}
        state="draft"
        runId={runId ? runId.slice(0, 8) : undefined}
      >
        {body ? <AgentBody text={body} /> : null}
        {claims.length > 0 ? (
          <div className="mt-3">
            <p className="eyebrow mb-1">Quoted from documents, found on the page by code</p>
            <ul className="space-y-1.5">
              {claims.map((claim, index) => (
                <li key={index}>
                  {claim.text ? <p className="text-body text-ink">{claim.text}</p> : null}
                  {claim.quote ? <Quote text={claim.quote} /> : null}
                  {claim.document_id && claim.page ? (
                    <button
                      type="button"
                      className="link mt-0.5 text-caption font-medium"
                      onClick={() =>
                        source.open({
                          type: 'document',
                          documentId: claim.document_id as string,
                          page: claim.page as number,
                          quote: claim.quote,
                          title: 'Cited document',
                          borrowerCode: code,
                        })
                      }
                    >
                      Open page {claim.page}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {missing.length > 0 ? (
          <div className="mt-2">
            <p className="eyebrow">Evidence the agent says is missing</p>
            <ul className="mt-1 list-disc pl-5 text-body text-ink">
              {missing.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {runId && code ? (
          <Link to="/clients/$code/file/$view" params={{ code, view: 'runs' }} search={{ run: runId }} className="link mt-2 inline-block text-body font-medium">
            See the run, step by step
          </Link>
        ) : null}
      </AgentNote>
      {item.guardrail_notes.length > 0 ? <GuardrailNotes notes={item.guardrail_notes} as={headingLevel} /> : null}
    </>
  );
}

/* ── Related items ────────────────────────────────────────────────────── */

/**
 * Open questions on the same borrower that may change this item's result: an amendment not yet
 * approved into terms, held figures, a correction. Shown before the decision; it does not block it.
 */
export function RelatedItems({ items, headingLevel: Heading, onOpen }: { items: RelatedItem[]; headingLevel: 'h3' | 'h4'; onOpen: (id: string) => void }) {
  const open = onOpen;
  const headingId = useId();
  if (items.length === 0) return null;
  return (
    <section data-related-items aria-labelledby={headingId} className="rounded-md border border-amber-border bg-amber-bg px-3 py-2.5">
      <Heading id={headingId} className="text-body font-semibold text-ink">
        <StatusDot tone="attention" className="whitespace-normal!">
          Open questions that may change this result
        </StatusDot>
      </Heading>
      <p className="mt-0.5 pl-[13px] text-caption text-pretty text-ink-700">
        {items.length === 1 ? 'This item is' : 'These items are'} still open. You can decide now; the result may change once{' '}
        {items.length === 1 ? 'it is' : 'they are'} settled.
      </p>
      <ul className="mt-1.5 space-y-1 pl-[13px]">
        {items.map((related) => (
          <li key={related.id} className="text-body">
            <button type="button" className="link text-left font-medium" onClick={() => open(related.id)}>
              {related.title}
            </button>
            <span className="text-ink-700">
              {' '}
              · {related.relation}
            </span>
            <span className="ident ml-1.5 text-caption text-ink-500">{related.id.slice(0, 8)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

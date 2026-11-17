import { Link } from '@tanstack/react-router';
import { ArrowLeft, ArrowUpRight, X } from 'lucide-react';
import { Dialog as RadixDialog } from 'radix-ui';
import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { errorMessage } from '@/api/client';
import { mul } from '@/api/decimal';
import { useCalculation, useFactSource, useQuoteLocation } from '@/api/hooks';
import type { FactSource, SourcePage } from '@/api/schema';
import type { ProvenanceKind, Unit } from '@/api/types';
import { Button, formatDate, formatFigure, provenance, ProvenanceGlyph, Quote, Skeleton, StatusDot, type StatusTone } from '@/design';
import { docTypeLabel, formatTimestamp, periodLabel, toFact } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { CalculationBreakdown } from './CalculationBreakdown';
import { SourceContext, useSource, type SourceRef } from './context';
import { PdfPage } from './PdfPage';

const PAGE_WIDTH = 548;

const STATUS: Record<string, { tone: StatusTone; label: string }> = {
  verified: { tone: 'pass', label: 'Verified by code' },
  confirmed: { tone: 'pass', label: 'Confirmed by a person' },
  proposed: { tone: 'attention', label: 'Proposed, not verified' },
  rejected: { tone: 'muted', label: 'Rejected' },
  superseded: { tone: 'muted', label: 'Superseded' },
};

/** "Verified" means different things by kind: only an extracted figure was checked against a page. */
const VERIFIED_BY_KIND: Record<string, string> = {
  extracted: 'Verified on the page by code',
  calculated: 'Calculated by code',
  system: 'From a system of record',
  seeded: 'Loaded history, not extracted from a document',
};

function statusFor(status: string, kind?: string): { tone: StatusTone; label: string } {
  if (status === 'verified' && kind && VERIFIED_BY_KIND[kind]) {
    return { tone: kind === 'seeded' ? 'neutral' : 'pass', label: VERIFIED_BY_KIND[kind] };
  }
  return STATUS[status] ?? { tone: 'neutral', label: status };
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-hairline py-1.5 text-body last:border-b-0">
      <dt className="shrink-0 text-ink-500">{label}</dt>
      <dd className="min-w-0 text-right text-ink">{children}</dd>
    </div>
  );
}

function Section({ title, children, note }: { title: string; children: ReactNode; note?: ReactNode }) {
  return (
    <section className="border-t border-hairline-strong px-5 pt-3.5 pb-4">
      <div className="mb-2 flex items-baseline justify-between gap-4">
        <h3 className="eyebrow">{title}</h3>
        {note ? <span className="text-caption text-ink-500">{note}</span> : null}
      </div>
      {children}
    </section>
  );
}

function Heading({ kind, eyebrow, title, context, value, valueNote }: { kind: ProvenanceKind; eyebrow?: string; title: string; context?: string; value?: string; valueNote?: string }) {
  return (
    <div className="flex items-start justify-between gap-5 px-5 pt-1 pb-4">
      <div className="min-w-0">
        <div className="eyebrow flex items-center gap-1.5">
          <ProvenanceGlyph kind={kind} />
          {eyebrow ?? provenance[kind].phrase}
        </div>
        <RadixDialog.Title className="mt-1 text-heading font-semibold text-pretty text-ink">{title}</RadixDialog.Title>
        {context ? <p className="text-body text-ink-500">{context}</p> : null}
      </div>
      {value ? (
        <div className="shrink-0 text-right">
          <p data-source-value className="tnum text-heading font-semibold text-ink">
            {value}
          </p>
          {valueNote ? <p className="text-caption text-ink-500">{valueNote}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function ViewerLink({ code, documentId, page, factId, quote, onNavigate }: { code?: string; documentId: string | null; page: number | null; factId?: string; quote?: string | null; onNavigate: () => void }) {
  if (!code || !documentId) return null;
  return (
    <Link
      to="/borrowers/$code/documents/$documentId"
      params={{ code, documentId }}
      search={{ page: page ?? 1, ...(factId ? { fact: factId } : {}), ...(quote && !factId ? { quote } : {}) }}
      onClick={onNavigate}
      className="link inline-flex items-center gap-0.5 text-body font-medium"
    >
      Open in the document viewer
      <ArrowUpRight size={12} aria-hidden />
    </Link>
  );
}

/** The page a figure or clause is printed on, with the figure outlined. */
function PageBlock({ page, code, factId, markLabel, onNavigate }: { page: SourcePage; code?: string; factId?: string; markLabel: string; onNavigate: () => void }) {
  if (!page.document_id || !page.page) return null;
  return (
    <figure>
      <PdfPage
        documentId={page.document_id}
        page={page.page}
        width={PAGE_WIDTH}
        title={page.document_title}
        maxHeight={360}
        marks={page.boxes.length > 0 ? [{ id: 'cited', boxes: page.boxes, active: true, label: markLabel }] : []}
      />
      <figcaption className="mt-2 flex items-baseline justify-between gap-4 text-caption text-ink-500">
        <span className="min-w-0 text-pretty">
          {page.document_title} · <span className="tnum">page {page.page}</span>
          {page.page_count ? <span className="tnum"> of {page.page_count}</span> : null}
        </span>
        <span className="shrink-0">
          <ViewerLink code={code} documentId={page.document_id} page={page.page} factId={factId} quote={factId ? null : page.quote} onNavigate={onNavigate} />
        </span>
      </figcaption>
    </figure>
  );
}

function factFormat(unit: Unit) {
  return unit === 'usd' ? { text: 'US dollars' } : unit === 'ratio' ? { text: 'Ratio' } : unit === 'pct' ? { text: 'Per cent' } : unit === 'days' ? { text: 'Days' } : { text: 'Count' };
}

function FactView({ id, onNavigate }: { id: string; onNavigate: () => void }) {
  const { data, isPending, error } = useFactSource(id);
  const source = useSource();
  if (isPending) return <LoadingBody label="Loading the source of this figure" />;
  if (error || !data) return <ErrorBody message={errorMessage(error)} />;
  const { fact, page, calculation, clause } = data;
  const shown = toFact(fact);
  const status = statusFor(fact.status, fact.kind);
  const located = page?.method === 'located';
  const yesNo = fact.unit === 'count' && fact.key.endsWith('in_compliance');

  return (
    <>
      <Heading
        kind={fact.kind}
        title={fact.label}
        context={`${data.borrower.name} · ${periodLabel(fact.period_end, fact.months)}`}
        value={yesNo ? (fact.value === '1' ? 'Yes' : 'No') : formatFigure(shown.value, shown.unit).text}
        valueNote={yesNo ? 'As certified' : factFormat(fact.unit).text}
      />

      {page ? (
        <Section title={located ? 'Where the figure is printed' : 'Source page'} note={located ? 'Located by code, not extracted' : 'Cited by the fact'}>
          <PageBlock page={page} code={data.borrower.code} factId={fact.id} markLabel={`${fact.label} as printed`} onNavigate={onNavigate} />
          <dl className="mt-3">
            <Row label="Printed as">
              {page.quote ? <Quote text={`${page.label_text ? `${page.label_text}  ` : ''}${page.quote}`} highlight={page.quote} /> : 'Not recorded'}
            </Row>
            {page.scale && page.scale > 1 ? <Row label="Scale">Reported in thousands, stored in whole dollars</Row> : null}
            {page.comparative_column ? <Row label="Column">The comparative column of a later statement</Row> : null}
          </dl>
          {located ? (
            <p className="mt-2 text-caption text-pretty text-ink-500">
              This fact was loaded from the synthetic book, not read from the page by an agent. Code searched the period’s {docTypeLabel(page.doc_type).toLowerCase()} for the
              stored value and outlined the row whose label matches. An extracted fact carries its own page and quote.
            </p>
          ) : null}
        </Section>
      ) : null}

      {fact.kind === 'seeded' && !page ? (
        <Section title="Source">
          <p className="text-body text-pretty text-ink-700">
            This fact was loaded from the synthetic book’s ground truth. Code did not find the stored value printed in the period’s documents (a line printed as a dash, or a
            document that is not on file), so there is no page to show.
          </p>
        </Section>
      ) : null}

      {calculation ? (
        <Section title="Calculation" note={calculation.expression ?? undefined}>
          <div className="-mx-5">
            <CalculationBreakdown calc={calculation} resultLabel={fact.label} resultUnit={fact.unit === 'pct' ? 'ratio' : fact.unit} selfContained />
          </div>
          <dl className="mt-2">
            <Row label="Method">
              <span className="ident">{calculation.formula_key}</span> · version <span className="ident">{calculation.formula_version}</span>
            </Row>
            {calculation.terms_version ? (
              <Row label="Terms in force">
                Version <span className="tnum">{calculation.terms_version.version}</span>, {calculation.terms_version.status}, effective {formatDate(calculation.terms_version.effective_from)}
              </Row>
            ) : null}
            <Row label="Calculation">
              <button type="button" className="link ident" onClick={() => source.open({ type: 'calculation', id: calculation.id, title: fact.label })}>
                {calculation.id.slice(0, 8)}
              </button>
            </Row>
          </dl>
        </Section>
      ) : null}

      {clause ? (
        <Section title="Clause that sets the threshold" note={clause.section ? `Section ${clause.section}` : undefined}>
          {clause.quote ? <Quote text={clause.quote} /> : null}
          <div className="mt-3">
            <PageBlock page={clause} code={data.borrower.code} markLabel="Quoted clause" onNavigate={onNavigate} />
          </div>
        </Section>
      ) : null}

      {fact.kind === 'system' ? (
        <Section title="System of record">
          <dl>
            <Row label="System">{fact.connector ? fact.connector.replace(/_/g, ' ') : 'Not recorded'}</Row>
            <Row label="Record">
              <span className="ident">{fact.record_ref ?? 'Not recorded'}</span>
            </Row>
            <Row label="As of">{fact.as_of ? formatDate(fact.as_of) : formatDate(fact.period_end)}</Row>
          </dl>
        </Section>
      ) : null}

      {fact.kind === 'manual' ? (
        <Section title="Entered by a person">
          {fact.reason ? <Quote text={fact.reason} /> : null}
          <dl className="mt-2">
            <Row label="Entered by">{fact.entered_by ?? 'Not recorded'}</Row>
            <Row label="When">{formatTimestamp(fact.created_at)}</Row>
          </dl>
        </Section>
      ) : null}

      <Section title="Record">
        <dl>
          <Row label="Check">
            <StatusDot tone={status.tone}>{status.label}</StatusDot>
          </Row>
          {fact.confirmed_by ? (
            <Row label="Confirmed by">
              {fact.confirmed_by}, {formatTimestamp(fact.confirmed_at)}
            </Row>
          ) : null}
          <Row label="Stored value">
            <span className="tnum">{fact.unit === 'usd' ? formatFigure(fact.value, 'usd', { unitMark: false, dp: fact.value.includes('.') ? 2 : 0 }).text : fact.value}</span>{' '}
            {fact.unit === 'pct' ? 'as a fraction, shown in per cent' : fact.unit === 'usd' ? 'whole US dollars' : factFormat(fact.unit).text.toLowerCase()}
          </Row>
          {fact.note ? <Row label="Note">{fact.note}</Row> : null}
          <Row label="Fact">
            <span className="ident">{fact.id}</span>
          </Row>
        </dl>
        <History entries={data.history} unit={fact.unit} />
      </Section>
    </>
  );
}

function History({ entries, unit }: { entries: FactSource['history']; unit: Unit }) {
  if (entries.length <= 1) {
    return <p className="mt-3 text-caption text-ink-500">History: this is the only version. A correction would add a new fact and keep this one.</p>;
  }
  return (
    <div className="mt-3">
      <h4 className="eyebrow mb-1">History, newest first</h4>
      <ol className="border-t border-ink">
        {entries.map((entry) => (
          <li key={entry.id} className={cx('grid grid-cols-[1fr_auto] gap-x-4 border-b border-hairline py-1.5 text-caption', entry.relation === 'this' && 'bg-cobalt-bg px-2')}>
            <span className="text-ink">
              <span className="tnum font-medium">{formatFigure(unit === 'pct' ? mul(entry.value, '100') : entry.value, unit).text}</span>
              {entry.relation === 'this' ? ' · this version' : ''}
            </span>
            <span className="text-ink-700">
              {(STATUS[entry.status] ?? { label: entry.status }).label} · {formatTimestamp(entry.created_at)}
            </span>
            {entry.reason ? (
              <span className="col-span-2 text-ink-700">
                {entry.entered_by ? `${entry.entered_by}: ` : ''}
                {entry.reason}
              </span>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}

function CalculationView({ id, title }: { id: string; title?: string }) {
  const { data, isPending, error } = useCalculation(id);
  if (isPending) return <LoadingBody label="Loading the calculation" />;
  if (error || !data) return <ErrorBody message={errorMessage(error)} />;
  const result = data.produced?.find((fact) => fact.key.endsWith('.value')) ?? data.produced?.[0];
  const label = title ?? result?.label ?? data.formula_key;
  const shown = result ? toFact(result) : null;
  return (
    <>
      <Heading
        kind="calculated"
        title={label}
        context={`Period ended ${formatDate(data.period_end)}`}
        value={shown ? formatFigure(shown.value, shown.unit).text : undefined}
        valueNote={data.expression ?? undefined}
      />
      {data.error ? (
        <Section title="Refused">
          <p className="text-body text-amber">{data.error}</p>
        </Section>
      ) : null}
      {data.steps.length > 0 ? (
        <Section title="Steps" note="Every input opens its own source">
          <div className="-mx-5">
            <CalculationBreakdown calc={data} resultLabel={label} resultUnit={result && result.unit !== 'pct' ? result.unit : 'ratio'} selfContained />
          </div>
        </Section>
      ) : data.inputs.length > 0 ? (
        <Section title="Inputs">
          <ul className="border-t border-ink">
            {data.inputs.map((input, index) => {
              const fact = input.fact_id ? data.facts[input.fact_id] : undefined;
              return (
                <li key={`${input.key}-${index}`} className="flex items-baseline justify-between gap-4 border-b border-hairline py-1.5 text-body">
                  <span className="text-ink-700">{fact?.label ?? input.name}</span>
                  {fact ? <InlineFact id={fact.id} text={formatFigure(toFact(fact).value, fact.unit).text} kind={fact.kind} /> : <span className="tnum">{input.value}</span>}
                </li>
              );
            })}
          </ul>
        </Section>
      ) : (
        <Section title="Inputs">
          <p className="text-body text-pretty text-ink-700">
            This calculation reads its inputs from the certificate and aging detail, not from spread facts. Its lines are shown where it is used.
          </p>
        </Section>
      )}
      <Section title="Record">
        <dl>
          <Row label="Method">
            <span className="ident">{data.formula_key}</span> · version <span className="ident">{data.formula_version}</span>
          </Row>
          {data.terms_version ? (
            <Row label="Terms in force">
              Version <span className="tnum">{data.terms_version.version}</span>, {data.terms_version.status}
            </Row>
          ) : null}
          <Row label="Engine">
            <span className="ident">{data.engine_version}</span>
          </Row>
          <Row label="Run">
            {formatTimestamp(data.created_at)} by {data.created_by_type} <span className="ident">{data.created_by_id}</span>
          </Row>
          <Row label="Calculation">
            <span className="ident">{data.id}</span>
          </Row>
        </dl>
      </Section>
    </>
  );
}

function InlineFact({ id, text, kind }: { id: string; text: string; kind: ProvenanceKind }) {
  const source = useSource();
  return (
    <button type="button" onClick={() => source.open({ type: 'fact', id })} className="-mx-1 inline-flex items-center gap-1 rounded-xs px-1 text-ink t-colors hover:bg-cobalt-bg hover:text-cobalt-strong">
      <span className="tnum">{text}</span>
      <ProvenanceGlyph kind={kind} labelled />
    </button>
  );
}

function DocumentView({ source, onNavigate }: { source: Extract<SourceRef, { type: 'document' }>; onNavigate: () => void }) {
  const needsLocation = !source.boxes && Boolean(source.quote);
  const located = useQuoteLocation(needsLocation ? source.documentId : null, source.page, source.quote);
  const boxes = source.boxes ?? located.data?.boxes ?? [];
  const title = source.title ?? 'Document';
  return (
    <>
      <Heading kind="extracted" eyebrow="Quoted from a document" title={title} context={`Page ${source.page}${source.section ? ` · Section ${source.section}` : ''}`} />
      <Section title="Source page" note={needsLocation && located.data && !located.data.found ? 'The quote was not found word for word on this page' : undefined}>
        {source.quote ? (
          <div className="mb-3">
            <Quote text={source.quote} />
          </div>
        ) : null}
        <PageBlock
          page={{ document_id: source.documentId, document_title: title, doc_type: null, page: source.page, page_count: null, boxes, quote: source.quote ?? null, method: 'cited' }}
          code={source.borrowerCode}
          markLabel="Quoted passage"
          onNavigate={onNavigate}
        />
      </Section>
    </>
  );
}

function RecordView({ source, onNavigate }: { source: Extract<SourceRef, { type: 'record' }>; onNavigate: () => void }) {
  return (
    <>
      <Heading kind={source.kind} title={source.title} value={source.value} />
      <Section title="Where this figure comes from">
        <p className="mb-2 text-body text-pretty text-ink-700">{source.note}</p>
        <dl>
          {source.rows.map(([label, value]) => (
            <Row key={label} label={label}>
              {value}
            </Row>
          ))}
        </dl>
        {source.link ? (
          <a href={source.link.to} onClick={onNavigate} className="link mt-3 inline-flex items-center gap-0.5 text-body font-medium">
            {source.link.label}
            <ArrowUpRight size={12} aria-hidden />
          </a>
        ) : null}
      </Section>
    </>
  );
}

function LoadingBody({ label }: { label: string }) {
  return (
    <div role="status" aria-label={label} className="space-y-3 px-5 py-4">
      <RadixDialog.Title className="sr-only">{label}</RadixDialog.Title>
      <Skeleton className="h-3 w-40" />
      <Skeleton className="h-6 w-72" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function ErrorBody({ message }: { message: string }) {
  return (
    <div role="alert" className="px-5 py-4">
      <RadixDialog.Title className="text-title font-semibold text-ink">The source could not be loaded</RadixDialog.Title>
      <p className="mt-1 text-body text-ink-700">{message}</p>
    </div>
  );
}

/**
 * The source drawer: one place, used by every figure, that answers "where did this number come from?".
 * Inputs of a calculation open in the same drawer; Back returns to where the reader was.
 */
export function SourceProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<SourceRef[]>([]);
  const current = stack[stack.length - 1] ?? null;
  const open = useCallback((ref: SourceRef) => {
    setStack((existing) => {
      const top = existing[existing.length - 1];
      if (top && JSON.stringify(top) === JSON.stringify(ref)) return existing;
      return [...existing, ref];
    });
  }, []);
  const close = useCallback(() => setStack([]), []);
  const api = useMemo(() => ({ open, close, current }), [open, close, current]);

  return (
    <SourceContext.Provider value={api}>
      {children}
      <RadixDialog.Root open={current !== null} onOpenChange={(next) => (next ? undefined : close())}>
        <RadixDialog.Portal>
          <RadixDialog.Overlay className="anim-fade fixed inset-0 z-40 bg-ink/20" />
          <RadixDialog.Content
            aria-describedby={undefined}
            data-source-drawer
            className="anim-fade fixed inset-y-0 right-0 z-50 flex w-[590px] max-w-full flex-col border-l border-hairline-strong bg-surface shadow-overlay outline-none"
          >
            <div className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-hairline px-3">
              <div className="flex items-center gap-1">
                {stack.length > 1 ? (
                  <Button variant="ghost" size="sm" iconLeft={<ArrowLeft size={13} aria-hidden />} onClick={() => setStack((existing) => existing.slice(0, -1))}>
                    Back
                  </Button>
                ) : (
                  <span className="eyebrow px-2">Source</span>
                )}
                {stack.length > 1 ? (
                  <span className="text-caption text-ink-500">
                    Step <span className="tnum">{stack.length}</span> of the trail
                  </span>
                ) : null}
              </div>
              <RadixDialog.Close aria-label="Close the source" className="inline-flex size-8 items-center justify-center rounded-sm text-ink-500 t-colors hover:bg-hover hover:text-ink">
                <X size={16} aria-hidden />
              </RadixDialog.Close>
            </div>
            <div key={JSON.stringify(current)} className="min-h-0 flex-1 overflow-y-auto pt-3">
              {current?.type === 'fact' ? <FactView id={current.id} onNavigate={close} /> : null}
              {current?.type === 'calculation' ? <CalculationView id={current.id} title={current.title} /> : null}
              {current?.type === 'document' ? <DocumentView source={current} onNavigate={close} /> : null}
              {current?.type === 'record' ? <RecordView source={current} onNavigate={close} /> : null}
            </div>
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>
    </SourceContext.Provider>
  );
}

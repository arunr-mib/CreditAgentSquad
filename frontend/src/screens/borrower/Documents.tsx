import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';
import { useMemo, useState } from 'react';
import { API } from '@/api/client';
import { useDocument, useDocuments, usePageFigures, useQuoteLocation } from '@/api/hooks';
import type { DocumentRow, PageFigure } from '@/api/schema';
import { useAuth } from '@/auth/context';
import { Button, Card, DataTable, EmptyState, formatDate, formatFigure, IconButton, ProvenanceGlyph, Quote, Select, StatusDot, type DataColumn } from '@/design';
import { docTypeLabel, quarterLabel, roleLabel, ROLES_WITH, toFact } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { useSource } from '@/source/context';
import { PdfPage, type PageMark } from '@/source/PdfPage';
import { EmptyCard, ErrorNotice, Load, SectionHead } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';
import { UploadDocument } from './UploadDocument';

const STATUS: Record<string, { tone: 'neutral' | 'attention' | 'muted'; label: string }> = {
  indexed: { tone: 'neutral', label: 'Read, page by page' },
  received: { tone: 'muted', label: 'Received' },
  image_only: { tone: 'attention', label: 'Image only, no text' },
  rejected: { tone: 'attention', label: 'Rejected' },
};

export function Documents() {
  const borrower = useCurrentBorrower();
  const documents = useDocuments(borrower.id);
  const navigate = useNavigate();
  const [type, setType] = useState('all');
  const [filing, setFiling] = useState(false);
  const { user, can } = useAuth();
  const mayFile = can('upload_document');

  const columns =useMemo<Array<DataColumn<DocumentRow>>>(
    () => [
      {
        id: 'title',
        header: 'Document',
        rowHeader: true,
        wrap: true,
        sortValue: (row) => row.title,
        cell: (row) => (
          <Link
            to="/borrowers/$code/documents/$documentId"
            params={{ code: borrower.code, documentId: row.id }}
            onClick={(event) => event.stopPropagation()}
            className="font-medium text-ink hover:text-cobalt-strong hover:underline"
          >
            {row.title}
          </Link>
        ),
      },
      { id: 'type', header: 'Type', sortValue: (row) => docTypeLabel(row.doc_type), cell: (row) => <span className="text-ink-700">{docTypeLabel(row.doc_type)}</span> },
      {
        id: 'period',
        header: 'Period',
        sortValue: (row) => row.period_end ?? row.effective_date,
        cell: (row) =>
          row.period_end ? (
            <span className="tnum text-ink-700">{quarterLabel(row.period_end)}</span>
          ) : row.effective_date ? (
            <span className="tnum text-ink-700">Effective {formatDate(row.effective_date)}</span>
          ) : (
            <span className="text-ink-500">Not dated</span>
          ),
      },
      { id: 'received', header: 'Received', sortValue: (row) => row.received_date, cell: (row) => <span className="tnum text-ink-700">{row.received_date ? formatDate(row.received_date) : 'Not recorded'}</span> },
      { id: 'pages', header: 'Pages', align: 'right', sortValue: (row) => row.page_count, cell: (row) => <span className="tnum text-ink-700">{row.page_count}</span> },
      {
        id: 'status',
        header: 'Status',
        sortValue: (row) => row.status,
        cell: (row) => {
          const status = STATUS[row.status] ?? { tone: 'neutral' as const, label: row.status };
          return <StatusDot tone={status.tone}>{status.label}</StatusDot>;
        },
      },
    ],
    [borrower.code],
  );

  return (
    <Load query={documents} what="The documents" rows={10}>
      {(rows) => {
        const types = [...new Set(rows.map((row) => row.doc_type ?? 'unclassified'))].sort();
        const filtered = rows.filter((row) => type === 'all' || (row.doc_type ?? 'unclassified') === type);
        const fileButton = mayFile && !filing ? <Button onClick={() => setFiling(true)}>File a document</Button> : undefined;
        const form = filing ? <UploadDocument borrowerId={borrower.id} code={borrower.code} onClose={() => setFiling(false)} /> : null;
        return rows.length === 0 ? (
          <div data-ready className="space-y-4">
            <EmptyCard title="No document is on file" description="Statements, certificates and agreements appear here as they are received." action={fileButton} />
            {form}
          </div>
        ) : (
          <section data-ready aria-labelledby="documents-heading">
            <SectionHead
              id="documents-heading"
              title="Documents"
              note={`${filtered.length} of ${rows.length} on file · newest first`}
              actions={
                <>
                  <Select
                    label="Document type"
                    hideLabel
                    size="sm"
                    className="w-56"
                    value={type}
                    onValueChange={setType}
                    options={[{ value: 'all', label: 'All types' }, ...types.map((id) => ({ value: id, label: docTypeLabel(id === 'unclassified' ? null : id) }))]}
                  />
                  {mayFile && !filing ? (
                    <Button size="sm" onClick={() => setFiling(true)}>
                      File a document
                    </Button>
                  ) : null}
                </>
              }
            />
            {form ? <div className="mb-4">{form}</div> : null}
            {!mayFile && user ? (
              <p className="mb-2 text-caption text-ink-500">
                Filing a document needs {(ROLES_WITH.upload_document ?? []).map((role) => `a ${roleLabel(role).toLowerCase()}`).join(' or ')}. Your role, {roleLabel(user.role)}, can read what is on file.
              </p>
            ) : null}
            <DataTable
              caption="Documents on file for this borrower"
              data={filtered}
              columns={columns}
              getRowId={(row) => row.id}
              onRowActivate={(row) => void navigate({ to: '/borrowers/$code/documents/$documentId', params: { code: borrower.code, documentId: row.id } })}
              stickyTop="var(--topbar-h)"
              empty={<EmptyState title="No document of this type" action={<Button onClick={() => setType('all')}>Show all types</Button>} />}
            />
          </section>
        );
      }}
    </Load>
  );
}

const PAGE_WIDTH = 760;

function figureText(figure: PageFigure): string {
  const fact = toFact(figure.fact);
  if (fact.unit === 'count') return figure.fact.value === '1' ? 'Yes' : 'No';
  return formatFigure(fact.value, fact.unit, fact.unit === 'usd' ? { scale: 1000, unitMark: false } : {}).text;
}

/** The document viewer: the page itself, every stored figure outlined on it, and the list of those figures. */
export function DocumentViewer() {
  const borrower = useCurrentBorrower();
  const { documentId } = useParams({ from: '/borrowers/$code/documents/$documentId' });
  const search = useSearch({ from: '/borrowers/$code/documents/$documentId' });
  const navigate = useNavigate({ from: '/borrowers/$code/documents/$documentId' });
  const source = useSource();
  const document = useDocument(documentId);
  const page = Math.min(search.page ?? 1, document.data?.page_count ?? search.page ?? 1);
  const figures = usePageFigures(documentId, page);
  const quote = useQuoteLocation(search.quote ? documentId : null, page, search.quote);

  if (document.error) return <ErrorNotice error={document.error} what="The document" onRetry={() => void document.refetch()} />;
  if (!document.data) return <Load query={document} what="The document" rows={12}>{() => null}</Load>;

  const doc = document.data;
  const go = (next: number) => void navigate({ search: { page: Math.max(1, Math.min(doc.page_count, next)) }, replace: true, resetScroll: false });
  const list = figures.data?.figures ?? [];
  const activeId = search.fact;
  const marks: PageMark[] = [
    ...list.map((figure) => ({
      id: figure.fact.id,
      boxes: figure.boxes,
      active: figure.fact.id === activeId,
      label: `${figure.fact.label}: ${figureText(figure)}. Show source.`,
      onSelect: () => source.open({ type: 'fact', id: figure.fact.id }),
    })),
    ...(quote.data?.found ? [{ id: 'quote', boxes: quote.data.boxes, active: true, label: 'Quoted passage' }] : []),
  ];
  const located = list.some((figure) => figure.method === 'located');

  return (
    <div data-ready={figures.data ? '' : undefined} className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <Link to="/borrowers/$code/documents" params={{ code: borrower.code }} className="link inline-flex items-center gap-1 text-caption font-medium">
            <ArrowLeft size={12} aria-hidden /> All documents
          </Link>
          <h2 className="mt-1 text-title font-semibold text-pretty text-ink">{doc.title}</h2>
          <p className="text-caption text-ink-500">
            {docTypeLabel(doc.doc_type)}
            {doc.period_end ? ` · period ended ${formatDate(doc.period_end)}` : ''}
            {doc.received_date ? ` · received ${formatDate(doc.received_date)}` : ''} · <span className="ident">{doc.file_name}</span>
          </p>
        </div>
        <div className="flex items-center gap-1">
          <IconButton label="Previous page" icon={<ChevronLeft size={16} aria-hidden />} disabled={page <= 1} onClick={() => go(page - 1)} />
          <Select
            label="Page"
            hideLabel
            size="sm"
            className="w-36"
            value={String(page)}
            onValueChange={(value) => go(Number.parseInt(value, 10))}
            options={Array.from({ length: doc.page_count }, (_, index) => ({ value: String(index + 1), label: `Page ${index + 1} of ${doc.page_count}` }))}
          />
          <IconButton label="Next page" icon={<ChevronRight size={16} aria-hidden />} disabled={page >= doc.page_count} onClick={() => go(page + 1)} />
          <Button asChild size="sm" className="ml-2">
            <a href={`${API}/documents/${doc.id}/file`} target="_blank" rel="noreferrer">
              Open the file
            </a>
          </Button>
        </div>
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0 overflow-x-auto">
          <PdfPage key={`${doc.id}-${page}`} documentId={doc.id} page={page} width={PAGE_WIDTH} title={doc.title} marks={marks} />
        </div>

        <aside aria-label="Figures on this page" className="xl:sticky xl:top-[68px]">
          <Card>
            <div className="px-4 pt-3.5 pb-2">
              <h3 className="text-title font-semibold text-ink">Figures on this page</h3>
              <p className="mt-0.5 text-caption text-pretty text-ink-500">
                {figures.isPending
                  ? 'Reading the page'
                  : list.length > 0
                    ? `${list.length} stored ${list.length === 1 ? 'figure is' : 'figures are'} printed here. Choose one to open its source.`
                    : 'No stored figure is printed on this page.'}
              </p>
            </div>
            {search.quote ? (
              <div className="border-t border-hairline px-4 py-3">
                <p className="eyebrow mb-1">Quoted passage</p>
                <Quote text={search.quote} />
                {quote.data && !quote.data.found ? <p className="mt-1 text-caption font-medium text-amber">This passage was not found word for word on this page.</p> : null}
              </div>
            ) : null}
            {figures.error ? (
              <div className="border-t border-hairline p-4">
                <ErrorNotice error={figures.error} what="The figures on this page" onRetry={() => void figures.refetch()} />
              </div>
            ) : list.length > 0 ? (
              <ul className="max-h-[calc(100vh-280px)] overflow-y-auto border-t border-ink" aria-label="Figures on this page, in reading order">
                {list.map((figure) => (
                  <li key={figure.fact.id} className="border-b border-hairline last:border-b-0">
                    <button
                      type="button"
                      data-figure={figure.fact.key}
                      onClick={() => source.open({ type: 'fact', id: figure.fact.id })}
                      className={cx(
                        'flex min-h-8 w-full items-center gap-3 px-4 py-1 text-left text-body t-colors hover:bg-hover last:rounded-b-md',
                        figure.fact.id === activeId && 'bg-cobalt-bg',
                      )}
                    >
                      <span className="min-w-0 flex-1 text-ink-700">{figure.fact.label}</span>
                      <span className="inline-flex shrink-0 items-center gap-1 text-ink">
                        <span className="tnum">{figureText(figure)}</span>
                        <ProvenanceGlyph kind={figure.fact.kind} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            {located ? (
              <p className="border-t border-hairline px-4 py-2.5 text-caption text-pretty text-ink-500">
                These facts were loaded from the synthetic book. Code found each one on the page by its printed value and row label; none was extracted by an agent. Amounts are
                in USD thousands.
              </p>
            ) : null}
          </Card>
        </aside>
      </div>
    </div>
  );
}

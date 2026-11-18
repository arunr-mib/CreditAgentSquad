import { Link } from '@tanstack/react-router';
import { Search } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { useBorrowers, useCalendar } from '@/api/hooks';
import type { Obligation } from '@/api/schema';
import { Button, DataTable, EmptyState, formatDate, Input, PageHeader, Select, StatusDot, Tag, type DataColumn } from '@/design';
import { docTypeLabel, humanize, quarterLabel } from '@/domain/labels';
import { useWorkspaceDrawer } from '@/drawer/context';
import { cx } from '@/lib/cx';
import { Load } from './parts';
import { layoutFor, useIsPhone, useKeepSelectedRowInView, useWidth } from './Portfolio';

const days = (count: number) => `${count} ${count === 1 ? 'day' : 'days'} late`;

/**
 * Overdue is the one status here a person acts on, so it is the one tag: amber, because a late
 * document needs attention and is not a breach. The days late are the API's count, shown as text.
 */
function ObligationStatus({ row }: { row: Obligation }) {
  switch (row.status) {
    case 'overdue':
      return (
        <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <Tag tone="attention">Overdue</Tag>
          {row.days_late ? <span className="tnum font-medium whitespace-nowrap text-amber">{days(row.days_late)}</span> : null}
        </span>
      );
    case 'received':
      return <StatusDot tone="pass">Received</StatusDot>;
    case 'due':
      return <StatusDot tone="neutral">Due</StatusDot>;
    case 'waived':
      return <StatusDot tone="muted">Waived</StatusDot>;
    case 'untracked':
      return <StatusDot tone="muted">Not tracked</StatusDot>;
    default:
      return <StatusDot tone="muted">{humanize(row.status)}</StatusDot>;
  }
}

/** Overdue first, the longest overdue at the top; then what is due, soonest first; then the rest. */
const STATUS_RANK: Record<string, number> = { overdue: 0, due: 1, received: 2, waived: 3, untracked: 4 };
export const statusSort = (row: Obligation): string =>
  `${STATUS_RANK[row.status] ?? 9}-${String(99_999 - (row.status === 'overdue' ? (row.days_late ?? 0) : 0)).padStart(5, '0')}-${row.due_date}`;

/** What "not tracked" means here, in the words the calendar shows beside the filter. */
export const UNTRACKED_NOTE =
  'Not tracked: requirements for past periods from before this book was loaded. The book holds documents for some past periods only, so a missing one is not counted as overdue.';

/** A choice of one, set out as separate buttons so that on a phone they wrap onto a second line instead of scrolling sideways. */
function Choice({ label, value, onValueChange, options }: { label: string; value: string; onValueChange: (value: string) => void; options: Array<{ value: string; label: string; count: number }> }) {
  return (
    <div role="group" aria-label={label} className="flex max-w-full flex-wrap gap-1.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onValueChange(option.value)}
          className={cx(
            'inline-flex h-8 items-center gap-1.5 rounded-sm border px-3 text-body font-medium t-colors',
            value === option.value ? 'border-ink bg-ink text-canvas' : 'border-hairline-strong bg-surface text-ink-700 hover:bg-hover hover:text-ink',
          )}
        >
          {option.label}
          <span className="tnum text-caption opacity-80">{option.count}</span>
        </button>
      ))}
    </div>
  );
}

/** Which columns the calendar shows in a frame of at least `min` pixels. Below 760 the requirement and its period sit under the borrower's name. */
const LAYOUTS: Array<{ min: number; columns: string[]; detail: boolean }> = [
  { min: 1000, columns: ['due', 'borrower', 'type', 'period', 'status', 'received'], detail: false },
  { min: 760, columns: ['due', 'borrower', 'type', 'status', 'received'], detail: false },
  // The due date stays in every layout: the table is sorted by it.
  { min: 0, columns: ['due', 'borrower', 'status'], detail: true },
];
const ON_A_PHONE = { min: 0, columns: ['borrower', 'type', 'period', 'due', 'status', 'received'], detail: false };

const periodText = (row: Obligation) => `${row.period_end.slice(5, 7) in { '03': 1, '06': 1, '09': 1, '12': 1 } ? `${quarterLabel(row.period_end)} · ` : ''}${formatDate(row.period_end)}`;

export function Calendar() {
  const calendar = useCalendar();
  const borrowers = useBorrowers();
  const drawer = useWorkspaceDrawer();
  const [status, setStatus] = useState('open');
  const [type, setType] = useState('all');
  const [text, setText] = useState('');
  const [chosen, setChosen] = useState<string | null>(null);
  const [frame, width] = useWidth();
  const phone = useIsPhone();
  const layout = phone ? ON_A_PHONE : layoutFor(LAYOUTS, width);
  const codes = useMemo(() => new Map((borrowers.data ?? []).map((row) => [row.id, row.code])), [borrowers.data]);
  const chosenRow = calendar.data?.obligations.find((row) => row.id === chosen);
  const selected = chosenRow && drawer.open && drawer.borrowerCode === codes.get(chosenRow.borrower_id) ? chosenRow.id : null;
  useKeepSelectedRowInView(selected, layout);

  const columns = useMemo<Array<DataColumn<Obligation>>>(() => {
    const all: Array<DataColumn<Obligation>> = [
      { id: 'due', header: 'Due', sortValue: (row) => row.due_date, cell: (row) => <span className="tnum text-ink">{formatDate(row.due_date)}</span> },
      {
        id: 'borrower',
        header: 'Borrower',
        rowHeader: true,
        wrap: true,
        sortValue: (row) => row.borrower_name,
        cell: (row) => {
          const code = codes.get(row.borrower_id);
          const name: ReactNode = code ? (
            <Link to="/borrowers/$code" params={{ code }} onClick={(event) => event.stopPropagation()} className="font-medium text-ink hover:text-cobalt-strong hover:underline">
              {row.borrower_name}
            </Link>
          ) : (
            <span className="font-medium text-ink">{row.borrower_name}</span>
          );
          return (
            <span className="block sm:min-w-[160px]">
              {name}
              {layout.detail ? (
                <span className="block text-caption font-regular text-ink-500">
                  {docTypeLabel(row.document_type)} · {periodText(row)}
                </span>
              ) : null}
            </span>
          );
        },
      },
      { id: 'type', header: 'Requirement', sortValue: (row) => docTypeLabel(row.document_type), cell: (row) => <span className="text-ink-700">{docTypeLabel(row.document_type)}</span> },
      { id: 'period', header: 'For the period', sortValue: (row) => row.period_end, cell: (row) => <span className="tnum text-ink-700">{periodText(row)}</span> },
      { id: 'status', header: 'Status', sortValue: statusSort, cell: (row) => <ObligationStatus row={row} /> },
      {
        id: 'received',
        header: 'Received',
        sortValue: (row) => row.received_date,
        cell: (row) => {
          const code = codes.get(row.borrower_id);
          if (!row.received_date) return <span className="text-ink-500">Not received</span>;
          return (
            <span className="whitespace-nowrap">
              {row.received_document_id && code ? (
                <Link to="/borrowers/$code/documents/$documentId" params={{ code, documentId: row.received_document_id }} onClick={(event) => event.stopPropagation()} className="tnum link">
                  {formatDate(row.received_date)}
                </Link>
              ) : (
                <span className="tnum text-ink-700">{formatDate(row.received_date)}</span>
              )}
              <span className="tnum text-ink-500"> · {row.days_late ? days(row.days_late) : 'on time'}</span>
            </span>
          );
        },
      },
    ];
    return all.filter((column) => layout.columns.includes(column.id)).sort((a, b) => layout.columns.indexOf(a.id) - layout.columns.indexOf(b.id));
  }, [codes, layout]);

  return (
    <div data-ready={calendar.data ? '' : undefined} className="space-y-5">
      <PageHeader
        eyebrow="Bank of Stoic · Commercial lending"
        title="Calendar"
        meta={calendar.data ? <span>Reporting requirements from the approved terms, as of {formatDate(calendar.data.as_of)}. Days late are counted to that date, or to the day the document arrived.</span> : undefined}
      />
      <Load query={calendar} what="The reporting calendar" rows={12}>
        {(data) => {
          const all = data.obligations;
          const matches = (row: Obligation, wanted: string) => wanted === 'all' || (wanted === 'open' ? row.status === 'due' || row.status === 'overdue' : row.status === wanted);
          const count = (wanted: string) => all.filter((row) => matches(row, wanted)).length;
          const types = [...new Set(all.map((row) => row.document_type))].sort();
          const needle = text.trim().toLowerCase();
          const shown = all.filter((row) => matches(row, status) && (type === 'all' || row.document_type === type) && (!needle || (row.borrower_name ?? '').toLowerCase().includes(needle)));
          return (
            <section aria-label="Reporting requirements" ref={frame} className="@container min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <Choice
                  label="Status"
                  value={status}
                  onValueChange={setStatus}
                  options={[
                    { value: 'open', label: 'Outstanding', count: count('open') },
                    { value: 'overdue', label: 'Overdue', count: count('overdue') },
                    { value: 'due', label: 'Due', count: count('due') },
                    { value: 'received', label: 'Received', count: count('received') },
                    ...(count('waived') > 0 ? [{ value: 'waived', label: 'Waived', count: count('waived') }] : []),
                    ...(count('untracked') > 0 ? [{ value: 'untracked', label: 'Not tracked', count: count('untracked') }] : []),
                    { value: 'all', label: 'All', count: all.length },
                  ]}
                />
                <Select
                  label="Requirement"
                  hideLabel
                  className="w-full sm:w-auto sm:min-w-52 sm:flex-1 @min-[640px]:w-60 @min-[640px]:flex-none"
                  value={type}
                  onValueChange={setType}
                  options={[{ value: 'all', label: 'All requirements' }, ...types.map((id) => ({ value: id, label: docTypeLabel(id) }))]}
                />
                <Input label="Borrower" hideLabel placeholder="Borrower" className="w-full sm:w-auto sm:min-w-44 sm:flex-1 @min-[640px]:w-56 @min-[640px]:flex-none" leading={<Search size={14} aria-hidden />} value={text} onChange={(event) => setText(event.target.value)} />
                <p className="ml-auto text-caption text-ink-500" aria-live="polite">
                  {shown.length} of {all.length} requirements
                </p>
              </div>
              <DataTable
                key={status}
                caption="Reporting requirements by due date, with status and days late"
                data={shown}
                columns={columns}
                getRowId={(row) => row.id}
                // Outstanding and overdue lead with what is most late; the other views run by due date.
                initialSort={status === 'open' || status === 'overdue' ? { id: 'status' } : { id: 'due', desc: status !== 'due' }}
                selectedRowId={selected}
                onRowActivate={(row) => {
                  const code = codes.get(row.borrower_id);
                  if (!code) return;
                  setChosen(row.id);
                  drawer.openBorrower(code);
                }}
                stickyTop="var(--topbar-h)"
                narrow="stack"
                empty={
                  <EmptyState
                    title="No requirement matches"
                    description="Nothing on the calendar fits this status, requirement and borrower."
                    action={
                      <Button
                        onClick={() => {
                          setStatus('all');
                          setType('all');
                          setText('');
                        }}
                      >
                        Clear filters
                      </Button>
                    }
                  />
                }
              />
              <p className="mt-2 text-caption text-ink-500">A row opens the borrower at a glance; the name opens the borrower page.</p>
              {count('untracked') > 0 ? <p className="mt-1 max-w-[80ch] text-caption text-pretty text-ink-500">{UNTRACKED_NOTE}</p> : null}
            </section>
          );
        }}
      </Load>
    </div>
  );
}

import { Link } from '@tanstack/react-router';
import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useBorrowers, useCalendar } from '@/api/hooks';
import type { Obligation } from '@/api/schema';
import { Button, DataTable, EmptyState, formatDate, Input, PageHeader, Segmented, Select, StatusDot, type DataColumn, type StatusTone } from '@/design';
import { docTypeLabel, quarterLabel } from '@/domain/labels';
import { Load } from './parts';

const STATUS: Record<Obligation['status'], { tone: StatusTone; label: string; emphasis?: boolean }> = {
  overdue: { tone: 'attention', label: 'Overdue', emphasis: true },
  due: { tone: 'neutral', label: 'Due' },
  received: { tone: 'pass', label: 'Received' },
  waived: { tone: 'muted', label: 'Waived' },
};

export function Calendar() {
  const calendar = useCalendar();
  const borrowers = useBorrowers();
  const [status, setStatus] = useState('open');
  const [type, setType] = useState('all');
  const [text, setText] = useState('');
  const codes = useMemo(() => new Map((borrowers.data ?? []).map((row) => [row.id, row.code])), [borrowers.data]);

  const columns = useMemo<Array<DataColumn<Obligation>>>(
    () => [
      { id: 'due', header: 'Due', sortValue: (row) => row.due_date, cell: (row) => <span className="tnum text-ink">{formatDate(row.due_date)}</span> },
      {
        id: 'borrower',
        header: 'Borrower',
        rowHeader: true,
        sortValue: (row) => row.borrower_name,
        cell: (row) => {
          const code = codes.get(row.borrower_id);
          return code ? (
            <Link to="/borrowers/$code" params={{ code }} className="font-medium text-ink hover:text-cobalt-strong hover:underline">
              {row.borrower_name}
            </Link>
          ) : (
            <span className="font-medium text-ink">{row.borrower_name}</span>
          );
        },
      },
      { id: 'type', header: 'Requirement', sortValue: (row) => docTypeLabel(row.document_type), cell: (row) => <span className="text-ink-700">{docTypeLabel(row.document_type)}</span> },
      { id: 'period', header: 'For the period', sortValue: (row) => row.period_end, cell: (row) => <span className="tnum text-ink-700">{row.period_end.slice(5, 7) in { '03': 1, '06': 1, '09': 1, '12': 1 } ? `${quarterLabel(row.period_end)} · ` : ''}{formatDate(row.period_end)}</span> },
      {
        id: 'status',
        header: 'Status',
        sortValue: (row) => row.status,
        cell: (row) => (
          <StatusDot tone={STATUS[row.status].tone} emphasis={STATUS[row.status].emphasis}>
            {STATUS[row.status].label}
          </StatusDot>
        ),
      },
      {
        id: 'received',
        header: 'Received',
        sortValue: (row) => row.received_date,
        cell: (row) => {
          const code = codes.get(row.borrower_id);
          if (!row.received_date) return <span className="text-ink-500">Not received</span>;
          return row.received_document_id && code ? (
            <Link to="/borrowers/$code/documents/$documentId" params={{ code, documentId: row.received_document_id }} className="tnum link">
              {formatDate(row.received_date)}
            </Link>
          ) : (
            <span className="tnum text-ink-700">{formatDate(row.received_date)}</span>
          );
        },
      },
      {
        id: 'late',
        header: 'Days late',
        align: 'right',
        sortValue: (row) => row.days_late,
        cell: (row) => (row.days_late ? <span className={row.status === 'overdue' ? 'tnum font-medium text-amber' : 'tnum text-ink-700'}>{row.days_late}</span> : <span className="text-ink-500">{row.status === 'received' ? 'On time' : 'Not late'}</span>),
      },
    ],
    [codes],
  );

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
          const count = (wanted: string) => all.filter((row) => (wanted === 'open' ? row.status === 'due' || row.status === 'overdue' : row.status === wanted)).length;
          const types = [...new Set(all.map((row) => row.document_type))].sort();
          const needle = text.trim().toLowerCase();
          const shown = all.filter(
            (row) =>
              (status === 'all' || (status === 'open' ? row.status === 'due' || row.status === 'overdue' : row.status === status)) &&
              (type === 'all' || row.document_type === type) &&
              (!needle || (row.borrower_name ?? '').toLowerCase().includes(needle)),
          );
          return (
            <section aria-label="Reporting requirements">
              <div className="mb-3 flex flex-wrap items-end gap-3">
                <Segmented
                  label="Status"
                  value={status}
                  onValueChange={setStatus}
                  options={[
                    { value: 'open', label: 'Outstanding', count: count('open') },
                    { value: 'overdue', label: 'Overdue', count: count('overdue') },
                    { value: 'due', label: 'Due', count: count('due') },
                    { value: 'received', label: 'Received', count: count('received') },
                    { value: 'all', label: 'All', count: all.length },
                  ]}
                />
                <Select label="Requirement" hideLabel className="w-60" value={type} onValueChange={setType} options={[{ value: 'all', label: 'All requirements' }, ...types.map((id) => ({ value: id, label: docTypeLabel(id) }))]} />
                <Input label="Borrower" hideLabel placeholder="Borrower" className="w-56" leading={<Search size={14} aria-hidden />} value={text} onChange={(event) => setText(event.target.value)} />
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
                initialSort={{ id: 'due', desc: status !== 'due' }}
                stickyTop="var(--topbar-h)"
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
            </section>
          );
        }}
      </Load>
    </div>
  );
}

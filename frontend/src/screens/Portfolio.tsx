import { Link, useNavigate } from '@tanstack/react-router';
import { Search } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { compare } from '@/api/decimal';
import { useBorrowers, usePortfolio } from '@/api/hooks';
import type { BorrowerRow, PortfolioSummary } from '@/api/schema';
import { Button, DataTable, EmptyState, formatDate, formatFigure, Input, PageHeader, Select, StatusDot, type DataColumn } from '@/design';
import { humanize, OUTCOME, quarterLabel, STAGE_ORDER, stageLabel } from '@/domain/labels';
import { FactFigure, ProvenanceLegend, SourcedFigure } from '@/source/figures';
import { Load } from './parts';

function Stat({ label, children, note }: { label: string; children: ReactNode; note?: ReactNode }) {
  return (
    <div className="min-w-0 px-5 py-3.5 first:pl-0 last:pr-0">
      <h2 className="eyebrow whitespace-nowrap">{label}</h2>
      <div className="mt-1 text-heading font-semibold text-ink">{children}</div>
      {note ? <div className="mt-0.5 text-caption text-ink-500">{note}</div> : null}
    </div>
  );
}

function commitmentSource(borrower: BorrowerRow) {
  return {
    type: 'record' as const,
    kind: 'system' as const,
    title: `Total commitment, ${borrower.name}`,
    value: formatFigure(borrower.total_commitment ?? '0', 'usd').text,
    note: 'The sum of the commitments on this borrower’s loan records, added by code with exact decimals. Each loan’s commitment is on the Loans tab.',
    rows: [
      ['System', 'Core loan accounting'],
      ['Record', borrower.code],
    ] as Array<[string, string]>,
    link: { to: `/borrowers/${borrower.code}/loans`, label: 'Open the loans' },
  };
}

function totalSource(title: string, value: string, summary: PortfolioSummary, what: string) {
  return {
    type: 'record' as const,
    kind: 'calculated' as const,
    title,
    value: formatFigure(value, 'usd').text,
    note: `${what} Added by code with exact decimals; the table below shows each borrower’s part, and each of those opens its own source.`,
    rows: [
      ['Borrowers', String(summary.borrowers)],
      ['Loans', String(summary.loans)],
      ['As of', formatDate(summary.as_of)],
    ] as Array<[string, string]>,
  };
}

function PortfolioTable({ borrowers, summary }: { borrowers: BorrowerRow[]; summary: PortfolioSummary }) {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [status, setStatus] = useState('all');
  const [stage, setStage] = useState('all');

  const filtered = useMemo(() => {
    const needle = text.trim().toLowerCase();
    return borrowers.filter(
      (row) =>
        (!needle || `${row.name} ${row.industry} ${row.analyst ?? ''} ${row.relationship_manager ?? ''}`.toLowerCase().includes(needle)) &&
        (status === 'all' || (status === 'none' ? !row.covenant_status : row.covenant_status === status)) &&
        (stage === 'all' || row.latest_cycle?.stage === stage),
    );
  }, [borrowers, text, status, stage]);

  const stages = STAGE_ORDER.filter((id) => borrowers.some((row) => row.latest_cycle?.stage === id));
  const statuses = (Object.keys(OUTCOME) as Array<keyof typeof OUTCOME>).filter((id) => borrowers.some((row) => row.covenant_status === id));

  const columns = useMemo<Array<DataColumn<BorrowerRow>>>(() => {
    const exposure = (row: BorrowerRow) => summary.borrower_exposure[row.id] ?? {};
    const sortable = (value: string | null | undefined) => (value === null || value === undefined ? null : Number.parseInt(value.split('.')[0] ?? '0', 10));
    return [
      {
        id: 'name',
        header: 'Borrower',
        rowHeader: true,
        sortValue: (row) => row.name,
        cell: (row) => (
          <Link to="/borrowers/$code" params={{ code: row.code }} onClick={(event) => event.stopPropagation()} className="font-medium text-ink hover:text-cobalt-strong hover:underline">
            {row.name}
          </Link>
        ),
      },
      {
        id: 'rating',
        header: 'Rating',
        align: 'right',
        sortValue: (row) => row.risk_rating,
        cell: (row) => <span className="tnum text-ink">{row.risk_rating ?? 'Not rated'}</span>,
      },
      {
        id: 'commitment',
        header: 'Commitment',
        align: 'right',
        sortValue: (row) => sortable(row.total_commitment),
        cell: (row) => (
          <SourcedFigure value={row.total_commitment} unit="usd" kind="system" label={`Total commitment, ${row.name}`} source={commitmentSource(row)} scale={1000} unitMark={false} align="column" />
        ),
      },
      {
        id: 'line',
        header: 'Line drawn',
        align: 'right',
        sortValue: (row) => sortable(exposure(row).revolver_outstanding?.value),
        cell: (row) => <FactFigure fact={exposure(row).revolver_outstanding} scale={1000} unitMark={false} align="column" absent="No line of credit balance on record" />,
      },
      {
        id: 'term',
        header: 'Term loan',
        align: 'right',
        sortValue: (row) => sortable(exposure(row).term_loan_outstanding?.value),
        cell: (row) => <FactFigure fact={exposure(row).term_loan_outstanding} scale={1000} unitMark={false} align="column" absent="No term loan balance on record" />,
      },
      {
        id: 'covenants',
        header: 'Covenants',
        sortValue: (row) => (row.covenant_status ? OUTCOME[row.covenant_status].rank : 9),
        cell: (row) =>
          row.covenant_status ? (
            <StatusDot tone={OUTCOME[row.covenant_status].tone} emphasis={OUTCOME[row.covenant_status].emphasis}>
              {OUTCOME[row.covenant_status].label}
            </StatusDot>
          ) : (
            <StatusDot tone="muted">Not tested yet</StatusDot>
          ),
      },
      {
        id: 'signals',
        header: 'Signals',
        align: 'right',
        sortValue: (row) => row.open_signals,
        cell: (row) =>
          row.open_signals > 0 ? (
            <Link to="/borrowers/$code/signals" params={{ code: row.code }} onClick={(event) => event.stopPropagation()} className="tnum link" aria-label={`${row.open_signals} open signals for ${row.name}`}>
              {row.open_signals}
            </Link>
          ) : (
            <span className="tnum text-ink-500">0</span>
          ),
      },
      {
        id: 'items',
        header: 'Items',
        align: 'right',
        sortValue: (row) => row.open_work_items,
        cell: (row) =>
          row.open_work_items > 0 ? (
            <Link to="/borrowers/$code" params={{ code: row.code }} onClick={(event) => event.stopPropagation()} className="tnum link" aria-label={`${row.open_work_items} open items for ${row.name}`}>
              {row.open_work_items}
            </Link>
          ) : (
            <span className="tnum text-ink-500">0</span>
          ),
      },
      {
        id: 'stage',
        header: 'Stage',
        sortValue: (row) => (row.latest_cycle ? STAGE_ORDER.indexOf(row.latest_cycle.stage) : 99),
        cell: (row) => <span className="text-ink-700">{row.latest_cycle ? (row.latest_cycle.stage === 'review_prep' ? 'Review prep' : stageLabel(row.latest_cycle.stage)) : 'No cycle'}</span>,
      },
    ];
  }, [summary]);

  return (
    <section aria-labelledby="book-heading">
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <h2 id="book-heading" className="sr-only">
          Borrowers
        </h2>
        <Input label="Search borrowers" hideLabel placeholder="Search by name, industry or person" className="w-72" leading={<Search size={14} aria-hidden />} value={text} onChange={(event) => setText(event.target.value)} />
        <Select
          label="Covenant status"
          hideLabel
          className="w-56"
          value={status}
          onValueChange={setStatus}
          options={[{ value: 'all', label: 'All covenant statuses' }, ...statuses.map((id) => ({ value: id, label: OUTCOME[id].label })), { value: 'none', label: 'Not tested yet' }]}
        />
        <Select label="Cycle stage" hideLabel className="w-48" value={stage} onValueChange={setStage} options={[{ value: 'all', label: 'All stages' }, ...stages.map((id) => ({ value: id, label: stageLabel(id) }))]} />
        <p className="ml-auto text-caption text-ink-500" aria-live="polite">
          {filtered.length} of {borrowers.length} borrowers · amounts in USD thousands
        </p>
      </div>
      <DataTable
        caption="Borrowers with rating, exposure in US dollars thousands, covenant status, open signals, open work items and cycle stage"
        data={filtered}
        columns={columns}
        getRowId={(row) => row.id}
        initialSort={{ id: 'covenants' }}
        onRowActivate={(row) => void navigate({ to: '/borrowers/$code', params: { code: row.code } })}
        stickyTop="var(--topbar-h)"
        empty={
          <EmptyState
            title="No borrower matches"
            description="Nothing in the book fits this search and these filters."
            action={
              <Button
                onClick={() => {
                  setText('');
                  setStatus('all');
                  setStage('all');
                }}
              >
                Clear filters
              </Button>
            }
          />
        }
      />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <p className="text-caption text-ink-500">Enter opens the borrower. Every amount opens its source.</p>
        <ProvenanceLegend kinds={['system', 'calculated']} />
      </div>
    </section>
  );
}

export function Portfolio() {
  const borrowers = useBorrowers();
  const portfolio = usePortfolio();
  const summary = portfolio.data;
  const breaches = summary?.covenants.by_outcome.filter((entry) => entry.outcome === 'breach' || entry.outcome === 'breach_reported_compliant').reduce((sum, entry) => sum + entry.count, 0);

  return (
    <div data-ready={borrowers.data && summary ? '' : undefined} className="space-y-5">
      <PageHeader
        eyebrow="Bank of Stoic · Commercial lending"
        title="Portfolio"
        meta={summary ? <span>{summary.period_end ? `Latest period: quarter ended ${formatDate(summary.period_end)}` : 'No period tested yet'} · balances from the system of record</span> : undefined}
      />
      <Load query={portfolio} what="The portfolio summary" rows={3}>
        {(data) => (
          <section aria-label="Portfolio figures" className="grid grid-cols-5 divide-x divide-hairline-strong border-t border-b border-t-ink border-b-hairline-strong">
            <Stat label="Total commitment, USD millions" note={`${data.loans} loans to ${data.borrowers} borrowers`}>
              <SourcedFigure
                value={data.exposure.commitment}
                unit="usd"
                kind="calculated"
                label="Total commitment across the book"
                source={totalSource('Total commitment', data.exposure.commitment, data, 'The sum of every loan’s commitment in the loan records.')}
                scale={1000000}
                dp={1}
                unitMark={false}
                weight="semibold"
              />
            </Stat>
            <Stat
              label="Outstanding, USD millions"
              note={
                compare(data.exposure.commitment, '0') > 0 ? (
                  <span className="inline-flex flex-wrap items-baseline gap-x-1.5">
                    Lines
                    <SourcedFigure
                      value={data.exposure.revolver_outstanding}
                      unit="usd"
                      kind="calculated"
                      label="Lines of credit outstanding across the book"
                      source={totalSource('Lines of credit outstanding', data.exposure.revolver_outstanding, data, 'The sum of each borrower’s latest line of credit balance from the system of record.')}
                      scale={1000000}
                      dp={1}
                      unitMark={false}
                    />
                    · term loans
                    <SourcedFigure
                      value={data.exposure.term_loan_outstanding}
                      unit="usd"
                      kind="calculated"
                      label="Term loans outstanding across the book"
                      source={totalSource('Term loans outstanding', data.exposure.term_loan_outstanding, data, 'The sum of each borrower’s latest term loan balance from the system of record.')}
                      scale={1000000}
                      dp={1}
                      unitMark={false}
                    />
                  </span>
                ) : undefined
              }
            >
              <SourcedFigure
                value={data.exposure.outstanding}
                unit="usd"
                kind="calculated"
                label="Total outstanding across the book"
                source={totalSource('Total outstanding', data.exposure.outstanding, data, 'The sum of each borrower’s latest line of credit and term loan balances from the system of record.')}
                scale={1000000}
                dp={1}
                unitMark={false}
                weight="semibold"
              />
            </Stat>
            <Stat label="Covenant tests" note={data.period_end ? `${quarterLabel(data.period_end)}, calculated by code` : undefined}>
              <span className="tnum">{data.covenants.tests}</span>
              {breaches ? (
                <StatusDot tone="breach" emphasis className="ml-3 text-body">
                  {breaches} in breach
                </StatusDot>
              ) : (
                <StatusDot tone="pass" className="ml-3 text-body font-regular">
                  None in breach
                </StatusDot>
              )}
            </Stat>
            <Stat label="Open signals" note={data.signals.by_severity.map((entry) => `${entry.count} ${entry.severity}`).join(' · ')}>
              <span className="tnum">{data.signals.open}</span>
            </Stat>
            <Stat
              label="Open items"
              note={
                <Link to="/command-centre" className="link">
                  Open the work queue
                </Link>
              }
            >
              <span className="tnum">{data.work_items.open}</span>
            </Stat>
          </section>
        )}
      </Load>
      <Load query={borrowers} what="The borrowers" rows={12}>
        {(rows) => (summary ? <PortfolioTable borrowers={rows} summary={summary} /> : null)}
      </Load>
    </div>
  );
}

/** The borrower directory: who they are and who looks after them. The portfolio page has the numbers. */
export function Borrowers() {
  const borrowers = useBorrowers();
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const columns = useMemo<Array<DataColumn<BorrowerRow>>>(
    () => [
      {
        id: 'name',
        header: 'Borrower',
        rowHeader: true,
        sortValue: (row) => row.name,
        cell: (row) => (
          <Link to="/borrowers/$code" params={{ code: row.code }} onClick={(event) => event.stopPropagation()} className="font-medium text-ink hover:text-cobalt-strong hover:underline">
            {row.name}
          </Link>
        ),
      },
      { id: 'code', header: 'Record', sortValue: (row) => row.code, cell: (row) => <span className="ident text-ink-700">{row.code}</span> },
      { id: 'industry', header: 'Industry', sortValue: (row) => row.industry, cell: (row) => <span className="text-ink-700">{humanize(row.industry)}</span> },
      { id: 'rm', header: 'Relationship manager', sortValue: (row) => row.relationship_manager, cell: (row) => row.relationship_manager ?? <span className="text-ink-500">Not assigned</span> },
      { id: 'analyst', header: 'Credit analyst', sortValue: (row) => row.analyst, cell: (row) => row.analyst ?? <span className="text-ink-500">Not assigned</span> },
      {
        id: 'stage',
        header: 'Cycle stage',
        sortValue: (row) => (row.latest_cycle ? STAGE_ORDER.indexOf(row.latest_cycle.stage) : 99),
        cell: (row) => <span className="text-ink-700">{row.latest_cycle ? stageLabel(row.latest_cycle.stage) : 'No cycle'}</span>,
      },
    ],
    [],
  );
  return (
    <div data-ready={borrowers.data ? '' : undefined} className="space-y-5">
      <PageHeader eyebrow="Bank of Stoic · Commercial lending" title="Borrowers" meta={<span>Open a borrower for its loans, documents, spreads, covenants and reviews</span>} />
      <Load query={borrowers} what="The borrowers" rows={12}>
        {(rows) => {
          const needle = text.trim().toLowerCase();
          const filtered = rows.filter((row) => !needle || `${row.name} ${row.code} ${row.industry} ${row.analyst ?? ''} ${row.relationship_manager ?? ''}`.toLowerCase().includes(needle));
          return (
            <section aria-label="Borrower directory">
              <div className="mb-3 flex items-end gap-3">
                <Input label="Search borrowers" hideLabel placeholder="Search by name, record, industry or person" className="w-80" leading={<Search size={14} aria-hidden />} value={text} onChange={(event) => setText(event.target.value)} />
                <p className="ml-auto text-caption text-ink-500" aria-live="polite">
                  {filtered.length} of {rows.length} borrowers
                </p>
              </div>
              <DataTable
                caption="Borrower directory"
                data={filtered}
                columns={columns}
                getRowId={(row) => row.id}
                initialSort={{ id: 'name' }}
                onRowActivate={(row) => void navigate({ to: '/borrowers/$code', params: { code: row.code } })}
                stickyTop="var(--topbar-h)"
                empty={<EmptyState title="No borrower matches" description="Nothing in the book fits this search." action={<Button onClick={() => setText('')}>Clear the search</Button>} />}
              />
            </section>
          );
        }}
      </Load>
    </div>
  );
}

import { Link, useRouterState } from '@tanstack/react-router';
import { ArrowRight, Search, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState, useSyncExternalStore, type CSSProperties, type ReactNode } from 'react';
import { useBorrowers, usePortfolio } from '@/api/hooks';
import type { BorrowerRow, PortfolioSummary } from '@/api/schema';
import type { CovenantOutcome, Severity } from '@/api/types';
import { barFill, Button, Card, DataTable, EmptyState, formatDate, formatFigure, Input, PageHeader, Select, StackedBar, type BarFill, type DataColumn } from '@/design';
import { humanize, OUTCOME, quarterLabel, SEVERITY_LABEL, SEVERITY_RANK, STAGE_ORDER, stageLabel } from '@/domain/labels';
import { HeadroomMeter, OutcomeMark } from '@/drawer/BorrowerTearSheet';
import { useWorkspaceDrawer } from '@/drawer/context';
import { cx } from '@/lib/cx';
import { FactFigure, ProvenanceLegend, SourcedFigure } from '@/source/figures';
import { Load } from './parts';

/* ── Fitting the page ─────────────────────────────────────────────────── */

/**
 * The width of an element, as it changes. The workspace drawer takes 520 px from the page when it
 * opens, so the room a table has does not follow the window: the table asks its own frame.
 * Null until measured (and where nothing can be measured), which callers read as "plenty of room".
 */
function useWidth(): [(node: HTMLElement | null) => (() => void) | undefined, number | null] {
  const [width, setWidth] = useState<number | null>(null);
  const ref = useCallback((node: HTMLElement | null) => {
    if (!node) return undefined;
    const measure = () => setWidth(node.clientWidth || null);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

function useMedia(query: string): boolean {
  const subscribe = useCallback(
    (notify: () => void) => {
      const list = window.matchMedia?.(query);
      list?.addEventListener('change', notify);
      return () => list?.removeEventListener('change', notify);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => window.matchMedia?.(query).matches ?? false);
}
/** On a phone the table is set out as a labelled list, so a column costs a line, not width. */
const useIsPhone = () => useMedia('(width < 640px)');
/** From 1200 px the open drawer stands beside the page and narrows it; below that it lies over the page. */
function useDrawerBeside(): boolean {
  const wide = useMedia('(width >= 1200px)');
  const { open } = useWorkspaceDrawer();
  return wide && open;
}

/**
 * What a table shows in a frame of at least `min` pixels: which columns, how wide the borrower's
 * name may count on being, and where the headroom meter sits. The tear-sheet always has the rest.
 * The widest layout comes first; the last one has `min: 0`.
 */
interface Layout {
  min: number;
  columns: string[];
  nameMin: string;
  meter: 'wide' | 'slim' | 'under';
}
/** Null is "not measured": the layout with the most in it. */
const layoutFor = (layouts: Layout[], width: number | null): Layout => layouts.find((layout) => width === null || width >= layout.min) ?? layouts[layouts.length - 1]!;

/** A control inside a row acts for itself: a click on it does not also open the row. */
function Own({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span role="presentation" className={className} onClick={(event) => event.stopPropagation()}>
      {children}
    </span>
  );
}

/* ── Columns the portfolio and the directory share ────────────────────── */

function nameColumn(minWidth: string): DataColumn<BorrowerRow> {
  return {
    id: 'name',
    header: 'Borrower',
    rowHeader: true,
    wrap: true,
    sortValue: (row) => row.name,
    cell: (row) => (
      // The name keeps a floor of its own, so the figure columns cannot squeeze it onto three lines.
      <span className="block sm:min-w-(--name-min)" style={{ '--name-min': minWidth } as CSSProperties}>
        <Link to="/borrowers/$code" params={{ code: row.code }} onClick={(event) => event.stopPropagation()} className="font-medium text-ink hover:text-cobalt-strong hover:underline">
          {row.name}
        </Link>
      </span>
    ),
  };
}

const covenantColumn: DataColumn<BorrowerRow> = {
  id: 'covenants',
  header: 'Covenants',
  sortValue: (row) => (row.covenant_status ? OUTCOME[row.covenant_status].rank : 9),
  cell: (row) => <OutcomeMark outcome={row.covenant_status} />,
};

/** The tightest covenant of the latest period: the stored headroom, with a meter of where it sits. */
function headroomColumn(meter: Layout['meter']): DataColumn<BorrowerRow> {
  return {
    id: 'headroom',
    header: 'Headroom',
    align: 'right',
    sortValue: (row) => (row.tightest_headroom ? Number(row.tightest_headroom.value) : null),
    cell: (row) => {
      const fact = row.tightest_headroom;
      if (!fact) return <FactFigure fact={fact} absent="No covenant tested for the latest period" />;
      return meter === 'under' ? (
        // Where the frame is tightest the meter sits under the figure, so the figure keeps the row's baseline.
        <Own className="relative inline-flex items-center">
          <FactFigure fact={fact} />
          <HeadroomMeter fact={fact} className="absolute right-[13px] -bottom-[5px] h-1! w-10!" />
        </Own>
      ) : (
        <Own className="inline-flex items-center gap-2.5">
          <HeadroomMeter fact={fact} className={meter === 'slim' ? 'w-10!' : undefined} />
          <FactFigure fact={fact} />
        </Own>
      );
    },
  };
}

const stageColumn = (header: string): DataColumn<BorrowerRow> => ({
  id: 'stage',
  header,
  sortValue: (row) => (row.latest_cycle ? STAGE_ORDER.indexOf(row.latest_cycle.stage) : 99),
  cell: (row) => <span className="text-ink-700">{row.latest_cycle ? (row.latest_cycle.stage === 'review_prep' ? 'Review prep' : stageLabel(row.latest_cycle.stage)) : 'No cycle'}</span>,
});

/** The borrower whose tear-sheet is open, and the way to open one: the same on every borrower table. */
function useTearSheetRows(rows: BorrowerRow[] | undefined, layout: Layout) {
  const drawer = useWorkspaceDrawer();
  const selected = drawer.open && drawer.borrowerCode ? (rows?.find((row) => row.code === drawer.borrowerCode)?.id ?? null) : null;
  // The drawer narrows the page as it opens, so the table changes its layout and the rows move.
  // The one just chosen is brought back into view, once on choosing it and again when the layout settles.
  useEffect(() => {
    if (!selected) return undefined;
    const frame = requestAnimationFrame(() => {
      const row = document.querySelector('main tr[data-row][aria-selected="true"]');
      if (!row) return;
      const { top, bottom } = row.getBoundingClientRect();
      const above = top - 96; // the top bar and the table's own header stay fixed over the page
      const below = bottom - (window.innerHeight - 16);
      if (above < 0) window.scrollBy({ top: above });
      else if (below > 0) window.scrollBy({ top: below });
    });
    return () => cancelAnimationFrame(frame);
  }, [selected, layout]);
  return { selectedRowId: selected, onRowActivate: (row: BorrowerRow) => drawer.openBorrower(row.code) };
}

/* ── Portfolio summary ────────────────────────────────────────────────── */

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

function SummaryCard({ title, note, children }: { title: string; note?: ReactNode; children: ReactNode }) {
  return (
    <Card className="flex min-w-0 flex-col px-4 pt-3 pb-3.5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="eyebrow">{title}</h2>
        {note ? <span className="text-caption whitespace-nowrap text-ink-500">{note}</span> : null}
      </div>
      {children}
    </Card>
  );
}

/** The one large number of a card, with what it counts beside it. */
function Headline({ children, note }: { children: ReactNode; note: ReactNode }) {
  return (
    <p className="mt-1 mb-2.5 flex flex-wrap items-baseline gap-x-2">
      <span className="text-page font-semibold tracking-[-0.018em] text-ink">{children}</span>
      <span className="text-caption text-ink-500">{note}</span>
    </p>
  );
}

function Swatch({ fill }: { fill: BarFill }) {
  return <span aria-hidden className="size-2 shrink-0 rounded-xs" style={{ background: barFill(fill) }} />;
}

const legendRow = '-mx-1.5 flex min-h-6 w-[calc(100%+12px)] items-center gap-2 rounded-xs px-1.5 text-left text-body text-ink-700';
const legendAction = 't-colors hover:bg-hover hover:text-ink aria-pressed:bg-sunken aria-pressed:font-medium aria-pressed:text-ink';
const legendCount = 'tnum ml-auto pl-3 font-semibold text-ink';

const OUTCOME_FILL: Record<CovenantOutcome, BarFill> = {
  breach_reported_compliant: 'breach',
  breach: 'breach',
  cannot_test: 'attention',
  compliant_variance: 'attention',
  compliant: 'pass',
};
/** Critical and high carry their colour; the rest are quantity, on the ink ramp. */
const SEVERITY_FILL: Record<Severity, BarFill> = { critical: 'breach', high: 'attention', medium: 4, low: 2 };
const bySeverity = <T extends { severity: Severity }>(rows: T[]) => [...rows].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);

const millions = { scale: 1000000, dp: 1, unitMark: false } as const;

/**
 * Four cards. Beside the open drawer they keep their number and their bar and drop the rows under
 * it, so the table a person is working stays where it was; the rows return when the drawer closes.
 */
function Summary({ data, status, onStatus }: { data: PortfolioSummary; status: string; onStatus: (status: string) => void }) {
  const brief = useDrawerBeside();
  const outcomes = [...data.covenants.by_outcome].sort((a, b) => OUTCOME[a.outcome].rank - OUTCOME[b.outcome].rank);
  const signals = bySeverity(data.signals.by_severity);
  const items = bySeverity(data.work_items.by_severity);
  const toggle = (outcome: string) => onStatus(status === outcome ? 'all' : outcome);
  const lines = totalSource('Lines of credit outstanding', data.exposure.revolver_outstanding, data, 'The sum of each borrower’s latest line of credit balance from the system of record.');
  const terms = totalSource('Term loans outstanding', data.exposure.term_loan_outstanding, data, 'The sum of each borrower’s latest term loan balance from the system of record.');
  return (
    <section aria-label="Portfolio figures" className="@container">
      <div className="grid gap-3 @min-[480px]:grid-cols-2 @min-[960px]:grid-cols-4">
        <SummaryCard title="Exposure" note="USD millions">
          <Headline note={`committed · ${data.loans} loans to ${data.borrowers} borrowers`}>
            <SourcedFigure
              value={data.exposure.commitment}
              unit="usd"
              kind="calculated"
              label="Total commitment across the book"
              source={totalSource('Total commitment', data.exposure.commitment, data, 'The sum of every loan’s commitment in the loan records.')}
              weight="semibold"
              {...millions}
            />
          </Headline>
          {/* Widths only. The amounts are the sourced figures in the rows below, so the bar itself says nothing to a pointer or a screen reader. */}
          <div aria-hidden className="pointer-events-none">
            <StackedBar
              label="Outstanding by loan type"
              segments={[
                { id: 'lines', label: 'Lines of credit', count: Number(data.exposure.revolver_outstanding), fill: 5 },
                { id: 'terms', label: 'Term loans', count: Number(data.exposure.term_loan_outstanding), fill: 3 },
              ]}
            />
          </div>
          <ul className="mt-2" hidden={brief}>
            <li className={cx(legendRow, 'font-medium text-ink')}>
              Outstanding
              <span className="ml-auto pl-3">
                <SourcedFigure
                  value={data.exposure.outstanding}
                  unit="usd"
                  kind="calculated"
                  label="Total outstanding across the book"
                  source={totalSource('Total outstanding', data.exposure.outstanding, data, 'The sum of each borrower’s latest line of credit and term loan balances from the system of record.')}
                  weight="semibold"
                  {...millions}
                />
              </span>
            </li>
            <li className={legendRow}>
              <Swatch fill={5} />
              Lines of credit
              <span className="ml-auto pl-3">
                <SourcedFigure value={data.exposure.revolver_outstanding} unit="usd" kind="calculated" label="Lines of credit outstanding across the book" source={lines} {...millions} />
              </span>
            </li>
            <li className={legendRow}>
              <Swatch fill={3} />
              Term loans
              <span className="ml-auto pl-3">
                <SourcedFigure value={data.exposure.term_loan_outstanding} unit="usd" kind="calculated" label="Term loans outstanding across the book" source={terms} {...millions} />
              </span>
            </li>
          </ul>
        </SummaryCard>

        <SummaryCard title="Covenant tests" note={data.period_end ? quarterLabel(data.period_end) : undefined}>
          <Headline note="tests, calculated by code">
            <span className="tnum">{data.covenants.tests}</span>
          </Headline>
          <StackedBar
            label="Covenant tests by outcome"
            segments={outcomes.map((entry) => ({ id: entry.outcome, label: OUTCOME[entry.outcome].label, count: entry.count, fill: OUTCOME_FILL[entry.outcome] }))}
            onSelect={toggle}
            selectedId={status in OUTCOME ? status : null}
          />
          <ul className="mt-2" hidden={brief}>
            {outcomes.map((entry) => (
              <li key={entry.outcome}>
                <button
                  type="button"
                  aria-pressed={status === entry.outcome}
                  aria-label={`${OUTCOME[entry.outcome].label}: ${entry.count} ${entry.count === 1 ? 'test' : 'tests'}. Show the borrowers whose worst result this is.`}
                  onClick={() => toggle(entry.outcome)}
                  className={cx(legendRow, legendAction)}
                >
                  <Swatch fill={OUTCOME_FILL[entry.outcome]} />
                  {OUTCOME[entry.outcome].label}
                  <span className={legendCount}>{entry.count}</span>
                </button>
              </li>
            ))}
          </ul>
        </SummaryCard>

        <SummaryCard title="Open signals" note="by severity">
          <Headline note="early warning signals">
            <span className="tnum">{data.signals.open}</span>
          </Headline>
          <StackedBar label="Open signals by severity" segments={signals.map((entry) => ({ id: entry.severity, label: SEVERITY_LABEL[entry.severity], count: entry.count, fill: SEVERITY_FILL[entry.severity] }))} />
          <ul className="mt-2" hidden={brief}>
            {signals.map((entry) => (
              <li key={entry.severity} className={legendRow}>
                <Swatch fill={SEVERITY_FILL[entry.severity]} />
                {SEVERITY_LABEL[entry.severity]}
                <span className={legendCount}>{entry.count}</span>
              </li>
            ))}
          </ul>
        </SummaryCard>

        <SummaryCard
          title="Open items"
          note={
            <Link to="/command-centre" className="link inline-flex items-center gap-0.5 font-medium">
              Command centre
              <ArrowRight size={12} aria-hidden />
            </Link>
          }
        >
          <Headline note="need a person">
            <span className="tnum">{data.work_items.open}</span>
          </Headline>
          <StackedBar label="Open items by severity" segments={items.map((entry) => ({ id: entry.severity, label: SEVERITY_LABEL[entry.severity], count: entry.count, fill: SEVERITY_FILL[entry.severity] }))} />
          <ul className="mt-2" hidden={brief}>
            {items.map((entry) => (
              <li key={entry.severity}>
                <Link
                  to="/command-centre"
                  search={{ severity: entry.severity }}
                  aria-label={`${SEVERITY_LABEL[entry.severity]}: ${entry.count} open ${entry.count === 1 ? 'item' : 'items'}. Open them in the command centre.`}
                  className={cx(legendRow, legendAction)}
                >
                  <Swatch fill={SEVERITY_FILL[entry.severity]} />
                  {SEVERITY_LABEL[entry.severity]}
                  <span className={legendCount}>{entry.count}</span>
                </Link>
              </li>
            ))}
          </ul>
        </SummaryCard>
      </div>
    </section>
  );
}

/* ── Portfolio table ──────────────────────────────────────────────────── */

const PORTFOLIO_LAYOUTS: Layout[] = [
  { min: 1300, columns: ['name', 'rating', 'commitment', 'line', 'term', 'covenants', 'headroom', 'signals', 'items', 'stage'], nameMin: '210px', meter: 'wide' },
  { min: 1160, columns: ['name', 'rating', 'commitment', 'line', 'term', 'covenants', 'headroom', 'signals', 'items'], nameMin: '210px', meter: 'slim' },
  { min: 1000, columns: ['name', 'rating', 'commitment', 'line', 'covenants', 'headroom', 'signals'], nameMin: '210px', meter: 'wide' },
  { min: 900, columns: ['name', 'commitment', 'line', 'covenants', 'headroom', 'signals'], nameMin: '190px', meter: 'slim' },
  { min: 700, columns: ['name', 'commitment', 'covenants', 'headroom'], nameMin: '190px', meter: 'slim' },
  { min: 560, columns: ['name', 'covenants', 'headroom'], nameMin: '190px', meter: 'slim' },
  { min: 0, columns: ['name', 'covenants', 'headroom'], nameMin: '150px', meter: 'under' },
];
/** On a phone the table is a labelled list: a column costs a line, not width. */
const PORTFOLIO_ON_A_PHONE: Layout = { min: 0, columns: ['name', 'rating', 'commitment', 'covenants', 'headroom', 'stage'], nameMin: '0px', meter: 'wide' };

function PortfolioTable({ borrowers, summary, status, onStatus }: { borrowers: BorrowerRow[]; summary: PortfolioSummary; status: string; onStatus: (status: string) => void }) {
  const [text, setText] = useState('');
  const [stage, setStage] = useState('all');
  const [frame, width] = useWidth();
  const phone = useIsPhone();
  const layout = phone ? PORTFOLIO_ON_A_PHONE : layoutFor(PORTFOLIO_LAYOUTS, width);
  const rows = useTearSheetRows(borrowers, layout);

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
  const statuses = (Object.keys(OUTCOME) as CovenantOutcome[]).filter((id) => id === status || borrowers.some((row) => row.covenant_status === id));

  const columns = useMemo<Array<DataColumn<BorrowerRow>>>(() => {
    const exposure = (row: BorrowerRow) => summary.borrower_exposure[row.id] ?? {};
    const sortable = (value: string | null | undefined) => (value === null || value === undefined ? null : Number.parseInt(value.split('.')[0] ?? '0', 10));
    const all: Array<DataColumn<BorrowerRow>> = [
      nameColumn(layout.nameMin),
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
          <Own>
            <SourcedFigure value={row.total_commitment} unit="usd" kind="system" label={`Total commitment, ${row.name}`} source={commitmentSource(row)} scale={1000} unitMark={false} align="column" />
          </Own>
        ),
      },
      {
        id: 'line',
        header: 'Line drawn',
        align: 'right',
        sortValue: (row) => sortable(exposure(row).revolver_outstanding?.value),
        cell: (row) => (
          <Own>
            <FactFigure fact={exposure(row).revolver_outstanding} scale={1000} unitMark={false} align="column" absent="No line of credit balance on record" />
          </Own>
        ),
      },
      {
        id: 'term',
        header: 'Term loan',
        align: 'right',
        sortValue: (row) => sortable(exposure(row).term_loan_outstanding?.value),
        cell: (row) => (
          <Own>
            <FactFigure fact={exposure(row).term_loan_outstanding} scale={1000} unitMark={false} align="column" absent="No term loan balance on record" />
          </Own>
        ),
      },
      covenantColumn,
      headroomColumn(layout.meter),
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
        cell: (row) => <span className={cx('tnum', row.open_work_items > 0 ? 'font-medium text-ink' : 'text-ink-500')}>{row.open_work_items}</span>,
      },
      stageColumn('Stage'),
    ];
    return all.filter((column) => layout.columns.includes(column.id));
  }, [summary, layout]);

  const clear = () => {
    setText('');
    onStatus('all');
    setStage('all');
  };

  return (
    <section aria-labelledby="book-heading" ref={frame} className="@container min-w-0">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 id="book-heading" className="sr-only">
          Borrowers
        </h2>
        <Input label="Search borrowers" hideLabel placeholder="Search by name, industry or person" className="w-full @min-[640px]:w-72" leading={<Search size={14} aria-hidden />} value={text} onChange={(event) => setText(event.target.value)} />
        <Select
          label="Covenant status"
          hideLabel
          className="w-full sm:w-auto sm:min-w-52 sm:flex-1 @min-[640px]:w-56 @min-[640px]:flex-none"
          value={status}
          onValueChange={onStatus}
          options={[{ value: 'all', label: 'All covenant statuses' }, ...statuses.map((id) => ({ value: id, label: OUTCOME[id].label })), { value: 'none', label: 'Not tested yet' }]}
        />
        <Select label="Cycle stage" hideLabel className="w-full sm:w-auto sm:min-w-44 sm:flex-1 @min-[640px]:w-48 @min-[640px]:flex-none" value={stage} onValueChange={setStage} options={[{ value: 'all', label: 'All stages' }, ...stages.map((id) => ({ value: id, label: stageLabel(id) }))]} />
        <p className="ml-auto text-caption text-ink-500" aria-live="polite">
          {filtered.length} of {borrowers.length} borrowers · amounts in USD thousands
        </p>
      </div>
      {status in OUTCOME ? (
        <p data-active-filter className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-body text-ink-700">
          <span>
            Showing the borrowers whose worst covenant result for the latest period is <span className="font-medium text-ink">{OUTCOME[status as CovenantOutcome].label.toLowerCase()}</span>.
          </span>
          <button type="button" onClick={() => onStatus('all')} className="link inline-flex items-center gap-1 font-medium">
            <X size={12} aria-hidden />
            Clear filter
          </button>
        </p>
      ) : null}
      <DataTable
        caption="Borrowers with rating, exposure in US dollars thousands, covenant status, tightest covenant headroom, open signals, open work items and cycle stage"
        data={filtered}
        columns={columns}
        getRowId={(row) => row.id}
        initialSort={{ id: 'covenants' }}
        stickyTop="var(--topbar-h)"
        narrow="stack"
        empty={<EmptyState title="No borrower matches" description="Nothing in the book fits this search and these filters." action={<Button onClick={clear}>Clear filters</Button>} />}
        {...rows}
      />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <p className="text-caption text-ink-500">A row opens the borrower at a glance; the name opens the borrower page. Every amount opens its source.</p>
        <ProvenanceLegend kinds={['system', 'calculated']} />
      </div>
    </section>
  );
}

export function Portfolio() {
  const borrowers = useBorrowers();
  const portfolio = usePortfolio();
  const summary = portfolio.data;
  // A link from another screen may ask for one outcome: /portfolio?outcome=breach
  const asked = useRouterState({ select: (state) => (state.location.search as Record<string, unknown>).outcome });
  const [status, setStatus] = useState(() => (typeof asked === 'string' && (asked in OUTCOME || asked === 'none') ? asked : 'all'));

  return (
    <div data-ready={borrowers.data && summary ? '' : undefined} className="space-y-5">
      <PageHeader
        eyebrow="Bank of Stoic · Commercial lending"
        title="Portfolio"
        meta={summary ? <span>{summary.period_end ? `Latest period: quarter ended ${formatDate(summary.period_end)}` : 'No period tested yet'} · balances from the system of record</span> : undefined}
      />
      <Load query={portfolio} what="The portfolio summary" rows={4}>
        {(data) => <Summary data={data} status={status} onStatus={setStatus} />}
      </Load>
      <Load query={borrowers} what="The borrowers" rows={12}>
        {(rows) => (summary ? <PortfolioTable borrowers={rows} summary={summary} status={status} onStatus={setStatus} /> : null)}
      </Load>
    </div>
  );
}

/* ── Borrower directory ───────────────────────────────────────────────── */

const DIRECTORY_LAYOUTS: Layout[] = [
  { min: 1400, columns: ['name', 'code', 'industry', 'rm', 'analyst', 'covenants', 'headroom', 'stage'], nameMin: '210px', meter: 'wide' },
  { min: 1160, columns: ['name', 'industry', 'rm', 'analyst', 'covenants', 'headroom'], nameMin: '210px', meter: 'wide' },
  { min: 1000, columns: ['name', 'rm', 'analyst', 'covenants', 'headroom'], nameMin: '210px', meter: 'wide' },
  { min: 900, columns: ['name', 'rm', 'analyst', 'covenants', 'headroom'], nameMin: '190px', meter: 'slim' },
  { min: 700, columns: ['name', 'industry', 'covenants', 'headroom'], nameMin: '190px', meter: 'slim' },
  { min: 560, columns: ['name', 'covenants', 'headroom'], nameMin: '190px', meter: 'slim' },
  { min: 0, columns: ['name', 'covenants', 'headroom'], nameMin: '150px', meter: 'under' },
];
const DIRECTORY_ON_A_PHONE: Layout = { min: 0, columns: ['name', 'code', 'industry', 'rm', 'analyst', 'covenants', 'headroom'], nameMin: '0px', meter: 'wide' };

/** The borrower directory: who they are, who looks after them, and how their covenants stand. The portfolio page has the amounts. */
export function Borrowers() {
  const borrowers = useBorrowers();
  const [text, setText] = useState('');
  const [frame, width] = useWidth();
  const phone = useIsPhone();
  const layout = phone ? DIRECTORY_ON_A_PHONE : layoutFor(DIRECTORY_LAYOUTS, width);
  const rows = useTearSheetRows(borrowers.data, layout);
  const columns = useMemo<Array<DataColumn<BorrowerRow>>>(() => {
    const all: Array<DataColumn<BorrowerRow>> = [
      nameColumn(layout.nameMin),
      { id: 'code', header: 'Record', sortValue: (row) => row.code, cell: (row) => <span className="ident text-ink-700">{row.code}</span> },
      { id: 'industry', header: 'Industry', sortValue: (row) => row.industry, cell: (row) => <span className="text-ink-700">{humanize(row.industry)}</span> },
      { id: 'rm', header: 'Relationship manager', sortValue: (row) => row.relationship_manager, cell: (row) => row.relationship_manager ?? <span className="text-ink-500">Not assigned</span> },
      { id: 'analyst', header: 'Credit analyst', sortValue: (row) => row.analyst, cell: (row) => row.analyst ?? <span className="text-ink-500">Not assigned</span> },
      covenantColumn,
      headroomColumn(layout.meter),
      stageColumn('Cycle stage'),
    ];
    return all.filter((column) => layout.columns.includes(column.id));
  }, [layout]);
  return (
    <div data-ready={borrowers.data ? '' : undefined} className="space-y-5">
      <PageHeader eyebrow="Bank of Stoic · Commercial lending" title="Borrowers" meta={<span>A row opens the borrower at a glance. The name opens its loans, documents, spreads, covenants and reviews.</span>} />
      <Load query={borrowers} what="The borrowers" rows={12}>
        {(all) => {
          const needle = text.trim().toLowerCase();
          const filtered = all.filter((row) => !needle || `${row.name} ${row.code} ${row.industry} ${row.analyst ?? ''} ${row.relationship_manager ?? ''}`.toLowerCase().includes(needle));
          return (
            <section aria-label="Borrower directory" ref={frame} className="min-w-0">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <Input label="Search borrowers" hideLabel placeholder="Search by name, record, industry or person" className="w-full sm:w-80" leading={<Search size={14} aria-hidden />} value={text} onChange={(event) => setText(event.target.value)} />
                <p className="ml-auto text-caption text-ink-500" aria-live="polite">
                  {filtered.length} of {all.length} borrowers
                </p>
              </div>
              <DataTable
                caption="Borrower directory, with covenant status and tightest covenant headroom for the latest period"
                data={filtered}
                columns={columns}
                getRowId={(row) => row.id}
                initialSort={{ id: 'name' }}
                stickyTop="var(--topbar-h)"
                narrow="stack"
                empty={<EmptyState title="No borrower matches" description="Nothing in the book fits this search." action={<Button onClick={() => setText('')}>Clear the search</Button>} />}
                {...rows}
              />
            </section>
          );
        }}
      </Load>
    </div>
  );
}

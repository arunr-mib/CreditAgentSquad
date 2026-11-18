import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { useBorrowerCovenants, useBorrowerOverview, useCalculation } from '@/api/hooks';
import type { BorrowerCovenants, BorrowerOverview, CovenantTestRow, FactsById } from '@/api/schema';
import { Card, CardHeader, DataTable, formatDate, Select, SkeletonRows, StatusDot, Stepper, type DataColumn, type Step } from '@/design';
import { decisionLabel, itemTypeLabel, OUTCOME, quarterLabel, STAGE_LABEL, STAGE_STATUS_LABEL } from '@/domain/labels';
import { CalculationBreakdown } from '@/source/CalculationBreakdown';
import { useSource } from '@/source/context';
import { FactFigure, ProvenanceLegend } from '@/source/figures';
import { EmptyCard, ErrorNotice, Load, SectionHead } from '../parts';
import { useIsPhone } from '../Portfolio';
import { WorkItemPanel } from '../work/WorkItemPanel';
import { useCurrentBorrower } from './BorrowerLayout';
import { RunStage } from './RunStage';

export function CycleStepper({ cycle }: { cycle: NonNullable<BorrowerOverview['cycle']> }) {
  const steps: Step[] = cycle.stages.map((stage) => ({
    id: stage.stage,
    label: STAGE_LABEL[stage.stage] ?? stage.stage,
    status: stage.status,
    detail: stage.open_work_items > 0 ? `${stage.open_work_items} open ${stage.open_work_items === 1 ? 'item' : 'items'}` : STAGE_STATUS_LABEL[stage.status],
  }));
  return (
    <section aria-label="Monitoring cycle" className="rounded-md border border-hairline-strong bg-surface px-4 pt-3 pb-3.5">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 className="text-body font-semibold text-ink">
          Monitoring cycle, {quarterLabel(cycle.period_end)} <span className="font-regular text-ink-500">· period ended {formatDate(cycle.period_end)}</span>
        </h2>
        <span className="text-caption text-ink-500">
          {cycle.status === 'closed' ? 'Closed' : 'Open'} · cycle <span className="ident">{cycle.id.slice(0, 8)}</span>
        </span>
      </div>
      <Stepper label={`Stages of the ${quarterLabel(cycle.period_end)} monitoring cycle`} steps={steps} collapseLater />
      <RunStage cycle={cycle} />
    </section>
  );
}

export interface TrendPoint {
  id: string;
  label: string;
  /** Plot positions only; figures beside the chart are formatted from the stored strings. */
  plot: number;
  /** The threshold in force in this period, or null where none was in force. */
  threshold: number | null;
  /** Failed against its own period's threshold. */
  breach: boolean;
  test: CovenantTestRow;
}

/** One point per tested period, each with the threshold that governed that period. */
export function trendPoints(tests: CovenantTestRow[]): TrendPoint[] {
  return tests
    .filter((test) => test.value !== null)
    .map((test) => {
      const threshold = test.threshold === null ? null : Number(test.threshold);
      return {
        id: test.id,
        label: quarterLabel(test.period_end),
        plot: Number(test.value),
        threshold: threshold !== null && Number.isFinite(threshold) ? threshold : null,
        // The stored result was tested against this period's own threshold; no threshold, no breach.
        breach: test.passed === false && test.threshold !== null,
        test,
      };
    });
}

function Trend({
  tests,
  facts,
  selectedId,
  onSelect,
}: {
  tests: CovenantTestRow[];
  facts: FactsById;
  selectedId: string;
  onSelect: (test: CovenantTestRow) => void;
}) {
  // Plot positions only: the figures shown beside the chart are the stored facts, formatted from their strings.
  const points = trendPoints(tests);
  // On a phone the quarter and the year sit on two lines, so seven periods fit side by side.
  const twoLines = useIsPhone();
  const selected = points.find((point) => point.id === selectedId) ?? points[points.length - 1];
  if (points.length < 2 || !selected) return null;
  const values = points.flatMap((point) => [point.plot, point.threshold]).filter((value): value is number => value !== null && Number.isFinite(value));
  const stepped = new Set(points.map((point) => point.threshold)).size > 1;
  const low = Math.min(...values);
  const high = Math.max(...values);
  const pad = (high - low || 1) * 0.15;
  const minimum = selected.test.operator === '>=';
  return (
    <div>
      <div className="h-[168px]" role="group" aria-label={`${selected.test.covenant_name} by period. Choose a period to see its test.`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 12, right: 30, bottom: 0, left: 0 }} accessibilityLayer={false}>
            <CartesianGrid vertical={false} stroke="var(--hairline)" />
            <XAxis
              dataKey="label"
              axisLine={{ stroke: 'var(--hairline-strong)' }}
              tickLine={false}
              interval={0}
              height={twoLines ? 38 : 28}
              tick={(props: { x?: number | string; y?: number | string; index?: number; payload?: { value?: string } }) => {
                const point = points[props.index ?? 0];
                const active = point?.id === selected.id;
                return (
                  <g
                    role="button"
                    tabIndex={0}
                    aria-label={`Show ${props.payload?.value ?? ''}`}
                    aria-pressed={active}
                    onClick={() => point && onSelect(point.test)}
                    onKeyDown={(event) => {
                      if ((event.key === 'Enter' || event.key === ' ') && point) {
                        event.preventDefault();
                        onSelect(point.test);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <rect x={Number(props.x) - 30} y={Number(props.y) - 2} width={60} height={twoLines ? 34 : 22} fill="transparent" />
                    <text
                      x={props.x}
                      y={Number(props.y) + 12}
                      textAnchor="middle"
                      fontSize={11}
                      fontWeight={active ? 600 : 500}
                      fill={active ? 'var(--cobalt-strong)' : 'var(--ink-500)'}
                      textDecoration={active ? 'underline' : undefined}
                    >
                      {twoLines
                        ? (props.payload?.value ?? '').split(' ').map((part, index) => (
                            <tspan key={part} x={props.x} dy={index === 0 ? 0 : 13}>
                              {part}
                            </tspan>
                          ))
                        : props.payload?.value}
                    </text>
                  </g>
                );
              }}
            />
            <YAxis
              domain={[low - pad, high + pad]}
              width={48}
              axisLine={false}
              tickLine={false}
              tickCount={4}
              tick={{ fontSize: 11, fill: 'var(--ink-500)' }}
              tickFormatter={(value: number) => value.toFixed(2)}
            />
            {/* Each period's own threshold, stepped where the terms change it. */}
            <Line
              dataKey="threshold"
              type="stepAfter"
              stroke="var(--ink-700)"
              strokeWidth={1.25}
              strokeDasharray="4 3"
              dot={false}
              activeDot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="plot"
              stroke="var(--ink-900)"
              strokeWidth={1.5}
              isAnimationActive={false}
              dot={(props: { cx?: number; cy?: number; index?: number }) => {
                const point = points[props.index ?? 0];
                const failed = point?.breach === true;
                const active = point?.id === selected.id;
                return (
                  <circle
                    key={props.index}
                    cx={props.cx}
                    cy={props.cy}
                    r={active ? 5 : 3.5}
                    fill={failed ? 'var(--red-mark)' : 'var(--ink-900)'}
                    stroke={active ? 'var(--cobalt)' : 'var(--surface)'}
                    strokeWidth={active ? 2 : 1.5}
                    onClick={() => point && onSelect(point.test)}
                    className="cursor-pointer"
                  />
                );
              }}
              activeDot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <ul aria-label="Chart key" className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-caption text-ink-700">
        <li className="inline-flex items-center gap-1.5">
          <svg width="18" height="8" aria-hidden>
            <line x1="0" y1="4" x2="18" y2="4" stroke="var(--ink-900)" strokeWidth="1.5" />
          </svg>
          Calculated
        </li>
        <li className="inline-flex items-center gap-1.5">
          <svg width="18" height="8" aria-hidden>
            <line x1="0" y1="4" x2="18" y2="4" stroke="var(--ink-700)" strokeWidth="1.25" strokeDasharray="4 3" />
          </svg>
          {minimum ? 'Minimum' : 'Maximum'} in force each period{stepped ? ', stepped as the terms change' : ''}
        </li>
        {points.some((point) => point.breach) ? (
          <li className="inline-flex items-center gap-1.5">
            <svg width="8" height="8" aria-hidden>
              <circle cx="4" cy="4" r="3.5" fill="var(--red-mark)" />
            </svg>
            Fails its own period’s threshold
          </li>
        ) : null}
      </ul>
      <p className="mt-1 text-body text-ink-700" aria-live="polite">
        {selected.label}: <FactFigure fact={selected.test.value_fact_id ? facts[selected.test.value_fact_id] : undefined} weight="semibold" /> against a{' '}
        {minimum ? 'minimum' : 'maximum'} of <FactFigure fact={selected.test.threshold_fact_id ? facts[selected.test.threshold_fact_id] : undefined} />
        {selected.test.passed === false ? (
          <StatusDot tone="breach" emphasis className="ml-3">
            {minimum ? 'Below the minimum' : 'Above the maximum'}
          </StatusDot>
        ) : null}
      </p>
    </div>
  );
}

function CertificateComparison({ test, facts }: { test: CovenantTestRow; facts: FactsById }) {
  const fact = (id: string | null) => (id ? facts[id] : undefined);
  const claim = test.reported_in_compliance;
  return (
    <dl className="grid grid-cols-1 divide-y divide-hairline border-t border-hairline-strong sm:grid-cols-4 sm:divide-x sm:divide-y-0 max-sm:[&>div]:flex max-sm:[&>div]:items-baseline max-sm:[&>div]:justify-between max-sm:[&>div]:gap-4 max-sm:[&_dd]:mt-0 max-sm:[&_dd]:text-right">
      <div className="px-4 py-2.5">
        <dt className="eyebrow">Calculated by code</dt>
        <dd className="mt-0.5 text-title">
          <FactFigure fact={fact(test.value_fact_id)} weight="semibold" absent="Not calculated" />
        </dd>
      </div>
      <div className="px-4 py-2.5">
        <dt className="eyebrow">{test.operator === '<=' ? 'Maximum allowed' : 'Minimum required'}</dt>
        <dd className="mt-0.5 text-title">
          <FactFigure fact={fact(test.threshold_fact_id)} absent="No threshold in force" />
        </dd>
      </div>
      <div className="px-4 py-2.5">
        <dt className="eyebrow">On the certificate</dt>
        <dd className="mt-0.5 text-title">
          <FactFigure fact={fact(test.reported_fact_id)} absent="Not reported" />
        </dd>
      </div>
      <div className="px-4 py-2.5">
        <dt className="eyebrow">Certificate claims</dt>
        <dd className="mt-0.5 text-body">
          {claim === null ? (
            <StatusDot tone="muted">Nothing certified</StatusDot>
          ) : claim ? (
            // What the borrower claims is not itself a breach; the outcome beside it carries the colour.
            <StatusDot tone="neutral">Compliance</StatusDot>
          ) : (
            <StatusDot tone="breach">Non-compliance</StatusDot>
          )}
        </dd>
      </div>
    </dl>
  );
}

function CalculationCard({
  test,
  facts,
  history,
  onSelect,
  code,
}: {
  test: CovenantTestRow;
  facts: FactsById;
  history: CovenantTestRow[];
  onSelect: (test: CovenantTestRow) => void;
  code: string;
}) {
  const calc = useCalculation(test.calc_run_id);
  const source = useSource();
  const outcome = OUTCOME[test.outcome];
  const citation = test.citation;
  return (
    <Card className="min-w-0">
      <CardHeader
        as="h2"
        eyebrow="Calculation"
        className="max-sm:flex-wrap max-sm:gap-y-1"
        title={test.covenant_name}
        meta={
          <>
            {calc.data?.expression ? `${calc.data.expression} · ` : ''}
            {test.loan_name ?? 'Loan'}
            {test.terms_version ? ` · terms version ${test.terms_version.version}, ${test.terms_version.status}` : ''}
            {citation?.document_id && citation.page ? (
              <>
                {' · '}
                <button
                  type="button"
                  className="link"
                  onClick={() =>
                    source.open({
                      type: 'document',
                      documentId: citation.document_id as string,
                      page: citation.page as number,
                      quote: citation.quote,
                      section: citation.section,
                      title: 'Credit agreement',
                      borrowerCode: code,
                    })
                  }
                >
                  {citation.section ? `Section ${citation.section}` : 'The clause'}, page {citation.page}
                </button>
              </>
            ) : null}
          </>
        }
        actions={
          <StatusDot tone={outcome.tone} emphasis={outcome.emphasis}>
            {outcome.label}
          </StatusDot>
        }
      />
      <CertificateComparison test={test} facts={facts} />
      {test.error ? <p className="border-t border-hairline-strong px-4 py-3 text-body text-amber">{test.error}</p> : null}
      {calc.error ? (
        <div className="border-t border-hairline-strong p-4">
          <ErrorNotice error={calc.error} what="The calculation" onRetry={() => void calc.refetch()} />
        </div>
      ) : calc.data ? (
        <div className="border-t border-hairline-strong max-md:relative max-md:overflow-x-auto max-sm:[&_thead_th]:w-auto max-sm:[&_thead_th]:whitespace-normal">
          <CalculationBreakdown calc={calc.data} resultLabel={test.covenant_name} resultUnit={test.unit} />
        </div>
      ) : test.calc_run_id ? (
        <div className="border-t border-hairline-strong p-4">
          <SkeletonRows rows={5} label="Loading the calculation" />
        </div>
      ) : null}
      {history.length > 1 ? (
        <div className="border-t border-hairline-strong px-4 pt-3.5 pb-4">
          <h3 className="eyebrow mb-1">By period</h3>
          <Trend tests={history} facts={facts} selectedId={test.id} onSelect={onSelect} />
        </div>
      ) : null}
    </Card>
  );
}

function Workspace({ data, overview }: { data: BorrowerCovenants; overview: BorrowerOverview | undefined }) {
  const borrower = useCurrentBorrower();
  const search = useSearch({ from: '/borrowers/$code/covenants' });
  const navigate = useNavigate({ from: '/borrowers/$code/covenants' });
  const { tests, facts } = data;

  const periods = useMemo(() => [...new Set(tests.map((test) => test.period_end))].sort().reverse(), [tests]);
  const linked = tests.find((test) => test.id === search.test);
  const period = linked?.period_end ?? (search.period && periods.includes(search.period) ? search.period : periods[0]);
  const current = useMemo(
    () =>
      tests
        .filter((test) => test.period_end === period)
        .sort((a, b) => OUTCOME[a.outcome].rank - OUTCOME[b.outcome].rank || a.covenant_name.localeCompare(b.covenant_name)),
    [tests, period],
  );
  const selected = current.find((test) => test.id === search.test) ?? current[0];
  const select = (test: CovenantTestRow) => void navigate({ search: { test: test.id }, replace: true, resetScroll: false });

  const columns = useMemo<Array<DataColumn<CovenantTestRow>>>(() => {
    const fact = (id: string | null) => (id ? facts[id] : undefined);
    return [
      {
        id: 'name',
        header: 'Covenant',
        rowHeader: true,
        wrap: true,
        sortValue: (row) => row.covenant_name,
        cell: (row) => <span className="font-medium text-ink">{row.covenant_name}</span>,
      },
      {
        id: 'calculated',
        header: 'Calculated',
        align: 'right',
        cell: (row) => <FactFigure fact={fact(row.value_fact_id)} weight="semibold" absent="Not calculated" />,
      },
      {
        id: 'threshold',
        header: 'Threshold',
        align: 'right',
        cell: (row) => (
          <span className="inline-flex items-center gap-1.5">
            {row.operator ? (
              <span className="text-ink-500" role="img" aria-label={row.operator === '>=' ? 'at least' : 'at most'}>
                {row.operator === '>=' ? '≥' : '≤'}
              </span>
            ) : null}
            <FactFigure fact={fact(row.threshold_fact_id)} absent="No threshold in force" />
          </span>
        ),
      },
      {
        id: 'headroom',
        header: 'Headroom',
        align: 'right',
        sortValue: (row) => (fact(row.headroom_fact_id) ? Number(fact(row.headroom_fact_id)?.value) : null),
        cell: (row) => <FactFigure fact={fact(row.headroom_fact_id)} />,
      },
      { id: 'certificate', header: 'Certificate', align: 'right', cell: (row) => <FactFigure fact={fact(row.reported_fact_id)} absent="Not reported" /> },
      {
        id: 'outcome',
        header: 'Outcome',
        // Wraps wherever the column is short of room: below 1280 px, or beside an open source drawer.
        wrap: true,
        sortValue: (row) => OUTCOME[row.outcome].rank,
        cell: (row) => (
          <StatusDot tone={OUTCOME[row.outcome].tone} emphasis={OUTCOME[row.outcome].emphasis} className="whitespace-normal!">
            {OUTCOME[row.outcome].label}
          </StatusDot>
        ),
      },
    ];
  }, [facts]);

  if (!selected || !period) return null;
  const history = tests
    .filter((test) => test.covenant_id === selected.covenant_id && test.facility_id === selected.facility_id)
    .sort((a, b) => a.period_end.localeCompare(b.period_end));
  const outcome = OUTCOME[selected.outcome];
  const cycle = overview?.cycle;

  return (
    <div data-ready className="@container space-y-5">
      {cycle && cycle.period_end === period ? <CycleStepper cycle={cycle} /> : null}
      <div className="grid items-start gap-5 @min-[1080px]:grid-cols-[minmax(0,1fr)_400px]">
        <div className="min-w-0 space-y-5">
          <section aria-labelledby="tests-heading" className="min-w-0">
            <SectionHead
              id="tests-heading"
              title="Covenant tests"
              note={`${current.length} ${current.length === 1 ? 'covenant' : 'covenants'} · calculated by code · every figure opens its source`}
              actions={
                <>
                  <ProvenanceLegend kinds={['calculated', 'seeded', 'extracted']} />
                  <Select
                    label="Period"
                    hideLabel
                    size="sm"
                    className="w-56"
                    value={period}
                    onValueChange={(value) => void navigate({ search: { period: value }, replace: true, resetScroll: false })}
                    options={periods.map((value) => ({ value, label: `${quarterLabel(value)} · ${formatDate(value)}` }))}
                  />
                </>
              }
            />
            <DataTable
              key={period}
              caption={`Covenant tests for the period ended ${formatDate(period)}`}
              data={current}
              columns={columns}
              getRowId={(row) => row.id}
              selectedRowId={selected.id}
              onRowActivate={select}
              stickyTop="var(--topbar-h)"
              narrow="stack"
            />
          </section>
          <CalculationCard key={selected.id} test={selected} facts={facts} history={history} onSelect={select} code={borrower.code} />
        </div>

        <aside
          aria-label="Exception for the selected covenant"
          className="min-w-0 @min-[1080px]:sticky @min-[1080px]:top-[68px] @min-[1080px]:max-h-[calc(100vh-88px)] @min-[1080px]:overflow-y-auto @min-[1080px]:rounded-md"
        >
          {selected.work_item ? (
            <WorkItemPanel key={selected.work_item.id} itemId={selected.work_item.id} />
          ) : (
            <Card>
              <CardHeader
                as="h2"
                eyebrow="Selected covenant"
                title={selected.covenant_name}
                meta={`${quarterLabel(selected.period_end)} · ${selected.loan_name ?? 'Loan'}`}
              />
              <div className="px-4 pb-4">
                <StatusDot tone={outcome.tone} emphasis={outcome.emphasis}>
                  {outcome.label}
                </StatusDot>
                <p className="mt-2 text-prose text-pretty text-ink-700">{outcome.explanation}</p>
                <p className="mt-2 text-body text-ink-500">No work item was raised on this test.</p>
              </div>
            </Card>
          )}
          {selected.work_item && selected.work_item.status !== 'open' ? (
            <p className="mt-2 text-caption text-ink-500">
              {itemTypeLabel(selected.work_item.item_type)}: {decisionLabel(selected.work_item.decision)} recorded.{' '}
              <Link to="/governance" search={{ tab: 'ledger', entity: selected.work_item.id }} className="link">
                Ledger
              </Link>
            </p>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

export function Covenants() {
  const borrower = useCurrentBorrower();
  const covenants = useBorrowerCovenants(borrower.id);
  const overview = useBorrowerOverview(borrower.id);
  return (
    <Load query={covenants} what="The covenant tests" rows={8}>
      {(data) =>
        data.tests.length === 0 ? (
          <div data-ready className="space-y-5">
            {overview.data?.cycle ? <CycleStepper cycle={overview.data.cycle} /> : null}
            <EmptyCard
              title="No covenant has been tested yet"
              description="Tests run once the period’s statements are spread and terms are in force. An open item on an earlier stage is holding this cycle; decide it and the tests follow."
              action={
                <Link to="/command-centre" className="link text-body font-medium">
                  Open the work queue
                </Link>
              }
            />
          </div>
        ) : (
          <Workspace data={data} overview={overview.data} />
        )
      }
    </Load>
  );
}

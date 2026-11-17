import { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { useCovenantWorkspace } from '@/api/queries';
import type { CovenantOutcome, CovenantTest, Fact, FactMap } from '@/api/types';
import {
  AgentNote,
  AgentText,
  Card,
  CardHeader,
  DataTable,
  FactsProvider,
  Figure,
  formatDue,
  GuardrailNotes,
  NOT_MEASURED,
  SkeletonRows,
  StatusDot,
  Stepper,
  useToast,
  WorkItemCard,
  type DataColumn,
  type StatusTone,
} from '@/design';
import type { BreakdownRow, TrendPoint } from '@/fixtures/brightwater';
import { workItemTypeLabel } from '@/fixtures/workItems';
import { cx } from '@/lib/cx';
import { useAsOf } from '@/shell/AsOf';
import { BorrowerHeader } from './BorrowerHeader';

const OUTCOME: Record<CovenantOutcome, { tone: StatusTone; label: string; emphasis?: boolean; explanation: string }> = {
  compliant: { tone: 'pass', label: 'Compliant', explanation: 'The calculated value passes and agrees with the certificate. Nothing is needed from a person.' },
  compliant_variance: {
    tone: 'attention',
    label: 'Compliant, variance',
    explanation: 'The calculated value passes but differs from the certificate beyond tolerance. The variance is logged; no decision is needed.',
  },
  breach: { tone: 'breach', label: 'Breach', emphasis: true, explanation: 'The calculated value fails the test.' },
  breach_reported_compliant: {
    tone: 'breach',
    label: 'Breach, reported compliant',
    emphasis: true,
    explanation: 'The calculated value fails the test and the certificate claims compliance.',
  },
  cannot_test: { tone: 'attention', label: 'Cannot test', explanation: 'An input is missing or no terms are in force.' },
};

function sourceHref(fact: Fact): string | undefined {
  return fact.provenance.kind === 'extracted' && (fact.key.startsWith('is.') || fact.key.startsWith('bs.') || fact.key.startsWith('stated.'))
    ? `/showcase/spread?cell=${fact.id}`
    : undefined;
}

function Breakdown({ rows, unitNote, facts }: { rows: BreakdownRow[]; unitNote: string; facts: FactMap }) {
  return (
    <table className="w-full border-separate border-spacing-0 text-body">
      <caption className="sr-only">Calculation breakdown</caption>
      <thead>
        <tr>
          <th scope="col" className="eyebrow h-8 border-b border-ink px-4 text-left">
            Component
          </th>
          <th scope="col" className="eyebrow h-8 w-40 border-b border-ink px-4 text-right">
            Value <span className="font-medium tracking-normal normal-case">{unitNote}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => {
          const fact = facts[row.factId];
          const strong = row.emphasis !== undefined;
          const total = row.emphasis === 'total';
          const last = index === rows.length - 1;
          return (
            <tr key={`${row.factId}-${index}`} className={cx(strong && 'bg-canvas')}>
              <th
                scope="row"
                className={cx(
                  'px-4 py-1.5 text-left align-top',
                  !last && 'border-b border-hairline',
                  strong ? 'font-semibold text-ink' : 'font-regular text-ink-700',
                )}
              >
                <span className="flex items-baseline gap-2" style={{ paddingLeft: row.depth * 16 }}>
                  <span aria-hidden className="inline-block w-3 shrink-0 text-center text-ink-500">
                    {row.op ?? ''}
                  </span>
                  <span className="min-w-0">
                    {row.label}
                    {row.note ? <AgentText text={row.note} className="mt-0.5 !text-caption font-regular !text-ink-500" /> : null}
                  </span>
                </span>
              </th>
              <td
                className={cx(
                  'px-4 py-1.5 text-right align-top',
                  !last && !total && 'border-b border-hairline',
                  row.emphasis === 'subtotal' && 'border-t border-t-ink',
                  total && 'border-t border-b-[3px] border-double border-ink',
                )}
              >
                {fact ? (
                  <Figure
                    fact={fact}
                    scale={fact.unit === 'usd' ? 1000 : 1}
                    unitMark={fact.unit !== 'usd'}
                    align="column"
                    weight={strong ? 'semibold' : 'regular'}
                  />
                ) : (
                  NOT_MEASURED
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Trend({ points, facts, threshold }: { points: TrendPoint[]; facts: FactMap; threshold: Fact }) {
  const [selected, setSelected] = useState(points.length - 1);
  const point = points[selected];
  const fact = point ? facts[point.factId] : undefined;
  const minimum = Number(threshold.value);
  return (
    <div>
      <div className="h-[168px]" role="group" aria-label="Fixed charge coverage by quarter. Choose a quarter to see its figure.">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 12, right: 36, bottom: 0, left: 0 }} accessibilityLayer={false}>
            <CartesianGrid vertical={false} stroke="var(--hairline)" />
            <XAxis
              dataKey="label"
              axisLine={{ stroke: 'var(--hairline-strong)' }}
              tickLine={false}
              interval={0}
              height={28}
              tick={(props: { x?: number | string; y?: number | string; index?: number; payload?: { value?: string } }) => {
                const index = props.index ?? 0;
                const active = index === selected;
                return (
                  <g
                    role="button"
                    tabIndex={0}
                    aria-label={`Show ${props.payload?.value ?? ''}`}
                    aria-pressed={active}
                    onClick={() => setSelected(index)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        setSelected(index);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <rect x={Number(props.x) - 30} y={Number(props.y) - 2} width={60} height={22} fill="transparent" />
                    <text
                      x={props.x}
                      y={Number(props.y) + 12}
                      textAnchor="middle"
                      fontSize={11}
                      fontWeight={active ? 600 : 500}
                      fill={active ? 'var(--cobalt-strong)' : 'var(--ink-500)'}
                      textDecoration={active ? 'underline' : undefined}
                    >
                      {props.payload?.value}
                    </text>
                  </g>
                );
              }}
            />
            <YAxis
              domain={[1, 1.6]}
              ticks={[1, 1.2, 1.4, 1.6]}
              width={44}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: 'var(--ink-500)' }}
              tickFormatter={(value: number) => `${value.toFixed(2)}x`}
            />
            <ReferenceLine
              y={minimum}
              stroke="var(--ink-700)"
              strokeDasharray="4 3"
              label={{ value: 'Minimum', position: 'insideBottomRight', fontSize: 11, fill: 'var(--ink-700)' }}
            />
            <Line
              dataKey="plot"
              stroke="var(--ink-900)"
              strokeWidth={1.5}
              isAnimationActive={false}
              dot={(props: { cx?: number; cy?: number; index?: number; payload?: TrendPoint }) => {
                const below = (props.payload?.plot ?? minimum) < minimum;
                const active = props.index === selected;
                return (
                  <circle
                    key={props.index}
                    cx={props.cx}
                    cy={props.cy}
                    r={active ? 5 : 3.5}
                    fill={below ? 'var(--red-mark)' : 'var(--ink-900)'}
                    stroke={active ? 'var(--cobalt)' : 'var(--surface)'}
                    strokeWidth={active ? 2 : 1.5}
                    onClick={() => setSelected(props.index ?? 0)}
                    className="cursor-pointer"
                  />
                );
              }}
              activeDot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {point && fact ? (
        <p className="mt-1 text-body text-ink-700" aria-live="polite">
          {point.label}: <Figure fact={fact} weight="semibold" /> against a minimum of <Figure fact={threshold} />
          {Number(fact.value) < minimum ? (
            <StatusDot tone="breach" emphasis className="ml-3">
              Below the minimum
            </StatusDot>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}

export function CovenantWorkspace() {
  const { data, isPending } = useCovenantWorkspace('BRW-0417');
  const { asOf } = useAsOf();
  const toast = useToast();
  const [selectedId, setSelectedId] = useState('fccr');

  const columns = useMemo<Array<DataColumn<CovenantTest>>>(() => {
    const facts = data?.facts ?? {};
    const figure = (id: string | null, weight: 'regular' | 'semibold' = 'regular') => {
      const fact = id ? facts[id] : undefined;
      return fact ? <Figure fact={fact} weight={weight} /> : <span className="text-ink-500">{NOT_MEASURED}</span>;
    };
    const numeric = (id: string | null) => (id && facts[id] ? Number(facts[id].value) : null);
    return [
      {
        id: 'name',
        header: 'Covenant',
        rowHeader: true,
        wrap: true,
        sortValue: (row) => row.name,
        cell: (row) => <span className="font-medium text-ink">{row.name}</span>,
      },
      { id: 'calculated', header: 'Calculated', align: 'right', cell: (row) => figure(row.calculatedFactId, 'semibold') },
      {
        id: 'threshold',
        header: 'Threshold',
        align: 'right',
        cell: (row) => (
          <span className="inline-flex items-center gap-1.5">
            <span className="text-ink-500" role="img" aria-label={row.operator === '>=' ? 'at least' : 'at most'}>
              {row.operator === '>=' ? '≥' : '≤'}
            </span>
            {figure(row.thresholdFactId)}
          </span>
        ),
      },
      { id: 'headroom', header: 'Headroom', align: 'right', sortValue: (row) => numeric(row.headroomFactId), cell: (row) => figure(row.headroomFactId) },
      { id: 'certificate', header: 'Certificate', align: 'right', cell: (row) => figure(row.certificateFactId) },
      {
        id: 'outcome',
        header: 'Outcome',
        sortValue: (row) => OUTCOME[row.outcome].label,
        cell: (row) => (
          <StatusDot tone={OUTCOME[row.outcome].tone} emphasis={OUTCOME[row.outcome].emphasis}>
            {OUTCOME[row.outcome].label}
          </StatusDot>
        ),
      },
    ];
  }, [data]);

  if (isPending || !data) return <SkeletonRows rows={8} label="Loading the covenant workspace" />;

  const { borrower, cycle, covenants, breakdowns, facts, workItem, named } = data;
  const selected = covenants.find((covenant) => covenant.id === selectedId) ?? covenants[0];
  if (!selected) return null;
  const breakdown = breakdowns[selected.id];
  const outcome = OUTCOME[selected.outcome];
  const isException = selected.id === 'fccr';
  const due = formatDue(workItem.dueDate, asOf);
  const recommendation = workItem.recommendation;

  return (
    <FactsProvider facts={facts} sourceHref={sourceHref}>
      <div data-ready className="space-y-5">
        <BorrowerHeader borrower={borrower} facts={facts} current="Covenants" />

        <section aria-label="Monitoring cycle" className="rounded-md border border-hairline-strong bg-surface px-4 pt-3 pb-3.5">
          <div className="mb-3 flex items-baseline justify-between gap-4">
            <h2 className="text-body font-semibold text-ink">
              Monitoring cycle, {cycle.periodLabel} <span className="font-regular text-ink-500">· period ended 30 Sep 2026</span>
            </h2>
            <span className="text-caption text-ink-500">
              Cycle <span className="ident">{cycle.id}</span>
            </span>
          </div>
          <Stepper label={`Stages of the ${cycle.periodLabel} monitoring cycle`} steps={cycle.stages} />
        </section>

        {/* One column below 1400 px: tests, then the exception, then the calculation. Two columns above. */}
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_344px] xl:grid-rows-[auto_1fr]">
          <section aria-labelledby="tests-heading" className="min-w-0 xl:col-start-1">
            <div className="mb-2 flex items-baseline justify-between gap-4">
              <h2 id="tests-heading" className="text-title font-semibold text-ink">
                Covenant tests
              </h2>
              <p className="text-caption text-ink-500">
                Terms in force: {borrower.termsVersion} · {covenants.length} covenants · calculated by code
              </p>
            </div>
            <DataTable
              caption="Covenant tests for the quarter ended 30 Sep 2026"
              data={covenants}
              columns={columns}
              getRowId={(row) => row.id}
              selectedRowId={selected.id}
              onRowActivate={(row) => setSelectedId(row.id)}
              stickyTop="var(--topbar-h)"
            />
          </section>

          <aside aria-label="Exception for the selected covenant" className="xl:sticky xl:top-[68px] xl:col-start-2 xl:row-span-2 xl:row-start-1">
            {isException ? (
              <WorkItemCard
                headingLevel="h2"
                typeLabel={workItemTypeLabel[workItem.type]}
                itemId={workItem.id}
                severity={{ tone: 'attention', label: 'Critical' }}
                breach
                subject="Fixed charge coverage"
                context={cycle.periodLabel}
                due={{ text: due.sentence, attention: due.overdue }}
                question={workItem.question}
                evidence={workItem.evidence}
                decisions={workItem.decisions}
                requiresSecondPerson={workItem.requiresSecondPerson}
                onDecide={(decision) =>
                  toast({ title: `${decision.label}: not recorded`, description: 'The showcase runs on fixture data. No decision was written to the ledger.' })
                }
              >
                {recommendation ? (
                  <>
                    <AgentNote
                      agent={recommendation.agent}
                      headline={recommendation.headline}
                      body={recommendation.body}
                      state={recommendation.approved ? 'approved' : 'draft'}
                      runId={recommendation.runId}
                      writtenAt={recommendation.writtenAt}
                    />
                    <GuardrailNotes notes={recommendation.guardrailNotes} as="h3" />
                  </>
                ) : null}
              </WorkItemCard>
            ) : (
              <Card>
                <CardHeader as="h2" eyebrow="Selected covenant" title={selected.name} meta={selected.citation} />
                <div className="px-4 pb-4">
                  <StatusDot tone={outcome.tone} emphasis={outcome.emphasis}>
                    {outcome.label}
                  </StatusDot>
                  <p className="mt-2 text-prose text-ink-700">{outcome.explanation}</p>
                  {selected.outcome === 'compliant_variance' ? (
                    <p className="mt-2 text-prose text-ink-700">
                      The certificate uses Consolidated EBITDA of <Figure fact={named.certEbitda} />; the bank’s calculation uses{' '}
                      <Figure fact={named.adjEbitda} />, because the restructuring add-back is capped at <Figure fact={named.addbackCap} />.
                    </p>
                  ) : null}
                </div>
              </Card>
            )}
          </aside>

          {breakdown ? (
            <Card className="min-w-0 xl:col-start-1 xl:row-start-2">
              <CardHeader
                as="h2"
                eyebrow="Calculation"
                title={breakdown.title}
                meta={`${selected.basis} · ${selected.citation}`}
                actions={
                  <StatusDot tone={outcome.tone} emphasis={outcome.emphasis}>
                    {outcome.label}
                  </StatusDot>
                }
              />
              <Breakdown rows={breakdown.rows} unitNote={breakdown.unitNote} facts={facts} />
              {isException ? (
                <div className="border-t border-hairline-strong px-4 pt-3.5 pb-4">
                  <h3 className="eyebrow mb-1">Eight quarters</h3>
                  <Trend points={data.trend} facts={facts} threshold={named.fccrMin} />
                </div>
              ) : null}
            </Card>
          ) : null}
        </div>
      </div>
    </FactsProvider>
  );
}

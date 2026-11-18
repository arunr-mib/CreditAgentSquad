import { Link } from '@tanstack/react-router';
import { ArrowUpRight, ChevronRight } from 'lucide-react';
import type { ReactNode } from 'react';
import { compare } from '@/api/decimal';
import { useBorrowerByCode, useBorrowerCovenants, useBorrowerOverview, useWorkItems } from '@/api/hooks';
import type { BorrowerOverview, BorrowerRow, CovenantTestRow, FactsById, FactSummary, WorkItemRow } from '@/api/schema';
import type { CovenantOutcome, StageStatus } from '@/api/types';
import { AgentMark, barFill, Button, formatDate, formatDue, formatFigure, Meter, SkeletonRows, StatusDot, Tag, type BarFill } from '@/design';
import { humanize, itemTypeLabel, OUTCOME, quarterLabel, SEVERITY_LABEL, SEVERITY_RANK, STAGE_STATUS_LABEL, stageLabel, toFact } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { ErrorNotice, Load, Notice } from '@/screens/parts';
import { useAsOf } from '@/shell/AsOf';
import { FactFigure, SourcedFigure } from '@/source/figures';
import { useWorkspaceDrawer } from './context';

/* ── Marks shared with the portfolio and the borrower directory ───────── */

/**
 * A covenant outcome. A breach or a variance is something a person acts on, so it is a tag;
 * compliant needs nothing from anyone, so it is a dot and a word.
 */
export function OutcomeMark({ outcome }: { outcome: CovenantOutcome | null | undefined }) {
  if (!outcome) return <StatusDot tone="muted">Not tested yet</StatusDot>;
  const meta = OUTCOME[outcome];
  if (outcome === 'compliant') return <StatusDot tone="pass">{meta.label}</StatusDot>;
  return <Tag tone={meta.tone === 'breach' ? 'breach' : 'attention'}>{meta.label}</Tag>;
}

/** Headroom is stored as a fraction of the threshold. Below zero is a breach; under a tenth is thin. */
export function headroomTone(value: string): 'breach' | 'attention' | 'pass' {
  if (compare(value, '0') < 0) return 'breach';
  return compare(value, '0.1') < 0 ? 'attention' : 'pass';
}

/** The track is full at headroom of half the threshold or more. A plot position, nothing else. */
const HEADROOM_AT_FULL_TRACK = 0.5;

/**
 * Where a stored headroom sits between the threshold and plenty of room. The figure itself is
 * always shown beside the meter as the stored fact; this only draws its length.
 */
export function HeadroomMeter({ fact, className }: { fact: FactSummary; className?: string }) {
  const shown = formatFigure(toFact(fact).value, fact.unit).text;
  return <Meter position={Math.abs(Number(fact.value)) / HEADROOM_AT_FULL_TRACK} tone={headroomTone(fact.value)} label={`${fact.label} ${shown}`} className={className} />;
}

/* ── The sheet ────────────────────────────────────────────────────────── */

function Section({ title, note, children }: { title: string; note?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-t border-hairline px-4 pt-3.5 pb-4">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
        <h3 className="eyebrow">{title}</h3>
        {note ? <span className="text-caption text-ink-500">{note}</span> : null}
      </div>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-8 items-center justify-between gap-4 border-b border-hairline py-1 text-body last:border-b-0">
      <dt className="min-w-0 text-ink-700">{label}</dt>
      <dd className="shrink-0 text-right text-ink">{children}</dd>
    </div>
  );
}

const thousands = { scale: 1000, unitMark: false } as const;

function Exposure({ borrower, exposure }: { borrower: BorrowerRow; exposure: BorrowerOverview['exposure'] }) {
  const drawn = exposure.revolver_outstanding;
  const line = exposure.commitment;
  const hasLine = drawn && line && compare(line.value, '0') > 0;
  return (
    <dl>
      <Row label="Total commitment">
        <SourcedFigure
          value={borrower.total_commitment}
          unit="usd"
          kind="system"
          label={`Total commitment, ${borrower.name}`}
          weight="semibold"
          source={{
            type: 'record',
            kind: 'system',
            title: `Total commitment, ${borrower.name}`,
            value: formatFigure(borrower.total_commitment ?? '0', 'usd').text,
            note: 'The sum of the commitments on this borrower’s loan records, added by code with exact decimals. Each loan’s commitment is on the Loans tab.',
            rows: [
              ['System', 'Core loan accounting'],
              ['Record', borrower.code],
            ],
            link: { to: `/borrowers/${borrower.code}/loans`, label: 'Open the loans' },
          }}
          {...thousands}
        />
      </Row>
      <Row
        label={
          <span className="flex flex-wrap items-center gap-x-2.5">
            Line of credit, drawn
            {hasLine ? (
              <Meter
                position={Number(drawn.value) / Number(line.value)}
                tone="neutral"
                label={`Line of credit: ${formatFigure(drawn.value, 'usd').text} drawn of ${formatFigure(line.value, 'usd').text} committed`}
              />
            ) : null}
          </span>
        }
      >
        <FactFigure fact={drawn} absent="No line of credit balance on record" {...thousands} />
        {line ? (
          <>
            <span className="mx-1.5 text-ink-500">of</span>
            <FactFigure fact={line} {...thousands} />
          </>
        ) : null}
      </Row>
      <Row label="Term loan, outstanding">
        <FactFigure fact={exposure.term_loan_outstanding} absent="No term loan balance on record" {...thousands} />
      </Row>
      {exposure.availability ? (
        <Row label="Borrowing base availability">
          <FactFigure fact={exposure.availability} {...thousands} />
        </Row>
      ) : null}
      {exposure.past_due_days ? (
        <Row label="Days past due">
          <FactFigure fact={exposure.past_due_days} />
        </Row>
      ) : null}
    </dl>
  );
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-caption text-ink-500">{label}</dt>
      <dd className="mt-0.5 text-body text-ink">{children}</dd>
    </div>
  );
}

function Covenant({ test, facts, onOpenItem }: { test: CovenantTestRow; facts: FactsById; onOpenItem: (id: string) => void }) {
  const fact = (id: string | null) => (id ? facts[id] : undefined);
  const headroom = fact(test.headroom_fact_id);
  const item = test.work_item?.status === 'open' ? test.work_item : null;
  return (
    <li className="py-3 first:pt-0.5 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="min-w-0 text-body font-medium text-ink">{test.covenant_name}</span>
        <OutcomeMark outcome={test.outcome} />
      </div>
      {test.outcome === 'cannot_test' && !fact(test.value_fact_id) ? (
        <p className="mt-1 text-body text-pretty text-ink-700">{test.error ?? OUTCOME.cannot_test.explanation}</p>
      ) : (
        <>
          <dl className="mt-1.5 grid grid-cols-3 gap-x-3">
            <Stat label="Calculated">
              <FactFigure fact={fact(test.value_fact_id)} weight="semibold" absent="Not calculated" />
            </Stat>
            <Stat label="Threshold">
              <span className="mr-1 text-ink-500" role="img" aria-label={test.operator === '>=' ? 'at least' : 'at most'}>
                {test.operator === '>=' ? '≥' : '≤'}
              </span>
              <FactFigure fact={fact(test.threshold_fact_id)} absent="No threshold in force" />
            </Stat>
            <Stat label="Headroom">
              <FactFigure fact={headroom} absent="Not calculated" />
            </Stat>
          </dl>
          {headroom ? <HeadroomMeter fact={headroom} className="mt-2 block! w-full!" /> : null}
        </>
      )}
      {item ? (
        <button type="button" onClick={() => onOpenItem(item.id)} className="link mt-2 inline-flex items-center gap-0.5 text-body font-medium">
          Open the exception raised on this test
          <ChevronRight size={13} aria-hidden />
        </button>
      ) : null}
    </li>
  );
}

/** One ink ramp for the stage bar: what is done, where the cycle is, what is still to come. */
function stageFill(status: StageStatus, current: boolean): BarFill {
  if (current) return 6;
  if (status === 'done') return 4;
  return status === 'skipped' ? 2 : 1;
}

function stageStatusMark(status: StageStatus | undefined): ReactNode {
  if (!status) return <span className="text-ink-500">Not recorded</span>;
  // Waiting for a person, or failed, is something to act on. Everything else is a plain state.
  if (status === 'needs_person' || status === 'failed') return <Tag tone="attention">{STAGE_STATUS_LABEL[status]}</Tag>;
  return <span className={status === 'pending' ? 'text-ink-500' : 'text-ink'}>{STAGE_STATUS_LABEL[status]}</span>;
}

function Cycle({ cycle }: { cycle: NonNullable<BorrowerOverview['cycle']> }) {
  const current = cycle.stages.find((stage) => stage.stage === cycle.stage);
  return (
    <>
      {/* Each block is one stage, all the same width: a picture of where the cycle stands, not a quantity. */}
      <div
        role="img"
        aria-label={`Stage ${stageLabel(cycle.stage)}: ${current ? STAGE_STATUS_LABEL[current.status].toLowerCase() : 'not recorded'}`}
        className="mb-2 flex h-2 gap-0.5"
      >
        {cycle.stages.map((stage) => (
          <span
            key={stage.id}
            title={`${stageLabel(stage.stage)}: ${STAGE_STATUS_LABEL[stage.status].toLowerCase()}`}
            className="h-full flex-1 rounded-xs"
            style={{ background: barFill(stageFill(stage.status, stage.stage === cycle.stage)) }}
          />
        ))}
      </div>
      <dl>
        <Row label="Stage">
          <span className="font-medium">{stageLabel(cycle.stage)}</span>
        </Row>
        <Row label="Status">{cycle.status === 'closed' ? 'Closed' : stageStatusMark(current?.status)}</Row>
        {current && current.open_work_items > 0 ? (
          <Row label="Open items at this stage">
            <span className="tnum">{current.open_work_items}</span>
          </Row>
        ) : null}
      </dl>
    </>
  );
}

/** The borrower's name leads every title; the sheet already names the borrower. */
function shortTitle(item: WorkItemRow): string {
  const prefix = `${item.borrower_name}: `;
  const rest = item.borrower_name && item.title.startsWith(prefix) ? item.title.slice(prefix.length) : item.title;
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}

function OpenItem({ item, asOf, onOpen }: { item: WorkItemRow; asOf: string | null; onOpen: (id: string) => void }) {
  const due = item.due_date && asOf ? formatDue(item.due_date, asOf) : null;
  const urgent = item.severity === 'critical' || item.severity === 'high';
  return (
    <li className="border-b border-hairline last:border-b-0">
      <button
        type="button"
        onClick={() => onOpen(item.id)}
        aria-label={`${SEVERITY_LABEL[item.severity]}: ${shortTitle(item)}. Open the exception.`}
        className="group -mx-2 flex w-[calc(100%+16px)] items-start gap-3 rounded-sm px-2 py-2 text-left t-colors hover:bg-hover"
      >
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-caption text-ink-500">
            {urgent ? <Tag tone={item.severity === 'critical' ? 'breach' : 'attention'}>{SEVERITY_LABEL[item.severity]}</Tag> : <span>{SEVERITY_LABEL[item.severity]}</span>}
            <span>{itemTypeLabel(item.item_type)}</span>
            {due ? <span className={cx('tnum', due.overdue && 'font-medium text-amber')}>{due.sentence}</span> : null}
          </span>
          <span className="mt-1 block text-body text-pretty text-ink group-hover:text-cobalt-strong">{shortTitle(item)}</span>
        </span>
        <ChevronRight size={14} aria-hidden className="mt-0.5 shrink-0 text-ink-400 group-hover:text-cobalt-strong" />
      </button>
    </li>
  );
}

/** A borrower at a glance, in the workspace drawer: exposure, covenants, the cycle, and what is open. */
export function BorrowerTearSheet({ code }: { code: string }) {
  const drawer = useWorkspaceDrawer();
  const lookup = useBorrowerByCode(code);
  const borrower = lookup.borrower;
  const overview = useBorrowerOverview(borrower?.id);
  const covenants = useBorrowerCovenants(borrower?.id);
  const items = useWorkItems({ status: 'open', borrower_id: borrower?.id });
  const { asOf } = useAsOf();

  if (lookup.error) {
    return (
      <div data-tear-sheet={code} className="px-4 py-4">
        <ErrorNotice error={lookup.error} what="The borrower" onRetry={() => void lookup.refetch()} />
      </div>
    );
  }
  if (lookup.notFound) {
    return (
      <div data-tear-sheet={code} className="px-4 py-4">
        <Notice title="No borrower has this record">
          Nothing in the book is filed under “{code}”.
        </Notice>
      </div>
    );
  }
  if (!borrower) {
    return (
      <div data-tear-sheet={code} className="px-4 py-4">
        <SkeletonRows rows={8} label="Loading the borrower" />
      </div>
    );
  }

  const period = borrower.latest_cycle?.period_end ?? null;
  const people = [borrower.relationship_manager ? `Relationship manager ${borrower.relationship_manager}` : null, borrower.analyst ? `Credit analyst ${borrower.analyst}` : null].filter(Boolean);

  return (
    <div data-tear-sheet={code} data-ready={overview.data && covenants.data && items.data ? '' : undefined}>
      <header className="px-4 pt-4 pb-4">
        <p className="eyebrow">
          Borrower <span className="ident tracking-normal normal-case">· {borrower.code}</span>
        </p>
        <h2 className="mt-0.5 text-heading font-semibold text-pretty text-ink">{borrower.name}</h2>
        <p className="mt-1 text-body text-ink-700">
          {humanize(borrower.industry)} · {borrower.risk_rating === null ? 'Not rated' : <>Risk rating <span className="tnum font-medium text-ink">{borrower.risk_rating}</span></>}
        </p>
        {people.length ? <p className="text-caption text-ink-500">{people.join(' · ')}</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/borrowers/$code" params={{ code: borrower.code }} onClick={() => drawer.close()}>
              Open the borrower page
              <ArrowUpRight size={13} aria-hidden />
            </Link>
          </Button>
          <Button
            iconLeft={<AgentMark size={8} />}
            onClick={() => drawer.openCopilot({ kind: 'borrower', code: borrower.code })}
            className="h-auto! min-h-8 max-w-full shrink! py-1 text-left whitespace-normal!"
          >
            Ask Copilot about {borrower.name}
          </Button>
        </div>
      </header>

      <Section title="Exposure" note="USD thousands · balances from the system of record">
        <Load query={overview} what="The exposure" rows={3}>
          {(data) => <Exposure borrower={borrower} exposure={data.exposure} />}
        </Load>
      </Section>

      <Section title="Covenants" note={period ? `${quarterLabel(period)} · calculated by code` : undefined}>
        <Load query={covenants} what="The covenant tests" rows={3}>
          {(data) => {
            const tests = data.tests.filter((test) => test.period_end === period).sort((a, b) => OUTCOME[a.outcome].rank - OUTCOME[b.outcome].rank || a.covenant_name.localeCompare(b.covenant_name));
            return tests.length === 0 ? (
              <p className="text-body text-pretty text-ink-700">No covenant has been tested for this period yet.</p>
            ) : (
              <ul className="divide-y divide-hairline">
                {tests.map((test) => (
                  <Covenant key={test.id} test={test} facts={data.facts} onOpenItem={drawer.openItem} />
                ))}
              </ul>
            );
          }}
        </Load>
      </Section>

      <Section title="Monitoring cycle" note={period ? `${quarterLabel(period)} · period ended ${formatDate(period)}` : undefined}>
        <Load query={overview} what="The monitoring cycle" rows={2}>
          {(data) => (data.cycle ? <Cycle cycle={data.cycle} /> : <p className="text-body text-ink-700">No monitoring cycle has been opened for this borrower.</p>)}
        </Load>
      </Section>

      <Section title="Open items" note={items.data ? `${items.data.length} ${items.data.length === 1 ? 'needs' : 'need'} a person` : undefined}>
        <Load query={items} what="The open items" rows={2}>
          {(rows) =>
            rows.length === 0 ? (
              <p className="text-body text-ink-700">Nothing is waiting for a decision on this borrower.</p>
            ) : (
              <ul>
                {[...rows]
                  .sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || (a.due_date ?? '9').localeCompare(b.due_date ?? '9'))
                  .map((item) => (
                    <OpenItem key={item.id} item={item} asOf={asOf} onOpen={drawer.openItem} />
                  ))}
              </ul>
            )
          }
        </Load>
      </Section>

      <Section title="Open signals">
        <Load query={overview} what="The signals" rows={1}>
          {(data) =>
            data.open_signals === 0 ? (
              <p className="text-body text-ink-700">No early warning signal is open.</p>
            ) : (
              <p className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-body text-ink">
                <span>
                  <span className="tnum font-semibold">{data.open_signals}</span> open early warning {data.open_signals === 1 ? 'signal' : 'signals'}
                </span>
                <Link to="/borrowers/$code/signals" params={{ code: borrower.code }} onClick={() => drawer.close()} className="link font-medium">
                  Open the signals
                </Link>
              </p>
            )
          }
        </Load>
      </Section>
    </div>
  );
}

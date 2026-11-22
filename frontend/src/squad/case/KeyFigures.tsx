import { useBorrowerCovenants, useCalculation, useFactsById } from '@/api/hooks';
import type { WorkItemDetail } from '@/api/schema';
import { Meter, Skeleton } from '@/design';
import { OUTCOME } from '@/domain/labels';
import { FactFigure, SourcedFigure } from '@/source/figures';
import type { ReactNode } from 'react';

/**
 * Tiles on a grid: they line up and wrap together. Each tile draws its own right and bottom rule just
 * outside itself, and the frame clips the rules that would fall on its edge, so no rule is left loose.
 */
const GRID = 'grid grid-cols-[repeat(auto-fit,minmax(124px,1fr))] border-t border-hairline';

const text = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);

function Tile({ label, note, children }: { label: string; note?: ReactNode; children: ReactNode }) {
  return (
    <div className="min-w-0 px-3 py-2.5 shadow-[1px_0_0_var(--hairline),0_1px_0_var(--hairline)]">
      <p className="eyebrow">{label}</p>
      <p className="mt-0.5 text-heading leading-tight font-semibold text-ink">{children}</p>
      {note ? <p className="mt-0.5 text-caption text-ink-700">{note}</p> : null}
    </div>
  );
}

/**
 * The few figures the question turns on, set out large. Every one is a stored fact or a stored
 * output of the calculation and opens its source; nothing here is worked out by the interface.
 * Renders nothing for an item that has no such figures.
 */
export function KeyFigures({ item }: { item: WorkItemDetail }) {
  const evidence = item.evidence;
  const testId = text(evidence.covenant_test_id);
  const reviewId = text(evidence.borrowing_base_review_id);
  const calcId = text(evidence.calc_run_id);
  const covenants = useBorrowerCovenants(testId ? item.borrower_id : undefined);
  const calc = useCalculation(reviewId ? calcId : null);
  const test = covenants.data?.tests.find((row) => row.id === testId);
  const facts = useFactsById(test ? [test.value_fact_id, test.threshold_fact_id, test.headroom_fact_id, test.reported_fact_id] : []);

  if (testId) {
    if (!test || !facts.data) return covenants.isPending || facts.isPending ? <Skeleton className="h-[74px] w-full" /> : null;
    const outcome = OUTCOME[test.outcome];
    const fact = (id: string | null) => (id ? facts.data?.[id] : undefined);
    const headroom = fact(test.headroom_fact_id);
    const headroomValue = headroom ? Number(headroom.value) : null;
    return (
      <section aria-label="Key figures" data-key-figures="covenant" className="overflow-hidden rounded-md border border-hairline-strong bg-canvas">
        <p className="px-3 pt-2.5 pb-1 text-caption text-ink-700">
          <span className="font-medium text-ink">{test.covenant_name}</span>
          {test.operator ? ` · must be ${test.operator === '>=' ? 'at least' : 'at most'} the threshold` : ''}
        </p>
        <div className={GRID}>
          <Tile label="Calculated by code" note={<span className={outcome.tone === 'breach' ? 'font-medium text-red' : undefined}>{outcome.label}</span>}>
            <FactFigure fact={fact(test.value_fact_id)} weight="semibold" />
          </Tile>
          <Tile label="Threshold" note="from the approved terms">
            <FactFigure fact={fact(test.threshold_fact_id)} weight="semibold" />
          </Tile>
          {test.reported_fact_id ? (
            <Tile
              label="Reported"
              note={
                test.reported_in_compliance === true
                  ? 'certificate says compliant'
                  : test.reported_in_compliance === false
                    ? 'certificate says not compliant'
                    : 'on the certificate'
              }
            >
              <FactFigure fact={fact(test.reported_fact_id)} weight="semibold" />
            </Tile>
          ) : null}
          {headroom ? (
            <Tile
              label="Headroom"
              note={
                headroomValue !== null && Number.isFinite(headroomValue) ? (
                  // the track runs from -20% to +40%; a plot position only, the figure is the stored fact above
                  <Meter
                    position={(headroomValue + 20) / 60}
                    tone={headroomValue < 0 ? 'breach' : headroomValue < 10 ? 'attention' : 'pass'}
                    label="Headroom against the threshold"
                    className="w-20"
                  />
                ) : undefined
              }
            >
              <FactFigure fact={headroom} weight="semibold" />
            </Tile>
          ) : null}
        </div>
      </section>
    );
  }

  if (reviewId && calcId) {
    if (!calc.data) return calc.isPending ? <Skeleton className="h-[74px] w-full" /> : null;
    const out = (key: string) => (typeof calc.data.outputs[key] === 'string' ? (calc.data.outputs[key] as string) : null);
    const figure = (key: string, label: string) => {
      const value = out(key);
      return value === null ? null : (
        <SourcedFigure
          value={value}
          unit="usd"
          kind="calculated"
          label={label}
          context="Borrowing base calculation"
          source={{ type: 'calculation', id: calcId }}
          weight="semibold"
          scale={1000}
        />
      );
    };
    const base = figure('borrowing_base', 'Borrowing base');
    const drawn = figure('outstanding', 'Borrowings');
    const over = figure('over_advance', 'Over-advance');
    const overValue = out('over_advance');
    if (!base && !drawn) return null;
    return (
      <section aria-label="Key figures" data-key-figures="borrowing-base" className="overflow-hidden rounded-md border border-hairline-strong bg-canvas">
        <p className="px-3 pt-2.5 pb-1 text-caption text-ink-700">
          <span className="font-medium text-ink">Borrowing base, recalculated by code</span> · USD thousands
        </p>
        <div className={GRID}>
          {base ? <Tile label="Recalculated base">{base}</Tile> : null}
          {drawn ? <Tile label="Borrowings">{drawn}</Tile> : null}
          {over && overValue !== null && Number(overValue) > 0 ? (
            <Tile label="Over-advance" note={<span className="font-medium text-red">Borrowings exceed the base</span>}>
              {over}
            </Tile>
          ) : null}
        </div>
      </section>
    );
  }
  return null;
}

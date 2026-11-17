import type { Calculation, CalcInputApi, CalcStep } from '@/api/schema';
import type { Unit } from '@/api/types';
import { formatDate } from '@/design';
import { humanize, periodLabel } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { FactFigure, SourcedFigure, StaticFigure } from './figures';

type Row =
  | { type: 'line'; step: CalcStep; depth: number }
  | { type: 'input'; input: CalcInputApi; depth: number }
  | { type: 'subtotal' | 'total'; step: CalcStep; label: string; depth: number };

/** The stored steps as ledger rows: each line, its parts when it is built from several periods, and each named result. */
function rowsOf(calc: Calculation, resultLabel: string): Row[] {
  const rows: Row[] = [];
  calc.steps.forEach((step, index) => {
    const next = calc.steps[index + 1];
    if (step.op === 'line') {
      rows.push({ type: 'line', step, depth: 1 });
      if (step.inputs.length > 1) for (const input of step.inputs) rows.push({ type: 'input', input, depth: 2 });
    } else if (step.op === 'named') {
      rows.push({ type: step.final ? 'total' : 'subtotal', step, label: step.final ? resultLabel : step.name, depth: 0 });
    } else if (step.op === 'addback') {
      rows.push({ type: 'line', step, depth: 1 });
    } else {
      // An unnamed sum or difference that the next step names is shown once, under its name.
      if (next && next.op === 'named' && next.value === step.value) return;
      rows.push({ type: step.final ? 'total' : 'subtotal', step, label: step.final ? resultLabel : step.name, depth: 0 });
    }
  });
  return rows;
}

const signMark = (sign: number) => (sign < 0 ? '−' : '+');

export interface CalculationBreakdownProps {
  calc: Calculation;
  /** Name of the final result, for example the covenant's name. */
  resultLabel: string;
  resultUnit: Unit;
  /** Inside the source drawer the calculation is already on screen, so its own lines do not link back to it. */
  selfContained?: boolean;
  className?: string;
}

/**
 * A calculation as code ran it. Every input is a stored fact that opens its own source; lines built
 * from several periods list those periods beneath them; named results carry a rule above.
 */
export function CalculationBreakdown({ calc, resultLabel, resultUnit, selfContained, className }: CalculationBreakdownProps) {
  const rows = rowsOf(calc, resultLabel);
  const outputValue = typeof calc.outputs.value === 'string' ? calc.outputs.value : null;

  const derived = (step: CalcStep, strong: boolean, unit: Unit, value: string) => {
    const format = unit === 'usd' ? { scale: 1000 as const, unitMark: false } : {};
    return selfContained ? (
      <StaticFigure value={value} unit={unit} kind="calculated" align="column" weight={strong ? 'semibold' : 'regular'} {...format} />
    ) : (
      <SourcedFigure
        value={value}
        unit={unit}
        kind="calculated"
        label={step.name}
        context={step.period_end ? `Period ended ${formatDate(step.period_end)}` : undefined}
        source={{ type: 'calculation', id: calc.id, title: resultLabel }}
        align="column"
        weight={strong ? 'semibold' : 'regular'}
        {...format}
      />
    );
  };

  return (
    <div className={className}>
      <table className="w-full border-separate border-spacing-0 text-body">
        <caption className="sr-only">Calculation of {resultLabel}, step by step</caption>
        <thead>
          <tr>
            <th scope="col" className="eyebrow h-8 border-b border-ink px-4 text-left">
              Component
            </th>
            <th scope="col" className="eyebrow h-8 w-44 border-b border-ink px-4 text-right whitespace-nowrap">
              Value <span className="font-medium tracking-normal normal-case">USD thousands, ratios as stated</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const last = index === rows.length - 1;
            if (row.type === 'input') {
              const fact = row.input.fact_id ? calc.facts[row.input.fact_id] : undefined;
              return (
                <tr key={`input-${index}`}>
                  <th scope="row" className={cx('px-4 py-1 text-left font-regular text-ink-500', !last && 'border-b border-hairline')}>
                    <span className="flex items-baseline gap-2" style={{ paddingLeft: row.depth * 16 }}>
                      <span aria-hidden className="inline-block w-3 shrink-0 text-center">
                        {signMark(row.input.sign)}
                      </span>
                      <span className="sr-only">{row.input.sign < 0 ? 'less' : 'plus'}</span>{' '}
                      {row.input.period_end ? periodLabel(row.input.period_end, row.input.months ?? 0) : row.input.name}
                    </span>
                  </th>
                  <td className={cx('px-4 py-1 text-right', !last && 'border-b border-hairline')}>
                    <FactFigure fact={fact} scale={1000} unitMark={fact?.unit !== 'usd'} align="column" absent="Input fact not found" />
                  </td>
                </tr>
              );
            }
            const strong = row.type !== 'line';
            const total = row.type === 'total';
            const step = row.step;
            const single = row.type === 'line' && step.inputs.length === 1 ? step.inputs[0] : undefined;
            const singleFact = single?.fact_id ? calc.facts[single.fact_id] : undefined;
            const unit: Unit = total ? resultUnit : step.unit;
            const value = total && outputValue ? outputValue : (step.value ?? '');
            return (
              <tr key={`step-${step.n}`} className={cx(strong && 'bg-canvas')}>
                <th
                  scope="row"
                  className={cx('px-4 py-1.5 text-left', !last && 'border-b border-hairline', strong ? 'font-semibold text-ink' : 'font-regular text-ink-700')}
                >
                  <span className="flex items-baseline gap-2" style={{ paddingLeft: row.depth * 16 }}>
                    <span className="min-w-0">
                      {row.type === 'line' ? step.name : row.label}
                      {row.type === 'line' && step.basis ? <span className="text-ink-500">, {step.basis}</span> : null}
                    </span>
                  </span>
                </th>
                <td
                  className={cx(
                    'px-4 py-1.5 text-right',
                    !last && !total && 'border-b border-hairline',
                    row.type === 'subtotal' && 'border-t border-t-ink',
                    total && 'border-t border-b-[3px] border-double border-ink',
                  )}
                >
                  {singleFact ? (
                    <FactFigure fact={singleFact} scale={1000} unitMark={singleFact.unit !== 'usd'} align="column" />
                  ) : value ? (
                    derived(step, strong, unit, value)
                  ) : (
                    <FactFigure fact={undefined} align="column" />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {calc.addbacks.length > 0 ? (
        <div className="border-t border-hairline-strong px-4 pt-3 pb-1">
          <h4 className="eyebrow mb-1">Add-backs under the terms in force</h4>
          <table className="w-full text-body">
            <caption className="sr-only">Add-backs applied to EBITDA</caption>
            <thead>
              <tr className="text-left">
                <th scope="col" className="eyebrow border-b border-ink py-1 font-semibold">
                  Add-back
                </th>
                <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                  Claimed
                </th>
                <th scope="col" className="eyebrow border-b border-ink py-1 text-right font-semibold">
                  Applied
                </th>
                <th scope="col" className="eyebrow border-b border-ink py-1 pl-4 font-semibold">
                  Cap
                </th>
              </tr>
            </thead>
            <tbody>
              {calc.addbacks.map((addback, index) => (
                <tr key={`${addback.name}-${index}`} className="border-b border-hairline last:border-b-0">
                  <th scope="row" className="py-1.5 text-left font-regular text-ink-700">
                    {humanize(addback.name)}
                  </th>
                  <td className="py-1.5 text-right">
                    <StaticFigure value={addback.raw} unit="usd" kind="calculated" scale={1000} unitMark={false} />
                  </td>
                  <td className="py-1.5 text-right">
                    <StaticFigure value={addback.applied} unit="usd" kind="calculated" scale={1000} unitMark={false} weight="semibold" />
                  </td>
                  <td className="py-1.5 pl-4 text-ink-700">
                    {addback.capped ? 'Capped' : addback.cap_type ? 'Within the cap' : 'Uncapped'}
                    {addback.cap_limit ? (
                      <>
                        {' at '}
                        <StaticFigure value={addback.cap_limit} unit="usd" kind="extracted" scale={1000} unitMark={false} />
                      </>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

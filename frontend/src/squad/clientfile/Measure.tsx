import { Absent, FactFigure } from '@/source/figures';
import type { MeasurePoint, MeasureSeries } from '../api/types';

/** Plot positions only: each bar's height comes from its stored value; the bars carry no number of their own.
 * Three kinds of point, never confused: a positive figure is a bar scaled to the largest; a stored zero or negative
 * figure (a breached headroom, the worst case) is a short bar marked `sq-bar-low` in the breach colour; a period
 * with no stored figure is an outline (`sq-bar-none`), never a bar. */
export function TrendBars({ points, label }: { points: MeasurePoint[]; label: string }) {
  const values = points.map((p) => (p.fact ? Number(p.fact.value) : null)); // parsed for the plot position only
  const max = Math.max(0, ...values.filter((v): v is number => v !== null));
  return (
    <span className="sq-bars" role="img" aria-label={`${label}, last ${points.length} ${points.length === 1 ? 'period' : 'periods'}`}>
      {points.map((p, i) => {
        const v = values[i];
        if (v === null || v === undefined) return <span key={p.period_end} className="sq-bar sq-bar-none" data-point="none" />;
        if (v <= 0 || max === 0) return <span key={p.period_end} className="sq-bar sq-bar-low" data-point="low" />;
        return <span key={p.period_end} className="sq-bar" data-point="measured" style={{ height: `${Math.max(12, Math.round((v / max) * 100))}%` }} />;
      })}
    </span>
  );
}

/** The latest point: its stored figure with its source, or the stored reason there is none. */
export function MeasureNow({ series }: { series: MeasureSeries }) {
  const last = series.points.at(-1);
  if (!last) return <Absent reason="No period has been tested yet" />;
  return last.fact ? <FactFigure fact={last.fact} /> : <span className="sq-muted">{last.note ?? 'Not measured'}</span>;
}

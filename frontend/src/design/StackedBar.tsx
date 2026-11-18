import { cx } from '@/lib/cx';

/** Fill for a segment: a status colour that carries meaning, or a step of the ink ramp (1 light to 6 dark). */
export type BarFill = 'breach' | 'attention' | 'pass' | 'agent' | 'muted' | 1 | 2 | 3 | 4 | 5 | 6;

const fills: Record<string, string> = {
  breach: 'var(--red-mark)',
  attention: 'var(--amber-mark)',
  pass: 'var(--green-mark)',
  agent: 'var(--iris-mark)',
  muted: 'var(--hairline-strong)',
  1: 'var(--ramp-1)',
  2: 'var(--ramp-2)',
  3: 'var(--ramp-3)',
  4: 'var(--ramp-4)',
  5: 'var(--ramp-5)',
  6: 'var(--ramp-6)',
};

export const barFill = (fill: BarFill): string => fills[String(fill)] ?? fills.muted!;

export interface BarSegment {
  id: string;
  label: string;
  /** A count from the API. The bar only turns it into a width. */
  count: number;
  fill: BarFill;
}

export interface StackedBarProps {
  /** What the whole bar shows, for a screen reader: "Cycles by stage". */
  label: string;
  segments: BarSegment[];
  /** Makes each segment a button. */
  onSelect?: (id: string) => void;
  selectedId?: string | null;
  className?: string;
}

/**
 * A proportional bar. Widths are plot positions only: the counts are shown as text beside it by
 * the caller, never read off the bar.
 */
export function StackedBar({ label, segments, onSelect, selectedId, className }: StackedBarProps) {
  const shown = segments.filter((segment) => segment.count > 0);
  const total = shown.reduce((sum, segment) => sum + segment.count, 0);
  const summary = shown.map((segment) => `${segment.label} ${segment.count}`).join(', ');
  return (
    <div
      role="img"
      aria-label={`${label}: ${summary || 'nothing to show'}`}
      className={cx('flex h-2.5 w-full gap-px overflow-hidden rounded-xs bg-sunken', className)}
    >
      {total === 0
        ? null
        : shown.map((segment) => {
            const style = { width: `${(segment.count / total) * 100}%`, background: barFill(segment.fill) };
            const dimmed = selectedId != null && selectedId !== segment.id;
            return onSelect ? (
              <button
                key={segment.id}
                type="button"
                tabIndex={-1}
                aria-hidden
                title={`${segment.label}: ${segment.count}`}
                onClick={() => onSelect(segment.id)}
                style={style}
                className={cx('h-full min-w-[3px] t-colors hover:opacity-80', dimmed && 'opacity-35')}
              />
            ) : (
              <span key={segment.id} title={`${segment.label}: ${segment.count}`} style={style} className={cx('h-full min-w-[3px]', dimmed && 'opacity-35')} />
            );
          })}
    </div>
  );
}

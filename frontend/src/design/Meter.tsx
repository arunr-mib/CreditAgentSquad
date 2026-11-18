import { cx } from '@/lib/cx';

export interface MeterProps {
  /** Position of the fill along the track, 0 to 1. A plot position only; the figure is shown as text by the caller. */
  position: number;
  tone: 'breach' | 'attention' | 'pass' | 'neutral';
  /** What the meter shows, in words, including the figure as text: "Headroom 7.2%". */
  label: string;
  className?: string;
}

const tones: Record<MeterProps['tone'], string> = {
  breach: 'var(--red-mark)',
  attention: 'var(--amber-mark)',
  pass: 'var(--green-mark)',
  neutral: 'var(--ramp-4)',
};

/** One quantity against its limit, as a short track. Never the only place a figure appears. */
export function Meter({ position, tone, label, className }: MeterProps) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(position) ? position : 0));
  return (
    <span role="img" aria-label={label} title={label} className={cx('inline-block h-1.5 w-16 overflow-hidden rounded-xs bg-sunken align-middle', className)}>
      <span className="block h-full rounded-xs" style={{ width: `${Math.max(clamped * 100, 4)}%`, background: tones[tone] }} />
    </span>
  );
}

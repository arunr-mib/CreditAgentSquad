import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

/**
 * Colour carries meaning only:
 * breach = covenant breach or a critical item, attention = needs a person or a high item, pass = verified pass or recorded resolution,
 * agent = written by an agent, neutral = informational state, muted = not started.
 */
export type StatusTone = 'breach' | 'attention' | 'pass' | 'agent' | 'neutral' | 'muted';

const dot: Record<StatusTone, string> = {
  breach: 'bg-red-mark',
  attention: 'bg-amber-mark',
  pass: 'bg-green-mark',
  agent: 'bg-iris-mark',
  neutral: 'bg-ink-700',
  muted: 'border border-ink-400 bg-transparent',
};

const word: Record<StatusTone, string> = {
  breach: 'text-red',
  attention: 'text-amber',
  pass: 'text-green',
  agent: 'text-iris',
  neutral: 'text-ink',
  muted: 'text-ink-500',
};

export interface StatusDotProps {
  tone: StatusTone;
  children: ReactNode;
  /** Colour the word as well as the dot, and set it in medium weight. For outcomes that must not be missed. */
  emphasis?: boolean;
  className?: string;
}

/** Status is a small dot plus a word. Never a pill, never colour alone. */
export function StatusDot({ tone, children, emphasis, className }: StatusDotProps) {
  return (
    <span className={cx('inline-flex items-baseline gap-1.5 whitespace-nowrap', className)}>
      <span aria-hidden className={cx('relative -top-px size-[7px] shrink-0 rounded-full', dot[tone])} />
      <span className={cx(emphasis ? cx(word[tone], 'font-medium') : tone === 'muted' ? 'text-ink-500' : 'text-ink')}>{children}</span>
    </span>
  );
}

import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

/**
 * A capsule tag. For severity and actionable status only: something a reader must act on or must
 * not miss. Dates, identifiers, periods and routine roles stay plain text.
 * gate = a human approval the reader cannot give; never iris, which is kept for agent output.
 */
export type TagTone = 'breach' | 'attention' | 'pass' | 'agent' | 'gate' | 'neutral';

const tones: Record<TagTone, string> = {
  breach: 'border-red-border bg-red-bg text-red',
  attention: 'border-amber-border bg-amber-bg text-amber',
  pass: 'border-green-border bg-green-bg text-green',
  agent: 'border-iris-border bg-iris-bg text-iris',
  gate: 'border-ink bg-ink text-canvas',
  neutral: 'border-hairline-strong bg-sunken text-ink-700',
};

export interface TagProps {
  tone: TagTone;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}

export function Tag({ tone, children, icon, className }: TagProps) {
  return (
    <span
      data-tag={tone}
      className={cx(
        'inline-flex h-5 max-w-full items-center gap-1 rounded-full border px-2 text-caption font-medium whitespace-nowrap',
        tones[tone],
        className,
      )}
    >
      {icon ? (
        <span aria-hidden className="inline-flex shrink-0">
          {icon}
        </span>
      ) : null}
      {children}
    </span>
  );
}

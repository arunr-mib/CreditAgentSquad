import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

export interface PageHeaderProps {
  eyebrow?: ReactNode;
  title: string;
  /** A line of facts about the page subject, under the title. */
  meta?: ReactNode;
  actions?: ReactNode;
  /** The page title is the h1. Use 'p' only where a header is shown as a specimen inside another page. */
  as?: 'h1' | 'p';
  className?: string;
}

export function PageHeader({ eyebrow, title, meta, actions, as: Title = 'h1', className }: PageHeaderProps) {
  return (
    <header className={cx('flex flex-col gap-x-6 gap-y-3 md:flex-row md:items-end md:justify-between', className)}>
      <div className="min-w-0">
        {eyebrow ? <div className="eyebrow mb-1 flex items-center gap-2">{eyebrow}</div> : null}
        <Title className="text-page font-semibold tracking-[-0.018em] text-ink">{title}</Title>
        {meta ? <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-body text-ink-700">{meta}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 pb-0.5 md:shrink-0 md:flex-nowrap">{actions}</div> : null}
    </header>
  );
}

/** A label and value pair for header meta lines and definition rows. */
export function MetaItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-ink-500">{label}</span>
      <span className="text-ink">{children}</span>
    </span>
  );
}

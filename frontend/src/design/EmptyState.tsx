import type { ReactNode } from 'react';
import { cx } from '@/lib/cx';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/** Says plainly what is absent and offers the one way forward, if there is one. */
export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cx('flex flex-col items-start gap-1 px-6 py-8', className)}>
      {icon ? <div className="mb-2 text-ink-500">{icon}</div> : null}
      <p className="text-title font-semibold text-ink">{title}</p>
      {description ? <p className="max-w-[52ch] text-prose text-ink-700">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

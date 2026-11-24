import type { HTMLAttributes, ReactNode } from 'react';
import { cx } from '@/lib/cx';

/** A surface with a hairline border. No shadow, no coloured edge. */
export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx('rounded-md border border-hairline-strong bg-surface', className)} {...rest} />;
}

export interface CardHeaderProps {
  title: ReactNode;
  eyebrow?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  as?: 'h2' | 'h3' | 'h4';
  className?: string;
}

export function CardHeader({ title, eyebrow, meta, actions, as: Heading = 'h3', className }: CardHeaderProps) {
  return (
    <div className={cx('flex items-start justify-between gap-4 px-4 pt-3.5 pb-3', className)}>
      <div className="min-w-0">
        {eyebrow ? <div className="eyebrow mb-0.5">{eyebrow}</div> : null}
        <Heading className="text-title font-semibold text-ink">{title}</Heading>
        {meta ? <div className="mt-0.5 text-caption text-ink-500">{meta}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx('px-4 pb-4', className)} {...rest} />;
}

/** A hairline between card regions. */
export function CardRule({ className }: { className?: string }) {
  return <hr className={cx('border-0 border-t border-hairline', className)} />;
}

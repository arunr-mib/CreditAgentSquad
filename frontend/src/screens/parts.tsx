import { useId, type ReactNode, type TextareaHTMLAttributes } from 'react';
import { errorMessage } from '@/api/client';
import type { Severity } from '@/api/types';
import { Button, Card, EmptyState, fieldLabelClass, SkeletonRows, StatusDot, type StatusTone } from '@/design';
import { SEVERITY_LABEL, SEVERITY_TONE } from '@/domain/labels';
import { cx } from '@/lib/cx';

/** A notice inside the page: a hairline border on all four sides and a dot plus a word. No coloured edge. */
export function Notice({
  tone = 'neutral',
  title,
  children,
  action,
  className,
}: {
  tone?: StatusTone;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role={tone === 'attention' || tone === 'breach' ? 'alert' : 'note'}
      className={cx('rounded-md border border-hairline-strong bg-surface px-4 py-3', className)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-body font-semibold text-ink">
            <StatusDot tone={tone} emphasis={tone === 'breach'} className="whitespace-normal!">
              {title}
            </StatusDot>
          </p>
          {children ? <div className="mt-0.5 pl-[13px] text-body text-pretty text-ink-700">{children}</div> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </div>
  );
}

/** A failed request, in the server's own words, with the one way forward. */
export function ErrorNotice({ error, onRetry, what }: { error: unknown; onRetry?: () => void; what: string }) {
  return (
    <Notice tone="attention" title={`${what} could not be loaded`} action={onRetry ? <Button onClick={onRetry}>Try again</Button> : undefined}>
      {errorMessage(error)}
    </Notice>
  );
}

interface LoadProps<T> {
  query: { data: T | undefined; isPending: boolean; error: unknown; refetch: () => unknown };
  /** What is loading, in plain words: "The work queue". */
  what: string;
  rows?: number;
  children: (data: T) => ReactNode;
}

/** Loading, then error or content. Every screen goes through this so no state is left blank. */
export function Load<T>({ query, what, rows = 8, children }: LoadProps<T>) {
  if (query.data !== undefined) return <>{children(query.data)}</>;
  if (query.error) return <ErrorNotice error={query.error} what={what} onRetry={() => void query.refetch()} />;
  return <SkeletonRows rows={rows} label={`Loading ${what.charAt(0).toLowerCase()}${what.slice(1)}`} />;
}

export function EmptyCard({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) {
  return (
    <Card>
      <EmptyState title={title} description={description} action={action} />
    </Card>
  );
}

export function SeverityDot({ severity }: { severity: Severity }) {
  return (
    <StatusDot tone={SEVERITY_TONE[severity] ?? 'neutral'}>
      <span className={severity === 'critical' ? 'font-semibold' : undefined}>{SEVERITY_LABEL[severity] ?? severity}</span>
    </StatusDot>
  );
}

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
  error?: string;
}

export function Textarea({ label, hint, error, className, id, ...rest }: TextareaProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const note = error ?? hint;
  return (
    <div className={className}>
      <label htmlFor={fieldId} className={fieldLabelClass}>
        {label}
      </label>
      <textarea
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={note ? `${fieldId}-note` : undefined}
        className={cx(
          'block min-h-[72px] w-full resize-y rounded-sm border bg-surface px-2.5 py-1.5 text-body text-ink t-colors placeholder:text-ink-500',
          error ? 'border-amber-mark' : 'border-ink-400 hover:border-ink-500',
        )}
        {...rest}
      />
      {note ? (
        <p id={`${fieldId}-note`} className={cx('mt-1 text-caption', error ? 'font-medium text-amber' : 'text-ink-500')}>
          {note}
        </p>
      ) : null}
    </div>
  );
}

/** A definition row used in summary cards: label left, value right, hairline between rows. */
export function Def({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-h-8 items-baseline justify-between gap-6 border-b border-hairline py-1.5 text-body last:border-b-0">
      <dt className="shrink-0 text-ink-500">{label}</dt>
      <dd className="min-w-0 text-right text-ink">{children}</dd>
    </div>
  );
}

/** A section heading with an optional line of context on the right. */
export function SectionHead({ id, title, note, actions }: { id?: string; title: string; note?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
      <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <h2 id={id} className="text-title font-semibold text-ink">
          {title}
        </h2>
        {note ? <p className="text-caption text-ink-500">{note}</p> : null}
      </div>
      {actions ? <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">{actions}</div> : null}
    </div>
  );
}

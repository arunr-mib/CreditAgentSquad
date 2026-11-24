import { useId, type InputHTMLAttributes, type ReactNode, type Ref } from 'react';
import { cx } from '@/lib/cx';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** Hide the visible label (it stays the accessible name). Use only where context names the field. */
  hideLabel?: boolean;
  hint?: string;
  /** Validation message. Amber, because it needs attention; red is reserved for covenant breaches. */
  error?: string;
  leading?: ReactNode;
  trailing?: ReactNode;
  ref?: Ref<HTMLInputElement>;
}

export const fieldLabelClass = 'mb-1 block text-caption font-medium text-ink-700';

export function Input({ label, hideLabel, hint, error, leading, trailing, className, id, ...rest }: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const noteId = `${inputId}-note`;
  const note = error ?? hint;
  return (
    <div className={className}>
      <label htmlFor={inputId} className={hideLabel ? 'sr-only' : fieldLabelClass}>
        {label}
      </label>
      <div
        className={cx(
          'flex h-8 items-center gap-2 rounded-sm border bg-surface px-2.5 t-colors',
          'focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-cobalt',
          error ? 'border-amber-mark' : 'border-ink-400 hover:border-ink-500',
        )}
      >
        {leading ? <span className="flex shrink-0 text-ink-500">{leading}</span> : null}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? noteId : undefined}
          className="min-w-0 flex-1 bg-transparent text-body text-ink outline-none placeholder:text-ink-500"
          {...rest}
        />
        {trailing ? <span className="flex shrink-0 text-ink-500">{trailing}</span> : null}
      </div>
      {note ? (
        <p id={noteId} className={cx('mt-1 text-caption', error ? 'font-medium text-amber' : 'text-ink-500')}>
          {note}
        </p>
      ) : null}
    </div>
  );
}

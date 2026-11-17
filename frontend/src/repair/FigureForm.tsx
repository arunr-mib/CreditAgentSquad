import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { ApiError, errorMessage } from '@/api/client';
import type { Unit } from '@/api/types';
import { Button, formatFigure, Input } from '@/design';
import { cx } from '@/lib/cx';
import { Textarea } from '@/screens/parts';

const UNIT_LABEL: Record<Unit, string> = {
  usd: 'whole US dollars',
  ratio: 'a ratio',
  pct: 'a fraction: 0.072 is 7.2%',
  days: 'days',
  count: 'a count',
};

/** The number a person typed, without grouping commas or spaces; null when it is not a plain decimal. */
export function parseFigureInput(text: string): string | null {
  const cleaned = text.replace(/[,\s]/g, '');
  return /^[-+]?\d+(\.\d+)?$/.test(cleaned) ? cleaned.replace(/^\+/, '') : null;
}

/** What will be stored, read back in the workspace's own formatting, so a slip of three zeros is seen before it is sent. */
export function readBack(value: string, unit: Unit, scale?: number): string {
  const dp = unit === 'usd' && value.includes('.') ? 2 : undefined;
  const stored = formatFigure(unit === 'pct' ? shiftPercent(value) : value, unit, { dp }).text;
  if (unit === 'usd' && scale === 1000) return `Will be stored as ${stored}, shown on a statement in thousands as ${formatFigure(value, 'usd', { scale: 1000, unitMark: false, dp: 0 }).text}.`;
  return `Will be stored as ${stored}.`;
}

/** 0.072 → 7.2, moving the decimal point on the string so no float is involved. */
function shiftPercent(value: string): string {
  const negative = value.startsWith('-');
  const [int = '0', frac = ''] = value.replace(/^-/, '').split('.');
  const padded = `${frac}00`;
  const whole = `${int}${padded.slice(0, 2)}`.replace(/^0+(?=\d)/, '');
  const rest = padded.slice(2).replace(/0+$/, '');
  return `${negative ? '-' : ''}${whole}${rest ? `.${rest}` : ''}`;
}

/** The server's refusal, named by what it means. The words that follow are the server's own. */
export function refusalTitle(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'Not recorded: your role cannot do this';
    if (error.status === 422) return 'Not recorded: the server refused this';
    if (error.status === 404) return 'Not recorded: it no longer exists';
  }
  return 'Not recorded';
}

export function Refusal({ error, className }: { error: unknown; className?: string }) {
  return (
    <p role="alert" data-refusal className={cx('text-body text-pretty text-amber', className)}>
      <span className="font-medium">{refusalTitle(error)}.</span> The server said: “{errorMessage(error)}”
    </p>
  );
}

export interface FigureFormProps {
  /** What the form does, as its accessible name and heading: "Correct accounts payable". */
  title: string;
  /** False for a rejection: only a reason is asked for. */
  withValue?: boolean;
  unit?: Unit;
  /** The value on file, to start from when correcting. */
  initialValue?: string;
  /** The scale the statement is printed in, for the read-back line. */
  scale?: number;
  submitLabel: string;
  pendingLabel: string;
  pending: boolean;
  /** The server's refusal of the last attempt, if any. */
  error: unknown;
  onSubmit: (entry: { value: string; reason: string }) => void;
  onCancel: () => void;
  /** What happens to the figure on file, said under the reason. */
  reasonHint?: string;
  className?: string;
}

/**
 * The value (in the units facts are stored in) and the reason for changing a figure. Both are checked
 * here before anything is sent; whatever the server then refuses is shown beside the button in its own words.
 */
export function FigureForm({ title, withValue = true, unit = 'usd', initialValue = '', scale, submitLabel, pendingLabel, pending, error, onSubmit, onCancel, reasonHint = 'Recorded in the ledger with your name.', className }: FigureFormProps) {
  const headingId = useId();
  const [value, setValue] = useState(initialValue);
  const [reason, setReason] = useState('');
  const [problems, setProblems] = useState<{ value?: string; reason?: string }>({});
  const parsed = parseFigureInput(value);
  const formRef = useRef<HTMLFormElement>(null);

  // The person asked for this form by pressing a button: focus moves to its first field so the
  // keyboard continues where the eye is. Nothing else on the page takes focus by itself.
  useEffect(() => {
    formRef.current?.querySelector<HTMLElement>('input, textarea')?.focus();
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    const next: { value?: string; reason?: string } = {};
    if (withValue && !parsed) next.value = value.trim() ? 'This is not a number. Enter digits only, for example 1236000.' : 'Enter the figure.';
    if (!reason.trim()) next.reason = 'A reason is required. It is recorded in the ledger with your name.';
    setProblems(next);
    if (next.value || next.reason) return;
    onSubmit({ value: parsed ?? '', reason: reason.trim() });
  }

  return (
    <form ref={formRef} onSubmit={submit} noValidate aria-labelledby={headingId} data-figure-form className={cx('space-y-2.5 rounded-md border border-hairline-strong bg-surface px-3 pt-2.5 pb-3', className)}>
      <p id={headingId} className="text-body font-semibold text-ink">
        {title}
      </p>
      {withValue ? (
        <Input
          label={`Value, in ${UNIT_LABEL[unit]}`}
          inputMode="decimal"
          autoComplete="off"
          className="[&_input]:[font-variant-numeric:tabular-nums_lining-nums]"
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setProblems((current) => ({ ...current, value: undefined }));
          }}
          error={problems.value}
          hint={parsed ? readBack(parsed, unit, scale) : unit === 'usd' ? 'A figure printed in thousands as 1,236 is entered as 1236000. Use a minus sign for a negative.' : undefined}
        />
      ) : null}
      <Textarea
        label="Reason (required)"
        rows={2}
        className="[&_textarea]:min-h-[52px]"
        value={reason}
        onChange={(event) => {
          setReason(event.target.value);
          setProblems((current) => ({ ...current, reason: undefined }));
        }}
        error={problems.reason}
        hint={reasonHint}
      />
      {error ? <Refusal error={error} /> : null}
      <div className="flex items-center gap-2">
        <Button type="submit" variant="primary" size="sm" disabled={pending}>
          {pending ? pendingLabel : submitLabel}
        </Button>
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={pending}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

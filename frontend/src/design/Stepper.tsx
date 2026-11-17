import { Check, Minus, X } from 'lucide-react';
import type { StageStatus } from '@/api/types';
import { cx } from '@/lib/cx';

export interface Step {
  id: string;
  label: string;
  status: StageStatus;
  detail?: string;
}

const statusWord: Record<StageStatus, string> = {
  pending: 'Not started',
  running: 'Running',
  needs_person: 'Needs a person',
  done: 'Done',
  skipped: 'Skipped',
  failed: 'Failed',
};

function Marker({ status }: { status: StageStatus }) {
  const base = 'relative z-10 flex size-4 shrink-0 items-center justify-center rounded-full';
  switch (status) {
    case 'done':
      return (
        <span className={cx(base, 'bg-ink text-canvas')}>
          <Check size={10} strokeWidth={3} aria-hidden />
        </span>
      );
    case 'running':
      return (
        <span className={cx(base, 'border-[1.5px] border-ink bg-canvas')}>
          <span className="size-1.5 rounded-full bg-ink" />
        </span>
      );
    case 'needs_person':
      return (
        <span className={cx(base, 'bg-amber-mark')}>
          <span className="size-1.5 rounded-full bg-white" />
        </span>
      );
    case 'failed':
      return (
        <span className={cx(base, 'bg-amber-mark text-white')}>
          <X size={10} strokeWidth={3} aria-hidden />
        </span>
      );
    case 'skipped':
      return (
        <span className={cx(base, 'border-[1.5px] border-ink-400 bg-canvas text-ink-500')}>
          <Minus size={10} strokeWidth={2.5} aria-hidden />
        </span>
      );
    case 'pending':
      return <span className={cx(base, 'border-[1.5px] border-ink-400 bg-canvas')} />;
  }
}

export interface StepperProps {
  steps: Step[];
  label: string;
  className?: string;
}

/**
 * The stages of a monitoring cycle. Done is ink, not green: finishing a stage is a screen state,
 * and green is kept for verified passes. Amber marks the stage waiting for a person.
 */
export function Stepper({ steps, label, className }: StepperProps) {
  const currentIndex = steps.findIndex((step) => step.status === 'needs_person' || step.status === 'running' || step.status === 'failed');
  return (
    <ol aria-label={label} className={cx('flex', className)}>
      {steps.map((step, index) => {
        const next = steps[index + 1];
        const attention = step.status === 'needs_person' || step.status === 'failed';
        const reached = step.status !== 'pending';
        return (
          <li key={step.id} aria-current={index === currentIndex ? 'step' : undefined} className="relative min-w-0 flex-1 pr-3 last:flex-none last:pr-0">
            {next ? (
              <span
                aria-hidden
                className={cx(
                  'absolute top-2 right-0 left-4 h-px -translate-y-1/2',
                  step.status === 'done' && next.status !== 'pending' ? 'bg-ink' : 'bg-hairline-strong',
                )}
              />
            ) : null}
            <Marker status={step.status} />
            <div className={cx('mt-2 text-caption font-medium text-pretty', reached ? 'text-ink' : 'text-ink-500')}>{step.label}</div>
            <div className={cx('text-caption text-pretty', attention ? 'font-medium text-amber' : 'text-ink-500')}>
              {step.detail ?? statusWord[step.status]}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

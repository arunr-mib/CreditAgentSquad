import { Check, Minus, X } from 'lucide-react';
import { useState } from 'react';
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
  /**
   * Show what is done, the current stage and the next one, and fold the stages after that into
   * one item a person can open. For long cycles, where a row of "Not started" says nothing.
   */
  collapseLater?: boolean;
}

/**
 * The stages of a monitoring cycle. Done is ink, not green: finishing a stage is a screen state,
 * and green is kept for verified passes. Amber marks the stage waiting for a person.
 */
export function Stepper({ steps, label, className, collapseLater = false }: StepperProps) {
  const [showAll, setShowAll] = useState(false);
  const currentIndex = steps.findIndex((step) => step.status === 'needs_person' || step.status === 'running' || step.status === 'failed');
  const lastReached = steps.reduce((last, step, index) => (step.status === 'pending' ? last : index), -1);
  // everything reached, plus the one stage that comes next
  const later = collapseLater ? steps.slice(lastReached + 2) : [];
  const folded = later.length >= 2 && !showAll;
  const shown = folded ? steps.slice(0, lastReached + 2) : steps;
  return (
    <div className={className}>
      <ol aria-label={label} className="flex max-sm:flex-col max-sm:gap-2.5">
        {shown.map((step, index) => {
          const next = shown[index + 1];
          const attention = step.status === 'needs_person' || step.status === 'failed';
          const reached = step.status !== 'pending';
          const line = next ?? (folded ? later[0] : undefined);
          return (
            <li
              key={step.id}
              aria-current={index === currentIndex ? 'step' : undefined}
              className={cx(
                'relative min-w-0 flex-1 pr-3 max-sm:flex max-sm:items-start max-sm:gap-2.5 max-sm:pr-0',
                folded ? undefined : 'sm:last:flex-none sm:last:pr-0',
              )}
            >
              {line ? (
                <span
                  aria-hidden
                  className={cx(
                    'absolute top-2 right-0 left-4 h-px -translate-y-1/2 max-sm:hidden',
                    step.status === 'done' && line.status !== 'pending' ? 'bg-ink' : 'bg-hairline-strong',
                  )}
                />
              ) : null}
              <Marker status={step.status} />
              <div className="min-w-0 max-sm:flex max-sm:flex-wrap max-sm:gap-x-2">
                <div className={cx('mt-2 text-caption font-medium text-pretty max-sm:mt-0', reached ? 'text-ink' : 'text-ink-500')}>{step.label}</div>
                <div className={cx('text-caption text-pretty', attention ? 'font-medium text-amber' : 'text-ink-500')}>
                  {step.detail ?? statusWord[step.status]}
                </div>
              </div>
            </li>
          );
        })}
        {folded ? (
          <li className="relative min-w-0 flex-none max-sm:flex max-sm:items-start max-sm:gap-2.5">
            <Marker status="pending" />
            <div className="max-sm:flex max-sm:flex-wrap max-sm:gap-x-2">
              <button
                type="button"
                onClick={() => setShowAll(true)}
                aria-expanded={false}
                className="link mt-2 block text-left text-caption font-medium max-sm:mt-0"
              >
                {later.length} later stages
              </button>
              <div className="text-caption text-ink-500">Not started</div>
            </div>
          </li>
        ) : null}
      </ol>
      {collapseLater && later.length >= 2 && showAll ? (
        <button type="button" onClick={() => setShowAll(false)} aria-expanded className="link mt-2 text-caption font-medium">
          Show fewer stages
        </button>
      ) : null}
    </div>
  );
}

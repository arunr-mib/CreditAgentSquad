import { useMemo } from 'react';
import { useBorrowerCovenants } from '@/api/hooks';
import type { Recalculation } from '@/api/schema';
import type { CovenantOutcome } from '@/api/types';
import { StatusDot } from '@/design';
import { OUTCOME } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { outcomeLabel, recalculationSummary } from './recalculation';

function Outcome({ outcome }: { outcome: string | null }) {
  const known = outcome ? OUTCOME[outcome as CovenantOutcome] : undefined;
  return (
    <StatusDot tone={known?.tone ?? 'muted'} emphasis={known?.emphasis}>
      {outcomeLabel(outcome)}
    </StatusDot>
  );
}

/**
 * What code recalculated after a figure changed, in words, announced to assistive technology.
 * A covenant whose outcome changed is listed with the outcome before and after.
 */
export function RecalculationNote({ recalculation, borrowerId, subject, className }: { recalculation: Recalculation; borrowerId?: string; subject?: string; className?: string }) {
  const covenants = useBorrowerCovenants(recalculation.covenants?.length ? borrowerId : undefined);
  const names = useMemo(() => Object.fromEntries((covenants.data?.tests ?? []).map((test) => [test.covenant_id, test.covenant_name])), [covenants.data]);
  const summary = recalculationSummary(recalculation, names, subject);
  return (
    <div role="status" aria-live="polite" data-recalculation className={cx('rounded-md border border-hairline-strong bg-canvas px-3 py-2', className)}>
      <p className="eyebrow">What code recalculated</p>
      <ul className="mt-1 space-y-0.5 text-body text-pretty text-ink-700">
        {summary.sentences.map((sentence) => (
          <li key={sentence}>{sentence}</li>
        ))}
      </ul>
      {summary.changes.length > 0 ? (
        <ul className="mt-2 border-t border-ink" aria-label="Covenant outcomes that changed">
          {summary.changes.map((change) => (
            <li key={`${change.covenant}-${change.period}`} aria-label={change.sentence} className="border-b border-hairline py-1.5 text-body last:border-b-0">
              <span className="font-medium text-ink">{change.covenant}</span> <span className="tnum text-ink-500">· {change.period}</span>
              <span className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
                <Outcome outcome={change.before} />
                <span aria-hidden className="text-ink-500">
                  →
                </span>
                <Outcome outcome={change.after} />
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

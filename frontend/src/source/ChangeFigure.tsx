import { useState } from 'react';
import { useCorrectFact, useRejectFact } from '@/api/hooks';
import type { FactChange, FactSource } from '@/api/schema';
import { Button, formatFigure, ProvenanceGlyph, StatusDot } from '@/design';
import { toFact } from '@/domain/labels';
import { FigureForm } from '@/repair/FigureForm';
import { RecalculationNote } from '@/repair/RecalculationNote';
import { useSource } from './context';

const CORRECTABLE = ['proposed', 'verified', 'confirmed'];

/**
 * Correct or reject the figure on show, for a person whose role may. A calculated figure offers
 * neither (the API refuses both): the figure it was calculated from is the one to correct. A
 * correction never edits the fact: a new fact supersedes it and both stay in the history.
 */
export function ChangeFigure({ data }: { data: FactSource }) {
  const { fact } = data;
  const source = useSource();
  const correct = useCorrectFact();
  const reject = useRejectFact();
  const [mode, setMode] = useState<'correct' | 'reject' | null>(null);
  const [result, setResult] = useState<{ kind: 'corrected' | 'rejected'; change: FactChange } | null>(null);

  if (result) {
    const { change } = result;
    const shown = toFact({ ...fact, ...change, label: fact.label });
    return (
      <div className="space-y-2" data-change-result={result.kind}>
        {result.kind === 'corrected' ? (
          <p className="flex flex-wrap items-baseline gap-x-1.5 text-body">
            <StatusDot tone="pass">Corrected. On file now:</StatusDot>
            <button
              type="button"
              aria-label={`${formatFigure(shown.value, shown.unit).text}, ${fact.label}. Entered by a person. Show source.`}
              onClick={() => source.open({ type: 'fact', id: change.id })}
              className="-mx-1 inline-flex items-center gap-1 rounded-xs px-1 font-medium text-ink t-colors hover:bg-cobalt-bg hover:text-cobalt-strong"
            >
              <span className="tnum">{formatFigure(shown.value, shown.unit).text}</span>
              <ProvenanceGlyph kind="manual" />
            </button>
          </p>
        ) : (
          <p className="text-body">
            <StatusDot tone="neutral">Rejected. This figure is set aside and nothing calculated from it stays in use.</StatusDot>
          </p>
        )}
        <p className="text-caption text-pretty text-ink-500">The earlier figure is kept in the history below. Every screen now reads the figures on file again.</p>
        <RecalculationNote recalculation={change.recalculation} borrowerId={data.borrower.id} subject={result.kind === 'corrected' ? 'the old figure' : 'this figure'} />
      </div>
    );
  }

  if (fact.kind === 'calculated') {
    return (
      <p className="text-body text-pretty text-ink-700" data-change-unavailable>
        Calculated by code; correct the figure it was calculated from. Each input of the calculation above opens its own source.
      </p>
    );
  }

  if (!CORRECTABLE.includes(fact.status)) {
    const later = data.history.find((entry) => entry.relation === 'later' && CORRECTABLE.includes(entry.status));
    return (
      <div className="space-y-2" data-change-unavailable>
        <p className="text-body text-pretty text-ink-700">This version is {fact.status}. Only the figure on file now can be corrected or rejected.</p>
        {later ? (
          <Button size="sm" onClick={() => source.open({ type: 'fact', id: later.id })}>
            Open the figure on file now
          </Button>
        ) : null}
      </div>
    );
  }

  const scale = data.page?.scale ?? fact.scale_as_reported ?? undefined;
  return (
    <div className="space-y-2.5">
      {mode === null ? (
        <>
          <p className="text-body text-pretty text-ink-700">If the figure is wrong, replace it or set it aside. Everything calculated from it is retired and run again from the figures on file.</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => (correct.reset(), setMode('correct'))}>
              Correct this figure
            </Button>
            <Button size="sm" onClick={() => (reject.reset(), setMode('reject'))}>
              Reject this figure
            </Button>
          </div>
        </>
      ) : null}
      {mode === 'correct' ? (
        <FigureForm
          title={`Correct ${fact.label}`}
          unit={fact.unit}
          initialValue={fact.value}
          scale={scale ?? undefined}
          submitLabel="Record the correction"
          pendingLabel="Recording"
          pending={correct.isPending}
          error={correct.error}
          reasonHint="Recorded in the ledger with your name. This figure is kept and marked superseded."
          onCancel={() => setMode(null)}
          onSubmit={({ value, reason }) => correct.mutate({ factId: fact.id, value, reason }, { onSuccess: (change) => (setMode(null), setResult({ kind: 'corrected', change })) })}
        />
      ) : null}
      {mode === 'reject' ? (
        <FigureForm
          title={`Reject ${fact.label}`}
          withValue={false}
          submitLabel="Record the rejection"
          pendingLabel="Recording"
          pending={reject.isPending}
          error={reject.error}
          reasonHint="Recorded in the ledger with your name. The line has no figure until one is keyed or read again."
          onCancel={() => setMode(null)}
          onSubmit={({ reason }) => reject.mutate({ factId: fact.id, reason }, { onSuccess: (change) => (setMode(null), setResult({ kind: 'rejected', change })) })}
        />
      ) : null}
    </div>
  );
}

import type { FactSummary } from '@/api/schema';
import type { Fact, ProvenanceKind, Unit } from '@/api/types';
import { Figure, formatFigure, NOT_MEASURED, provenance, ProvenanceGlyph, type FigureFormat } from '@/design';
import { toFact } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { useSource, type SourceRef } from './context';

interface Common extends FigureFormat {
  align?: 'inline' | 'column';
  weight?: 'regular' | 'medium' | 'semibold';
  tabIndex?: number;
  className?: string;
}

/** Shown where a figure would be when nothing was measured. Never a zero. */
export function Absent({ align, reason = 'Not measured' }: { align?: 'inline' | 'column'; reason?: string }) {
  return (
    <span className={cx('text-ink-500', align === 'column' && 'pr-[21px]')}>
      <span aria-hidden>{NOT_MEASURED}</span>
      <span className="sr-only">{reason}</span>
    </span>
  );
}

/** A stored fact: the figure, its glyph, and one click to the source drawer. */
export function FactFigure({ fact, absent, ...rest }: Common & { fact: FactSummary | null | undefined; absent?: string }) {
  const source = useSource();
  if (!fact) return <Absent align={rest.align} reason={absent} />;
  const selected = source.current?.type === 'fact' && source.current.id === fact.id;
  return <Figure fact={toFact(fact)} onSelect={() => source.open({ type: 'fact', id: fact.id })} selected={selected} {...rest} />;
}

export interface SourcedFigureProps extends Common {
  value: string | null | undefined;
  unit: Unit;
  kind: ProvenanceKind;
  /** What the figure is, for the accessible name. */
  label: string;
  context?: string;
  source: SourceRef;
}

/**
 * A figure that is not itself a stored fact (a line of a calculation, a field of a loan record,
 * a total). It still carries a glyph and opens the thing it came from.
 */
export function SourcedFigure({ value, unit, kind, label, context, source: ref, ...rest }: SourcedFigureProps) {
  const source = useSource();
  if (value === null || value === undefined || value === '') return <Absent align={rest.align} />;
  const fact: Fact = {
    id: `${ref.type}:${label}`,
    key: label,
    label,
    value,
    unit,
    periodLabel: context ?? '',
    status: 'verified',
    provenance:
      kind === 'system'
        ? { kind: 'system', connector: '', recordRef: '', asOf: '' }
        : kind === 'extracted'
          ? { kind: 'extracted', documentId: '', documentTitle: '', page: 0, quote: '', printed: '', labelText: '', scaleAsReported: 1, agentRunId: '' }
          : { kind: 'calculated', calcId: '', formulaKey: '', formulaVersion: '', expression: '', inputs: [] },
  };
  return <Figure fact={fact} onSelect={() => source.open(ref)} {...rest} />;
}

/**
 * A figure shown inside its own source (an intermediate line of the calculation on screen).
 * It keeps the glyph; the inputs it comes from are listed with it, each one a link.
 */
export function StaticFigure({ value, unit, kind, weight = 'regular', align, ...format }: Common & { value: string; unit: Unit; kind: ProvenanceKind }) {
  const { text, negative } = formatFigure(value, unit, format);
  const weights = { regular: 'font-regular', medium: 'font-medium', semibold: 'font-semibold' };
  return (
    <span className={cx('inline-flex items-center gap-1 align-baseline text-ink', weights[weight])}>
      <span className="tnum whitespace-nowrap">
        {text}
        {align === 'column' && unit === 'usd' && !negative ? <span className="invisible">)</span> : null}
      </span>
      <ProvenanceGlyph kind={kind} labelled />
    </span>
  );
}

/** The four kinds of source, for a legend above a table of figures. */
export function ProvenanceLegend({ kinds = ['extracted', 'calculated', 'system', 'manual'] }: { kinds?: ProvenanceKind[] }) {
  return (
    <ul aria-label="Provenance glyphs" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-700">
      {kinds.map((kind) => (
        <li key={kind} className="inline-flex items-center gap-1.5">
          <ProvenanceGlyph kind={kind} />
          {provenance[kind].label}
        </li>
      ))}
    </ul>
  );
}

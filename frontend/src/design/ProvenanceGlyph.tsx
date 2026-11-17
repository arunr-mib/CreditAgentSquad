import { Database, FileText, Sigma, UserRound, type LucideIcon } from 'lucide-react';
import type { ProvenanceKind } from '@/api/types';
import { cx } from '@/lib/cx';

/** Provenance is a glyph beside the figure, never a colour. */
export const provenance: Record<ProvenanceKind, { icon: LucideIcon; label: string; phrase: string }> = {
  extracted: { icon: FileText, label: 'Document', phrase: 'Read from a document' },
  calculated: { icon: Sigma, label: 'Calculation', phrase: 'Calculated by code' },
  system: { icon: Database, label: 'System of record', phrase: 'From a system of record' },
  manual: { icon: UserRound, label: 'Person', phrase: 'Entered by a person' },
};

export interface ProvenanceGlyphProps {
  kind: ProvenanceKind;
  size?: number;
  className?: string;
  /** Give the glyph its own accessible name. Leave off when a parent control already names the source. */
  labelled?: boolean;
}

export function ProvenanceGlyph({ kind, size = 12, className, labelled }: ProvenanceGlyphProps) {
  const { icon: Icon, label } = provenance[kind];
  return (
    <Icon
      size={size}
      strokeWidth={1.75}
      className={cx('shrink-0 text-ink-500', className)}
      {...(labelled ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true })}
    />
  );
}

/**
 * Plain words for the identifiers the API returns, and the adapter from an API fact to the
 * design system's `Fact`. Nothing here invents data: an unknown identifier is shown in sentence case.
 */
import { mul } from '@/api/decimal';
import type { FactSummary } from '@/api/schema';
import type { CovenantOutcome, Fact, Provenance, Severity, StageId, StageStatus } from '@/api/types';
import { formatDate, type StatusTone } from '@/design';
import { outcomeWords, word } from '@/api/words';

export function humanize(id: string | null | undefined): string {
  if (!id) return '';
  const text = id.replace(/[_.]+/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/* ── Severity ─────────────────────────────────────────────────────────── */

/** One mark per level, the same on every screen: critical red, high amber, medium ink, low an outline. The words are
 * the server's (`word('severities', …)`). */
export const SEVERITY_TONE: Record<Severity, StatusTone> = { critical: 'breach', high: 'attention', medium: 'neutral', low: 'muted' };
export const severityLabel = (severity: string) => word('severities', severity);

/* ── Monitoring cycle ─────────────────────────────────────────────────── */

export const stageLabel = (stage: StageId | string) => word('stages', stage);
export const stageStatusLabel = (status: StageStatus | string) => word('stage_statuses', status);

/* ── Covenants ────────────────────────────────────────────────────────── */

/** How an outcome is shown (colour, emphasis, order) beside the server's words for it (label, explanation). */
const OUTCOME_LOOK: Record<CovenantOutcome, { tone: StatusTone; emphasis?: boolean; rank: number }> = {
  breach_reported_compliant: { tone: 'breach', emphasis: true, rank: 0 },
  breach: { tone: 'breach', emphasis: true, rank: 1 },
  cannot_test: { tone: 'attention', rank: 2 },
  compliant_variance: { tone: 'attention', rank: 3 },
  compliant: { tone: 'pass', rank: 4 },
};

export function outcomeOf(outcome: CovenantOutcome | string): { tone: StatusTone; label: string; emphasis?: boolean; rank: number; explanation: string } {
  const look = OUTCOME_LOOK[outcome as CovenantOutcome] ?? { tone: 'neutral' as StatusTone, rank: 9 };
  return { ...look, ...outcomeWords(outcome) };
}

/* ── People ───────────────────────────────────────────────────────────── */

export const roleLabel = (role: string | null | undefined) => (role ? word('roles', role) : '');

/* ── Periods and time ─────────────────────────────────────────────────── */

const QUARTER_BY_MONTH: Record<number, string> = { 3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4' };

/** "At 30 Sep 2026" for a balance; "9 months to 30 Sep 2026" for a year-to-date flow. */
export function periodLabel(periodEnd: string, months: number): string {
  const date = formatDate(periodEnd);
  if (!months) return `At ${date}`;
  return months === 12 ? `Year to ${date}` : `${months} months to ${date}`;
}

/** "Q3 2026" for a calendar quarter end; otherwise the date. */
export function quarterLabel(periodEnd: string): string {
  const [year, month] = periodEnd.split('-').map(Number);
  const quarter = QUARTER_BY_MONTH[month ?? 0];
  return quarter ? `${quarter} ${year}` : formatDate(periodEnd);
}

/** "period ended 30 Sep 2026": true of a monthly and of a quarterly period, where the screen does not know which it is. */
export function periodEnded(periodEnd: string): string {
  return `period ended ${formatDate(periodEnd)}`;
}

/** A period in a list of choices: "Q3 2026 · 30 Sep 2026" for a calendar quarter end; the date once for any other month end. */
export function periodOption(periodEnd: string): string {
  const quarter = quarterLabel(periodEnd);
  const day = formatDate(periodEnd);
  return quarter === day ? day : `${quarter} · ${day}`;
}

/** "September 2026" for a monthly schedule; the quarter for any other. */
export function schedulePeriod(periodEnd: string, cadence: string | undefined): string {
  if (cadence !== 'monthly') return quarterLabel(periodEnd);
  const [year, month] = periodEnd.split('-').map(Number);
  return new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, 1)).toLocaleDateString('en-GB', { timeZone: 'UTC', month: 'long', year: 'numeric' });
}

/** "17 Nov 2026, 08:37" in UTC, as the ledger records it. */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '';
  const time = iso.slice(11, 16);
  return time ? `${formatDate(iso)}, ${time}` : formatDate(iso);
}

/* ── Facts ────────────────────────────────────────────────────────────── */

function provenanceOf(fact: FactSummary): Provenance {
  switch (fact.kind) {
    case 'extracted':
      return { kind: 'extracted', documentId: fact.document_id ?? '', documentTitle: '', page: fact.page ?? 0, quote: '', printed: '', labelText: '', scaleAsReported: 1, agentRunId: '' };
    case 'calculated':
      return { kind: 'calculated', calcId: fact.calc_run_id ?? '', formulaKey: '', formulaVersion: '', expression: '', inputs: [] };
    case 'system':
      return { kind: 'system', connector: '', recordRef: '', asOf: '' };
    case 'manual':
      return { kind: 'manual', enteredBy: '', enteredAt: '', reason: '' };
    case 'seeded':
      return { kind: 'seeded', note: 'Loaded from the synthetic book, not extracted.' };
  }
}

/**
 * An API fact as the design system's `Fact`. Percentages are stored as fractions (0.072) and shown
 * in points (7.2%): the decimal point is moved exactly, on the string, never through a float.
 */
export function toFact(fact: FactSummary): Fact {
  return {
    id: fact.id,
    key: fact.key,
    label: fact.label,
    value: fact.unit === 'pct' ? mul(fact.value, '100') : fact.value,
    unit: fact.unit,
    periodLabel: periodLabel(fact.period_end, fact.months),
    status: fact.status,
    provenance: provenanceOf(fact),
  };
}

/* ── Ledger ───────────────────────────────────────────────────────────── */


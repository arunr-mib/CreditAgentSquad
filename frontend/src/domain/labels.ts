/**
 * Plain words for the identifiers the API returns, and the adapter from an API fact to the
 * design system's `Fact`. Nothing here invents data: an unknown identifier is shown in sentence case.
 */
import { mul } from '@/api/decimal';
import type { FactSummary } from '@/api/schema';
import type { CovenantOutcome, Fact, Provenance, Severity, StageId, StageStatus } from '@/api/types';
import { formatDate, type StatusTone } from '@/design';

export function humanize(id: string | null | undefined): string {
  if (!id) return '';
  const text = id.replace(/[_.]+/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Abbreviations of legal forms, written the way they are written in an agreement. */
const LEGAL_ABBREVIATIONS: Record<string, string> = { llc: 'LLC', lp: 'LP', llp: 'LLP', lllp: 'LLLP', pllc: 'PLLC', pc: 'PC', plc: 'PLC', inc: 'Inc.', corp: 'Corp.', co: 'Co.', ltd: 'Ltd.' };

/** A borrower's legal form as stored ("llc", "s_corporation") in words ("LLC", "S corporation"). */
export function legalFormLabel(form: string | null | undefined): string {
  if (!form) return '';
  const words = form.replace(/[_.-]+/g, ' ').trim().split(/\s+/);
  return words
    .map((word, index) => {
      const known = LEGAL_ABBREVIATIONS[word.toLowerCase()];
      if (known) return known;
      if (word.length === 1) return word.toUpperCase();
      return index === 0 ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase() : word.toLowerCase();
    })
    .join(' ');
}

/* ── Severity ─────────────────────────────────────────────────────────── */

export const SEVERITY_LABEL: Record<Severity, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
export const SEVERITY_RANK: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };
/** One mark per level, the same on every screen: critical red, high amber, medium ink, low an outline. */
export const SEVERITY_TONE: Record<Severity, StatusTone> = { critical: 'breach', high: 'attention', medium: 'neutral', low: 'muted' };

/* ── Monitoring cycle ─────────────────────────────────────────────────── */

export const STAGE_ORDER: StageId[] = [
  'awaiting_package',
  'intake',
  'spreading',
  'covenant_testing',
  'borrowing_base',
  'signals',
  'review_prep',
  'in_review',
  'actions_open',
  'closed',
];

export const STAGE_LABEL: Record<StageId, string> = {
  awaiting_package: 'Awaiting package',
  intake: 'Intake',
  spreading: 'Spreading',
  covenant_testing: 'Covenant testing',
  borrowing_base: 'Borrowing base',
  signals: 'Signals',
  review_prep: 'Review preparation',
  in_review: 'In review',
  actions_open: 'Actions open',
  closed: 'Closed',
};


export const STAGE_STATUS_LABEL: Record<StageStatus, string> = {
  pending: 'Not started',
  running: 'Running',
  needs_person: 'Needs a person',
  done: 'Done',
  skipped: 'Skipped',
  failed: 'Failed',
};

/* ── Covenants ────────────────────────────────────────────────────────── */

export const OUTCOME: Record<CovenantOutcome, { tone: StatusTone; label: string; emphasis?: boolean; rank: number; explanation: string }> = {
  breach_reported_compliant: {
    tone: 'breach',
    label: 'Breach, reported compliant',
    emphasis: true,
    rank: 0,
    explanation: 'The calculated value fails the test and the certificate claims compliance.',
  },
  breach: { tone: 'breach', label: 'Breach', emphasis: true, rank: 1, explanation: 'The calculated value fails the test.' },
  cannot_test: { tone: 'attention', label: 'Cannot test', rank: 2, explanation: 'An input is missing or no terms are in force.' },
  compliant_variance: {
    tone: 'attention',
    label: 'Compliant, variance',
    rank: 3,
    explanation: 'The calculated value passes but differs from the certificate beyond tolerance. The variance is logged; no decision is needed.',
  },
  compliant: { tone: 'pass', label: 'Compliant', rank: 4, explanation: 'The calculated value passes and agrees with the certificate. Nothing is needed from a person.' },
};

/* ── Work items ───────────────────────────────────────────────────────── */


/* ── People ───────────────────────────────────────────────────────────── */

export const ROLE_LABEL: Record<string, string> = {
  analyst: 'Credit analyst',
  portfolio_manager: 'Portfolio manager',
  credit_officer: 'Credit officer',
  credit_admin: 'Credit administration',
  credit_review: 'Credit review',
  admin: 'Administrator',
};

export const roleLabel = (role: string | null | undefined) => (role ? (ROLE_LABEL[role] ?? humanize(role)) : '');



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


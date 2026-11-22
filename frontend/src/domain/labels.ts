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

export const stageLabel = (stage: string | null | undefined) => (stage ? (STAGE_LABEL[stage as StageId] ?? humanize(stage)) : 'No stage');

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

export type ItemGroup = 'covenant' | 'spreading' | 'terms' | 'borrowing_base' | 'intake' | 'signals' | 'review';

export const ITEM_GROUP_LABEL: Record<ItemGroup, string> = {
  covenant: 'Covenant',
  spreading: 'Spreading',
  terms: 'Terms',
  borrowing_base: 'Borrowing base',
  intake: 'Intake',
  signals: 'Signals',
  review: 'Review',
};

const GROUP_BY_PREFIX: Record<string, ItemGroup> = {
  covenant: 'covenant',
  spread: 'spreading',
  document: 'spreading',
  terms: 'terms',
  bb: 'borrowing_base',
  intake: 'intake',
  signal: 'signals',
  review: 'review',
  package: 'review',
};

export const itemGroup = (itemType: string): ItemGroup => GROUP_BY_PREFIX[itemType.split('.')[0] ?? ''] ?? 'review';

const ITEM_TYPE_LABEL: Record<string, string> = {
  'intake.missing_document': 'Missing document',
  'intake.unclassified': 'Unclassified document',
  'spread.value_unverified': 'Value not verified',
  'spread.does_not_foot': 'Section does not foot',
  'spread.restatement': 'Restated prior period',
  'spread.image_only': 'Image-only page',
  'document.spreadsheet_unreadable': 'Spreadsheet not readable',
  'terms.approval_needed': 'Terms awaiting approval',
  'terms.unapproved_amendment': 'Amendment not approved into terms',
  'covenant.breach': 'Covenant breach',
  'reading.review': 'Reading to confirm',
  'covenant.reported_mismatch': 'Covenant breach, certificate reports compliant',
  'covenant.reported_breach_unconfirmed': 'Certificate reports a breach the calculation does not show',
  'fact.correction_changed_outcome': 'Corrected figure changed a covenant outcome',
  'covenant.cannot_test': 'Covenant cannot be tested',
  'bb.over_advance': 'Over-advance',
  'bb.certificate_mismatch': 'Borrowing base certificate mismatch',
  'signal.high': 'High-severity signal',
  'review.commentary_approval': 'Commentary awaiting approval',
  'package.release': 'Package release',
};

export const itemTypeLabel = (itemType: string) => ITEM_TYPE_LABEL[itemType] ?? humanize(itemType);
export const isBreachItem = (itemType: string) => itemType === 'covenant.breach' || itemType === 'covenant.reported_mismatch';

/** What each allowed decision means, in the words a person would use. `reason` marks decisions that should carry one. */
const DECISION: Record<string, { label: string; hint: string; reason?: boolean }> = {
  waiver_requested: { label: 'Waiver requested', hint: 'The borrower has asked for a waiver; the breach stands until one is granted.', reason: true },
  reservation_of_rights: { label: 'Reserve rights', hint: 'Send a reservation of rights letter while the breach is worked through.', reason: true },
  escalate_to_committee: { label: 'Escalate to committee', hint: 'Take the breach to credit committee.', reason: true },
  ask_for_new_timeline: { label: 'Ask for a new timeline', hint: 'Ask the client for a new expected close. Squad drafts the email; a person sends it.' },
  note_and_watch: { label: 'Note and keep watching', hint: 'Noted; Squad keeps watching for the close.' },
  reserve_rights: { label: 'Reserve the bank’s rights', hint: 'The bank reserves its rights while the round is late.', reason: true },
  escalate: { label: 'Escalate', hint: 'Take it to the credit officer or committee.', reason: true },
  not_a_breach: { label: 'Not a breach', hint: 'The calculation is wrong or the terms differ. Say why.', reason: true },
  paydown_required: { label: 'Require a paydown', hint: 'The borrower must repay down to the borrowing base.', reason: true },
  temporary_overadvance_approved: { label: 'Approve a temporary over-advance', hint: 'Allow the excess for a stated period.', reason: true },
  bank_figures_stand: { label: 'The bank’s figures stand', hint: 'Use the recalculation; the certificate is wrong.' },
  borrower_to_resubmit: { label: 'Ask the borrower to resubmit', hint: 'Request a corrected certificate.' },
  certificate_correct: { label: 'The certificate is correct', hint: 'The recalculation is wrong. Say why.', reason: true },
  chaser_sent: { label: 'Chaser sent', hint: 'The reminder has gone to the borrower.' },
  extension_granted: { label: 'Extension granted', hint: 'The borrower has more time. Say until when.', reason: true },
  received_elsewhere: { label: 'Received elsewhere', hint: 'The document arrived outside the workspace.', reason: true },
  acknowledged: { label: 'Acknowledge', hint: 'Seen; no change to the risk rating.' },
  rating_review_requested: { label: 'Request a rating review', hint: 'The risk rating should be looked at again.', reason: true },
  add_to_watch_list: { label: 'Add to the watch list', hint: 'Monitor this borrower more closely.', reason: true },
  values_confirmed: { label: 'Values confirmed', hint: 'Every held figure is accepted as read, and the spread is finished from them.' },
  values_corrected: { label: 'Values corrected', hint: 'The figures have been corrected with a citation.', reason: true },
  accept_as_reported: { label: 'Accept as reported', hint: 'Use the statement as it stands. Say why.', reason: true },
  request_new_document: { label: 'Request a new document', hint: 'Ask the borrower for a complete, readable copy.' },
  key_by_hand: { label: 'Key by hand', hint: 'A person will enter the figures from the page.' },
  restated_update_prior: { label: 'Restated: update the prior period', hint: 'The borrower restated; supersede the earlier figures.', reason: true },
  keep_prior: { label: 'Keep the prior figures', hint: 'Leave last year’s confirmed spread as it is.', reason: true },
  ask_borrower: { label: 'Ask the borrower', hint: 'Find out why the comparative column changed.' },
  terms_update_requested: { label: 'Request a terms update', hint: 'Prepare a new terms version from the amendment for approval.' },
  amendment_not_applicable: { label: 'Amendment does not apply', hint: 'The amendment does not change the tested terms. Say why.', reason: true },
  terms_approved: { label: 'Approve the terms', hint: 'The proposed terms govern from their effective date.' },
  not_applicable: { label: 'Not applicable', hint: 'Say why this does not apply.', reason: true },
  approve: { label: 'Approve', hint: 'The commentary is approved as written.' },
  return_for_rework: { label: 'Return for rework', hint: 'Send it back with what needs to change.', reason: true },
  reject: { label: 'Reject', hint: 'Say why.', reason: true },
};

export const decisionLabel = (id: string | null | undefined) => (id ? (DECISION[id]?.label ?? humanize(id)) : '');
export const decisionHint = (id: string) => DECISION[id]?.hint ?? '';
export const decisionNeedsReason = (id: string) => DECISION[id]?.reason ?? false;

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

const PERMISSION_LABEL: Record<string, string> = {
  decide_work_item: 'decide work items',
  decide_breach: 'decide the response to a breach',
  confirm_spread: 'confirm a spread',
  prepare_terms: 'prepare terms',
  approve_terms: 'approve terms',
  upload_document: 'file documents',
  approve_commentary: 'approve commentary',
  edit_commentary: 'write commentary',
  manage_actions: 'manage actions',
  release_package: 'release a package',
  advance_clock: 'set the simulated date',
};

export const permissionLabel = (permission: string) => PERMISSION_LABEL[permission] ?? humanize(permission).toLowerCase();

/** Roles that hold each permission, for telling a person who can decide (mirrors backend/app/core/roles.py). */
export const ROLES_WITH: Record<string, string[]> = {
  decide_breach: ['credit_officer'],
  confirm_spread: ['analyst'],
  prepare_terms: ['analyst', 'credit_admin'],
  approve_terms: ['credit_officer', 'credit_admin'],
  upload_document: ['analyst', 'portfolio_manager', 'credit_admin'],
  decide_work_item: ['analyst', 'portfolio_manager', 'credit_officer', 'credit_admin'],
  approve_commentary: ['portfolio_manager', 'credit_officer'],
  edit_commentary: ['analyst', 'portfolio_manager'],
  release_package: ['portfolio_manager', 'credit_officer'],
  manage_actions: ['analyst', 'portfolio_manager', 'credit_officer', 'credit_admin'],
  advance_clock: ['admin'],
};

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

const ACTION_LABEL: Record<string, string> = {
  'auth.signed_in': 'Signed in',
  'auth.signed_out': 'Signed out',
  'user.created': 'User created',
  'clock.set': 'Simulated date set',
  'document.received': 'Document received',
  'fact.recorded': 'Fact recorded',
  'fact.confirmed': 'Fact confirmed',
  'fact.superseded': 'Fact superseded',
  'fact.rejected': 'Fact rejected',
  'cycle.opened': 'Monitoring cycle opened',
  'cycle.stage_changed': 'Cycle stage changed',
  'cycle.closed': 'Monitoring cycle closed',
  'covenant.tested': 'Covenant tested',
  'borrowing_base.reviewed': 'Borrowing base reviewed',
  'signal.fired': 'Signal fired',
  'work_item.raised': 'Work item raised',
  'work_item.decided': 'Decision recorded',
  'obligation.received': 'Reporting requirement met',
  'obligation.overdue': 'Reporting requirement overdue',
  'terms.approved': 'Terms approved',
  'terms.proposed': 'Terms proposed',
  'commentary.written': 'Commentary written',
  'review_sheet.approved': 'Review sheet approved',
  'review_meeting.created': 'Review meeting created',
  'review_meeting.phase_changed': 'Review meeting moved on',
  'action.raised': 'Action raised',
  'action.status_changed': 'Action status changed',
};

export const actionLabel = (action: string) => ACTION_LABEL[action] ?? humanize(action);

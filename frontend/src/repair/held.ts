/**
 * Reading a held spread: what the work item's evidence lists, what each held figure needs from a
 * person, and the words the panel says about it. Nothing here calculates a figure: values are
 * passed on exactly as the API returned them.
 */
import type { FactSummary, FootingProblem, HeldCell, SpreadContext, SpreadLineApi } from '@/api/schema';
import { humanize, periodLabel } from '@/domain/labels';

/* ── Reading the item's evidence ──────────────────────────────────────── */

export const str = (value: unknown): string | null => (typeof value === 'string' && value ? value : null);
const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value) && typeof value === 'object' && !Array.isArray(value);

function readsAs(value: unknown): HeldCell['reads_as'] {
  if (!isRecord(value)) return null;
  const key = str(value.key);
  const amount = str(value.value);
  return key && amount ? { key, value: amount } : null;
}

/** The figures a spread held for a person, as the item's evidence lists them. Anything malformed is left out. */
export function heldCells(evidence: Record<string, unknown>): HeldCell[] {
  if (!Array.isArray(evidence.cells)) return [];
  return evidence.cells.filter(isRecord).flatMap((cell) => {
    const key = str(cell.key);
    if (!key) return [];
    return [
      {
        key,
        page: typeof cell.page === 'number' ? cell.page : null,
        printed_figure: str(cell.printed_figure),
        printed_label: str(cell.printed_label),
        row_label: str(cell.row_label),
        reason: str(cell.reason) ?? 'held',
        detail: str(cell.detail),
        fact_id: str(cell.fact_id),
        reads_as: readsAs(cell.reads_as),
      },
    ];
  });
}

/** The footing checks that failed, as the item's evidence lists them. */
export function footingProblems(evidence: Record<string, unknown>): FootingProblem[] {
  if (!Array.isArray(evidence.checks)) return [];
  return evidence.checks.filter(isRecord).flatMap((check) => {
    const code = str(check.code);
    if (!code) return [];
    const detail = isRecord(check.detail) ? { actual: str(check.detail.actual) ?? undefined, expected: str(check.detail.expected) ?? undefined, difference: str(check.detail.difference) ?? undefined } : null;
    return [{ key: str(check.key), code, message: str(check.message) ?? '', detail }];
  });
}

/** The period and units the spread was read in, when the item carries them. */
export function spreadContext(evidence: Record<string, unknown>): SpreadContext | null {
  const spread = isRecord(evidence.spread) ? evidence.spread : null;
  const periodEnd = spread ? str(spread.period_end) : null;
  if (!spread || !periodEnd || typeof spread.months !== 'number') return null;
  return { document_id: str(spread.document_id) ?? str(evidence.document_id), period_end: periodEnd, months: spread.months, scale: typeof spread.scale === 'number' ? spread.scale : undefined };
}

/* ── Lines of the statement ───────────────────────────────────────────── */

const STATED = 'stated.';
const COMPARATIVE = '@comparative';
export const STATEMENT_LABEL: Record<string, string> = { is: 'Income statement', bs: 'Balance sheet', cf: 'Cash flow statement', sup: 'Supplemental' };

export interface LineDescription {
  /** The template line's key, without the printed-total prefix or the comparative suffix. */
  base: string;
  label: string;
  statement: string;
  /** "printed total" or "comparative column" when the held figure is not the line's own current figure. */
  qualifier: string | null;
  /** True when a person may enter this line: an input line of the template, for the period itself. */
  input: boolean;
  /** True for a line measured over the period (income and cash flow); false for a balance at the period end. */
  flow: boolean;
}

export function describeLine(key: string, lines: SpreadLineApi[]): LineDescription {
  const stated = key.startsWith(STATED);
  const comparative = key.endsWith(COMPARATIVE);
  const base = key.slice(stated ? STATED.length : 0, comparative ? key.length - COMPARATIVE.length : undefined);
  const line = lines.find((entry) => entry.key === base);
  const [prefix = '', ...rest] = base.split('.');
  return {
    base,
    label: line?.label ?? humanize(rest.join(' ') || base),
    statement: STATEMENT_LABEL[line?.statement ?? prefix] ?? humanize(prefix),
    qualifier: stated ? 'printed total' : comparative ? 'comparative column' : null,
    input: !stated && !comparative && (line ? !line.computed : true),
    flow: (line?.statement ?? prefix) !== 'bs',
  };
}

/** "at 30 Sep 2026" for a balance, "9 months to 30 Sep 2026" for a flow: the period a figure is for. */
export function periodPhrase(line: LineDescription, context: SpreadContext): string {
  const label = periodLabel(context.period_end, line.flow ? context.months : 0);
  return label.charAt(0).toLowerCase() + label.slice(1);
}

/** True while this line still needs a person: a held figure not yet cleared, or no figure at all. */
export function needsPerson(heldId: string | null, held: FactSummary | undefined, current: FactSummary | undefined): boolean {
  if (current) return false;
  if (!heldId) return true;
  return !held || held.status === 'proposed' || held.status === 'rejected';
}

/* ── Why a figure was held, in plain words ────────────────────────────── */

const HOLD_REASON: Record<string, string> = {
  mapping_doubt: 'The check on the line this figure was filed under did not pass.',
  label_mismatch: 'The row label the reader reported is not on the page.',
  not_found: 'The figure the reader reported is not on the page it cited.',
  column_unconfirmed: 'The figure is on the page, but its column could not be confirmed as the one for this period.',
  ambiguous: 'The figure appears more than once on the page, so its row could not be settled.',
  unparseable: 'The printed figure could not be read as a number.',
};
/** A code check's reason for holding a figure, without the figure's own particulars. */
export const holdReason = (reason: string) => HOLD_REASON[reason] ?? `${humanize(reason)}.`;

export interface WhyHeld {
  sentence: string;
  /** The check's own wording, shown beneath when the sentence does not already say everything it says. */
  detail: string | null;
}

/**
 * Why code held this figure. `target` is the line the row's printed label names, when the API
 * says it names another one. The sentence is built from the API's reason and the labels on screen.
 */
export function whyHeld(cell: HeldCell, line: LineDescription, target: LineDescription | null): WhyHeld {
  const row = cell.row_label ? `“${cell.row_label}”` : null;
  const stored = cell.fact_id ? '' : ' Nothing was stored.';
  const detail = cell.detail ?? '';
  if (cell.reason === 'mapping_doubt') {
    if (target && row) return { sentence: `The row is printed ${row}, which names ${target.label}, not ${line.label}, the line it was filed under.`, detail: null };
    if (row && /is not a known name for/.test(detail)) return { sentence: `The row is printed ${row}, which is not a name ${line.label} is known by.`, detail: null };
    if (/no row label could be read/.test(detail)) return { sentence: 'No row label could be read beside this figure, so the line it belongs to could not be checked.', detail: null };
    if (/same printed figure was already reported/.test(detail)) return { sentence: 'The same printed figure was already reported for another line.', detail: cell.detail };
    if (/does not name/.test(detail)) return { sentence: 'The page it was read from does not name the borrower; it may belong to another entity.', detail: null };
    if (/is negative as printed/.test(detail)) return { sentence: 'The figure is negative as printed, where only a positive amount is expected.', detail: null };
    return { sentence: holdReason(cell.reason), detail: cell.detail };
  }
  const plain = cell.reason === 'label_mismatch' || cell.reason === 'not_found' || cell.reason === 'unparseable';
  return { sentence: `${holdReason(cell.reason)}${stored}`, detail: plain ? null : cell.detail };
}

/* ── Footing checks ───────────────────────────────────────────────────── */

const CHECK_FINDING: Record<string, string> = {
  missing_input: 'No figure is on file for this line',
  total_not_read: 'The printed total was not read',
  absent_not_verified: 'Not shown to be absent from the statement',
  does_not_foot: 'The lines do not add to the printed total',
  does_not_balance: 'Assets do not equal liabilities and equity',
  does_not_tie: 'The cash flow statement does not tie to the income statement',
  cash_roll_mismatch: 'The change in cash does not match the balance sheet',
};
export const checkFinding = (code: string) => CHECK_FINDING[code] ?? humanize(code);
export const knownCheck = (code: string) => code in CHECK_FINDING;

/** What the two amounts of a failed comparison are. */
export const COMPARED: Record<string, [string, string]> = {
  does_not_foot: ['Lines add to', 'Printed total'],
  does_not_balance: ['Total assets', 'Total liabilities and equity'],
  does_not_tie: ['Cash flow statement', 'Income statement'],
  cash_roll_mismatch: ['Net change in cash', 'Change in the cash balance'],
};

/* ── What one click will do ───────────────────────────────────────────── */

/**
 * Two held figures look swapped when each row's printed label names the line the other was filed
 * under. Only pairs that two ordinary corrections can put right are returned: both figures were
 * stored, both lines are input lines for the period itself, and both rows are on the same page
 * (a correction cites the page of the figure it replaces). Each figure is in one pair at most.
 */
export function swappedPairs(cells: HeldCell[], lines: SpreadLineApi[]): Array<[number, number]> {
  const pairs: Array<[number, number]> = [];
  const taken = new Set<number>();
  const fits = (cell: HeldCell) => Boolean(cell.fact_id && cell.reads_as && cell.page !== null && describeLine(cell.key, lines).input);
  cells.forEach((first, i) => {
    if (taken.has(i) || !fits(first)) return;
    const j = cells.findIndex((second, index) => index > i && !taken.has(index) && fits(second) && first.reads_as?.key === second.key && second.reads_as?.key === first.key && first.page === second.page);
    if (j < 0) return;
    taken.add(i).add(j);
    pairs.push([i, j]);
  });
  return pairs;
}

/**
 * The one action offered first for a held figure:
 * - `file`: the label names another line that has nothing on file; store the figure there and set this reading aside;
 * - `reject`: the label names another line that already has a figure; set this reading aside;
 * - `keep`: accept the figure where it was filed, as read;
 * - `enter`: nothing is on file for the line; a person enters the figure;
 * - null: nothing is asked of a person here (cleared, covered by a pair's action, or it cannot be entered).
 */
export type Primary = 'file' | 'reject' | 'keep' | 'enter' | null;

export function primaryAction(state: {
  /** The held fact is still proposed: nobody has confirmed, replaced or rejected it. */
  heldOpen: boolean;
  /** A usable or confirmed figure is on file for the line. */
  onFile: boolean;
  /** The line named by the printed label, when the figure can be filed under it. */
  target: LineDescription | null;
  /** That line already has a figure for the period, held or in use. */
  targetOnFile: boolean;
  /** Both figures of a swapped pair are still held: the pair's own action covers this one. */
  inPair: boolean;
  /** The line can be entered by hand for the period. */
  canEnter: boolean;
}): Primary {
  if (state.heldOpen) {
    if (state.inPair) return null;
    if (state.target) return state.targetOnFile ? 'reject' : 'file';
    return 'keep';
  }
  if (!state.onFile && state.canEnter) return 'enter';
  return null;
}

/**
 * What code does once a figure changes, said before the click. While a statement has no totals
 * on file nothing rests on its figures yet: the decision on the item is what foots it.
 */
export function whatCodeWillDo(totalsOnFile: boolean): string {
  return totalsOnFile
    ? 'Results calculated from the old figure will be retired, totals refooted and this period’s covenants retested.'
    : 'This statement has no totals on file yet: totals will be footed and this period’s covenants tested once the decision below is recorded.';
}

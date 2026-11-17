import { isNegative, round, scaleDown } from '@/api/decimal';
import type { Unit } from '@/api/types';

export interface FigureFormat {
  /** Display scale for US dollar amounts. Tables state the scale in their header. */
  scale?: 1 | 1000 | 1000000;
  /** Decimal places. Defaults: usd 0, ratio 2, pct 1, days 0, count 0. */
  dp?: number;
  /** Show the unit mark ($, x, %, days). Tables that state the unit in the header turn it off. */
  unitMark?: boolean;
}

export interface FormattedFigure {
  /** The figure as shown, for example "(620)", "$250,000", "1.12x", "−6.7%". */
  text: string;
  negative: boolean;
}

const MINUS = '−';
export const NOT_MEASURED = '—';

function group(integer: string): string {
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function split(value: string): { negative: boolean; int: string; frac: string } {
  const negative = value.startsWith('-');
  const [int = '0', frac = ''] = value.replace(/^-/, '').split('.');
  return { negative, int, frac };
}

/**
 * Formats a stored decimal for display. Money uses accounting negatives in parentheses;
 * ratios and percentages use a true minus sign.
 */
export function formatFigure(value: string, unit: Unit, format: FigureFormat = {}): FormattedFigure {
  const { scale = 1, unitMark = true } = format;
  switch (unit) {
    case 'usd': {
      const scaled = scaleDown(value, scale, format.dp ?? 0);
      const { negative, int, frac } = split(scaled);
      const body = `${unitMark ? '$' : ''}${group(int)}${frac ? `.${frac}` : ''}`;
      return { text: negative ? `(${body})` : body, negative };
    }
    case 'ratio': {
      const { negative, int, frac } = split(round(value, format.dp ?? 2));
      return { text: `${negative ? MINUS : ''}${group(int)}.${frac}${unitMark ? 'x' : ''}`, negative };
    }
    case 'pct': {
      const dp = format.dp ?? 1;
      const { negative, int, frac } = split(round(value, dp));
      return { text: `${negative ? MINUS : ''}${group(int)}${dp > 0 ? `.${frac}` : ''}${unitMark ? '%' : ''}`, negative };
    }
    case 'days': {
      const { negative, int } = split(round(value, format.dp ?? 0));
      return { text: `${negative ? MINUS : ''}${group(int)}${unitMark ? ' days' : ''}`, negative };
    }
    case 'count': {
      const { negative, int } = split(round(value, 0));
      return { text: `${negative ? MINUS : ''}${group(int)}`, negative };
    }
  }
}

export function isNegativeValue(value: string): boolean {
  return isNegative(value);
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-11-12" → "12 Nov 2026". Dates are formatted without time-zone arithmetic. */
export function formatDate(iso: string, opts: { year?: boolean } = {}): string {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  const month = MONTHS[(m ?? 1) - 1];
  return `${d} ${month}${opts.year === false ? '' : ` ${y}`}`;
}

/** Whole days from `fromIso` to `toIso` (positive when `toIso` is later). */
export function daysBetween(fromIso: string, toIso: string): number {
  const toUtc = (iso: string) => {
    const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
    return Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1);
  };
  return Math.round((toUtc(toIso) - toUtc(fromIso)) / 86_400_000);
}

/** Due date relative to the simulated "as of" date. `text` is for a table cell ("Today", "3 days late", "17 Nov"); `sentence` stands alone ("Due today"). */
export function formatDue(dueIso: string, asOfIso: string): { text: string; sentence: string; overdue: boolean; today: boolean } {
  const delta = daysBetween(asOfIso, dueIso);
  const days = `${Math.abs(delta)} ${Math.abs(delta) === 1 ? 'day' : 'days'}`;
  if (delta < 0) return { text: `${days} late`, sentence: `Overdue by ${days}`, overdue: true, today: false };
  if (delta === 0) return { text: 'Today', sentence: 'Due today', overdue: false, today: true };
  if (delta === 1) return { text: 'Tomorrow', sentence: 'Due tomorrow', overdue: false, today: false };
  const date = formatDate(dueIso, { year: false });
  return { text: date, sentence: `Due ${date}`, overdue: false, today: false };
}

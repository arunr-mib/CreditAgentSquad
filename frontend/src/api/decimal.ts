/**
 * Exact decimal helpers on strings. No floats: values are scaled to BigInt.
 * Used by fixtures and by formatting. The backend calculation engine remains the authority.
 */

const SCALE = 6;
const ONE = 10n ** BigInt(SCALE);

function toScaled(value: string): bigint {
  const trimmed = value.trim();
  const negative = trimmed.startsWith('-');
  const [intPart = '0', fracPart = ''] = trimmed.replace(/^[-+]/, '').split('.');
  if (!/^\d+$/.test(intPart) || !/^\d*$/.test(fracPart)) throw new Error(`Not a decimal: "${value}"`);
  const frac = (fracPart + '0'.repeat(SCALE)).slice(0, SCALE);
  const scaled = BigInt(intPart) * ONE + BigInt(frac);
  return negative ? -scaled : scaled;
}

function fromScaled(scaled: bigint, dp: number): string {
  const negative = scaled < 0n;
  const abs = negative ? -scaled : scaled;
  const drop = 10n ** BigInt(SCALE - dp);
  // Round half-up on the magnitude.
  const rounded = (abs + drop / 2n) / drop;
  const digits = rounded.toString().padStart(dp + 1, '0');
  const intPart = dp === 0 ? digits : digits.slice(0, -dp);
  const fracPart = dp === 0 ? '' : `.${digits.slice(-dp)}`;
  const isZero = rounded === 0n;
  return `${negative && !isZero ? '-' : ''}${intPart}${fracPart}`;
}

export function add(...values: string[]): string {
  return fromScaled(
    values.reduce((sum, v) => sum + toScaled(v), 0n),
    SCALE,
  );
}

export function sub(a: string, ...rest: string[]): string {
  return fromScaled(
    rest.reduce((acc, v) => acc - toScaled(v), toScaled(a)),
    SCALE,
  );
}

export function mul(a: string, b: string): string {
  return fromScaled((toScaled(a) * toScaled(b)) / ONE, SCALE);
}

/** Division rounded half-up to `dp` places. A denominator of zero or less is an error. */
export function div(num: string, den: string, dp: number): string {
  const d = toScaled(den);
  if (d <= 0n) throw new Error('Denominator must be greater than zero');
  const n = toScaled(num);
  const negative = n < 0n;
  const abs = negative ? -n : n;
  const factor = 10n ** BigInt(dp);
  const q = (abs * factor * 2n + d) / (d * 2n);
  const digits = q.toString().padStart(dp + 1, '0');
  const text = dp === 0 ? digits : `${digits.slice(0, -dp)}.${digits.slice(-dp)}`;
  return `${negative && q !== 0n ? '-' : ''}${text}`;
}

export function min(a: string, b: string): string {
  return toScaled(a) <= toScaled(b) ? a : b;
}

export function compare(a: string, b: string): -1 | 0 | 1 {
  const x = toScaled(a);
  const y = toScaled(b);
  return x < y ? -1 : x > y ? 1 : 0;
}

export function isNegative(value: string): boolean {
  return toScaled(value) < 0n;
}

/** Rounds half-up to `dp` places. */
export function round(value: string, dp: number): string {
  return fromScaled(toScaled(value), dp);
}

/** Moves the decimal point left by the scale's power of ten, exactly. */
export function scaleDown(value: string, scale: 1 | 1000 | 1000000, dp: number): string {
  if (scale === 1) return round(value, dp);
  return div(value, String(scale), dp);
}

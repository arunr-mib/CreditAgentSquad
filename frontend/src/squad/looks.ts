// frontend/src/squad/looks.ts
/** The five looks. Source of truth for colour in the Squad experience; applied as --sq-* variables. */
export type LookId = 'night' | 'warm' | 'cool' | 'lavender' | 'sage';
export type TokenName =
  | 'ground' | 'surface' | 'sunk' | 'line' | 'ink' | 'ink2' | 'ink3' | 'onInk' | 'onEmber'
  | 'squad' | 'squadSoft' | 'squadLine' | 'ok' | 'warn' | 'bad' | 'ember' | 'paper' | 'paperInk';
export interface Look {
  id: LookId;
  label: string;
  dark: boolean;
  swatch: [string, string];
  vars: Record<TokenName, string>;
}

const LIGHT = { onInk: '#ffffff', onEmber: '#ffffff', squad: '#3d2a9e', squadSoft: '#f2efff', squadLine: '#ddd5ff', ok: '#1c6e42', warn: '#8f5a00', bad: '#a8261c', ember: '#c4421a', paper: '#fbfaf6', paperInk: '#2b2925' };

export const LOOKS: Record<LookId, Look> = {
  night: {
    id: 'night', label: 'Night', dark: true, swatch: ['#141318', '#8f7bf0'],
    vars: { ground: '#141318', surface: '#1d1c22', sunk: '#25242b', line: '#2f2e36', ink: '#f1eff5', ink2: '#bbb7c6', ink3: '#9a96a6', onInk: '#141318', onEmber: '#1c0c05',
      squad: '#cbbfff', squadSoft: '#262140', squadLine: '#3d3561', ok: '#7fd3a0', warn: '#f0c06a', bad: '#ff9b8f', ember: '#f2643a', paper: '#fbfaf6', paperInk: '#2b2925' },
  },
  warm: {
    id: 'warm', label: 'Warm paper', dark: false, swatch: ['#f5f3ee', '#2f2d28'],
    vars: { ...LIGHT, ground: '#f5f3ee', surface: '#ffffff', sunk: '#efebe3', line: '#e3ded3', ink: '#161513', ink2: '#4f4a42', ink3: '#6f695f' },
  },
  cool: {
    id: 'cool', label: 'Cool slate', dark: false, swatch: ['#f1f3f6', '#33557a'],
    vars: { ...LIGHT, ground: '#f1f3f6', surface: '#ffffff', sunk: '#e7ebf0', line: '#dce1e8', ink: '#13161b', ink2: '#49505b', ink3: '#5d6776' },
  },
  lavender: {
    id: 'lavender', label: 'Lavender mist', dark: false, swatch: ['#f4f2fb', '#4a35b8'],
    vars: { ...LIGHT, ground: '#f4f2fb', surface: '#ffffff', sunk: '#ebe7f7', line: '#e0dbf0', ink: '#1a1726', ink2: '#4d4862', ink3: '#625c79' },
  },
  sage: {
    id: 'sage', label: 'Sage', dark: false, swatch: ['#f0f3ee', '#3f6b4a'],
    vars: { ...LIGHT, ground: '#f0f3ee', surface: '#ffffff', sunk: '#e5eae1', line: '#d9e0d4', ink: '#151a14', ink2: '#4a5347', ink3: '#5c6656' },
  },
};

export const LOOK_IDS = Object.keys(LOOKS) as LookId[];

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * (channels[0] ?? 0) + 0.7152 * (channels[1] ?? 0) + 0.0722 * (channels[2] ?? 0);
}

/** WCAG contrast ratio of two six-digit hex colours. */
export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Owner decision 3: Warm paper for credit officers, Night for everyone else. */
export function defaultLookFor(role: string): LookId {
  return role === 'credit_officer' ? 'warm' : 'night';
}

const cssName = (token: string) => `--sq-${token.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;

export function applyLook(id: LookId, root: HTMLElement = document.documentElement): void {
  root.dataset.look = id;
  root.style.colorScheme = LOOKS[id].dark ? 'dark' : 'light';
  for (const [token, value] of Object.entries(LOOKS[id].vars)) root.style.setProperty(cssName(token), value);
}

/**
 * The words the server serves for every identifier a screen shows (`GET /api/v1/words/labels`, built in
 * `backend/app/squad/words.py`). The browser keeps no table of words: it loads them once, before the first screen, and
 * an identifier the tables lack reads as its own words in sentence case. Colour, order and emphasis are presentation
 * and stay in the browser.
 */
import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { request } from './client';

export interface WordTables {
  severities: Record<string, string>;
  stages: Record<string, string>;
  stage_statuses: Record<string, string>;
  roles: Record<string, string>;
  covenant_outcomes: Record<string, { label: string; explanation: string }>;
  funding_kinds: Record<string, string>;
  recommendations: Record<string, string>;
  document_reads: Record<string, string>;
  cadences: Record<string, string>;
  statements: Record<string, string>;
  hold_reasons: Record<string, string>;
  check_findings: Record<string, string>;
  check_compared: Record<string, [string, string]>;
  fact_statuses: Record<string, string>;
  verified_by_kind: Record<string, string>;
  units: Record<string, string>;
  case_history: Record<string, string>;
  case_statuses: Record<string, string>;
  decisions: Record<string, string>;
}

type FlatTable = { [K in keyof WordTables]: WordTables[K] extends Record<string, string> ? K : never }[keyof WordTables];

let loaded: WordTables | null = null;

/** Set the served tables (the gate below does it on load; the test setup does it with the served snapshot). */
export function setWords(tables: WordTables | null): void {
  loaded = tables;
}

/** The served tables, or null before they have loaded (or when they could not be). */
export function wordTables(): WordTables | null {
  return loaded;
}

/** An identifier as its own words: "needs_person" reads "Needs person". Used only where the server has no word. */
export function asWords(id: string | null | undefined): string {
  if (!id) return '';
  const text = id.replace(/[_.]+/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** The served word for `key` in `table`, or the identifier as words. */
export function word(table: FlatTable, key: string | null | undefined): string {
  if (!key) return '';
  return loaded?.[table]?.[key] ?? asWords(key);
}

/** True when the server has a word for `key` in `table`. */
export function hasWord(table: FlatTable, key: string): boolean {
  return Boolean(loaded?.[table] && key in loaded[table]);
}

export function outcomeWords(outcome: string | null | undefined): { label: string; explanation: string } {
  const known = outcome ? loaded?.covenant_outcomes?.[outcome] : undefined;
  return known ?? { label: asWords(outcome), explanation: '' };
}

export function comparedWords(code: string): [string, string] | undefined {
  return loaded?.check_compared?.[code];
}

/** Loads the tables once, before anything that shows a word is drawn. If they cannot be loaded, screens still open
 * and show each identifier as words. The words are not secret: the route is open before sign-in (the sign-in list
 * names each person's role). */
export function WordsGate({ children }: { children: ReactNode }) {
  const q = useQuery({
    queryKey: ['words', 'labels'],
    queryFn: async () => {
      const tables = await request<WordTables>('/words/labels');
      setWords(tables);
      return tables;
    },
    staleTime: Infinity,
  });
  if (q.isPending) return null;
  return <>{children}</>;
}

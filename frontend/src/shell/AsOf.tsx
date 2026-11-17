import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

interface AsOfValue {
  /** The simulated "as of" date, ISO. The demo clock is advanced by a person, never by the wall clock. */
  asOf: string;
  advanceDays: (days: number) => void;
  reset: () => void;
}

const START = '2026-11-12';
const AsOfContext = createContext<AsOfValue>({ asOf: START, advanceDays: () => {}, reset: () => {} });

function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, (d ?? 1) + days));
  return date.toISOString().slice(0, 10);
}

export function AsOfProvider({ children }: { children: ReactNode }) {
  const [asOf, setAsOf] = useState(START);
  const value = useMemo<AsOfValue>(() => ({ asOf, advanceDays: (days) => setAsOf((current) => addDays(current, days)), reset: () => setAsOf(START) }), [asOf]);
  return <AsOfContext.Provider value={value}>{children}</AsOfContext.Provider>;
}

export function useAsOf(): AsOfValue {
  return useContext(AsOfContext);
}

import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { ApiError, get } from '@/api/client';

interface Options {
  intervalMs?: number;
  enabled?: boolean;
}
const REFRESH = [['briefing'], ['thread'], ['trail'], ['borrowers'], ['case'], ['approvals'], ['measure'], ['funding'], ['my-portfolio'], ['lessons']] as const;

/**
 * No push channel exists (spec 6), so the browser asks the ledger for its newest sequence number (`/ledger/head`).
 * One request at a time, paused while the tab is hidden, and a failed poll changes nothing.
 */
export function useLedgerHeartbeat({ intervalMs = 4000, enabled = true }: Options = {}) {
  const qc = useQueryClient();
  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let inFlight = false;
    let failures = 0;
    let cursor: number | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    const { signal } = controller;
    const refresh = () => REFRESH.forEach((queryKey) => void qc.invalidateQueries({ queryKey: [...queryKey] }));

    async function tick() {
      if (stopped || inFlight) return;
      clearTimeout(timer);
      if (document.hidden) {
        schedule();
        return;
      }
      inFlight = true;
      try {
        // the ledger's newest sequence number only: no event's payload travels to every screen every few seconds
        const { seq } = await get<{ seq: number }>('/ledger/head', undefined, signal);
        if (stopped) return;
        if (cursor === null || seq > cursor) {
          // the first read refreshes anything that landed between the page's first read and this one
          cursor = seq;
          refresh();
        }
        failures = 0;
      } catch (error) {
        if (stopped) return;
        if (error instanceof ApiError && error.status === 401) {
          stopped = true; // the session ended; the auth provider sends the person to sign in
          return;
        }
        failures += 1; // keep the cursor and what is on screen; back off, then try again
      } finally {
        inFlight = false;
      }
      schedule();
    }
    function schedule() {
      if (stopped) return;
      timer = setTimeout(() => void tick(), intervalMs * 2 ** Math.min(failures, 4));
    }
    function onVisible() {
      if (!document.hidden) void tick();
    }
    document.addEventListener('visibilitychange', onVisible);
    void tick();
    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [qc, intervalMs, enabled]);
}

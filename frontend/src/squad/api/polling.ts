import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { ApiError, get } from '@/api/client';

interface Options {
  intervalMs?: number;
  enabled?: boolean;
}
const REFRESH = [['briefing'], ['thread'], ['trail'], ['borrowers'], ['case'], ['approvals']] as const;
const PAGE = 500; // the ledger route's cap

/**
 * No push channel exists (spec 6), so the browser asks the ledger for anything after its cursor.
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
        if (cursor === null) {
          const [newest] = await get<Array<{ seq: number }>>('/ledger', { limit: 1 }, signal);
          if (stopped) return;
          cursor = newest?.seq ?? 0;
          refresh(); // anything that landed between the page's first read and this one
        } else {
          // A full page means more may be waiting: keep paging from the new cursor, skipping nothing.
          for (;;) {
            const rows: Array<{ seq: number }> = await get('/ledger', { after_seq: cursor, limit: PAGE }, signal);
            if (stopped) return;
            if (rows.length > 0) {
              cursor = rows[rows.length - 1]!.seq;
              refresh();
            }
            if (rows.length < PAGE) break;
          }
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

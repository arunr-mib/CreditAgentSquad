import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { get } from '@/api/client';

interface Options {
  intervalMs?: number;
  enabled?: boolean;
}
const REFRESH = [['briefing'], ['thread'], ['trail'], ['borrowers']] as const;
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
    let cursor: number | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => REFRESH.forEach((queryKey) => void qc.invalidateQueries({ queryKey: [...queryKey] }));

    async function tick() {
      if (stopped) return;
      if (!document.hidden) {
        try {
          if (cursor === null) {
            const [newest] = await get<Array<{ seq: number }>>('/ledger', { limit: 1 });
            cursor = newest?.seq ?? 0;
            refresh(); // anything that landed between the page's first read and this one
          } else {
            // A full page means more may be waiting: keep paging from the new cursor, skipping nothing.
            for (;;) {
              const rows: Array<{ seq: number }> = await get('/ledger', { after_seq: cursor, limit: PAGE }, undefined);
              if (rows.length > 0) {
                cursor = rows[rows.length - 1]!.seq;
                refresh();
              }
              if (rows.length < PAGE || stopped) break;
            }
          }
        } catch {
          /* keep the cursor and what is on screen; try again next time */
        }
      }
      if (!stopped) timer = setTimeout(() => void tick(), intervalMs);
    }
    void tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [qc, intervalMs, enabled]);
}

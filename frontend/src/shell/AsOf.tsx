import { useClock } from '@/api/hooks';
import { useAuth } from '@/auth/context';

/**
 * The simulated "as of" date, from the server's clock. Due dates, overdue items and cycle stages
 * follow this date, never the wall clock. Null until the clock has been read.
 */
export function useAsOf(): { asOf: string | null; latestDocument: string | null; daysSinceLatestDocument: number | null } {
  const { status } = useAuth();
  const clock = useClock(status === 'signed-in');
  return {
    asOf: clock.data?.today ?? null,
    latestDocument: clock.data?.latest_document_received ?? null,
    daysSinceLatestDocument: clock.data?.days_since_latest_document ?? null,
  };
}

/** Past this many days without a document, the book is shown as possibly out of date. */
export const STALE_AFTER_DAYS = 45;

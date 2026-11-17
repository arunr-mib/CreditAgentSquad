import { useClock } from '@/api/hooks';
import { useAuth } from '@/auth/context';

/**
 * The simulated "as of" date, from the server's clock. Due dates, overdue items and cycle stages
 * follow this date, never the wall clock. Null until the clock has been read.
 */
export function useAsOf(): { asOf: string | null } {
  const { status } = useAuth();
  const clock = useClock(status === 'signed-in');
  return { asOf: clock.data?.today ?? null };
}

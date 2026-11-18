import { useQuery } from '@tanstack/react-query';
import { get } from '@/api/client';
import type { AgentRunRow } from '@/api/schema';

/** How often the rail asks whether an agent is at work. Never more often than every 20 seconds. */
export const RUNS_POLL_MS = 30_000;

/**
 * How many agent runs are in progress now, counted from the newest runs the API lists.
 * Undefined until the list has been read. The key starts with `agent-runs`, so anything
 * that refreshes the runs elsewhere refreshes this too.
 */
export function useRunsInProgress(): number | undefined {
  const runs = useQuery({
    queryKey: ['agent-runs', 'in-progress'],
    queryFn: () => get<AgentRunRow[]>('/agent-runs', { limit: 50 }),
    refetchInterval: RUNS_POLL_MS,
    staleTime: RUNS_POLL_MS,
  });
  return runs.data?.filter((run) => run.status === 'running').length;
}

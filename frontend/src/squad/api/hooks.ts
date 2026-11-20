// frontend/src/squad/api/hooks.ts
import { useQuery } from '@tanstack/react-query';
import { get } from '@/api/client';
import type { Briefing, Thread, Trail } from './types';

export const useBriefing = () => useQuery({ queryKey: ['briefing'], queryFn: () => get<Briefing>('/me/briefing') });
export const useThread = (borrowerId?: string) =>
  useQuery({ queryKey: ['thread', borrowerId], queryFn: () => get<Thread>(`/threads/${borrowerId}`), enabled: Boolean(borrowerId) });
export const useTrail = (workItemId: string, enabled: boolean) =>
  useQuery({ queryKey: ['trail', workItemId], queryFn: () => get<Trail>(`/cases/${workItemId}/trail`), enabled });

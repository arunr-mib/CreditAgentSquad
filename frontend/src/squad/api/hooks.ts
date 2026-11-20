// frontend/src/squad/api/hooks.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { get, post } from '@/api/client';
import type { Briefing, Thread, Trail } from './types';

export const useBriefing = () => useQuery({ queryKey: ['briefing'], queryFn: () => get<Briefing>('/me/briefing') });
export const useThread = (borrowerId?: string) =>
  useQuery({ queryKey: ['thread', borrowerId], queryFn: () => get<Thread>(`/threads/${borrowerId}`), enabled: Boolean(borrowerId) });
export const useTrail = (workItemId: string, enabled: boolean) =>
  useQuery({ queryKey: ['trail', workItemId], queryFn: () => get<Trail>(`/cases/${workItemId}/trail`), enabled });

function useWrite<TIn, TOut>(path: (input: TIn) => string, body: (input: TIn) => unknown, also: string[] = []) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: TIn) => post<TOut>(path(input), body(input)),
    // Settle, not just succeed: a refused write (e.g. already sent by someone else) means the screen is stale.
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ['briefing'] });
      void qc.invalidateQueries({ queryKey: ['thread'] });
      also.forEach((key) => void qc.invalidateQueries({ queryKey: [key] }));
    },
  });
}

export interface AnswerInput { option_id: string; remember: boolean; note?: string }
export const useAnswer = (workItemId: string) =>
  useWrite<AnswerInput, { lesson_id: string | null }>(() => `/work-items/${workItemId}/answer`, (i) => i, ['trail']);

export const useAskCopilot = () =>
  useWrite<{ question: string; borrower_id: string; work_item_id?: string }, { status: string; answer: string }>(() => '/copilot/ask', (i) => ({ ...i, history: [] }));

// A sent draft is recorded, never emailed: the server says so with delivered: false.
interface DraftResult { draft_id: string; status: 'draft' | 'sent'; delivered?: false }
export const useCreateDraft = (borrowerId: string) =>
  useWrite<{ to: string; subject: string; body: string; kind?: string; work_item_id?: string }, DraftResult>(() => `/borrowers/${borrowerId}/drafts`, (i) => i);
export const useEditDraft = () =>
  useWrite<{ draft_id: string; subject?: string; body?: string }, DraftResult>((i) => `/drafts/${i.draft_id}/edit`, ({ subject, body }) => ({ subject, body }));
export const useSendDraft = () => useWrite<{ draft_id: string }, DraftResult>((i) => `/drafts/${i.draft_id}/send`, () => ({}));

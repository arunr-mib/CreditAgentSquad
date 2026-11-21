// frontend/src/squad/api/hooks.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { get, post } from '@/api/client';
import type { ApprovalRow, Briefing, CaseView, FundingEventRow, LessonRow, MeasureSeries, PortfolioSection, Thread, TrackRecordRow, Trail } from './types';

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

export const useCase = (id?: string) =>
  useQuery({ queryKey: ['case', id], queryFn: () => get<CaseView>(`/cases/${id}`), enabled: Boolean(id) });
export const useApprovals = () => useQuery({ queryKey: ['approvals'], queryFn: () => get<ApprovalRow[]>('/me/approvals') });
const CASE_KEYS = ['case', 'approvals', 'trail', 'work-item', 'borrowers'];
export const useDecideCase = (id: string) =>
  useWrite<{ decision: string; reason: string }, unknown>(() => `/work-items/${id}/decide`, (i) => i, CASE_KEYS);
export const useRouteCase = (id: string) =>
  useWrite<{ to: string; view: string }, CaseView>(() => `/work-items/${id}/route`, (i) => i, CASE_KEYS);
export const useReturnCase = (id: string) =>
  useWrite<{ reason: string }, CaseView>(() => `/work-items/${id}/return`, (i) => i, CASE_KEYS);
export const useAttachEvidence = (id: string) =>
  useWrite<{ document_id: string; note?: string }, CaseView>(() => `/work-items/${id}/attach`, (i) => i, CASE_KEYS);

export const useMeasure = (borrowerId?: string) =>
  useQuery({ queryKey: ['measure', borrowerId], queryFn: () => get<MeasureSeries>(`/borrowers/${borrowerId}/measure`), enabled: Boolean(borrowerId) });
export const useDocumentTypeWords = () =>
  useQuery({ queryKey: ['words', 'document-types'], queryFn: () => get<{ types: Record<string, string>; unclassified: string; notes: Record<string, string> }>('/words/document-types'), staleTime: Infinity });
export const useFundingEvents = (borrowerId?: string) =>
  useQuery({ queryKey: ['funding', borrowerId], queryFn: () => get<FundingEventRow[]>(`/borrowers/${borrowerId}/funding-events`), enabled: Boolean(borrowerId) });

export const usePortfolio = () => useQuery({ queryKey: ['my-portfolio'], queryFn: () => get<{ as_of: string; sections: PortfolioSection[] }>('/me/portfolio') });
export const useTrackRecord = (borrowerId?: string) =>
  useQuery({ queryKey: ['track-record', borrowerId], queryFn: () => get<TrackRecordRow[]>(`/borrowers/${borrowerId}/track-record`), enabled: Boolean(borrowerId) });
export const useLessons = (borrowerId?: string) =>
  useQuery({ queryKey: ['lessons', borrowerId], queryFn: () => get<LessonRow[]>(`/borrowers/${borrowerId}/lessons`), enabled: Boolean(borrowerId) });

// frontend/src/squad/api/hooks.ts
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { get, post, type Query } from '@/api/client';
import type { AgentRunRow, AgentSpec, LedgerEvent } from '@/api/schema';
import type { GuardrailNote } from '@/api/types';
import type { ApprovalRow, Briefing, CaseView, FundingEventRow, LessonRow, MeasureSeries, NeedInput, PortfolioSection, Thread, TrackRecordRow, Trail } from './types';

export interface ClientRun {
  id: string; agent_label: string; task_label: string; status_label: string; created_at: string; error_words: string | null;
  guardrail_notes: Array<{ words: string }>;
}
export const useClientRuns = (borrowerId?: string) =>
  useQuery({ queryKey: ['client-runs', borrowerId], queryFn: () => get<ClientRun[]>(`/borrowers/${borrowerId}/runs`), enabled: Boolean(borrowerId) });
export const useRunDetail = (id: string | null) =>
  useQuery({ queryKey: ['run-detail', id], queryFn: () => get<{ steps: Array<{ id: string; n: number; words: string }> }>(`/runs/${id}`), enabled: Boolean(id) });
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

export interface CopilotReply {
  status: string;
  answer: string;
  answer_with_references: string;
  fact_ids: string[];
  citations: Array<{ document_id: string; page: number }>;
}
export const useAskCopilot = () =>
  useWrite<{ question: string; borrower_id: string | null; work_item_id?: string }, CopilotReply>(() => '/copilot/ask', (i) => ({ ...i, history: [] }));

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
// A decision can change a review sheet, the queue and the ledger (what `invalidateAfterDecision` refetches for the cockpit).
const CASE_KEYS = ['case', 'approvals', 'trail', 'work-item', 'work-items', 'borrowers', 'borrower', 'review-sheet', 'review-sheets', 'ledger', 'cycles', 'portfolio', 'actions', 'signals'];
export const useDecideCase = (id: string) =>
  useWrite<{ decision: string; reason: string }, unknown>(() => `/work-items/${id}/decide`, (i) => i, CASE_KEYS);
export const useRouteCase = (id: string) =>
  useWrite<{ to: string; view: string }, CaseView>(() => `/work-items/${id}/route`, (i) => i, CASE_KEYS);
export const useReturnCase = (id: string) =>
  useWrite<{ reason: string; needs?: NeedInput[] }, CaseView>(() => `/work-items/${id}/return`, (i) => i, CASE_KEYS);
export const useAttachEvidence = (id: string) =>
  useWrite<{ document_id: string; note?: string }, CaseView>(() => `/work-items/${id}/attach`, (i) => i, CASE_KEYS);

export const useMeasure = (borrowerId?: string) =>
  useQuery({ queryKey: ['measure', borrowerId], queryFn: () => get<MeasureSeries>(`/borrowers/${borrowerId}/measure`), enabled: Boolean(borrowerId) });
export const useDocumentTypeWords = () =>
  useQuery({ queryKey: ['words', 'document-types'], queryFn: () => get<{ types: Record<string, string>; unclassified: string; notes: Record<string, string>; needable: string[] }>('/words/document-types'), staleTime: Infinity });
export const useSignalWordsTable = () =>
  useQuery({ queryKey: ['words', 'signals'], queryFn: () => get<{ rules: Record<string, string> }>('/words/signals'), staleTime: Infinity });
export const useFundingEvents = (borrowerId?: string) =>
  useQuery({ queryKey: ['funding', borrowerId], queryFn: () => get<FundingEventRow[]>(`/borrowers/${borrowerId}/funding-events`), enabled: Boolean(borrowerId) });

export const usePortfolio = () => useQuery({ queryKey: ['my-portfolio'], queryFn: () => get<{ as_of: string; owns_clients: boolean; sections: PortfolioSection[] }>('/me/portfolio') });
export const useTrackRecord = (borrowerId?: string) =>
  useQuery({ queryKey: ['track-record', borrowerId], queryFn: () => get<TrackRecordRow[]>(`/borrowers/${borrowerId}/track-record`), enabled: Boolean(borrowerId) });
export const useLessons = (borrowerId?: string) =>
  useQuery({ queryKey: ['lessons', borrowerId], queryFn: () => get<LessonRow[]>(`/borrowers/${borrowerId}/lessons`), enabled: Boolean(borrowerId) });

export interface EvaluationRow { key: string; label: string; value: string | null; unit: 'pct' | 'count' }
export interface Evaluation {
  source: 'database' | 'file'; id: string | null; suite: string | null; commit: string | null; borrowers: number | null;
  mode: string | null; standin: boolean; notice: string | null; gate_passed: boolean | null; created_at: string | null; rows: EvaluationRow[];
}
export const useEvaluation = () => useQuery({ queryKey: ['oversight-evaluation'], queryFn: () => get<Evaluation>('/oversight/evaluation'), retry: false });

// Runs, agents and ledger events in the server's words (`app/squad/oversight.py`, `app/squad/words.py`); the browser builds no names.
export type OversightRun = Omit<AgentRunRow, 'guardrail_notes'> & { agent_label: string; task_label: string; status_label: string; tool_calls: number; error: string | null; guardrail_notes: Array<GuardrailNote & { words: string }> };
export const RUNS_PAGE = 100;
export const useOversightRuns = (offset = 0) =>
  useQuery({ queryKey: ['oversight-runs', offset], queryFn: () => get<OversightRun[]>('/oversight/runs', { limit: RUNS_PAGE, offset }), placeholderData: keepPreviousData });
export type OversightAgent = AgentSpec & { label: string };
export const useOversightAgents = () => useQuery({ queryKey: ['oversight-agents'], queryFn: () => get<OversightAgent[]>('/oversight/agents') });
export type OversightEvent = LedgerEvent & { actor_label: string };
export interface OversightLedgerFilter { action?: string; before_seq?: number; hide_sign_ins: boolean; limit: number }
export const useOversightLedger = (filter: OversightLedgerFilter) =>
  useQuery({ queryKey: ['oversight-ledger', filter], queryFn: () => get<OversightEvent[]>('/oversight/ledger', filter as unknown as Query), placeholderData: keepPreviousData });
export const useLedgerActions = () =>
  useQuery({ queryKey: ['oversight-ledger-actions'], queryFn: () => get<Array<{ key: string; words: string }>>('/oversight/ledger-actions') });

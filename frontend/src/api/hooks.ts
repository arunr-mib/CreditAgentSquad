/**
 * One query per resource, on /api/v1 (see schema.ts for shapes). Screens never call fetch directly.
 * Query keys start with the resource name so a decision can invalidate what it changes.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { get, post, upload, type Query } from './client';
import type { StageId, StageStatus } from './types';
import type {
  ActionRow,
  AgentRunDetail,
  AgentRunRow,
  AgentSpec,
  BorrowerCovenants,
  BorrowerDetail,
  BorrowerOverview,
  BorrowerRow,
  BorrowingBaseReview,
  Box,
  Calculation,
  CalendarResponse,
  CycleRow,
  DocumentDetail,
  DocumentRow,
  FactChange,
  FactsById,
  FactSource,
  LedgerEvent,
  LedgerVerification,
  LoanTerms,
  Meeting,
  PageFigures,
  PortfolioSummary,
  ReviewSheetDetail,
  ReviewSheetRow,
  SignalRow,
  Spread,
  StoredFact,
  UserName,
  WorkItemDetail,
  WorkItemRow,
} from './schema';

const enabled = (value: unknown) => Boolean(value);

/* ── Portfolio and borrowers ──────────────────────────────────────────── */

export const usePortfolio = () => useQuery({ queryKey: ['portfolio'], queryFn: () => get<PortfolioSummary>('/ui/portfolio') });
export const useBorrowers = () => useQuery({ queryKey: ['borrowers'], queryFn: () => get<BorrowerRow[]>('/borrowers') });
export const useUsers = () => useQuery({ queryKey: ['users'], queryFn: () => get<UserName[]>('/ui/users'), staleTime: 10 * 60_000 });

/** Borrowers are addressed by their stable code in the address bar; the API uses row ids. */
export function useBorrowerByCode(code: string) {
  const query = useBorrowers();
  const borrower = query.data?.find((row) => row.code === code || row.id === code);
  return { ...query, borrower, notFound: Boolean(query.data) && !borrower };
}

export const useBorrower = (id?: string) =>
  useQuery({ queryKey: ['borrower', id], queryFn: () => get<BorrowerDetail>(`/borrowers/${id}`), enabled: enabled(id) });
export const useBorrowerOverview = (id?: string) =>
  useQuery({ queryKey: ['borrower', id, 'overview'], queryFn: () => get<BorrowerOverview>(`/ui/borrowers/${id}/overview`), enabled: enabled(id) });
export const useBorrowerTerms = (id?: string) =>
  useQuery({ queryKey: ['borrower', id, 'terms'], queryFn: () => get<LoanTerms[]>(`/ui/borrowers/${id}/terms`), enabled: enabled(id) });
export const useBorrowerCovenants = (id?: string) =>
  useQuery({ queryKey: ['borrower', id, 'covenants'], queryFn: () => get<BorrowerCovenants>(`/ui/borrowers/${id}/covenants`), enabled: enabled(id) });
export const useBorrowingBase = (id?: string) =>
  useQuery({
    queryKey: ['borrower', id, 'borrowing-base'],
    queryFn: () => get<BorrowingBaseReview[]>(`/ui/borrowers/${id}/borrowing-base`),
    enabled: enabled(id),
  });
export const useSpread = (id?: string) =>
  useQuery({ queryKey: ['borrower', id, 'spread'], queryFn: () => get<Spread>(`/borrowers/${id}/spread`), enabled: enabled(id) });
export const useTimeline = (id?: string, includeRoutine = false) =>
  useQuery({
    queryKey: ['borrower', id, 'timeline', includeRoutine],
    queryFn: () => get<LedgerEvent[]>(`/ui/borrowers/${id}/timeline`, { include_routine: includeRoutine, limit: 400 }),
    enabled: enabled(id),
  });

/* ── Documents ────────────────────────────────────────────────────────── */

export const useDocuments = (borrowerId?: string) =>
  useQuery({
    queryKey: ['borrower', borrowerId, 'documents'],
    queryFn: () => get<DocumentRow[]>(`/borrowers/${borrowerId}/documents`),
    enabled: enabled(borrowerId),
  });
/** Files a PDF for the borrower. The route takes the file and an optional title; nothing else. */
export function useUploadDocument(borrowerId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ file, title }: { file: File; title: string }) => {
      const form = new FormData();
      form.append('file', file);
      if (title.trim()) form.append('title', title.trim());
      return upload<DocumentRow>(`/borrowers/${borrowerId}/documents`, form);
    },
    onSuccess: () => {
      for (const key of ['borrower', 'ledger', 'portfolio']) void client.invalidateQueries({ queryKey: [key] });
    },
  });
}
export const useDocument = (id?: string | null) =>
  useQuery({ queryKey: ['document', id], queryFn: () => get<DocumentDetail>(`/documents/${id}`), enabled: enabled(id), staleTime: 10 * 60_000 });
export const usePageFigures = (documentId?: string | null, page?: number | null) =>
  useQuery({
    queryKey: ['document', documentId, 'figures', page],
    queryFn: () => get<PageFigures>(`/ui/documents/${documentId}/pages/${page}/figures`),
    enabled: enabled(documentId) && enabled(page),
    staleTime: 10 * 60_000,
  });
export const useQuoteLocation = (documentId?: string | null, page?: number | null, quote?: string | null) =>
  useQuery({
    queryKey: ['document', documentId, 'locate', page, quote],
    queryFn: () =>
      get<{ found: boolean; boxes: Box[]; width: number; height: number }>(`/ui/documents/${documentId}/pages/${page}/locate`, { quote: quote ?? '' }),
    enabled: enabled(documentId) && enabled(page) && enabled(quote),
    staleTime: 10 * 60_000,
  });

/* ── Facts and calculations ───────────────────────────────────────────── */

export const useFactSource = (id?: string | null) =>
  useQuery({ queryKey: ['fact-source', id], queryFn: () => get<FactSource>(`/ui/facts/${id}/source`), enabled: enabled(id) });
export const useCalculation = (id?: string | null) =>
  useQuery({ queryKey: ['calculation', id], queryFn: () => get<Calculation>(`/ui/calculations/${id}`), enabled: enabled(id) });

/** Facts by id, fetched in batches so the address stays short. Unknown ids are simply absent. */
export function useFactsById(ids: Array<string | null | undefined>) {
  const wanted = [...new Set(ids.filter((id): id is string => Boolean(id)))].sort();
  return useQuery({
    queryKey: ['facts', wanted],
    queryFn: async () => {
      const out: FactsById = {};
      for (let index = 0; index < wanted.length; index += 60) {
        Object.assign(out, await get<FactsById>('/ui/facts', { ids: wanted.slice(index, index + 60).join(',') }));
      }
      return out;
    },
    enabled: wanted.length > 0,
    placeholderData: keepPreviousData,
  });
}

/**
 * Confirming, correcting, rejecting or keying a figure changes what every screen shows: the
 * figure itself, everything calculated from it, the queue and the ledger. Everything is read again.
 */
function useFigureMutation<TBody, TOut>(send: (body: TBody) => Promise<TOut>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: send, onSuccess: () => void client.invalidateQueries() });
}

export const useConfirmFact = () => useFigureMutation((factId: string) => post<StoredFact>(`/facts/${factId}/confirm`));
export const useCorrectFact = () =>
  useFigureMutation(({ factId, value, reason }: { factId: string; value: string; reason: string }) =>
    post<FactChange>(`/facts/${factId}/correct`, { value, reason }),
  );
export const useRejectFact = () =>
  useFigureMutation(({ factId, reason }: { factId: string; reason: string }) => post<FactChange>(`/facts/${factId}/reject`, { reason }));
export const useEnterFact = () =>
  useFigureMutation(({ borrowerId, ...body }: { borrowerId: string; key: string; period_end: string; months: number; value: string; reason: string }) =>
    post<FactChange>(`/borrowers/${borrowerId}/facts`, body),
  );

/* ── Work ─────────────────────────────────────────────────────────────── */

export const useWorkItems = (query: { status?: string; borrower_id?: string } = {}) =>
  useQuery({ queryKey: ['work-items', query], queryFn: () => get<WorkItemRow[]>('/work-items', query as Query) });
export const useWorkItem = (id?: string | null) =>
  useQuery({ queryKey: ['work-item', id], queryFn: () => get<WorkItemDetail>(`/work-items/${id}`), enabled: enabled(id) });

/** Everything a recorded decision can change: the queue, cycle stages, counts, the ledger. */
export function invalidateAfterDecision(client: QueryClient) {
  for (const key of [
    'work-items',
    'work-item',
    'portfolio',
    'borrowers',
    'borrower',
    'cycles',
    'ledger',
    'review-sheets',
    'review-sheet',
    'actions',
    'signals',
  ]) {
    void client.invalidateQueries({ queryKey: [key] });
  }
}

export function useDecide(itemId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { decision: string; reason: string }) => post<WorkItemDetail>(`/work-items/${itemId}/decide`, body),
    onSuccess: () => invalidateAfterDecision(client),
  });
}

export interface RunCycleResult {
  ran: Array<{ stage: StageId; result: StageStatus | null; error: string | null }>;
  cycle_status: string;
  stage: StageId;
  stage_status: StageStatus | null;
  open_blocking_items: number;
}

/** Run the cycle's next stage now, in the request. Everything on screen may change afterwards. */
export function useRunCycle(cycleId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => post<RunCycleResult>(`/cycles/${cycleId}/run`, {}),
    onSettled: () => void client.invalidateQueries(),
  });
}

export const useAgentsStatus = () =>
  useQuery({
    queryKey: ['agents-status'],
    queryFn: () => get<{ model_connected: boolean; mode: string; model: string; reason: string }>('/agents/status'),
    staleTime: 60_000,
  });

export const useCycles = (query: { period_end?: string; borrower_id?: string } = {}, options: { enabled?: boolean } = {}) =>
  useQuery({
    queryKey: ['cycles', query],
    queryFn: () => get<Array<CycleRow & { borrower_name: string | null }>>('/cycles', query as Query),
    enabled: options.enabled ?? true,
  });
export const useCalendar = () => useQuery({ queryKey: ['calendar'], queryFn: () => get<CalendarResponse>('/calendar') });
export const useSignals = (query: { status?: string; borrower_id?: string } = {}) =>
  useQuery({ queryKey: ['signals', query], queryFn: () => get<SignalRow[]>('/signals', query as Query) });

/* ── Agents ───────────────────────────────────────────────────────────── */

export const useAgentRuns = (query: { borrower_id?: string } = {}) =>
  useQuery({ queryKey: ['agent-runs', query], queryFn: () => get<AgentRunRow[]>('/agent-runs', { ...query, limit: 200 }) });
export const useAgentRun = (id?: string | null) =>
  useQuery({ queryKey: ['agent-run', id], queryFn: () => get<AgentRunDetail>(`/agent-runs/${id}`), enabled: enabled(id) });
export const useAgents = () => useQuery({ queryKey: ['agents'], queryFn: () => get<AgentSpec[]>('/agents') });

/* ── Governance ───────────────────────────────────────────────────────── */

export interface LedgerFilter {
  action?: string;
  entity_type?: string;
  entity_id?: string;
  before_seq?: number;
  limit?: number;
}
export const useLedger = (filter: LedgerFilter) =>
  useQuery({ queryKey: ['ledger', filter], queryFn: () => get<LedgerEvent[]>('/ledger', filter as Query), placeholderData: keepPreviousData });
export const useLedgerVerification = (run: boolean) =>
  useQuery({ queryKey: ['ledger-verify'], queryFn: () => get<LedgerVerification>('/ledger/verify'), enabled: run, staleTime: 0, gcTime: 0 });
export const useClock = (signedIn: boolean) =>
  useQuery({
    queryKey: ['clock'],
    queryFn: () => get<{ today: string; latest_document_received?: string | null; days_since_latest_document?: number | null }>('/clock'),
    enabled: signedIn,
    staleTime: 5 * 60_000,
  });

export function useSetClock() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (today: string) => post<{ today: string; obligations_now_overdue: number }>('/clock', { today }),
    onSuccess: () => void client.invalidateQueries(),
  });
}

/* ── Reviews ──────────────────────────────────────────────────────────── */

export const useReviewSheets = (query: { borrower_id?: string; period_end?: string } = {}) =>
  useQuery({ queryKey: ['review-sheets', query], queryFn: () => get<ReviewSheetRow[]>('/review-sheets', query as Query) });
export const useReviewSheet = (id?: string | null) =>
  useQuery({ queryKey: ['review-sheet', id], queryFn: () => get<ReviewSheetDetail>(`/review-sheets/${id}`), enabled: enabled(id) });
export const useMeetings = () => useQuery({ queryKey: ['review-meetings'], queryFn: () => get<Meeting[]>('/review-meetings') });
export const useActions = (query: { status?: string; borrower_id?: string } = {}) =>
  useQuery({ queryKey: ['actions', query], queryFn: () => get<ActionRow[]>('/actions', query as Query) });

function useReviewMutation<TBody, TOut>(path: (body: TBody) => string, strip: (body: TBody) => unknown = (body) => body) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: TBody) => post<TOut>(path(body), strip(body)),
    onSuccess: () => {
      for (const key of ['review-meetings', 'review-sheets', 'review-sheet', 'actions', 'ledger', 'borrower'])
        void client.invalidateQueries({ queryKey: [key] });
    },
  });
}

export const useCreateMeeting = () => useReviewMutation<{ title: string; meeting_date: string; period_end: string }, Meeting>(() => '/review-meetings');
export const useSetMeetingPhase = () =>
  useReviewMutation<{ id: string; phase: Meeting['phase']; notes?: string }, Meeting>(
    (body) => `/review-meetings/${body.id}/phase`,
    ({ phase, notes }) => ({ phase, notes }),
  );
export const useCreateAction = () =>
  useReviewMutation<
    { borrower_id: string; title: string; detail?: string; owner_id?: string | null; due_date?: string | null; meeting_id?: string | null },
    ActionRow
  >(() => '/actions');
export const useSetActionStatus = () =>
  useReviewMutation<{ id: string; status: ActionRow['status']; note?: string }, ActionRow>(
    (body) => `/actions/${body.id}/status`,
    ({ status, note }) => ({ status, note: note ?? '' }),
  );
export const useWriteCommentary = () =>
  useReviewMutation<{ sheetId: string; section: string; body: string }, ReviewSheetDetail>(
    (body) => `/review-sheets/${body.sheetId}/commentary`,
    ({ section, body }) => ({ section, body }),
  );

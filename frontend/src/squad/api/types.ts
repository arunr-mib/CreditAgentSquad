import type { FactSummary } from '@/api/schema';
// Shapes of the real responses from backend/app/squad (briefing.py, threads.py, drafts.py, trail.py, track_record.py).
export interface BriefingItem {
  key: string;
  kind: 'breach' | 'overdue_report' | 'signal' | 'question' | 'review' | 'funding' | 'decided';
  borrower_id: string;
  borrower_code: string;
  borrower_name: string;
  title: string;
  state: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  needs_you: boolean;
  work_item_id: string | null;
}
export interface Briefing {
  as_of: string;
  needs_you: number;
  items: BriefingItem[];
  overnight: Array<{ agent_name: string; text: string; borrower_id: string; borrower_code: string; borrower_name: string; finished_at: string }>;
  open_clients: Array<{ borrower_id: string; code: string; name: string; open: number }>;
  approvals: { offered: boolean; waiting: number };
}
export interface AskOption { id: string; label: string; evidence: string }
interface MessageBase { id: string; ts: string }
export type ThreadMessage = MessageBase &
  (
    | { type: 'report'; agent_name: string; task: string; text: string; run_id: string }
    | { type: 'case'; work_item_id: string; item_type: string; title: string; question: string; severity: string; status: string; allowed_decisions: string[]; needs_you: boolean; state_words: string }
    | { type: 'ask'; work_item_id: string; title: string; question: string; options: AskOption[]; status: string; choice: string | null; chosen_by: string | null; needs_you: boolean; state_words: string; habits: Habit[] }
    | { type: 'document'; document_id: string; title: string; doc_type: string | null; doc_type_words: string; pages: number; period_end: string | null }
    | { type: 'arrivals'; title: string; period_end: string; documents: Array<MessageBase & { type: 'document'; document_id: string; title: string; doc_type: string | null; doc_type_words: string; pages: number; period_end: string | null }> }
    | { type: 'held'; document_id: string; title: string; reason: string }
    | { type: 'draft'; draft_id: string; borrower_id: string; to: string; subject: string; body: string; kind: string; status: 'draft' | 'sent'; created_by: string; created_at: string; edited_by: string | null; sent_by: string | null; sent_at: string | null; work_item_id: string | null }
    | { type: 'decision'; work_item_id: string; decision: string | null; decision_words?: string; reason: string; by: string; by_id: string }
    | { type: 'handoff'; work_item_id: string; assigned_to: string | null; assigned_to_id: string | null; by: string; view?: string | null }
    | { type: 'returned'; work_item_id: string; reason: string; by: string; to: string | null }
    | { type: 'attached'; work_item_id: string; document_id: string; title: string; note: string; by: string }
    | { type: 'qa'; question: string; answer: string; fact_ids: string[]; citations: Array<{ document_id: string; page: number }>; status: string; run_id: string; asked_by: string }
  );
export interface Thread {
  borrower: { id: string; code: string; name: string; template_id: string };
  head_seq: number;
  opening_id: string | null;
  messages: ThreadMessage[];
}
export interface TrailStep { n: number; who: string; role_line: string; text: string; check: string; run_id: string | null }
export interface TrailInput { name?: string; key?: string; fact_id?: string; value?: unknown }
export interface Trail {
  work_item_id: string;
  steps: TrailStep[];
  calculation: { id: string; formula_key: string; inputs: TrailInput[]; outputs: Record<string, unknown> } | null;
  checks: Array<{ layer: string | null; check: string | null; action: string | null; detail: string | null }>;
}
/** A draft as returned by the draft routes; sending records who sent it and delivers nothing. */
export type DraftMessage = Extract<ThreadMessage, { type: 'draft' }>;
export type Draft = Omit<DraftMessage, 'id' | 'ts' | 'type'>;
export type DraftSendResult = Draft & { delivered: false };
export interface TrackRecordRow {
  task: string;
  agent_name: string;
  right: number;
  corrected: number;
  unreviewed: number;
  checked: number;
  since: string;
  last_correction_at: string | null;
}
export interface CaseHistoryEntry { kind: 'routed' | 'returned' | 'evidence_attached'; seq: number; at: string; by: string; by_id: string; to: string | null; to_id: string | null; text: string; document_id: string | null }
export interface CaseDecisionOption { id: string; needs_reason: boolean; permitted: boolean }
export interface CaseView {
  work_item_id: string;
  borrower: { id: string; code: string; name: string };
  item_type: string;
  title: string;
  question: string;
  severity: string;
  status: string;
  due_date: string | null;
  decision: string | null;
  decision_words: string | null;
  decision_reason: string;
  decided_by: string | null;
  requires_second_person: boolean;
  with: string | null;
  state_words: string;
  needs_you: boolean;
  view: { text: string; by: string; at: string } | null;
  history: CaseHistoryEntry[];
  attached: Array<{ document_id: string; title: string; by: string; note: string }>;
  candidates: Array<{ document_id: string; title: string; doc_type: string | null; pages: number }>;
  decisions: CaseDecisionOption[];
  route_to: Array<{ id: string; name: string; title: string }>;
  may_route: boolean;
  may_return: boolean;
  may_attach: boolean;
}
export interface ApprovalRow {
  work_item_id: string;
  borrower_id: string;
  borrower_code: string;
  borrower_name: string;
  title: string;
  severity: string;
  due_date: string | null;
  view: string | null;
  routed_by: string | null;
  routed_at: string | null;
  returns: number;
}

export interface MeasurePoint { period_end: string; fact: FactSummary | null; note: string | null }
export interface MeasureSeries { kind: 'rml' | 'headroom'; label: string; points: MeasurePoint[] }
export interface FundingEventRow { id: string; kind: string; amount: string; expected_close: string; status: string; evidence_document_ids: string[] }

export interface PortfolioRow { borrower_id: string; code: string; name: string; analyst: string | null; mine: boolean; open: number; measure: MeasureSeries }
export interface PortfolioSection { template_id: 'vc-1' | 'ci-1'; title: string; measure_label: string; rows: PortfolioRow[] }
export interface Habit { id: string; text: string; by: string; at: string }
export interface LessonRow extends Habit { topic: string; tag: string | null; work_item_id: string | null }

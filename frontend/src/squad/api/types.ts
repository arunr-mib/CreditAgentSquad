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
}
export interface AskOption { id: string; label: string; evidence: string }
interface MessageBase { id: string; ts: string }
export type ThreadMessage = MessageBase &
  (
    | { type: 'report'; agent_name: string; task: string; text: string; run_id: string }
    | { type: 'case'; work_item_id: string; item_type: string; title: string; question: string; severity: string; status: string; allowed_decisions: string[] }
    | { type: 'ask'; work_item_id: string; title: string; question: string; options: AskOption[]; status: string; choice: string | null; chosen_by: string | null }
    | { type: 'document'; document_id: string; title: string; doc_type: string | null; pages: number; period_end: string | null }
    | { type: 'held'; document_id: string; title: string; reason: string }
    | { type: 'draft'; draft_id: string; borrower_id: string; to: string; subject: string; body: string; kind: string; status: 'draft' | 'sent'; created_by: string; created_at: string; edited_by: string | null; sent_by: string | null; sent_at: string | null; work_item_id: string | null }
    | { type: 'decision'; work_item_id: string; decision: string | null; reason: string; by: string; by_id: string }
    | { type: 'handoff'; work_item_id: string; assigned_to: string | null; assigned_to_id: string | null; by: string }
    | { type: 'qa'; question: string; answer: string; fact_ids: string[]; citations: Array<{ document_id: string; page: number }>; status: string; run_id: string; asked_by: string }
  );
export interface Thread {
  borrower: { id: string; code: string; name: string; template_id: string };
  head_seq: number;
  messages: ThreadMessage[];
}
export interface TrailStep { n: number; who: string; role_line: string; text: string; check: string; run_id: string | null }
export interface Trail {
  work_item_id: string;
  steps: TrailStep[];
  calculation: { id: string; formula_key: string; inputs: unknown[]; outputs: Record<string, unknown> } | null;
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

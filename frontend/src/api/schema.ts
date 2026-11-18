/**
 * Shapes returned by /api/v1 (backend/app/api/*.py), named as the server names them.
 * Decimals arrive as strings and stay strings; the workspace formats them and never does float arithmetic.
 * The schema says `facility`; the interface says "loan".
 */
import type { CovenantOutcome, GuardrailNote, Severity, StageId, StageStatus, Unit } from './types';

export interface ApiUser {
  id: string;
  email: string;
  name: string;
  title: string;
  role: string;
  permissions: string[];
}

export interface UserName {
  id: string;
  name: string;
  title: string;
  role: string;
}

export type FactKind = 'extracted' | 'calculated' | 'system' | 'manual' | 'seeded';
export type FactStatusApi = 'proposed' | 'verified' | 'confirmed' | 'rejected' | 'superseded';

/** A fact as the bulk endpoints return it: enough to show the figure, its glyph and its label. */
export interface FactSummary {
  id: string;
  key: string;
  label: string;
  value: string;
  unit: Unit;
  kind: FactKind;
  status: FactStatusApi;
  period_end: string;
  months: number;
  borrower_id: string;
  document_id: string | null;
  page: number | null;
  calc_run_id: string | null;
}

export type FactsById = Record<string, FactSummary>;

export interface BorrowerRow {
  id: string;
  code: string;
  name: string;
  industry: string;
  risk_rating: number | null;
  fiscal_year_end_month: number;
  relationship_manager: string | null;
  analyst: string | null;
  total_commitment: string | null;
  open_work_items: number;
  open_signals: number;
  latest_cycle: { id: string; period_end: string; stage: StageId; status: string } | null;
  covenant_status: CovenantOutcome | null;
  /**
   * The stored headroom fact with the lowest value among the covenant tests in force for the
   * latest period. Chosen by the API, never worked out here. Null when nothing has been tested.
   */
  tightest_headroom: FactSummary | null;
}

export interface Loan {
  id: string;
  borrower_id: string;
  code: string;
  name: string;
  facility_type: 'revolver' | 'term_loan' | string;
  commitment: string;
  has_borrowing_base: boolean;
  origination_date: string | null;
  maturity_date: string | null;
  profile: { interest_rate?: string; original_amount?: string };
}

export interface BorrowerDetail extends Omit<BorrowerRow, 'total_commitment' | 'open_work_items' | 'open_signals' | 'latest_cycle' | 'covenant_status' | 'tightest_headroom'> {
  profile: { city?: string; state?: string; auditor?: string; legal_form?: string; statement_scale?: number; chief_financial_officer?: string };
  facilities: Loan[];
}

export interface StageRow {
  id: string;
  stage: StageId;
  position: number;
  status: StageStatus;
  detail: Record<string, unknown>;
  open_work_items: number;
}

export interface CycleRow {
  id: string;
  borrower_id: string;
  period_end: string;
  months: number;
  cycle_type: string;
  stage: StageId;
  status: 'open' | 'closed';
  origin: string;
  due_date: string | null;
}

export interface BorrowerOverview {
  /** `availability` is there only for a borrower with a borrowing base review. */
  exposure: Partial<Record<'revolver_outstanding' | 'commitment' | 'term_loan_outstanding' | 'past_due_days' | 'availability', FactSummary>>;
  cycle: (CycleRow & { stages: StageRow[] }) | null;
  metrics: Record<string, FactSummary>;
  open_work_items: number;
  open_signals: number;
  documents: number;
}

export interface PortfolioSummary {
  as_of: string;
  borrowers: number;
  loans: number;
  period_end: string | null;
  exposure: { commitment: string; revolver_outstanding: string; term_loan_outstanding: string; outstanding: string };
  borrower_exposure: Record<string, BorrowerOverview['exposure']>;
  cycles: { open: number; by_stage: Array<{ stage: StageId; count: number }> };
  covenants: { tests: number; by_outcome: Array<{ outcome: CovenantOutcome; count: number }> };
  work_items: { open: number; by_type: Array<{ item_type: string; count: number }>; by_severity: Array<{ severity: Severity; count: number }> };
  signals: { open: number; by_severity: Array<{ severity: Severity; count: number }> };
  obligations: { overdue: number; due_within_7_days: number; received_in_last_30_days: number };
}

/* ── Work items ───────────────────────────────────────────────────────── */

export interface WorkItemRow {
  id: string;
  borrower_id: string;
  borrower_name: string | null;
  facility_id: string | null;
  cycle_id: string | null;
  stage: StageId | null;
  item_type: string;
  severity: Severity;
  title: string;
  question: string;
  allowed_decisions: string[];
  blocks_stage: boolean;
  requires_second_person: boolean;
  required_permission: string;
  prepared_by_id: string | null;
  /** The person the item is routed to, if any. */
  assigned_to?: string | null;
  due_date: string | null;
  status: 'open' | 'decided' | 'dismissed';
  decision: string | null;
  decision_reason: string | null;
  decided_by: string | null;
  decided_at: string | null;
  agent_run_id: string | null;
  created_at: string;
}

export interface ApiRecommendation {
  recommendation?: string;
  kind?: string;
  agent?: string;
  agent_name?: string;
  headline?: string;
  explanation?: string;
  body?: string;
  text?: string;
  run_id?: string;
  claims?: Array<{ text?: string; document_id?: string; page?: number; quote?: string }>;
  missing_evidence?: string[];
  [key: string]: unknown;
}

export interface WorkItemDetail extends WorkItemRow {
  evidence: Record<string, unknown>;
  recommendation: ApiRecommendation | null;
  guardrail_notes: GuardrailNote[];
}

/* ── Documents ────────────────────────────────────────────────────────── */

export interface DocumentRow {
  id: string;
  borrower_id: string;
  title: string;
  file_name: string;
  page_count: number;
  doc_type: string | null;
  doc_type_source: string;
  period_end: string | null;
  received_date: string | null;
  effective_date: string | null;
  source: string;
  status: string;
  meta: { external_id?: string };
}

export interface DocumentDetail extends DocumentRow {
  facts_by_page: Record<string, number>;
}

export type Box = [number, number, number, number];

export interface PageFigure {
  fact: FactSummary;
  boxes: Box[];
  quote: string | null;
  label_text: string | null;
  method: 'cited' | 'located';
}

export interface PageFigures {
  document_id: string;
  page_number: number;
  width: number;
  height: number;
  has_text: boolean;
  figures: PageFigure[];
}

/* ── Source of a fact ─────────────────────────────────────────────────── */

export interface SourcePage {
  document_id: string | null;
  document_title: string;
  doc_type: string | null;
  page: number | null;
  page_count: number | null;
  width?: number | null;
  height?: number | null;
  boxes: Box[];
  quote: string | null;
  label_text?: string | null;
  /** `cited`: the fact stores this page. `located`: code found the figure on the page at read time. */
  method: 'cited' | 'located';
  comparative_column?: boolean;
  scale?: number | null;
  section?: string | null;
}

export interface CalcInputApi {
  key: string;
  name: string;
  sign: number;
  value: string | null;
  fact_id: string | null;
  period_end: string | null;
  months: number | null;
}

export interface CalcStep {
  n: number;
  op: string;
  name: string;
  key: string | null;
  basis: string | null;
  value: string | null;
  period_end: string | null;
  inputs: CalcInputApi[];
  unit: Unit;
  final: boolean;
}

export interface Addback {
  name: string;
  raw: string;
  applied: string;
  capped: boolean;
  cap_type?: string | null;
  cap_value?: string | null;
  cap_limit?: string | null;
}

export interface Calculation {
  id: string;
  formula_key: string;
  formula_version: string;
  engine_version: string;
  period_end: string;
  error: string | null;
  created_at: string;
  created_by_type: string;
  created_by_id: string;
  terms_version: { id: string; version: number; status: string; effective_from: string } | null;
  expression: string | null;
  inputs: CalcInputApi[];
  steps: CalcStep[];
  addbacks: Addback[];
  outputs: Record<string, string | boolean | null>;
  facts: FactsById;
  produced?: FactSummary[];
}

export interface FactHistoryEntry {
  id: string;
  value: string;
  unit: Unit;
  kind: FactKind;
  status: FactStatusApi;
  created_at: string;
  reason: string | null;
  relation: 'later' | 'this' | 'earlier';
  entered_by: string | null;
}

export interface FactSource {
  fact: FactSummary & {
    quote: string | null;
    label_text: string | null;
    scale_as_reported: number | null;
    connector: string | null;
    record_ref: string | null;
    as_of: string | null;
    entered_by: string | null;
    reason: string | null;
    note: string | null;
    confirmed_by: string | null;
    confirmed_at: string | null;
    created_at: string;
    agent_run_id: string | null;
    /** `term`: a covenant threshold read from approved terms. `headroom`: a covenant's headroom. Absent on older APIs. */
    provenance?: 'term' | 'headroom' | null;
  };
  borrower: { id: string; name: string; code: string };
  page: SourcePage | null;
  calculation: Calculation | null;
  clause: SourcePage | null;
  /** For a threshold fact: the covenant's term in force and its schedule. Absent on older APIs. */
  term?: TermSource | null;
  /** For a headroom fact: the arithmetic from the value and the threshold. Absent on older APIs. */
  headroom?: HeadroomSource | null;
  /** For a headroom fact: the calculation of the ratio the headroom is measured on. */
  ratio_calculation_id?: string | null;
  history: FactHistoryEntry[];
}

export type CovenantOperator = '>=' | '<=' | '>' | '<';

export interface TermStep {
  /** The date the step takes effect (ISO). */
  from: string;
  value: string;
  in_force: boolean;
}

export interface TermSource {
  covenant_name: string;
  operator: CovenantOperator;
  unit: Unit;
  threshold_in_force: string;
  base_threshold: string;
  steps: TermStep[];
  terms_version: { id: string; version: number; status: string; effective_from: string };
  clause: SourcePage | null;
}

export interface HeadroomSource {
  operator: CovenantOperator;
  value: string;
  value_fact_id: string | null;
  threshold: string;
  threshold_fact_id: string | null;
  headroom: string;
  /** Headroom over the threshold's size, as a fraction. */
  headroom_pct: string | null;
  /** For example "(threshold − value) ÷ |threshold|". */
  formula: string;
  ratio_calculation_id?: string | null;
}

/* ── Spread ───────────────────────────────────────────────────────────── */

export interface SpreadCell {
  fact_id: string;
  value: string;
  kind: FactKind;
  status: FactStatusApi;
  usable: boolean;
}

export interface SpreadLineApi {
  key: string;
  label: string;
  statement: 'is' | 'bs' | 'cf' | 'sup' | string;
  computed: boolean;
  cells: Record<string, SpreadCell>;
}

export interface Spread {
  template: string;
  periods: Array<{ period_end: string; months: number }>;
  lines: SpreadLineApi[];
}

/* ── Covenants ────────────────────────────────────────────────────────── */

export interface ItemRef {
  id: string;
  item_type: string;
  status: 'open' | 'decided' | 'dismissed';
  severity: Severity;
  decision: string | null;
  title: string;
}

export interface CovenantTestRow {
  id: string;
  borrower_id: string;
  facility_id: string;
  cycle_id: string | null;
  covenant_id: string;
  covenant_name: string;
  period_end: string;
  calc_run_id: string | null;
  value_fact_id: string | null;
  threshold_fact_id: string | null;
  headroom_fact_id: string | null;
  reported_fact_id: string | null;
  value: string | null;
  threshold: string | null;
  operator: '>=' | '<=' | null;
  unit: Unit;
  passed: boolean | null;
  reported_value: string | null;
  reported_in_compliance: boolean | null;
  outcome: CovenantOutcome;
  error: string | null;
  loan_name: string | null;
  terms_version: { id: string; version: number; status: string } | null;
  citation: { section: string | null; page: number | null; quote: string | null; document_id: string | null } | null;
  work_item: ItemRef | null;
}

export interface BorrowerCovenants {
  tests: CovenantTestRow[];
  facts: FactsById;
}

/* ── Terms ────────────────────────────────────────────────────────────── */

export interface Citation {
  section: string | null;
  page: number | null;
  quote: string | null;
  field: string | null;
  document_id: string | null;
  document_title: string | null;
}

export interface TermsVersionRow {
  id: string;
  version: number;
  status: 'proposed' | 'approved' | 'superseded' | 'rejected';
  effective_from: string;
  effective_to: string | null;
  in_force: boolean;
  prepared_by_type: string;
  prepared_by_id: string;
  approved_by_name: string | null;
  approved_at: string | null;
  warnings: unknown[] | null;
  source_documents: Array<{ reference: string; id: string | null; title: string; doc_type: string | null }>;
  covenants: Array<{
    id: string;
    name: string;
    archetype: string | null;
    operator: '>=' | '<=' | null;
    threshold: string | null;
    unit: Unit;
    steps: Array<Record<string, string>>;
    measurement: { basis?: string; frequency?: string } | null;
    citations: Array<Citation | null>;
  }>;
  addbacks: Array<Record<string, unknown>>;
  reporting_requirements: Array<{ id: string; document_type: string; frequency?: string | null; due_days?: number | null; quality?: string | null; citation: Citation | null }>;
  has_borrowing_base: boolean;
}

export interface LoanTerms extends Loan {
  terms_versions: TermsVersionRow[];
}

/* ── Borrowing base ───────────────────────────────────────────────────── */

export interface BorrowingBaseLine {
  line: string;
  label: string;
  depth: number;
  computed: string | null;
  certificate: string | null;
  difference: string | null;
  status: 'match' | 'mismatch' | null;
}

export interface BorrowingBaseReview {
  id: string;
  facility_id: string;
  period_end: string;
  calc_run_id: string | null;
  availability: string | null;
  over_advance: string | null;
  outcome: 'agrees' | 'mismatch' | 'over_advance' | 'cannot_compute';
  loan_name: string | null;
  lines: BorrowingBaseLine[];
  certificate_document: { id: string; title: string; page_count: number } | null;
  availability_fact: FactSummary | null;
  work_item: ItemRef | null;
  customers: Array<Record<string, string | null>>;
}

/* ── Signals, calendar, ledger, agents ────────────────────────────────── */

export interface SignalRow {
  id: string;
  borrower_id: string;
  borrower_name: string | null;
  cycle_id: string | null;
  period_end: string;
  rule_id: string;
  rule_version: string;
  severity: Severity;
  basis: Record<string, unknown>;
  explanation: { text?: string; agent_run_id?: string } | null;
  rank: number | null;
  status: 'open' | 'acknowledged' | 'closed';
  created_at: string;
}

export interface Obligation {
  id: string;
  borrower_id: string;
  borrower_name: string | null;
  facility_id: string;
  requirement_id: string;
  document_type: string;
  period_end: string;
  due_date: string;
  /** `untracked`: a past period the book holds no document for; it was never chased here, so it is not shown as overdue. */
  status: 'due' | 'received' | 'overdue' | 'waived' | 'untracked';
  received_document_id: string | null;
  received_date: string | null;
  days_late: number | null;
}

export interface CalendarResponse {
  as_of: string;
  obligations: Obligation[];
}

export interface LedgerEvent {
  seq: number;
  id: string;
  ts: string;
  actor_type: 'user' | 'agent' | 'system';
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  hash: string;
  prev_hash?: string;
  note: string | null;
  actor_name?: string | null;
  document_title?: string | null;
}

export interface LedgerVerification {
  ok: boolean;
  events_checked: number;
  problem: string | null;
}

export interface AgentRunRow {
  id: string;
  agent_name: string;
  agent_version: string;
  model: string;
  served_model: string | null;
  task: string;
  borrower_id: string | null;
  borrower_name: string | null;
  /** The borrower's code, for a link to its page. Null for a run about no one borrower. */
  borrower_code?: string | null;
  cycle_id: string | null;
  period_end: string | null;
  status: 'running' | 'completed' | 'abstained' | 'failed' | 'refused';
  steps_count: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  llm_mode: string;
  guardrail_notes: GuardrailNote[];
  error: string | null;
  created_at: string;
  finished_at: string | null;
  /** Start to finish, worked out by the server. Null until the run has finished. */
  duration_ms?: number | null;
}

export interface AgentStepRow {
  id: string;
  n: number;
  kind: 'model' | 'tool' | 'guardrail' | 'note' | string;
  name: string;
  input_summary: string;
  output_summary: string;
  detail: Record<string, unknown>;
  refused: boolean;
  duration_ms: number | null;
}

export interface AgentRunDetail extends AgentRunRow {
  scope: Record<string, unknown>;
  raw_output: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  steps: AgentStepRow[];
}

export interface AgentSpec {
  id: string;
  name: string;
  version: string;
  model: string;
  effort: string;
  max_steps: number;
  tools: string[];
  prompt_sha256: string;
  spec_sha256: string;
  purpose: string;
  active: boolean;
  runs: number;
  created_at: string;
}

/* ── Governance ───────────────────────────────────────────────────────── */

/** The permission table as the code holds it (`/governance/roles`). */
export interface RolesAndPermissions {
  roles: Array<{ id: string; label: string; people: number }>;
  permissions: Array<{ id: string; label: string; group: string; second_person: boolean }>;
  /** Role id to the permission ids it holds. */
  grants: Record<string, string[]>;
  second_person: { rule: string; applies_to: Array<{ permission: string; what: string; detail: string; source: string }> };
}

export interface PolicyRule {
  id: string;
  rule: string;
  /** The value in force, already in words or with its unit. */
  setting: string;
  effect: string;
  /** The module that enforces the rule. */
  source: string;
  kind: 'text' | 'ident';
  /** "verified": code checked the rule just now and it holds. "attention": it checked and it does not. */
  state: 'verified' | 'attention' | null;
}

export interface PolicySignalRule {
  id: string;
  name: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  trigger: string;
}

export interface PolicyAgent {
  name: string;
  version: string;
  purpose: string;
  model: string;
  effort: string;
  max_steps: number;
  tools: string[];
  prompt_sha256: string;
}

/** The rules code applies without a model (`/governance/policy`). */
export interface PolicyRegister {
  sections: Array<{ id: string; title: string; summary: string; rules: PolicyRule[] }>;
  signal_rules: { version: string; rules: PolicySignalRule[] };
  agents: PolicyAgent[];
}

/* ── Reviews ──────────────────────────────────────────────────────────── */

export interface ReviewSheetRow {
  id: string;
  borrower_id: string;
  borrower_name: string;
  cycle_id: string;
  meeting_id: string | null;
  status: 'draft' | 'ready' | 'reviewed' | 'released';
  period_end: string;
  approved_by: string | null;
  approved_at: string | null;
}

export interface CommentaryRow {
  id: string;
  section: string;
  version: number;
  body: string;
  rendered: string;
  fact_ids: string[];
  author_type: 'agent' | 'user';
  author_name: string | null;
  written_by_agent: boolean;
  status: 'draft' | 'approved' | 'superseded';
  agent_run_id: string | null;
  created_at: string;
}

export interface SheetFact {
  value: string;
  unit: Unit;
  kind: FactKind;
  status: FactStatusApi;
  key: string;
  period_end: string;
}

export interface ReviewSheetDetail extends ReviewSheetRow {
  approved_by_name: string | null;
  content: {
    period_end?: string;
    risk_rating?: number | null;
    loans?: Array<{ loan: string; type: string; has_borrowing_base: boolean }>;
    metrics?: Array<{ metric: string; label: string; current: string | null; year_earlier: string | null }>;
    covenants?: Array<{
      covenant: string;
      operator: string | null;
      outcome: CovenantOutcome;
      value: string | null;
      threshold: string | null;
      headroom_pct: string | null;
      reported: string | null;
      certificate_claims_compliance: boolean | null;
    }>;
    signals?: Array<{ signal_id: string; rule: string; severity: Severity; explanation: string | null }>;
    collateral?: { as_of: string; outcome: string; availability: string | null; mismatched_lines: string[] } | null;
    work_items?: Array<{ type: string; severity: Severity; title: string; status: string; decision: string | null }>;
    fact_labels?: Record<string, string>;
  };
  changes_since_last: unknown[];
  facts: Record<string, SheetFact>;
  commentary: CommentaryRow[];
  warnings?: string[];
}

export interface Meeting {
  id: string;
  title: string;
  meeting_date: string;
  period_end: string;
  phase: 'before' | 'during' | 'after' | 'closed';
  chair_id: string | null;
  notes: string;
  sheets: Array<{ id: string; borrower_name: string; status: string }>;
}

export interface ActionRow {
  id: string;
  borrower_id: string;
  borrower_name: string | null;
  cycle_id: string | null;
  meeting_id: string | null;
  work_item_id: string | null;
  title: string;
  detail: string;
  owner_id: string | null;
  owner_name: string | null;
  due_date: string | null;
  status: 'open' | 'in_progress' | 'done' | 'cancelled';
  escalated: boolean;
  closing_note: string | null;
  overdue: boolean;
}

/* ── Repairing figures ────────────────────────────────────────────────── */

/** One figure the spread held for a person (`evidence.cells` of a held-spread work item). */
export interface HeldCell {
  key: string;
  page: number | null;
  printed_figure: string | null;
  /** The label the reader reported. */
  printed_label: string | null;
  /** The row's label as code read it from the page. */
  row_label: string | null;
  reason: string;
  detail: string | null;
  /** Absent when nothing could be stored: the figure has to be entered. */
  fact_id: string | null;
  /**
   * When the row's printed label names another line of the template: that line's key, and the
   * value the printed figure has when filed under it (lines differ in the sign they store).
   * Worked out by the API; the workspace never derives either.
   */
  reads_as: { key: string; value: string } | null;
}

/** One failed footing check (`evidence.checks` of a spread that does not foot). */
export interface FootingProblem {
  key: string | null;
  code: string;
  message: string;
  /** For a check that compared two amounts: what the lines give, what it was compared with, and the gap. */
  detail?: { actual?: string; expected?: string; difference?: string } | null;
}

/** What the spread needs to be finished later (`evidence.spread`). */
export interface SpreadContext {
  document_id: string | null;
  period_end: string;
  months: number;
  scale?: number;
}

export interface CovenantRetest {
  facility_id: string;
  period_end: string;
  covenant_id: string;
  before: string | null;
  after: string;
}

/** What code did to the results that used a figure after it was corrected, rejected or keyed. */
export interface Recalculation {
  retired: number;
  totals: null | 'recalculated' | 'does_not_foot' | 'not_recalculated';
  metrics: Array<{ key: string; period_end: string; fact_id: string | null }>;
  covenants: CovenantRetest[];
}

/** A fact as the confirm, correct, reject and key routes return it. */
export interface StoredFact {
  id: string;
  borrower_id: string;
  key: string;
  value: string;
  unit: Unit;
  kind: FactKind;
  status: FactStatusApi;
  period_end: string;
  months: number;
}

export interface FactChange extends StoredFact {
  recalculation: Recalculation;
}

/**
 * Domain types as the API will return them (design spec sections 6, 8 and 10).
 * Values are decimal strings: the workspace formats them, it never does float arithmetic on them.
 */

export type Unit = 'usd' | 'ratio' | 'days' | 'pct' | 'count' | 'months';
export type FactStatus = 'proposed' | 'verified' | 'confirmed' | 'rejected' | 'superseded';
/** `seeded` marks a fact loaded from the synthetic book's ground truth: demonstration data only, never extracted. */
export type ProvenanceKind = 'extracted' | 'calculated' | 'system' | 'manual' | 'seeded';

export interface ExtractedProvenance {
  kind: 'extracted';
  documentId: string;
  documentTitle: string;
  page: number;
  /** Text as printed on the page; the figure itself is `printed`. */
  quote: string;
  /** The figure exactly as printed, for highlighting inside the quote. */
  printed: string;
  labelText: string;
  scaleAsReported: 1 | 1000;
  agentRunId: string;
}

export interface CalcInput {
  name: string;
  factId: string;
  /** How the input enters the formula, shown before the name: '+', '−', '÷' or ''. */
  op?: string;
}

export interface CalculatedProvenance {
  kind: 'calculated';
  calcId: string;
  formulaKey: string;
  formulaVersion: string;
  expression: string;
  inputs: CalcInput[];
  termsVersion?: string;
}

export interface SystemProvenance {
  kind: 'system';
  connector: string;
  recordRef: string;
  asOf: string;
}

export interface ManualProvenance {
  kind: 'manual';
  enteredBy: string;
  enteredAt: string;
  reason: string;
}

export interface SeededProvenance {
  kind: 'seeded';
  note: string;
}

export type Provenance = ExtractedProvenance | CalculatedProvenance | SystemProvenance | ManualProvenance | SeededProvenance;

export interface Fact {
  id: string;
  key: string;
  label: string;
  /** Decimal string in base units (whole dollars, ratio, percentage points, days). */
  value: string;
  unit: Unit;
  periodLabel: string;
  status: FactStatus;
  provenance: Provenance;
}

export type FactMap = Record<string, Fact>;

/* ── Monitoring cycle ─────────────────────────────────────────────────── */

export type StageId =
  | 'awaiting_package'
  | 'intake'
  | 'spreading'
  | 'covenant_testing'
  | 'borrowing_base'
  | 'signals'
  | 'review_prep'
  | 'in_review'
  | 'actions_open'
  | 'closed';

export type StageStatus = 'pending' | 'running' | 'needs_person' | 'done' | 'skipped' | 'failed';

export interface CycleStage {
  id: StageId;
  label: string;
  status: StageStatus;
  detail?: string;
}

/* ── Covenants ────────────────────────────────────────────────────────── */

export type CovenantOutcome = 'compliant' | 'compliant_variance' | 'breach' | 'breach_reported_compliant' | 'cannot_test';

export interface CovenantTest {
  id: string;
  name: string;
  basis: string;
  operator: '>=' | '<=';
  calculatedFactId: string | null;
  thresholdFactId: string;
  headroomFactId: string | null;
  certificateFactId: string | null;
  outcome: CovenantOutcome;
  citation: string;
}

/* ── Agents ───────────────────────────────────────────────────────────── */

export type RecommendationKind = 'resolve' | 'escalate' | 'request' | 'abstain' | 'draft';

export interface GuardrailNote {
  layer: string;
  check: string;
  action: 'passed' | 'changed' | 'blocked';
  detail: string;
}

export interface AgentRecommendation {
  agent: string;
  kind: RecommendationKind;
  /** Headline in the agent's voice, for example "Recommends escalate". */
  headline: string;
  /** Agent text. Figures appear only as {{fact:<id>}} references; code renders them. */
  body: string;
  runId: string;
  writtenAt: string;
  approved: boolean;
  guardrailNotes: GuardrailNote[];
}

/* ── Work items ───────────────────────────────────────────────────────── */

export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type WorkItemType =
  | 'intake.missing_document'
  | 'intake.unclassified'
  | 'spread.value_unverified'
  | 'spread.does_not_foot'
  | 'spread.restatement'
  | 'spread.image_only'
  | 'document.spreadsheet_unreadable'
  | 'terms.approval_needed'
  | 'terms.unapproved_amendment'
  | 'covenant.breach'
  | 'reading.review'
  | 'covenant.reported_mismatch'
  | 'covenant.reported_breach_unconfirmed'
  | 'fact.correction_changed_outcome'
  | 'covenant.cannot_test'
  | 'bb.over_advance'
  | 'bb.certificate_mismatch'
  | 'signal.high'
  | 'review.commentary_approval'
  | 'package.release';

export type WorkItemGroup = 'covenant' | 'spreading' | 'terms' | 'borrowing_base' | 'intake' | 'signals' | 'review';

export interface EvidenceLink {
  kind: ProvenanceKind;
  label: string;
  detail?: string;
  /** Identifier shown in the mono face (fact id, calculation id, record reference). */
  ref?: string;
  href?: string;
}

export interface Decision {
  id: string;
  label: string;
  /** Exactly one decision per item is primary: the one clear next action. */
  primary?: boolean;
  needsReason?: boolean;
}

export interface WorkItem {
  id: string;
  type: WorkItemType;
  severity: Severity;
  borrowerId: string;
  borrowerName: string;
  stage: StageId;
  periodLabel: string;
  /** One specific question, in plain words. */
  question: string;
  /** Short form of the question for a table row. */
  summary: string;
  evidence: EvidenceLink[];
  decisions: Decision[];
  requiresSecondPerson: boolean;
  /** ISO date. */
  dueDate: string;
  recommendation: AgentRecommendation | null;
}

/* ── Spread ───────────────────────────────────────────────────────────── */

export interface SpreadPeriod {
  id: string;
  label: string;
  periodEnd: string;
  months: 3 | 6 | 9 | 12;
  quality: 'audited' | 'reviewed' | 'compiled' | 'internal';
  spreadStatus: 'confirmed' | 'verified';
  documentId: string;
}

export interface SpreadLine {
  key: string;
  label: string;
  computed: boolean;
  /** 'subtotal' draws a single rule above; 'total' adds a double rule below. */
  emphasis?: 'subtotal' | 'total';
  /** Fact id per period id. Null means not measured. */
  cells: Record<string, string | null>;
  /** Stated-total fact id per period id, for computed lines the statement prints. */
  stated?: Record<string, string | null>;
}

export interface SpreadSection {
  id: 'is' | 'bs';
  title: string;
  basis: string;
  groups: Array<{ title?: string; lines: SpreadLine[] }>;
}

export interface FootingCheck {
  id: string;
  label: string;
  detail: string;
  result: 'pass' | 'attention' | 'info';
  resultLabel: string;
}

export interface SourcePage {
  documentId: string;
  documentTitle: string;
  page: number;
  heading: string;
  subheading: string;
  columnHeads: string[];
  rows: Array<{ label: string; values: string[]; factIds: Array<string | null>; strong?: boolean; indent?: boolean; gapBefore?: boolean }>;
}
